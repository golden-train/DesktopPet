"""
路径常量模块。

支持两种运行模式：
- 开发模式：BUNDLE_DIR = USER_DIR = 项目根目录
- 打包模式：BUNDLE_DIR = sys._MEIPASS（只读），USER_DIR = %APPDATA%/DesktopPet（可写）

所有用户配置、日志等需要持久化的数据写入 USER_DIR，
程序自带的图片、音频、默认配置从 BUNDLE_DIR 读取。
"""

import sys
import os
from pathlib import Path

# ── 检测是否 PyInstaller 打包 ──────────────────────────────
_IS_FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


# ── 应用根目录 ─────────────────────────────────────────────
if _IS_FROZEN:
    # 打包后：BUNDLE_DIR = PyInstaller 临时解压目录（只读）
    BUNDLE_DIR = Path(sys._MEIPASS).resolve()
    # USER_DIR = exe 同级目录（便携模式，可写持久化）
    USER_DIR = Path(sys.executable).resolve().parent
else:
    # 开发模式：两者相同，都是项目根
    _root = Path(__file__).resolve().parent.parent.parent
    BUNDLE_DIR = _root
    USER_DIR = _root


# 允许通过环境变量覆盖（测试/调试时有用）
if os.getenv("PET_ROOT"):
    BUNDLE_DIR = Path(os.environ["PET_ROOT"]).resolve()
if os.getenv("PET_USER_DIR"):
    USER_DIR = Path(os.environ["PET_USER_DIR"]).resolve()

# ── 数据目录（BUNDLE → 只读参考，USER → 可写副本）────────
# 用户配置目录（ConfigManager 写入此目录）
USER_CONFIG_DIR = USER_DIR / "data" / "config"
# 捆绑配置目录（作为默认配置的源）
BUNDLE_CONFIG_DIR = BUNDLE_DIR / "data" / "config"

# 用户数据目录（其他可写数据）
USER_DATA_DIR = USER_DIR / "data"

# 捆绑资产目录（只读，图片、音频、Live2D 模型等）
DATA_DIR = BUNDLE_DIR / "data"
CONFIG_DIR_SRC = BUNDLE_DIR / "data" / "config"  # 仅作为默认源
AUDIO_DIR = BUNDLE_DIR / "data" / "audio"
ASSETS_DIR = BUNDLE_DIR / "data" / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
LIVE2D_DIR = BUNDLE_DIR / "data" / "live2d"

# ── 角色资源目录 ────────────────────────────────────────────
FIREFLY_DIR = IMAGES_DIR / "firefly"
ACTIONS_DIR = FIREFLY_DIR / "actions"
ICON_DIR = IMAGES_DIR / "icon"
FIREFLY_ICON_DIR = FIREFLY_DIR / "icon"
AUDIO_FIREFLY_DIR = AUDIO_DIR / "firefly"

# ── 用户导入的自定义模型目录（可写）────────────────────────
CUSTOM_MODELS_DIR = USER_DIR / "data" / "assets" / "images" / "custom"
CUSTOM_AUDIO_DIR = USER_DIR / "data" / "audio" / "custom"

# ── .env 文件路径（始终在用户可写目录）─────────────────────
ENV_PATH = USER_DIR / ".env"

# ── 日志目录 ────────────────────────────────────────────────
LOGS_DIR = USER_DIR / "data" / "logs"

# ── 源码目录（仅开发模式）────────────────────────────────────
SRC_DIR = BUNDLE_DIR / "src"


# 需要确保存在的用户目录
_USER_REQUIRED_DIRS = [
    USER_CONFIG_DIR,
    USER_DIR / "data" / "audio",
    USER_DIR / "data" / "assets" / "images",
    USER_DIR / "data" / "assets" / "images" / "custom",
    USER_DIR / "data" / "audio" / "custom",
    LOGS_DIR,
]


def ensure_dirs():
    """确保所有必要的用户数据目录存在。"""
    for d in _USER_REQUIRED_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def is_frozen() -> bool:
    """是否处于 PyInstaller 打包运行状态。"""
    return _IS_FROZEN
