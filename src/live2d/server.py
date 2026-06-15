"""
Live2D 本地 HTTP 服务器。

基于 Python http.server，在后台线程运行。
为 Live2DViewer 提供模型文件和页面资源。
支持多模型路由 + 通用加载器 + 模型列表 API。
"""

import json
import logging
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from src.core.paths import BUNDLE_DIR, USER_DIR

logger = logging.getLogger(__name__)

_LIVE2D_DIR = BUNDLE_DIR / "data" / "live2d"
_PAGES_DIR = _LIVE2D_DIR / "pages"
_STATIC_DIR = _LIVE2D_DIR / "static"

# 内置模型定义：URL路径 → (页面文件名, 模型目录名)
BUILT_IN_MODELS = {
    "firefly": ("firefly.html", "Firefly"),
}


def _collect_models() -> dict:
    """
    收集所有可用模型（内置 + 用户导入）。
    返回 {route: (page_file, model_dir)} 格式。
    """
    from src.core.config import ConfigManager

    models = dict(BUILT_IN_MODELS)

    try:
        config = ConfigManager()
        custom_data = config.read("custom_live2d")
        for entry in custom_data.get("models", []):
            mid = entry.get("id", "")
            model_dir = entry.get("model_dir", mid)

            # 对于用户导入的模型，需要通过通用加载器 viewer.html
            if entry.get("source_type") == "user_imported":
                # 注册到 /viewer?model=<name> 路径，而不是短路由
                # 这里我们保留通过 viewer.html?model=<name> 加载
                pass

            # 用户导入模型也加入模型列表（供 /model-list API 使用）
            models[mid] = ("/viewer?model=" + model_dir, model_dir)
    except Exception as e:
        logger.debug("读取 custom_live2d 失败: %s", e)

    return models


class _Live2DHandler(SimpleHTTPRequestHandler):
    """自定义请求处理器，路由到页面和静态文件。"""

    def do_GET(self):
        # ── 模型列表 API ────────────────────────────────────
        if self.path == "/model-list":
            self._serve_model_list()
            return

        # ── 通用加载器 ──────────────────────────────────────
        if self.path.startswith("/viewer"):
            self._serve_page("viewer.html")
            return

        # ── 匹配内置模型页面路由 ────────────────────────────
        for route, (page, _) in BUILT_IN_MODELS.items():
            if self.path == f"/{route}":
                self._serve_page(page)
                return

        # ── 其他路径解析为静态文件 ──────────────────────────
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

    def _serve_model_list(self) -> None:
        """返回可用模型列表 JSON。"""
        from src.core.config import ConfigManager

        config = ConfigManager()
        live2d_cfg = config.read("live2d")
        custom_data = config.read("custom_live2d")
        current = live2d_cfg.get("current_model", "firefly")

        models = []

        # 内置模型
        for mid, (page_file, model_dir) in BUILT_IN_MODELS.items():
            models.append({
                "id": mid,
                "name": self._get_builtin_name(mid),
                "type": "bundled",
            })

        # 用户导入模型
        for entry in custom_data.get("models", []):
            if entry.get("source_type") != "bundled":
                models.append({
                    "id": entry.get("id", ""),
                    "name": entry.get("name", entry.get("id", "")),
                    "type": "user_imported",
                })

        response = {"models": models, "current": current}
        data = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _get_builtin_name(model_id: str) -> str:
        names = {"firefly": "流萤"}
        return names.get(model_id, model_id)

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
