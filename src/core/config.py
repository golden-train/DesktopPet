"""
统一配置管理器。

负责读取、写入、修改 data/config/ 下的 JSON 配置文件。
所有配置变更通过此模块完成，保证读写接口一致。
"""

import json
import logging
from pathlib import Path
from typing import Any

from src.core.paths import CONFIG_DIR

logger = logging.getLogger(__name__)


class ConfigManager:
    """统一读写 data/config/ 下的所有 JSON 配置。"""

    def __init__(self, config_dir: str | Path | None = None):
        """
        :param config_dir: 配置文件目录，默认使用 paths.CONFIG_DIR
        """
        self._config_dir = Path(config_dir) if config_dir else CONFIG_DIR
        self._config_dir.mkdir(parents=True, exist_ok=True)
        # 简单内存缓存，避免高频重复读盘
        self._cache: dict[str, dict] = {}

    # ── 公开接口 ────────────────────────────────────────────

    def read(self, name: str) -> dict:
        """读取 ``name.json``，返回 dict。"""
        path = self._resolve(name)
        if not path.exists():
            logger.debug("Config '%s' not found at %s, returning empty dict", name, path)
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data: dict = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read config '%s': %s", name, e)
            raise RuntimeError(f"Failed to read config '{name}': {e}") from e
        self._cache[name] = data
        logger.debug("Config '%s' loaded (%d keys)", name, len(data))
        return data

    def write(self, name: str, data: dict) -> None:
        """将 ``data`` 写入 ``name.json``。"""
        path = self._resolve(name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error("Failed to write config '%s': %s", name, e)
            raise RuntimeError(f"Failed to write config '{name}': {e}") from e
        self._cache[name] = data
        logger.info("Config '%s' saved (%d keys)", name, len(data))

    def get(self, name: str, key: str, default: Any = None) -> Any:
        """读取 ``name.json`` 中 ``key`` 的值，不存在时返回 ``default``。"""
        data = self._cached_read(name)
        return data.get(key, default)

    def set(self, name: str, key: str, value: Any) -> None:
        """修改 ``name.json`` 中 ``key`` 的值并保存。"""
        data = self._cached_read(name)
        data[key] = value
        self.write(name, data)

    # ── 内部方法 ────────────────────────────────────────────

    def _resolve(self, name: str) -> Path:
        """将配置名转为文件路径（自动补 .json）。"""
        name = name if name.endswith(".json") else f"{name}.json"
        return self._config_dir / name

    def _cached_read(self, name: str) -> dict:
        """带缓存的读取，避免高频重复文件 IO。"""
        if name not in self._cache:
            self._cache[name] = self.read(name)
        return self._cache[name]
