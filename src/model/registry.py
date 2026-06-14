"""
模型注册表管理器。

管理 custom_models.json 中注册的用户导入角色模型，
提供 CRUD + 默认模型切换能力。
"""

import logging
from copy import deepcopy
from typing import Any

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)

# 注册表文件名（不含 .json 扩展名，传给 ConfigManager）
_REGISTRY_NAME = "custom_models"


class ModelRegistry:
    """管理用户导入的所有角色模型注册信息。"""

    # ── 读取 ────────────────────────────────────────────────

    @staticmethod
    def load(config: ConfigManager) -> list[dict]:
        """
        从 ``custom_models.json`` 加载已注册模型列表。

        返回::
            [
                {
                    "id": "firefly",
                    "name": "流萤",
                    "source_type": "bundled",       # "bundled" | "user_imported"
                    "dir": "data/assets/images/firefly/",
                    "has_walking": True,
                    "voice_available": True,
                    "has_icon": True,
                    "actions": ["Standby", "mention", ...],
                    "registered_at": "2026-06-14T10:30:00"
                }
            ]
        """
        data = config.read(_REGISTRY_NAME)
        models: list[dict] = data.get("models", [])
        logger.debug("模型注册表加载: %d 个模型", len(models))
        return models

    @staticmethod
    def get_by_id(config: ConfigManager, model_id: str) -> dict | None:
        """根据 ID 查找已注册的模型信息，未找到返回 None。"""
        models = ModelRegistry.load(config)
        for m in models:
            if m["id"] == model_id:
                return m
        return None

    # ── 写入 ────────────────────────────────────────────────

    @staticmethod
    def register(config: ConfigManager, model_info: dict) -> None:
        """
        注册一个新模型到 ``custom_models.json``。

        ``model_info`` 必须包含:
            - ``id``: 唯一标识符
            - ``name``: 显示名称
            - ``dir``: 资源目录路径（相对应用根）

        如果 ``id`` 已存在则覆盖（更新）该条目。
        """
        model_info = deepcopy(model_info)
        data = config.read(_REGISTRY_NAME)
        models: list[dict] = data.get("models", [])

        # 查找并替换，或追加
        found = False
        for i, m in enumerate(models):
            if m["id"] == model_info["id"]:
                models[i] = model_info
                found = True
                logger.info("更新模型注册: %s (%s)", model_info["id"], model_info.get("name", ""))
                break

        if not found:
            models.append(model_info)
            logger.info("新增模型注册: %s (%s)", model_info["id"], model_info.get("name", ""))

        config.write(_REGISTRY_NAME, {"models": models})

    @staticmethod
    def unregister(config: ConfigManager, model_id: str) -> bool:
        """
        从注册表中移除指定模型。

        注意：仅移除注册记录，**不删除资源文件**。
        如需删除资源文件请调用 ``ModelImporter.remove_model()``。

        返回 True 表示成功移除，False 表示未找到该模型。
        """
        data = config.read(_REGISTRY_NAME)
        models: list[dict] = data.get("models", [])
        filtered = [m for m in models if m["id"] != model_id]

        if len(filtered) == len(models):
            logger.warning("取消注册失败: 模型 '%s' 不存在", model_id)
            return False

        config.write(_REGISTRY_NAME, {"models": filtered})
        logger.info("取消注册: %s", model_id)
        return True

    # ── 默认模型 ────────────────────────────────────────────

    @staticmethod
    def get_default(config: ConfigManager) -> str | None:
        """返回当前默认使用的模型 ID。"""
        return config.get("main", "current_model", None)

    @staticmethod
    def set_default(config: ConfigManager, model_id: str) -> None:
        """设置默认模型 ID（写入 ``main.json`` 的 ``current_model`` 字段）。"""
        config.set("main", "current_model", model_id)
        logger.info("设置默认模型: %s", model_id)

    # ── 路径解析 ────────────────────────────────────────────

    @staticmethod
    def resolve_dir(model_info: dict) -> str | None:
        """
        根据模型信息返回资源目录的**绝对路径**字符串。

        根据 ``source_type`` 区分:
        - ``"bundled"`` → 相对于 ``BUNDLE_DIR``
        - ``"user_imported"`` → 相对于 ``USER_DIR``
        """
        from src.core.paths import BUNDLE_DIR, USER_DIR

        raw_dir: str | None = model_info.get("dir")
        if not raw_dir:
            return None

        base = BUNDLE_DIR if model_info.get("source_type") == "bundled" else USER_DIR
        return str((base / raw_dir).resolve())
