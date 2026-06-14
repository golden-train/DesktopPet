"""
弹出消息窗。

右下角弹出的消息气泡，显示头像 + 文字，数秒后自动关闭。
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton,
)

from src.core.paths import FIREFLY_ICON_DIR

logger = logging.getLogger(__name__)

_POPUP_DURATION = 5000
_ANIM_DURATION = 300


class PopupWindow(QWidget):
    """右下角弹出的消息气泡，显示头像 + 文字，自动关闭。"""

    def __init__(self, text: str, icon_path: Optional[str] = None,
                 duration_ms: int = _POPUP_DURATION, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setFixedSize(320, 80)

        # ── UI ──────────────────────────────────────────────
        self.setStyleSheet("""
            PopupWindow {
                background: rgba(30, 30, 40, 220);
                border: 1px solid #555;
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # 头像
        self._icon = QLabel(self)
        self._icon.setFixedSize(50, 50)
        icon_path = icon_path or (FIREFLY_ICON_DIR / "icon.png")
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            self._icon.setPixmap(
                pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        self._icon.setStyleSheet("border-radius: 25px;")
        layout.addWidget(self._icon)

        # 文字
        self._label = QLabel(text, self)
        self._label.setWordWrap(True)
        self._label.setStyleSheet("color: #e0e0e0; font-size: 12px; background: transparent;")
        layout.addWidget(self._label, 1)

        # 关闭按钮
        self._close_btn = QPushButton("×", self)
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #888;
                border: none; font-size: 16px;
            }
            QPushButton:hover { color: #fff; }
        """)
        self._close_btn.clicked.connect(self._close_now)
        layout.addWidget(self._close_btn)

        # ── 定时关闭 ────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._close_now)
        self._timer.start(duration_ms)

        # ── 动画弹出 ────────────────────────────────────────
        self._position_at_bottom_right()

    def _position_at_bottom_right(self) -> None:
        """定位到屏幕右下角（避开任务栏）。"""
        screen = self.screen().availableGeometry() if self.screen() else None
        if not screen:
            return
        start_x = screen.right() - self.width()
        start_y = screen.bottom()
        target_y = screen.bottom() - self.height() - 10
        self.move(start_x, start_y)
        self.show()

        # 弹出动画
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(_ANIM_DURATION)
        self._slide_anim.setStartValue(QPoint(start_x, start_y))
        self._slide_anim.setEndValue(QPoint(start_x, target_y))
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.start()

    def _close_now(self) -> None:
        """立即关闭。"""
        self._timer.stop()
        self.close()

    def mouseDoubleClickEvent(self, event) -> None:
        """双击关闭。"""
        self._close_now()
