"""
统一配置管理器。

读取时优先从用户配置目录（可写）加载，若不存在则回退到捆绑默认配置。
写入时始终写入用户配置目录，确保打包后修改可持久化。
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from src.core.paths import USER_CONFIG_DIR, BUNDLE_CONFIG_DIR

logger = logging.getLogger(__name__)


class ConfigManager:
    """统一读写 data/config/ 下的所有 JSON 配置。"""

    def __init__(self, config_dir: str | Path | None = None,
                 fallback_dir: str | Path | None = None):
        """
        :param config_dir: 用户配置目录（写入目标），默认 USER_CONFIG_DIR
        :param fallback_dir: 捆绑配置目录（只读默认值源），默认 BUNDLE_CONFIG_DIR
        """
        self._config_dir = Path(config_dir) if config_dir else USER_CONFIG_DIR
        self._fallback_dir = Path(fallback_dir) if fallback_dir else BUNDLE_CONFIG_DIR
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict] = {}

    # ── 公开接口 ────────────────────────────────────────────

    def read(self, name: str) -> dict:
        """读取 ``name.json``。优先读用户目录，不存在则读捆绑默认。"""
        user_path = self._resolve(name, self._config_dir)
        bundle_path = self._resolve(name, self._fallback_dir)

        # 优先读用户目录
        if user_path.exists():
            return self._read_file(user_path, name)

        # 回退到捆绑默认
        if bundle_path.exists():
            data = self._read_file(bundle_path, name)
            # 自动复制到用户目录，使修改可持久化
            try:
                shutil.copy2(bundle_path, user_path)
                logger.debug("已复制默认配置 %s 到用户目录", name)
            except OSError:
                pass
            self._cache[name] = data
            return data

        logger.debug("Config '%s' not found, returning empty dict", name)
        return {}

    def write(self, name: str, data: dict) -> None:
        """将 ``data`` 写入用户配置目录下的 ``name.json``。"""
        path = self._resolve(name, self._config_dir)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error("Failed to write config '%s': %s", name, e)
            raise RuntimeError(f"Failed to write config '{name}': {e}") from e
        self._cache[name] = data
        logger.info("Config '%s' saved (%d keys)", name, len(data))

    def get(self, name: str, key: str, default: Any = None) -> Any:
        """读取配置中指定 key 的值，不存在时返回 default。"""
        data = self._cached_read(name)
        return data.get(key, default)

    def set(self, name: str, key: str, value: Any) -> None:
        """修改指定 key 的值并保存到用户目录。"""
        data = self._cached_read(name)
        data[key] = value
        self.write(name, data)

    # ── 内部方法 ────────────────────────────────────────────

    @staticmethod
    def _resolve(name: str, base_dir: Path) -> Path:
        """将配置名转为文件路径。"""
        name = name if name.endswith(".json") else f"{name}.json"
        return base_dir / name

    def _cached_read(self, name: str) -> dict:
        if name not in self._cache:
            self._cache[name] = self.read(name)
        return self._cache[name]

    @staticmethod
    def _read_file(path: Path, name: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data: dict = json.load(f)
            logger.debug("Config '%s' loaded from %s", name, path)
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read config '%s' at %s: %s", name, path, e)
            raise RuntimeError(f"Failed to read config '{name}': {e}") from e
