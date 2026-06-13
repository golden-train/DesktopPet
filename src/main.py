"""
DesktopPet 应用入口。

启动流程：
  1. 确保数据目录存在
  2. 初始化 QApplication
  3. 初始化 ConfigManager
  4. 验证核心配置可读写
  5. 进入事件循环

后续阶段会逐步加入 VoiceService、AnimationManager、MainWindow 等模块。
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

# 确保项目根目录在 sys.path 中，支持直接 python src/main.py 启动
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.core.paths import ensure_dirs
from src.core.config import ConfigManager

logger = logging.getLogger(__name__)


class _ColoredFormatter(logging.Formatter):
    """按日志等级着色的 Formatter（ANSI 颜色码）。"""

    _COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",    # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[1;31m", # 红 + 加粗
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        color = self._COLORS.get(record.levelname, self._RESET)
        return f"{color}{formatted}{self._RESET}"


class DesktopPetApplication:
    """应用主控制器，负责组装所有模块并连接信号。"""

    def __init__(self):
        # 1. 确保数据目录存在
        ensure_dirs()

        # 2. Qt 应用
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("DesktopPet")
        self.app.setApplicationDisplayName("桌面宠物")

        # 3. 配置管理器
        self.config = ConfigManager()

        # 4. 验证核心配置
        self._verify_config()

        logger.info("DesktopPet 基础设施初始化完成")

    def _verify_config(self) -> None:
        """验证关键配置是否存在，若不存在则用默认值创建。"""
        main_cfg = self.config.read("main")
        if not main_cfg:
            self.config.write("main", {
                "scaling": 0,
                "current_bg_image": "",
                "voice_on_start": False,
                "voice_on_close": False,
            })
            logger.info("已创建默认 main.json")

    def run(self) -> int:
        """启动应用事件循环。"""
        logger.info("DesktopPet 启动")
        return self.app.exec()


def main():
    # Windows 旧终端启用 ANSI 颜色支持
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(_ColoredFormatter(
        "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logging.basicConfig(
        level=logging.INFO,
        handlers=[_handler],
    )
    app = DesktopPetApplication()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
