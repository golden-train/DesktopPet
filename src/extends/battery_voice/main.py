"""
电池语音扩展。

检测电源插拔和电量变化，自动播放对应语音。
作为 ExtensionBase 子类，由 ExtensionRegistry 自动发现和管理。
"""

import logging
from typing import Optional

from PySide6.QtWidgets import QWidget

from src.core.config import ConfigManager
from src.extends.base import ExtensionBase
from src.extends.battery_voice.monitor import BatteryMonitor

logger = logging.getLogger(__name__)


class BatteryVoiceExtension(ExtensionBase):
    """电池语音扩展——检测电源/电量变化，播放语音提醒。"""

    name = "电池语音"
    description = "检测电源插拔和电量变化，自动播放对应语音"
    icon = "🔋"

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(config, parent)
        self._monitor: BatteryMonitor | None = None

    def on_enable(self) -> None:
        """开启电池监控线程。"""
        if self._monitor is not None:
            return

        self._monitor = BatteryMonitor(self)
        # 连接信号到语音服务（由 main.py 中的 ExtensionRegistry 完成信号连接）
        logger.info("电池语音扩展已启用")

    def on_disable(self) -> None:
        """停止电池监控线程。"""
        if self._monitor:
            self._monitor.stop()
            self._monitor.wait(2000)
            self._monitor = None
            logger.info("电池语音扩展已禁用")

    def start_monitor(self, voice_callback) -> None:
        """
        启动监控（由主控制器调用）。
        将 voice_triggered 信号连接到 VoiceService。
        """
        if self._monitor and not self._monitor.isRunning():
            self._monitor.voice_triggered.connect(voice_callback)
            self._monitor.start()
            logger.info("电池监控线程已启动")

    @property
    def monitor(self) -> BatteryMonitor | None:
        return self._monitor
