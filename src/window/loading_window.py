"""
启动加载窗口。

应用初始化时显示的加载动画窗口，初始化完成后自动关闭。
"""

import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar

logger = logging.getLogger(__name__)

_LOADING_DURATION = 2000  # 加载最大时长


class LoadingWindow(QWidget):
    """启动加载窗口——显示进度条和加载状态。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(280, 120)

        # 居中
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen:
            self.move(
                screen.center().x() - self.width() // 2,
                screen.center().y() - self.height() // 2,
            )

        # ── UI ──────────────────────────────────────────────
        self.setStyleSheet("""
            LoadingWindow {
                background: rgba(25, 25, 35, 230);
                border: 1px solid #555;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        self._title = QLabel("桌面宠物", self)
        self._title.setAlignment(Qt.AlignCenter)
        tf = QFont()
        tf.setPointSize(16)
        tf.setBold(True)
        self._title.setFont(tf)
        self._title.setStyleSheet("color: #e0e0e0; background: transparent;")
        layout.addWidget(self._title)

        self._status = QLabel("正在加载…", self)
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        layout.addWidget(self._status)

        self._progress = QProgressBar(self)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar {
                background: #333; border: none; border-radius: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3a6ea5, stop:1 #5ba3e6
                );
                border-radius: 2px;
            }
        """)
        layout.addWidget(self._progress)

        # ── 进度动画 ────────────────────────────────────────
        self._progress_value = 0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        """模拟进度条推进。"""
        self._progress_value += 2
        if self._progress_value >= 98:
            self._progress_value = 98
            self._timer.stop()
        self._progress.setValue(self._progress_value)

    def set_status(self, text: str) -> None:
        """更新状态文字。"""
        self._status.setText(text)

    def finish(self) -> None:
        """加载完成，关闭窗口。"""
        self._progress.setValue(100)
        self.set_status("加载完成")
        # 稍后自动关闭
        QTimer.singleShot(300, self.close)
