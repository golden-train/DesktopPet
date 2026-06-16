"""
统一语音服务。

使用 PySide6.QtMultimedia 播放音频，支持 WAV/MP3 等格式。
管理开关机语音包和电池语音的统一播放入口。
语音跟随模型：每个模型通过注册表的 voice_available 控制是否播放。
"""

import logging
import random
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from src.core.config import ConfigManager
from src.core.paths import BUNDLE_DIR

logger = logging.getLogger(__name__)


class VoiceService(QObject):
    """统一管理所有语音播放（电池语音 + 语音包）。"""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.8)

        self._current_wav: str = ""
        self._player.errorOccurred.connect(self._on_error)

    # ── 核心播放 ────────────────────────────────────────────

    def play(self, wav_path: str) -> None:
        """播放一个音频文件。如果正在播放则立即切换（不排队）。"""
        full_path = self._resolve_path(wav_path)
        if not full_path:
            logger.warning("语音文件不存在: %s", wav_path)
            return

        self._player.stop()
        self._current_wav = str(full_path)
        source = QUrl.fromLocalFile(str(full_path))
        self._player.setSource(source)
        self._player.play()
        logger.debug("播放语音: %s", full_path.name)

    def stop(self) -> None:
        self._player.stop()
        self._current_wav = ""

    # ── 语音包播放 ──────────────────────────────────────────

    def play_voice_pack(self, key: str, time_of_day: str = "") -> None:
        """
        从 ``voicepack.json`` 中按时段取列表，随机选一条播放。
        如果当前模型没有语音资源，静默跳过。

        :param key: VoiceOnStart / VoiceOnClose
        :param time_of_day: morn / noon / night / other（为空时自动检测）
        """
        if not self._is_enabled(key):
            return

        model_id = self._config.get("main", "current_model", "firefly")
        if not self._model_has_voice(model_id):
            logger.debug("模型 '%s' 无语音包，跳过", model_id)
            return

        data = self._config.read("voicepack")
        slot_data = data.get(key, {})
        if not time_of_day:
            time_of_day = self.get_time_of_day(datetime.now().hour)

        candidates = slot_data.get(time_of_day, [])
        if not candidates:
            logger.debug("语音 %s[%s] 无条目", key, time_of_day)
            return

        chosen = random.choice(candidates)
        self.play(chosen["wav"])

    # ── 电池语音播放 ────────────────────────────────────────

    def play_battery_voice(self, key: str) -> None:
        """
        从 ``battery_voice.json`` 中读取列表，随机选一条播放。

        :param key: power_plugged / power_not_plugged / LOW_BATTERY /
                     HEALTHY_POWER / FULL_POWER
        """
        if not self._config.get("main", "enable_battery_monitor", False):
            return

        model_id = self._config.get("main", "current_model", "firefly")
        if not self._model_has_voice(model_id):
            logger.debug("模型 '%s' 无语音，跳过电池语音", model_id)
            return

        data = self._config.read("battery_voice")
        candidates = data.get(key, [])
        if not candidates:
            logger.debug("电池语音 %s 无条目", key)
            return

        chosen = random.choice(candidates)
        self.play(chosen["wav"])

    # ── 随机闲时语音 ────────────────────────────────────────

    def play_random_idle(self) -> None:
        """从语音池中随机选一条播放（闲时自动触发）。"""
        if not self._config.get("main", "is_play_idle_voice", False):
            return

        model_id = self._config.get("main", "current_model", "firefly")
        if not self._model_has_voice(model_id):
            logger.debug("模型 '%s' 无语音，跳过闲时语音", model_id)
            return

        pool: list[str] = []
        data = self._config.read("voicepack")
        for key in ("VoiceOnStart", "VoiceOnClose"):
            slots = data.get(key, {})
            for entries in slots.values():
                for entry in entries:
                    if "wav" in entry:
                        pool.append(entry["wav"])

        if not pool:
            return
        self.play(random.choice(pool))

    # ── 时段判断 ────────────────────────────────────────────

    @staticmethod
    def get_time_of_day(hour: int) -> str:
        if 6 <= hour <= 8:
            return "morn"
        if 10 <= hour <= 12:
            return "noon"
        if 18 <= hour <= 21 or hour < 6 or hour >= 21:
            return "night"
        return "other"

    # ── 内部辅助 ────────────────────────────────────────────

    def _model_has_voice(self, model_id: str) -> bool:
        """检查指定模型是否有语音资源。"""
        from src.model.registry import ModelRegistry
        info = ModelRegistry.get_by_id(self._config, model_id)
        if not info:
            return False
        return bool(info.get("voice_available", False))

    def _resolve_path(self, wav_path: str) -> Path | None:
        p = Path(wav_path)
        if p.is_absolute():
            return p if p.exists() else None
        full = BUNDLE_DIR / wav_path
        if full.exists():
            return full
        from src.core.paths import USER_DIR
        full2 = USER_DIR / wav_path
        if full2.exists():
            return full2
        return None

    def _is_enabled(self, key: str) -> bool:
        cfg_key = "is_play_VoiceOnStart" if key == "VoiceOnStart" else "is_play_VoiceOnClose"
        return self._config.get("main", cfg_key, False)

    def _on_error(self, error, error_str: str) -> None:
        if error != QMediaPlayer.Error.NoError:
            logger.warning("语音播放错误: %s", error_str)
