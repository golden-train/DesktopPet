"""
扩展注册表。

自动发现 ``src/extends/`` 下所有扩展，提供查询和生命周期管理。
"""

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Optional

from src.core.config import ConfigManager
from src.extends.base import ExtensionBase

logger = logging.getLogger(__name__)


class ExtensionRegistry:
    """扩展注册表——自动发现和管理扩展。"""

    _extensions: list[ExtensionBase] | None = None

    @classmethod
    def discover(cls, config: ConfigManager) -> list[ExtensionBase]:
        """
        扫描 ``src/extends/`` 目录，实例化所有扩展。

        每个子目录下的 ``main.py`` 需导出一个继承 ``ExtensionBase`` 的类。
        首次调用后会缓存结果。
        """
        if cls._extensions is not None:
            return cls._extensions

        cls._extensions = []
        extends_dir = Path(__file__).resolve().parent

        for item in extends_dir.iterdir():
            if not item.is_dir() or item.name.startswith("_") or item.name.startswith("."):
                continue

            main_file = item / "main.py"
            if not main_file.exists():
                continue

            try:
                # 动态导入: src.extends.<name>.main
                module_name = f"src.extends.{item.name}.main"
                module = importlib.import_module(module_name)

                # 查找模块中 ExtensionBase 的子类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and issubclass(attr, ExtensionBase)
                            and attr is not ExtensionBase):
                        instance = attr(config)
                        cls._extensions.append(instance)
                        logger.info("发现扩展: %s (%s)", instance.name, item.name)
                        break  # 每个模块只取一个扩展类
            except Exception as e:
                logger.warning("加载扩展 %s 失败: %s", item.name, e)

        logger.info("扩展发现完成: %d 个扩展", len(cls._extensions))
        return cls._extensions

    @classmethod
    def get_by_name(cls, name: str, config: ConfigManager) -> Optional[ExtensionBase]:
        """按名称查找扩展。"""
        for ext in cls.discover(config):
            if ext.name == name or ext.__class__.__name__ == name:
                return ext
        return None

    @classmethod
    def start_enabled(cls, config: ConfigManager) -> list[ExtensionBase]:
        """启动所有已启用的扩展。返回已启动的扩展列表。"""
        started = []
        for ext in cls.discover(config):
            if ext.is_enabled():
                try:
                    ext.on_enable()
                    started.append(ext)
                    logger.info("扩展已启动: %s", ext.name)
                except Exception as e:
                    logger.warning("启动扩展 %s 失败: %s", ext.name, e)
        return started

    @classmethod
    def stop_all(cls) -> None:
        """停止所有扩展。"""
        if cls._extensions:
            for ext in cls._extensions:
                try:
                    ext.on_disable()
                except Exception as e:
                    logger.debug("停止扩展 %s 失败: %s", ext.name, e)
            logger.info("所有扩展已停止")

    @classmethod
    def clear_cache(cls) -> None:
        """清除缓存（用于测试）。"""
        cls._extensions = None
