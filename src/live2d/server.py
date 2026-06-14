"""
Live2D 本地 HTTP 服务器。

基于 Python http.server，在后台线程运行。
为 Live2DViewer 提供模型文件和页面资源。
支持多模型路由。
"""

import logging
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from src.core.paths import BUNDLE_DIR

logger = logging.getLogger(__name__)

_LIVE2D_DIR = BUNDLE_DIR / "data" / "live2d"
_PAGES_DIR = _LIVE2D_DIR / "pages"
_STATIC_DIR = _LIVE2D_DIR / "static"

# 可用模型定义：URL路径 → (页面文件名, 模型目录名)
AVAILABLE_MODELS = {
    "firefly": ("firefly.html", "Firefly"),
    "chun": ("chun.html", "chun"),
}


class _Live2DHandler(SimpleHTTPRequestHandler):
    """自定义请求处理器，路由到页面和静态文件。"""

    def do_GET(self):
        # 匹配模型页面路由
        for route, (page, _) in AVAILABLE_MODELS.items():
            if self.path == f"/{route}":
                self._serve_page(page)
                return
        # 其他路径解析为静态文件
        self._serve_static()

    def _serve_page(self, filename: str) -> None:
        """返回 HTML 页面。"""
        path = _PAGES_DIR / filename
        if not path.exists():
            self.send_error(404, f"Page {filename} not found")
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            logger.error("读取页面失败: %s", e)
            self.send_error(500)

    def _serve_static(self) -> None:
        """从 static/ 目录提供静态文件。"""
        self.path = "/static" + self.path
        super().do_GET()

    def log_message(self, fmt, *args):
        logger.debug("Live2D HTTP: %s", fmt % args)


class Live2DServer:
    """本地 HTTP 服务器，在后台线程中提供 Live2D 资源。"""

    def __init__(self, port: int = 8687):
        self.port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        """启动服务器（非阻塞，后台线程）。"""
        try:
            self._original_cwd = Path.cwd()
            import os
            os.chdir(str(_LIVE2D_DIR))

            self._server = HTTPServer(("127.0.0.1", self.port), _Live2DHandler)
            self._thread = threading.Thread(
                target=self._server.serve_forever, daemon=True
            )
            self._thread.start()
            logger.info("Live2D 服务器已启动: http://127.0.0.1:%d", self.port)
            return True
        except Exception as e:
            logger.error("Live2D 服务器启动失败: %s", e)
            import os
            os.chdir(str(self._original_cwd))
            return False

    def stop(self) -> None:
        """停止服务器。"""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            logger.info("Live2D 服务器已停止")
        if hasattr(self, "_original_cwd"):
            import os
            os.chdir(str(self._original_cwd))

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
