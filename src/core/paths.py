"""
路径常量模块。

以 src/core/paths.py 为锚点，向上定位项目根目录，
再派生出 data/、config/ 等子目录的路径。
"""

from pathlib import Path
import os

# ── 项目根目录 ──────────────────────────────────────────────
# src/core/paths.py → src/ → 项目根
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 允许通过环境变量覆盖（打包/测试时有用）
if os.getenv("PET_ROOT"):
    ROOT_DIR = Path(os.environ["PET_ROOT"]).resolve()

# ── 数据目录 ────────────────────────────────────────────────
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = DATA_DIR / "config"
AUDIO_DIR = DATA_DIR / "audio"
ASSETS_DIR = DATA_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
LIVE2D_DIR = DATA_DIR / "live2d"

# ── 源码目录 ────────────────────────────────────────────────
SRC_DIR = ROOT_DIR / "src"

# ── 快捷检查 ────────────────────────────────────────────────
_REQUIRED_DIRS = [DATA_DIR, CONFIG_DIR, AUDIO_DIR, ASSETS_DIR, IMAGES_DIR, LIVE2D_DIR]


def ensure_dirs():
    """确保所有必要的数据目录存在（首次运行时调用）"""
    for d in _REQUIRED_DIRS:
        d.mkdir(parents=True, exist_ok=True)
