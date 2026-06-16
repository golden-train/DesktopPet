"""
扩展系统。

每个扩展是一个继承 ``ExtensionBase`` 的独立模块，
放置在 ``src/extends/<name>/main.py`` 中。
由 ``ExtensionRegistry`` 自动发现和管理生命周期。
"""

from src.extends.base import ExtensionBase
from src.extends.registry import ExtensionRegistry

__all__ = ["ExtensionBase", "ExtensionRegistry"]
