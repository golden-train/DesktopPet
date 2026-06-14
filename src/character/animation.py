"""
动作动画系统。

管理角色动作图片的加载和循环播放。
支持循环动作（Standby/mention/sleep/discomfort）和一次性动作（eat/love/left/right）。
支持多角色切换：通过 ModelRegistry 按 ID 切换显示不同角色的动作帧。
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.core.config import ConfigManager
from src.core.paths import BUNDLE_DIR, USER_DIR

logger = logging.getLogger(__name__)

# ── 动作分类 ────────────────────────────────────────────────
LOOP_ACTIONS = {"Standby", "mention", "sleep", "discomfort", "left", "right", "up", "down"}
ONE_SHOT_ACTIONS = {"eat", "love"}
WALK_ACTIONS = {"left", "right", "up", "down"}
ALL_ACTIONS = LOOP_ACTIONS | ONE_SHOT_ACTIONS | WALK_ACTIONS

# 图片文件扩展名
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class AnimationManager(QObject):
    """管理角色动作图片的加载和循环播放。"""

    # 一次性动作播放完毕时发出，参数为动作名
    action_finished = Signal(str)

    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config

        # 动作名 → 目录绝对路径（从 action_pictures.json 或模型注册表加载）
        self._action_dirs: dict[str, str] = {}

        # 动作名 → 排序后的图片绝对路径列表（缓存）
        self._cache: dict[str, list[str]] = {}

        # 当前状态
        self._current_action: str = "Standby"
        self._frame_index: int = 0

        # 当前激活的角色 ID
        self._active_model_id: str = "firefly"

        self._load_config()

    # ── 公开接口 ────────────────────────────────────────────

    def load_action(self, key: str) -> list[str]:
        """获取指定动作的图片路径列表（缓存命中则直接返回）。"""
        if key not in self._action_dirs:
            logger.warning("未知动作: %s", key)
            return []

        if key not in self._cache:
            raw = self._action_dirs[key]
            dir_path = Path(raw)
            if not dir_path.is_absolute():
                dir_path = BUNDLE_DIR / raw

            if not dir_path.is_dir():
                logger.warning("动作目录不存在: %s", dir_path)
                self._cache[key] = []
            else:
                files = sorted(
                    str(p) for p in dir_path.iterdir()
                    if p.suffix.lower() in _IMAGE_EXTS
                )
                self._cache[key] = files
                logger.debug("动作 '%s' 加载了 %d 帧", key, len(files))

        return self._cache[key]

    def switch_action(self, key: str) -> None:
        """切换到指定动作，帧指针归零。"""
        if key not in self._action_dirs:
            logger.warning("尝试切换到未知动作: %s", key)
            return
        if key == self._current_action:
            return  # 已在目标动作上
        # 确保图片已缓存
        self.load_action(key)
        self._current_action = key
        self._frame_index = 0
        logger.info("切换动作: %s", key)

    def switch_model(self, model_info: dict) -> None:
        """
        切换到指定角色模型。

        参数:
            model_info: 模型注册信息字典，必须有 ``id``、``dir``、``source_type``、``actions`` 等字段。
        """
        model_id = model_info.get("id", "")
        if model_id == self._active_model_id and model_id != "firefly":
            logger.debug("已在目标模型: %s", model_id)
            return

        self._apply_model_dirs(model_info)
        self._active_model_id = model_id
        # 停用当前动作，切回 Standby
        self._current_action = "Standby"
        self._frame_index = 0
        self.switch_action("Standby")
        logger.info("切换角色模型: %s (%s)", model_id, model_info.get("name", ""))

    def has_model_action(self, action: str) -> bool:
        """检查当前角色模型是否支持指定动作。"""
        return action in self._action_dirs

    @property
    def active_model_id(self) -> str:
        return self._active_model_id

    def get_next_image(self, key: Optional[str] = None) -> Optional[str]:
        """
        返回当前动作的下一帧图片路径。

        - 循环动作：播完从头再播
        - 一次性动作：播完发出 action_finished 信号并回到 Standby
        - 当前无帧时返回 None
        """
        action = key if key else self._current_action
        frames = self.load_action(action)
        if not frames:
            return None

        # 帧指针超出 → 处理循环/结束
        if self._frame_index >= len(frames):
            if action in LOOP_ACTIONS:
                self._frame_index = 0
            else:
                # 一次性动作播放完毕
                self.action_finished.emit(action)
                self.switch_action("Standby")
                return self.get_next_image()

        frame = frames[self._frame_index]
        self._frame_index += 1
        return frame

    def available_actions(self) -> list[str]:
        """返回所有可用动作名。"""
        return list(self._action_dirs.keys())

    @property
    def current_action(self) -> str:
        return self._current_action

    # ── 内部方法 ────────────────────────────────────────────

    def _load_config(self) -> None:
        """从 action_pictures.json 读取动作目录配置，并应用当前模型（如果不是默认）。"""
        data = self._config.read("action_pictures")
        # 先加载为绝对路径
        from src.core.paths import BUNDLE_DIR
        self._action_dirs = {k: str(BUNDLE_DIR / v["path"]) for k, v in data.items()}
        logger.info("已加载 %d 个动作配置", len(self._action_dirs))

        # 检查当前模型是否非默认
        current_model = self._config.get("main", "current_model", "firefly")
        if current_model and current_model != "firefly":
            try:
                from src.model.registry import ModelRegistry
                model_info = ModelRegistry.get_by_id(self._config, current_model)
                if model_info:
                    self._apply_model_dirs(model_info)
                    self._active_model_id = current_model
                    logger.info("已应用当前模型: %s", current_model)
            except Exception as e:
                logger.debug("无法应用模型 '%s': %s", current_model, e)

        # 预加载默认动作
        self.load_action("Standby")

    def _apply_model_dirs(self, model_info: dict) -> None:
        """根据模型信息更新所有动作目录路径。"""
        base = BUNDLE_DIR if model_info.get("source_type") == "bundled" else USER_DIR
        model_dir = base / model_info["dir"]

        new_dirs: dict[str, str] = {}
        actions_dir = model_dir / "actions"
        if actions_dir.is_dir():
            for subdir in sorted(actions_dir.iterdir()):
                if subdir.is_dir():
                    new_dirs[subdir.name] = str(subdir.resolve())

        if not new_dirs:
            logger.warning("模型 '%s' 没有动作目录: %s", model_info.get("id", ""), actions_dir)
            return

        self._action_dirs = new_dirs
        self._cache.clear()
        logger.info("模型 '%s' 动作目录已更新 (%d 个动作)",
                     model_info.get("id", ""), len(new_dirs))
