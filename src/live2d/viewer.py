"""
Live2D 查看器窗口。

透明无边框置顶窗口，通过 QWebEngineView 加载 Live2D 模型。
支持右键菜单切换模型和退出。
"""

import logging

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QAction, QContextMenuEvent
from PySide6.QtWidgets import QMainWindow, QMenu
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.live2d.server import Live2DServer

logger = logging.getLogger(__name__)

# 可用模型
AVAILABLE_MODELS = {
    "流萤": "firefly",
    "椿": "chun",
}


class Live2DViewer(QMainWindow):
    """透明无边框窗口，通过 QWebEngineView 加载 Live2D 模型。"""

    closed = Signal()

    def __init__(self, server: Live2DServer, model: str = "firefly"):
        super().__init__()
        self._server = server
        self._current_model = model

        self.setWindowTitle("Live2D")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setMinimumSize(300, 400)
        self.resize(360, 480)

        # ── WebView ─────────────────────────────────────────
        self._view = QWebEngineView(self)
        self._view.setAttribute(Qt.WA_TranslucentBackground)
        self._view.page().setBackgroundColor(Qt.transparent)
        self.setCentralWidget(self._view)

        # ── 右键菜单 ────────────────────────────────────────
        self._setup_menu()

        # ── 加载模型 ────────────────────────────────────────
        self.load_model(model)

    def _setup_menu(self) -> None:
        self._menu = QMenu(self)
        self._menu.setStyleSheet("""
            QMenu {
                background: #2a2a2a; color: #e0e0e0;
                border: 1px solid #444; border-radius: 8px;
                padding: 4px;
            }
            QMenu::item { padding: 6px 28px 6px 16px; border-radius: 4px; }
            QMenu::item:selected { background: #3a6ea5; color: #fff; }
            QMenu::separator { height: 1px; background: #444; margin: 4px 12px; }
        """)

        # 刷新
        self._act_refresh = QAction("刷新", self)
        self._act_refresh.triggered.connect(self._refresh)
        self._menu.addAction(self._act_refresh)

        self._menu.addSeparator()

        # 切换模型子菜单
        self._model_menu = self._menu.addMenu("切换模型")
        self._model_actions = {}
        for name, key in AVAILABLE_MODELS.items():
            act = QAction(name, self)
            act.setCheckable(True)
            act.setChecked(key == self._current_model)
            act.triggered.connect(lambda checked, k=key: self.load_model(k))
            self._model_menu.addAction(act)
            self._model_actions[key] = act

        self._menu.addSeparator()

        self._act_exit = QAction("关闭", self)
        self._act_exit.triggered.connect(self.close)
        self._menu.addAction(self._act_exit)

    def load_model(self, model_name: str) -> None:
        """切换模型并刷新页面。"""
        if not self._server.is_running:
            logger.warning("Live2D 服务器未运行")
            return

        self._current_model = model_name
        url = QUrl(f"http://127.0.0.1:{self._server.port}/{model_name}")
        self._view.setUrl(url)
        self.setWindowTitle(f"Live2D - {model_name}")

        # 更新菜单选中状态
        for key, act in self._model_actions.items():
            act.setChecked(key == model_name)

        logger.info("Live2D 切换到模型: %s", model_name)

    def _refresh(self) -> None:
        """刷新当前页面。"""
        self._view.reload()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self._menu.exec(event.globalPos())

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)
