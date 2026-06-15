"""
Live2D 查看器窗口。

支持动态模型列表：从 live2d.json 和 custom_live2d.json 加载所有已注册模型，
右键菜单「切换模型」动态列出所有可用模型。
"""

import logging

from PySide6.QtCore import Qt, QUrl, Signal, QPoint, QEvent
from PySide6.QtGui import QAction, QMouseEvent, QPainter, QColor, QCursor
from PySide6.QtWidgets import QMainWindow, QMenu, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings

from src.live2d.server import Live2DServer, BUILT_IN_MODELS

logger = logging.getLogger(__name__)

DRAG_BAR_H = 28


class _Live2DPage(QWebEnginePage):
    """自定义页面：JS 阻止默认菜单 + Qt 层拦截后备。"""
    def __init__(self, viewer: "Live2DViewer"):
        super().__init__(viewer)
        self._viewer = viewer
        # 页面加载后注入 JS（只 preventDefault，不阻止 Qt 事件）
        self.loadFinished.connect(lambda ok: ok and self.runJavaScript(
            "document.addEventListener('contextmenu', e => e.preventDefault())"
        ))

    def contextMenuEvent(self, event):
        """Qt 层拦截（仅当 JS 没成功时触发）。"""
        event.accept()
        self._viewer._show_context_menu()


class _DragBar(QWidget):
    """顶部半透明拖拽条。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(DRAG_BAR_H)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_pos: QPoint | None = None
        self._hovered = False

    def enterEvent(self, event):
        self._hovered = True; self.update()

    def leaveEvent(self, event):
        self._hovered = False; self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.window().move(self.window().pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        alpha = 30 if not self._hovered else 55
        painter.fillRect(self.rect(), QColor(0, 0, 0, alpha))
        painter.setPen(QColor(255, 255, 255, 20))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 80))
            cx = self.width() // 2
            for x in (cx - 8, cx, cx + 8):
                painter.drawEllipse(QPoint(x, self.height() // 2), 2, 2)


class Live2DViewer(QMainWindow):
    closed = Signal()

    def __init__(self, server: Live2DServer, model: str = "firefly"):
        super().__init__()
        self._server = server
        self._current_model = model

        self.setWindowTitle("Live2D")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setMinimumSize(300, 400)
        self.resize(360, 480)

        # WebView + 自定义页面（双重拦截右键）
        self._page = _Live2DPage(self)
        self._view = QWebEngineView(self)
        self._view.setPage(self._page)
        self._view.setAttribute(Qt.WA_TranslucentBackground)
        self._view.page().setBackgroundColor(Qt.transparent)
        self._view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )
        self.setCentralWidget(self._view)

        # 事件过滤器
        self._view.installEventFilter(self)
        self._page.installEventFilter(self)

        # 拖拽条
        self._drag_bar = _DragBar(self)
        self._drag_bar.raise_()

        self._setup_menu()
        self.load_model(model)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._drag_bar.setGeometry(0, 0, self.width(), DRAG_BAR_H)

    # ── 事件过滤器 ─────────────────────────────────────────

    def eventFilter(self, obj, event) -> bool:
        # 拦截右键菜单事件
        if event.type() == QEvent.Type.ContextMenu:
            self._show_context_menu()
            return True
        return super().eventFilter(obj, event)

    # ── 菜单 ────────────────────────────────────────────────

    def _setup_menu(self) -> None:
        self._menu = QMenu(self)
        self._menu.setStyleSheet("""
            QMenu { background: #2a2a2a; color: #e0e0e0;
                border: 1px solid #444; border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 6px 28px 6px 16px; border-radius: 4px; }
            QMenu::item:selected { background: #3a6ea5; color: #fff; }
            QMenu::separator { height: 1px; background: #444; margin: 4px 12px; }
        """)
        self._act_refresh = QAction("刷新", self)
        self._act_refresh.triggered.connect(self._refresh)
        self._menu.addAction(self._act_refresh)
        self._menu.addSeparator()

        # ── 动态模型菜单 ─────────────────────────────────────
        self._model_menu = self._menu.addMenu("切换模型")
        self._model_actions: dict[str, QAction] = {}
        self._refresh_model_menu()

        self._menu.addSeparator()
        self._act_exit = QAction("关闭", self)
        self._act_exit.triggered.connect(self.close)
        self._menu.addAction(self._act_exit)

    def _refresh_model_menu(self) -> None:
        """从注册表动态刷新模型列表菜单。"""
        self._model_menu.clear()
        self._model_actions.clear()

        models = self._collect_models()

        # 分组：系统模型 / 用户导入
        bundled_items = [m for m in models if m["type"] == "bundled"]
        user_items = [m for m in models if m["type"] == "user_imported"]

        for items, group_name in [(bundled_items, "系统模型"), (user_items, "用户导入")]:
            if items:
                if self._model_menu.actions():
                    self._model_menu.addSeparator()
                # QMenu 不支持分组标签，用不可用的 QAction 模拟
                label_act = QAction(f"— {group_name} —", self._model_menu)
                label_act.setEnabled(False)
                self._model_menu.addAction(label_act)

            for m in items:
                act = QAction(m["name"], self._model_menu)
                act.setCheckable(True)
                act.setChecked(m["id"] == self._current_model)
                act.triggered.connect(lambda checked, mid=m["id"]: self.load_model(mid))
                self._model_menu.addAction(act)
                self._model_actions[m["id"]] = act

    @staticmethod
    def _collect_models() -> list[dict]:
        """从配置文件收集所有可用 Live2D 模型。"""
        from src.core.config import ConfigManager

        config = ConfigManager()
        models = []

        # 内置模型
        for mid, (_, model_dir) in BUILT_IN_MODELS.items():
            names = {"firefly": "流萤"}
            models.append({
                "id": mid,
                "name": names.get(mid, mid),
                "type": "bundled",
                "model_dir": model_dir,
            })

        # 用户导入模型
        try:
            custom_data = config.read("custom_live2d")
            for entry in custom_data.get("models", []):
                if entry.get("source_type") == "user_imported":
                    models.append({
                        "id": entry.get("id", ""),
                        "name": entry.get("name", entry.get("id", "")),
                        "type": "user_imported",
                        "model_dir": entry.get("model_dir", entry.get("id", "")),
                    })
        except Exception as e:
            logger.debug("读取自定义 Live2D 模型失败: %s", e)

        return models

    def _show_context_menu(self) -> None:
        # 每次展示前刷新模型列表（确保最新）
        self._refresh_model_menu()
        self._menu.exec(QCursor.pos())

    # ── 模型 ────────────────────────────────────────────────

    def load_model(self, model_id: str) -> None:
        if not self._server.is_running:
            logger.warning("Live2D 服务器未运行"); return

        self._current_model = model_id

        # 确定 URL：内置模型用短路由，用户导入用通用加载器
        if model_id in BUILT_IN_MODELS:
            url_path = f"/{model_id}"
        else:
            # 查找 model_dir
            models = self._collect_models()
            model_info = next((m for m in models if m["id"] == model_id), None)
            model_dir = model_info["model_dir"] if model_info else model_id
            url_path = f"/viewer?model={model_dir}"

        url = QUrl(f"http://127.0.0.1:{self._server.port}{url_path}")
        self._view.setUrl(url)
        self.setWindowTitle(f"Live2D - {model_id}")

        for key, act in self._model_actions.items():
            act.setChecked(key == model_id)
        logger.info("Live2D 加载模型: %s", model_id)

    def _refresh(self) -> None:
        self._view.reload()

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)
