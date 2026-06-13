"""
主窗口——角色显示窗口。

透明无边框置顶窗口，通过 QLabel 显示角色动画。
支持鼠标拖拽、点击交互、右键菜单。
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtGui import QAction, QPixmap, QMouseEvent, QContextMenuEvent
from PySide6.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout, QMenu

from src.character.animation import AnimationManager

logger = logging.getLogger(__name__)

# 动画帧间隔（毫秒）
_FRAME_INTERVAL_MS = 200


class MainWindow(QMainWindow):
    """桌面角色显示主窗口。"""

    # 鼠标交互信号：参数为动作名
    action_triggered = Signal(str)
    # 用户点击"设置..."时发出
    settings_requested = Signal()

    def __init__(self, animation: AnimationManager, parent=None):
        super().__init__(parent)
        self._animation = animation

        # 窗口状态
        self._drag_position: Optional[QPoint] = None
        self._scaling: int = 0

        # ── UI ──────────────────────────────────────────────
        self._setup_window()
        self._setup_ui()
        self._setup_menu()

        # ── 动画定时器 ──────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(_FRAME_INTERVAL_MS)

        # ── 初始帧 ──────────────────────────────────────────
        self._update_image()

    # ── 窗口设置 ────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle("桌面宠物")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

    def _setup_ui(self) -> None:
        central = QWidget(self)
        central.setAttribute(Qt.WA_TranslucentBackground)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(central)
        self._label.setAttribute(Qt.WA_TranslucentBackground)
        self._label.setScaledContents(True)
        layout.addWidget(self._label)

        self.setCentralWidget(central)

    def _setup_menu(self) -> None:
        self._menu = QMenu(self)
        self._menu.setStyleSheet("""
            QMenu { background: #2d2d2d; color: #eee; border: 1px solid #555; }
            QMenu::item:selected { background: #4a4a4a; }
        """)

        self._act_toggle_ai = QAction("暂停 AI（开发中）", self)
        self._act_toggle_ai.setEnabled(False)
        self._menu.addAction(self._act_toggle_ai)

        self._menu.addSeparator()

        self._act_settings = QAction("设置...", self)
        self._act_settings.triggered.connect(self.settings_requested.emit)
        self._menu.addAction(self._act_settings)

        self._act_exit = QAction("退出", self)
        self._act_exit.triggered.connect(self.close)
        self._menu.addAction(self._act_exit)

    # ── 动画驱动 ────────────────────────────────────────────

    def _tick(self) -> None:
        """定时器回调：取下一帧并更新显示。"""
        self._update_image()

    def _update_image(self) -> None:
        """获取当前动作下一帧，更新 QLabel。"""
        path = self._animation.get_next_image()
        if not path:
            self._label.clear()
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            logger.warning("无法加载图片: %s", path)
            self._label.clear()
            return
        # 缩放
        if self._scaling > 0:
            w = pixmap.width() * (1 + self._scaling)
            h = pixmap.height() * (1 + self._scaling)
            pixmap = pixmap.scaled(int(w), int(h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._label.setPixmap(pixmap)
        self._label.resize(pixmap.size())
        self.resize(pixmap.size())

    def switch_action(self, key: str) -> None:
        """外部调用：切换动作。"""
        self._animation.switch_action(key)
        self._update_image()

    # ── 缩放 ────────────────────────────────────────────────

    def set_scaling(self, value: int) -> None:
        """设置缩放等级（0/2/4/8）。"""
        self._scaling = value
        self._update_image()

    # ── 鼠标事件（窗口拖拽 + 交互；文档 §4.2）──────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPosition().toPoint()
            # 上半区 → love / 下半区 → mention
            action = "love" if event.position().y() < self.height() / 2 else "mention"
            self.action_triggered.emit(action)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_position = None
            self.action_triggered.emit("Standby")
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_position is not None:
            delta = event.globalPosition().toPoint() - self._drag_position
            self.move(self.pos() + delta)
            self._drag_position = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.action_triggered.emit("love")
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """右键弹出菜单。"""
        self._menu.exec(event.globalPos())

    # ── 生命周期 ────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._timer.stop()
        logger.info("主窗口关闭")
        super().closeEvent(event)
