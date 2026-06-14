"""
自由行走控制。

通过 QTimer 定时控制窗口在屏幕上移动，
支持 X/Y 轴，碰撞屏幕边缘自动反向。
作为基础服务，可被任意角色模型调用。
"""

import logging
from typing import Optional, Callable

from PySide6.QtCore import QTimer, QPoint
from PySide6.QtWidgets import QMainWindow

logger = logging.getLogger(__name__)

# 所有行走方向
DIRECTIONS = ("left", "right", "up", "down")


class WalkingController:
    """控制窗口在屏幕上自由行走。

    设计为通用服务，可被任意角色模型（Live2D/动画帧等）调用。
    外部只需传入窗口对象和动作切换回调即可。
    """

    def __init__(self, window: QMainWindow,
                 switch_action_cb: Optional[Callable[[str], None]] = None):
        """
        :param window: 要移动的窗口
        :param switch_action_cb: 切换动作的回调，参数为方向名 (left/right/up/down)
        """
        self.window = window
        self._switch_action = switch_action_cb
        self._direction: str = "left"
        self._is_walking: bool = False
        self._timer: Optional[QTimer] = None
        self.speed: int = 6          # 每帧像素
        self.interval_ms: int = 50   # 帧间隔（毫秒）

    @property
    def is_walking(self) -> bool:
        return self._is_walking

    @property
    def direction(self) -> str:
        return self._direction

    def toggle(self) -> None:
        """切换行走/停止。"""
        if self._is_walking:
            self.stop()
        else:
            self.start()

    def start(self, direction: str = "") -> None:
        """开始行走。

        :param direction: left / right / up / down，默认延续上次方向
        """
        if direction:
            self._direction = direction
        if self._timer is None:
            self._timer = QTimer(self.window)
            self._timer.setInterval(self.interval_ms)
            self._timer.timeout.connect(self._move)
        self._is_walking = True
        self._timer.start()
        self._update_action()
        logger.info("行走开始: %s", self._direction)

    def stop(self) -> None:
        """停止行走。"""
        self._is_walking = False
        if self._timer:
            self._timer.stop()
        if self._switch_action:
            self._switch_action("Standby")
        logger.info("行走停止")

    def set_speed(self, pixels: int, interval_ms: int = 50) -> None:
        """设置行走速度。"""
        self.speed = pixels
        self.interval_ms = interval_ms
        if self._timer:
            self._timer.setInterval(interval_ms)

    def _move(self) -> None:
        """每 tick：按方向移动窗口，碰撞边缘换向。"""
        if not self.window:
            return

        current = self.window.pos()
        screen = self.window.screen().availableGeometry() if self.window.screen() else None
        if not screen:
            return

        win_w = self.window.width()
        win_h = self.window.height()
        dx, dy = 0, 0

        if self._direction == "right":
            dx = self.speed
        elif self._direction == "left":
            dx = -self.speed
        elif self._direction == "down":
            dy = self.speed
        elif self._direction == "up":
            dy = -self.speed

        new_x = current.x() + dx
        new_y = current.y() + dy

        # 碰撞检测 + 换向
        changed = False
        if new_x < 0:
            new_x = 0
            self._direction = "right"
            changed = True
        elif new_x + win_w > screen.right():
            new_x = screen.right() - win_w
            self._direction = "left"
            changed = True

        if new_y < 0:
            new_y = 0
            self._direction = "down" if self._direction in ("up",) else self._direction
            changed = True
        elif new_y + win_h > screen.bottom():
            new_y = screen.bottom() - win_h
            self._direction = "up" if self._direction in ("down",) else self._direction
            changed = True

        self.window.move(new_x, new_y)

        if changed:
            self._update_action()

    def _update_action(self) -> None:
        """通知外部切换行走动作。"""
        if self._switch_action:
            self._switch_action(self._direction)
