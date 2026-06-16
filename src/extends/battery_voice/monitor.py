"""
电池状态监控器（独立线程）。
"""

import logging

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

_LOW_THRESHOLD = 50
_HEALTHY_MIN = 50
_FULL_THRESHOLD = 100


class BatteryMonitor(QThread):
    """
    独立线程，每 3 秒检测一次电池状态。
    检测到状态变化时通过信号通知主线程播放对应语音。
    """
    voice_triggered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_flag: bool = False
        self._was_plugged: bool | None = None
        self._low_triggered: bool = False
        self._healthy_triggered: bool = False
        self._full_triggered: bool = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        logger.info("电池监控线程启动")
        while not self._stop_flag:
            try:
                self._check_once()
            except Exception as e:
                logger.debug("电池检测异常（可能无电池）: %s", e)
            self.msleep(3000)
        logger.info("电池监控线程停止")

    def _check_once(self) -> None:
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            return

        plugged = battery.power_plugged
        percent = battery.percent

        if self._was_plugged is not None and plugged != self._was_plugged:
            if plugged:
                logger.info("电源插入")
                self.voice_triggered.emit("power_plugged")
                self._low_triggered = False
                self._healthy_triggered = False
                self._full_triggered = False
            else:
                logger.info("电源拔出")
                self.voice_triggered.emit("power_not_plugged")

        self._was_plugged = plugged

        if not plugged:
            return

        if percent >= _FULL_THRESHOLD and not self._full_triggered:
            logger.info("电量充满: %d%%", percent)
            self.voice_triggered.emit("FULL_POWER")
            self._full_triggered = True
        elif _HEALTHY_MIN <= percent < _FULL_THRESHOLD and not self._healthy_triggered:
            logger.info("电量健康: %d%%", percent)
            self.voice_triggered.emit("HEALTHY_POWER")
            self._healthy_triggered = True
        elif percent < _LOW_THRESHOLD and not self._low_triggered:
            logger.info("低电量: %d%%", percent)
            self.voice_triggered.emit("LOW_BATTERY")
            self._low_triggered = True
