"""
主窗口——角色显示窗口。

透明无边框置顶窗口，通过 QLabel 显示角色动画。
支持鼠标拖拽、点击交互、右键菜单。
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QAction, QPixmap, QMouseEvent, QContextMenuEvent,
    QPainter, QPainterPath, QColor,
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout, QMenu

from src.core.paths import FIREFLY_ICON_DIR

from src.character.animation import AnimationManager

logger = logging.getLogger(__name__)

# 动画帧间隔（毫秒）
_FRAME_INTERVAL_MS = 200


class MainWindow(QMainWindow):
    """桌面角色显示主窗口。"""

    # 鼠标交互信号：参数为动作名
    action_triggered = Signal(str)
    # 菜单信号
    settings_requested = Signal()
    chat_requested = Signal()
    live2d_requested = Signal()
    quit_requested = Signal()
    # 生命周期信号（用于语音触发等）
    shown = Signal()
    closing = Signal()

    def __init__(self, animation: AnimationManager, parent=None):
        super().__init__(parent)
        self._animation = animation

        # 窗口状态
        self._drag_position: Optional[QPoint] = None
        self._scaling: float = 1.0

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

        # 设置应用图标
        icon_path = FIREFLY_ICON_DIR / "icon.png"
        if icon_path.exists():
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self) -> None:
        central = QWidget(self)
        central.setAttribute(Qt.WA_TranslucentBackground)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(central)
        self._label.setAttribute(Qt.WA_TranslucentBackground)
        self._label.setScaledContents(True)

        # 角色阴影效果
        shadow = QGraphicsDropShadowEffect(self._label)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 120))
        self._label.setGraphicsEffect(shadow)

        layout.addWidget(self._label)

        self.setCentralWidget(central)

    def _setup_menu(self) -> None:
        self._menu = QMenu(self)
        self._menu.setStyleSheet("""
            QMenu {
                background: #2a2a2a; color: #e0e0e0;
                border: 1px solid #444; border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 28px 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected { background: #3a6ea5; color: #fff; }
            QMenu::separator {
                height: 1px; background: #444;
                margin: 4px 12px;
            }
        """)

        self._act_chat = QAction("打开聊天", self)
        self._act_chat.triggered.connect(self.chat_requested.emit)
        self._menu.addAction(self._act_chat)

        self._act_live2d = QAction("Live2D 查看器", self)
        self._act_live2d.triggered.connect(self.live2d_requested.emit)
        self._menu.addAction(self._act_live2d)

        self._menu.addSeparator()

        self._act_settings = QAction("设置...", self)
        self._act_settings.triggered.connect(self.settings_requested.emit)
        self._menu.addAction(self._act_settings)

        self._act_exit = QAction("退出", self)
        self._act_exit.triggered.connect(self.quit_requested.emit)
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
        # 缩放（self._scaling 为倍数，1.0=原始大小）
        if self._scaling != 1.0:
            w = pixmap.width() * self._scaling
            h = pixmap.height() * self._scaling
            pixmap = pixmap.scaled(int(w), int(h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._label.setPixmap(pixmap)
        self._label.resize(pixmap.size())
        self.resize(pixmap.size())

    def switch_action(self, key: str) -> None:
        """外部调用：切换动作。"""
        self._animation.switch_action(key)
        self._update_image()

    # ── 缩放 ────────────────────────────────────────────────

    def set_scaling(self, value: float) -> None:
        """设置缩放倍数（0.25=1/4, 0.5=1/2, 1=原始, 2=2倍...）。"""
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

    # ── 窗口移动动画 ────────────────────────────────────────

    def animate_to(self, target_x: int, target_y: int,
                   duration: int = 600) -> QPropertyAnimation:
        """平滑移动到指定坐标（单次动画）。返回动画对象，调用方需保持引用。"""
        self._walk_anim = QPropertyAnimation(self, b"pos")
        self._walk_anim.setDuration(duration)
        self._walk_anim.setStartValue(self.pos())
        self._walk_anim.setEndValue(QPoint(target_x, target_y))
        self._walk_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._walk_anim.start()
        # 行走时切换为 left/right 朝向
        dx = target_x - self.pos().x()
        if dx < -5:
            self.switch_action("left")
        elif dx > 5:
            self.switch_action("right")
        return self._walk_anim

    def follow_to(self, target_x: int, target_y: int) -> None:
        """闪现到目标位置（聊天窗拖动时跟随）。"""
        self.move(target_x, target_y)

    # ── 生命周期 ────────────────────────────────────────────

    def showEvent(self, event) -> None:
        """窗口显示时发出信号（用于触发启动语音）。"""
        super().showEvent(event)
        self.shown.emit()

    def closeEvent(self, event) -> None:
        """用户点击 X 时隐藏到托盘，触发关闭语音。"""
        self.closing.emit()
        self.hide()
        event.ignore()
