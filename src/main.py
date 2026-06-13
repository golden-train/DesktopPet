"""
DesktopPet 应用入口。

启动流程：
  1. 确保数据目录存在
  2. 初始化 QApplication
  3. 初始化 ConfigManager
  4. 初始化 AnimationManager
  5. 初始化 MainWindow
  6. 连接信号
  7. 显示窗口
  8. 进入事件循环
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# 确保项目根目录在 sys.path 中，支持直接 python src/main.py 启动
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.core.paths import ensure_dirs
from src.core.config import ConfigManager
from src.character.animation import AnimationManager
from src.window.main_window import MainWindow
from src.window.management_window import ManagementWindow

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
        self._bg_image: str = ""
        self._verify_config()

        # 4. 动画管理器
        self.animation = AnimationManager(self.config)

        # 5. 主窗口
        self.main_window = MainWindow(self.animation)
        self._apply_config_to_window()

        # 6. 管理窗口（延迟显示，不初始化时创建）
        self.management_window: Optional[ManagementWindow] = None

        # 7. 连接信号
        self._connect_signals()

        # 8. 显示窗口（默认右下区域）
        self._place_window()
        self.main_window.show()

        logger.info("DesktopPet 初始化完成，角色窗口已显示")

    def _verify_config(self) -> None:
        """验证关键配置是否存在，若不存在则用默认值创建。"""
        main_cfg = self.config.read("main")
        if not main_cfg:
            self.config.write("main", {
                "scaling": 0,
                "currentBgImage": "",
                "is_play_VoiceOnStart": False,
                "is_play_VoiceOnClose": False,
            })
            logger.info("已创建默认 main.json")

    def _apply_config_to_window(self) -> None:
        """将配置中的缩放等设置应用到窗口。"""
        scaling = self.config.get("main", "scaling", 0)
        self.main_window.set_scaling(scaling)
        # 记录背景配置（后续 PopupWindow / Live2D 使用）
        self._bg_image = self.config.get("main", "currentBgImage", "")

    def _connect_signals(self) -> None:
        """连接模块间的信号（§ 信号连接图）。"""
        self.main_window.action_triggered.connect(
            self.animation.switch_action
        )
        self.main_window.settings_requested.connect(
            self._open_settings
        )

    def _open_settings(self) -> None:
        """打开设置窗口（单例，切换可见性）。"""
        if self.management_window is None:
            self.management_window = ManagementWindow(self.config, self.main_window)
        if self.management_window.isVisible():
            self.management_window.raise_()
            self.management_window.activateWindow()
        else:
            self.management_window.show()

    def _place_window(self) -> None:
        """将窗口放在屏幕右下区域（800px 偏移）。"""
        screen = self.app.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.right() - 400
            y = geom.bottom() - 400
            self.main_window.move(x, y)

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
