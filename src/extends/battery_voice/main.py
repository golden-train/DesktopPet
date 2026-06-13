"""
电池语音扩展。

独立线程每 3 秒检测一次电池状态（通过 psutil），
检测到电源插拔或电量阶段变化时通过信号通知主线程播放语音。
"""

import logging

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

# 电量阶段阈值
_LOW_THRESHOLD = 50      # < 50% → LOW_BATTERY
_HEALTHY_MIN = 50        # 50-99% → HEALTHY_POWER
_FULL_THRESHOLD = 100    # 100% → FULL_POWER


class BatteryMonitor(QThread):
    """
    独立线程，每 3 秒检测一次电池状态。
    检测到状态变化时通过信号通知主线程播放对应语音。
    """
    voice_triggered = Signal(str)  # 参数: key

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_flag: bool = False
        self._was_plugged: bool | None = None
        self._low_triggered: bool = False
        self._healthy_triggered: bool = False
        self._full_triggered: bool = False

    def stop(self):
        """请求线程停止。"""
        self._stop_flag = True

    def run(self):
        """每 3 秒检测电池状态。"""
        logger.info("电池监控线程启动")
        while not self._stop_flag:
            try:
                self._check_once()
            except Exception as e:
                logger.debug("电池检测异常（可能无电池）: %s", e)
            self.msleep(3000)
        logger.info("电池监控线程停止")

    def _check_once(self) -> None:
        """单次电池状态检测。"""
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            return  # 无电池设备（如台式机）

        plugged = battery.power_plugged
        percent = battery.percent

        # ── 电源插拔检测 ────────────────────────────────────
        if self._was_plugged is not None and plugged != self._was_plugged:
            if plugged:
                logger.info("电源插入")
                self.voice_triggered.emit("power_plugged")
                # 重置阶段触发标记
                self._low_triggered = False
                self._healthy_triggered = False
                self._full_triggered = False
            else:
                logger.info("电源拔出")
                self.voice_triggered.emit("power_not_plugged")

        self._was_plugged = plugged

        # ── 电量阶段检测（仅插入电源时）─────────────────────
        if not plugged:
            return

        if percent >= _FULL_THRESHOLD and not self._full_triggered:
            logger.info("电量充满: %d%%", percent)
            self.voice_triggered.emit("FULL_POWER")
            self._full_triggered = True
        elif _HEALTHY_MIN <= percent < _FULL_THRESHOLD and not self._healthy_triggered:
            logger.info("电量健康: %d%%", percent)
            # 单次触发后标记
            self.voice_triggered.emit("HEALTHY_POWER")
            self._healthy_triggered = True
        elif percent < _LOW_THRESHOLD and not self._low_triggered:
            logger.info("低电量: %d%%", percent)
            self.voice_triggered.emit("LOW_BATTERY")
            self._low_triggered = True
