"""
动作动画系统。

管理角色动作图片的加载和循环播放。
支持循环动作（Standby/mention/sleep/discomfort）和一次性动作（eat/love/left/right）。
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from src.core.config import ConfigManager
from src.core.paths import ROOT_DIR

logger = logging.getLogger(__name__)

# ── 动作分类 ────────────────────────────────────────────────
LOOP_ACTIONS = {"Standby", "mention", "sleep", "discomfort"}
ONE_SHOT_ACTIONS = {"eat", "love"}
WALK_ACTIONS = {"left", "right"}
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

        # 动作名 → 目录相对路径（从 action_pictures.json 读取）
        self._action_dirs: dict[str, str] = {}

        # 动作名 → 排序后的图片绝对路径列表（缓存）
        self._cache: dict[str, list[str]] = {}

        # 当前状态
        self._current_action: str = "Standby"
        self._frame_index: int = 0

        self._load_config()

    # ── 公开接口 ────────────────────────────────────────────

    def load_action(self, key: str) -> list[str]:
        """获取指定动作的图片路径列表（缓存命中则直接返回）。"""
        if key not in self._action_dirs:
            logger.warning("未知动作: %s", key)
            return []

        if key not in self._cache:
            dir_path = ROOT_DIR / self._action_dirs[key]
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
        """从 action_pictures.json 读取动作目录配置。"""
        data = self._config.read("action_pictures")
        self._action_dirs = {k: v["path"] for k, v in data.items()}
        logger.info("已加载 %d 个动作配置", len(self._action_dirs))
        # 预加载默认动作
        self.load_action("Standby")
