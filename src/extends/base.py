"""
扩展基类。

所有桌面宠物扩展必须继承 ``ExtensionBase``。
扩展通过 ``ExtensionRegistry`` 自动发现和加载。
"""

import logging
from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)


class ExtensionBase(QObject):
    """扩展基类——所有扩展必须继承此类。"""

    # ── 子类必须定义 ────────────────────────────────────────
    name: str = ""                     # 扩展显示名称
    description: str = ""              # 扩展描述
    icon: str = ""                     # Emoji 图标，如 "🔋"

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._started = False

    # ── 配置持久化 ───────────────────────────────────────────

    @property
    def config_key(self) -> str:
        """在 main.json 中存储启用状态的键名。"""
        return f"enable_{self.__class__.__name__}"

    def is_enabled(self) -> bool:
        """检查扩展是否已启用。"""
        return self._config.get("main", self.config_key, False)

    def set_enabled(self, enabled: bool) -> None:
        """持久化启用状态。"""
        self._config.set("main", self.config_key, enabled)

    # ── 生命周期（子类可选重写）──────────────────────────────

    def on_enable(self) -> None:
        """用户开启扩展时调用。在此启动线程/资源。"""
        pass

    def on_disable(self) -> None:
        """用户关闭扩展时调用。在此清理线程/资源。"""
        pass

    def get_config_widget(self, parent: QWidget) -> Optional[QWidget]:
        """
        返回扩展的自定义配置界面，会在扩展页面的开关下方展示。
        返回 None 表示无需额外配置。
        """
        return None
