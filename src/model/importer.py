"""
模型导入器。

将用户指定的自定义角色模型目录复制到应用数据目录，
并在 ``custom_models.json`` 注册表中创建记录。
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.config import ConfigManager
from src.model.registry import ModelRegistry
from src.model.validator import ModelValidator

logger = logging.getLogger(__name__)

# ── 目标路径常量（用户可写目录） ───────────────────────────
# 导入后的图片存放路径: USER_DIR/data/assets/images/custom/<id>/
CUSTOM_IMAGES_DIR = Path("data") / "assets" / "images" / "custom"
# 导入后的音频存放路径: USER_DIR/data/audio/custom/<id>/
CUSTOM_AUDIO_DIR = Path("data") / "audio" / "custom"


class ModelImporter:
    """
    将用户指定的模型目录复制到应用数据目录，
    并在注册表中创建记录。
    """

    @staticmethod
    def import_model(
        source_dir: str,
        target_id: str,
        config: ConfigManager,
        *,
        display_name: Optional[str] = None,
    ) -> dict:
        """
        导入模型。

        步骤:
            1. 调用 ``ModelValidator.validate(source_dir)`` 校验
            2. 校验失败 → 抛出 ``ValueError``（携带校验报告）
            3. 清理已存在的同名目标目录（覆盖）
            4. 复制所有图片到 ``CUSTOM_IMAGES_DIR/{target_id}/actions/``
            5. 复制所有音频到 ``CUSTOM_AUDIO_DIR/{target_id}/voice/``
            6. 复制缩略图到 ``CUSTOM_IMAGES_DIR/{target_id}/icon/``
            7. 在注册表中创建记录
            8. 返回注册记录

        参数:
            source_dir: 用户选择的源模型目录
            target_id:  目标标识符（字母、数字、下划线、短横线）
            config:     ConfigManager 实例
            display_name: 显示名称（默认取 target_id）

        返回:
            dict: 注册记录

        异常:
            ValueError: 校验失败或 target_id 不合法
            IOError: 磁盘空间不足或文件操作失败
        """
        source = Path(source_dir)

        # ── 1. 校验 ├─────────────────────────────────────────
        report = ModelValidator.validate(source_dir)
        if not report["valid"]:
            error_msg = "模型导入校验失败:\n" + "\n".join(report["errors"])
            logger.error(error_msg)
            raise ValueError(error_msg, report)

        # ── 2. 校验 target_id ────────────────────────────────
        ModelImporter._validate_id(target_id)

        # ── 3. 准备目标目录路径 ───────────────────────────────
        from src.core.paths import USER_DIR

        target_images_dir = USER_DIR / CUSTOM_IMAGES_DIR / target_id
        target_audio_dir = USER_DIR / CUSTOM_AUDIO_DIR / target_id
        target_icon_dir = target_images_dir / "icon"

        # ── 4. 清理已有目录（覆盖导入） ───────────────────────
        if target_images_dir.exists():
            shutil.rmtree(target_images_dir)
            logger.info("已清理旧目录: %s", target_images_dir)
        if target_audio_dir.exists():
            shutil.rmtree(target_audio_dir)

        # ── 5. 复制资源 ──────────────────────────────────────
        try:
            # 图片
            actions_source = source / "actions"
            if actions_source.is_dir():
                ModelImporter._copy_with_progress(
                    actions_source,
                    target_images_dir / "actions",
                    "图片",
                )

            # 音频
            voice_source = source / "voice"
            if voice_source.is_dir():
                ModelImporter._copy_with_progress(
                    voice_source,
                    target_audio_dir / "voice",
                    "音频",
                )

            # 缩略图
            icon_source = source / "icon"
            if icon_source.is_dir():
                shutil.copytree(icon_source, target_icon_dir, dirs_exist_ok=True)

        except (OSError, shutil.Error) as e:
            logger.error("导入时文件操作失败: %s", e)
            # 清理已复制的残留文件
            ModelImporter._cleanup_failed(target_images_dir, target_audio_dir)
            raise IOError(f"导入时文件操作失败: {e}") from e

        # ── 6. 构建注册记录 ──────────────────────────────────
        name = display_name or target_id
        actions_found = report.get("actions_found", [])
        has_walking = report.get("has_walking", False)
        voice_available = report.get("voice_available", False)
        has_icon = icon_source.is_dir() if (icon_source := source / "icon").exists() else False

        # 构建 dir 字段（相对于 USER_DIR）
        model_dir_relative = str(CUSTOM_IMAGES_DIR / target_id)

        model_info = {
            "id": target_id,
            "name": name,
            "source_type": "user_imported",
            "dir": model_dir_relative,
            "has_walking": has_walking,
            "voice_available": voice_available,
            "has_icon": has_icon,
            "actions": actions_found,
            "registered_at": datetime.now().isoformat(timespec="seconds"),
        }

        # 如果源目录有 model.json，读取其中额外的描述信息
        model_json = source / "model.json"
        if model_json.is_file():
            import json
            try:
                with open(model_json, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("description"):
                    model_info["description"] = meta["description"]
                if meta.get("author"):
                    model_info["author"] = meta["author"]
                if meta.get("version"):
                    model_info["version"] = meta["version"]
            except (json.JSONDecodeError, OSError):
                pass  # 忽略，已有基本 info

        # ── 7. 注册 ──────────────────────────────────────────
        ModelRegistry.register(config, model_info)
        logger.info("模型导入完成: %s (%s)", target_id, name)
        return model_info

    @staticmethod
    def remove_model(model_id: str, config: ConfigManager) -> bool:
        """
        从注册表中移除模型 **并删除资源文件**。

        安全保护:
        - 系统内置模型（source_type == "bundled"）不允许删除
        - 如果当前正在使用此模型，不允许删除

        返回 True 表示成功，False 表示不允许删除（bundled 或当前正在使用）。
        """
        models = ModelRegistry.load(config)

        # 查找模型
        model_info = next((m for m in models if m["id"] == model_id), None)
        if model_info is None:
            logger.warning("删除失败: 模型 '%s' 不存在", model_id)
            return False

        # 禁止删除系统内置模型
        if model_info.get("source_type") == "bundled":
            logger.warning("删除失败: 系统内置模型 '%s' 不可删除", model_id)
            return False

        # 禁止删除当前正在使用的模型
        current = ModelRegistry.get_default(config)
        if current == model_id:
            logger.warning("删除失败: 模型 '%s' 正在使用中", model_id)
            return False

        # 从注册表移除
        ModelRegistry.unregister(config, model_id)

        # 删除资源文件
        from src.core.paths import USER_DIR

        images_dir = USER_DIR / CUSTOM_IMAGES_DIR / model_id
        audio_dir = USER_DIR / CUSTOM_AUDIO_DIR / model_id

        for d in [images_dir, audio_dir]:
            if d.exists():
                shutil.rmtree(d)
                logger.info("已删除资源目录: %s", d)

        logger.info("模型已彻底删除: %s", model_id)
        return True

    # ── 内部方法 ────────────────────────────────────────────

    @staticmethod
    def _validate_id(target_id: str) -> None:
        """校验模型 ID 合法性：只允许字母、数字、下划线、短横线。"""
        if not target_id or not target_id.strip():
            raise ValueError("模型 ID 不能为空")
        import re
        if not re.match(r'^[a-zA-Z0-9_\-]+$', target_id):
            raise ValueError(
                f"模型 ID 只能包含字母、数字、下划线和短横线: {target_id!r}"
            )

    @staticmethod
    def _copy_with_progress(src: Path, dst: Path, label: str) -> int:
        """复制目录树并返回复制的文件数。"""
        dst.mkdir(parents=True, exist_ok=True)
        count = 0
        for item in src.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(src)
                target = dst / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                count += 1
        logger.debug("已复制 %d 个%s文件: %s → %s", count, label, src, dst)
        return count

    @staticmethod
    def _cleanup_failed(*paths: Path) -> None:
        """导入失败时清理已创建的目录。"""
        for p in paths:
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
                logger.debug("已清理失败残留: %s", p)
