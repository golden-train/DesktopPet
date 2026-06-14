"""
Live2D 模型导入器。

导入用户的自定义 Live2D 模型到 data/live2d/static/live2d-model/ 目录，
并在 custom_live2d.json 注册表中创建记录。
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.config import ConfigManager
from src.core.paths import LIVE2D_DIR

logger = logging.getLogger(__name__)

# Live2D 模型存放根目录
LIVE2D_MODEL_DIR = LIVE2D_DIR / "static" / "live2d-model"
# 缩略图缓存目录
THUMBNAILS_DIR = LIVE2D_DIR / "thumbnails"

# 支持的 Live2D 模型配置扩展名
_MODEL3_EXTS = {".model3.json"}
_SUPPORTED_TEXTURE_EXTS = {".png", ".jpg", ".jpeg"}
_SUPPORTED_MOTION_EXTS = {".motion3.json"}


class Live2DModelImporter:
    """导入 Live2D 模型到应用数据目录。"""

    @staticmethod
    def validate(source_dir: str) -> dict:
        """
        校验 Live2D 模型目录。

        检查:
        - 是否存在 ``.model3.json`` 文件（有且只有一个）
        - 引用的贴图文件是否存在
        - 引用的动作 ``.motion3.json`` 是否存在

        返回::
            {
                "valid": True | False,
                "errors": ["..."],
                "warnings": ["未找到 voice 目录"],
                "model3_file": "Firefly.model3.json",
                "textures": 4,
                "motions": 8,
                "expressions": 3
            }
        """
        source = Path(source_dir)
        report: dict = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "model3_file": "",
            "textures": 0,
            "motions": 0,
            "expressions": 0,
        }

        if not source.is_dir():
            report["valid"] = False
            report["errors"].append(f"目录不存在: {source_dir}")
            return report

        # ── 查找 .model3.json ────────────────────────────────
        model3_files = sorted(
            p for p in source.rglob("*")
            if p.suffix.lower() == ".json" and "model3" in p.suffixes
        )
        # 更精确：找文件名包含 model3 的 json
        model3_files = [
            p for p in source.iterdir()
            if p.is_file() and p.suffix.lower() == ".json" and "model3" in p.name.lower()
        ]

        if not model3_files:
            report["valid"] = False
            report["errors"].append("未找到 .model3.json 文件")
            return report

        if len(model3_files) > 1:
            report["warnings"].append(
                f"找到多个 .model3.json: {', '.join(p.name for p in model3_files)}，将使用第一个"
            )

        model3_path = model3_files[0]
        report["model3_file"] = model3_path.name

        # ── 解析 model3.json 检查资源 ────────────────────────
        try:
            with open(model3_path, "r", encoding="utf-8") as f:
                model3_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            report["valid"] = False
            report["errors"].append(f"解析 {model3_path.name} 失败: {e}")
            return report

        # 检查贴图
        textures = model3_data.get("FileReferences", {}).get("Textures", [])
        report["textures"] = len(textures)
        missing_textures = []
        for tex_path in textures:
            tex_file = source / tex_path
            if not tex_file.exists():
                missing_textures.append(tex_path)
        if missing_textures:
            report["errors"].append(f"缺少贴图: {', '.join(missing_textures)}")

        # 检查动作
        motions = model3_data.get("FileReferences", {}).get("Motions", {})
        motion_count = sum(len(v) for v in motions.values())
        report["motions"] = motion_count

        # 检查表情
        expressions = model3_data.get("FileReferences", {}).get("Expressions", [])
        report["expressions"] = len(expressions)

        # 检查 voice 目录
        voice_dir = source / "voice"
        if not voice_dir.is_dir():
            report["warnings"].append("未找到 voice/ 目录（语音可选）")

        # 检查是否有物理/用户数据
        physics = model3_data.get("FileReferences", {}).get("Physics", "")
        if physics:
            phys_path = source / physics
            if not phys_path.exists():
                report["warnings"].append(f"物理文件不存在: {physics}")

        report["valid"] = len(report["errors"]) == 0
        logger.info(
            "Live2D 校验: valid=%s, model3=%s, textures=%d, motions=%d",
            report["valid"], report["model3_file"], report["textures"], report["motions"],
        )
        return report

    @staticmethod
    def import_model(source_dir: str, config: ConfigManager) -> str:
        """
        导入 Live2D 模型。

        步骤:
            1. 校验
            2. 生成唯一 ID（使用目录名或模型名）
            3. 复制整个模型目录到 ``LIVE2D_MODEL_DIR/{id}/``
            4. 注册到 ``custom_live2d.json``
            5. 返回 model_id

        参数:
            source_dir: 用户选择的 Live2D 模型目录
            config: ConfigManager 实例

        返回:
            str: 导入后的模型 ID

        异常:
            ValueError: 校验失败
            IOError: 文件操作失败
        """
        source = Path(source_dir)

        # 1. 校验
        report = Live2DModelImporter.validate(source_dir)
        if not report["valid"]:
            error_msg = "Live2D 导入校验失败:\n" + "\n".join(report["errors"])
            logger.error(error_msg)
            raise ValueError(error_msg, report)

        # 2. 生成唯一 ID
        model3_name = Path(report["model3_file"]).stem
        # 移除 .model3 后缀
        base_name = model3_name.replace(".model3", "").replace(".Model3", "")
        # 清理特殊字符
        import re
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', base_name)
        if not safe_id:
            safe_id = f"live2d_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_id = safe_id

        # 防止 ID 冲突：如果已存在则追加数字
        data = config.read("custom_live2d")
        existing_ids = {m.get("id") for m in data.get("models", [])}
        if target_id in existing_ids:
            counter = 1
            while f"{target_id}_{counter}" in existing_ids:
                counter += 1
            target_id = f"{target_id}_{counter}"

        # 3. 复制目录
        target_dir = LIVE2D_MODEL_DIR / target_id
        if target_dir.exists():
            shutil.rmtree(target_dir)
            logger.info("已清理旧 Live2D 目录: %s", target_dir)

        try:
            shutil.copytree(source, target_dir, dirs_exist_ok=True)
            logger.info("Live2D 模型已复制: %s → %s", source, target_dir)
        except (OSError, shutil.Error) as e:
            logger.error("复制 Live2D 模型失败: %s", e)
            # 清理
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            raise IOError(f"复制 Live2D 模型失败: {e}") from e

        # 4. 注册
        entry = {
            "id": target_id,
            "name": base_name,
            "source_type": "user_imported",
            "model_dir": target_id,
            "model_file": report["model3_file"],
            "thumbnail": "",
            "imported_at": datetime.now().isoformat(timespec="seconds"),
        }

        models = data.get("models", [])
        models.append(entry)
        config.write("custom_live2d", {"models": models})
        logger.info("Live2D 模型导入完成: %s (%s)", target_id, base_name)
        return target_id

    @staticmethod
    def remove_model(model_id: str, config: ConfigManager) -> bool:
        """
        从注册表中移除 Live2D 模型并删除资源文件。

        系统内置模型不可删除。
        """
        data = config.read("custom_live2d")
        models = data.get("models", [])

        model_info = next((m for m in models if m.get("id") == model_id), None)
        if not model_info:
            logger.warning("删除失败: Live2D 模型 '%s' 不存在", model_id)
            return False

        if model_info.get("source_type") == "bundled":
            logger.warning("删除失败: 系统内置 Live2D 模型 '%s' 不可删除", model_id)
            return False

        # 从注册表移除
        filtered = [m for m in models if m.get("id") != model_id]
        config.write("custom_live2d", {"models": filtered})

        # 删除资源文件
        model_dir = LIVE2D_MODEL_DIR / model_id
        if model_dir.exists():
            shutil.rmtree(model_dir)
            logger.info("已删除 Live2D 目录: %s", model_dir)

        logger.info("Live2D 模型已删除: %s", model_id)
        return True
