"""
Live2D 本地 HTTP 服务器。

基于 Python http.server，在后台线程运行。
为 Live2DViewer 提供模型文件和页面资源。
"""

import logging
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from src.core.paths import BUNDLE_DIR

logger = logging.getLogger(__name__)

_LIVE2D_DIR = BUNDLE_DIR / "data" / "live2d"
_TEMPLATES_DIR = _LIVE2D_DIR / "templates"
_STATIC_DIR = _LIVE2D_DIR / "static"


class _Live2DHandler(SimpleHTTPRequestHandler):
    """自定义请求处理器，路由到对应的模板和静态文件。"""

    def do_GET(self):
        if self.path == "/firefly":
            self._serve_template("firefly.html")
        elif self.path == "/chun":
            self._serve_template("chun.html")
        else:
            # 其他路径从 static/ 目录提供
            self.path = "/static" + self.path
            super().do_GET()

    def _serve_template(self, filename: str) -> None:
        """返回 HTML 模板。"""
        path = _TEMPLATES_DIR / filename
        if not path.exists():
            self.send_error(404, f"Template {filename} not found")
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
            logger.error("读取模板失败: %s", e)
            self.send_error(500)

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
            # 切换工作目录到 static 目录，使 SimpleHTTPRequestHandler 能正确提供静态文件
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
            # 恢复工作目录
            import os
            os.chdir(str(self._original_cwd))
            return False

    def stop(self) -> None:
        """停止服务器。"""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            logger.info("Live2D 服务器已停止")
        # 恢复工作目录
        if hasattr(self, "_original_cwd"):
            import os
            os.chdir(str(self._original_cwd))

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
