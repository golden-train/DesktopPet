"""
模型目录校验器。

检查用户准备导入的角色模型目录结构是否完整，
返回详细的校验报告供导入向导展示。
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────────

# 必需动作（缺少则导入失败）
REQUIRED_ACTIONS = {"Standby"}

# 可选动作（缺少仅警告，不阻塞导入）
OPTIONAL_ACTIONS = {
    "mention", "sleep", "discomfort", "love", "eat",
    "left", "right",
}

# 支持的图片扩展名
SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# 支持的音频扩展名
SUPPORTED_AUDIO_EXTS = {".wav", ".mp3", ".ogg"}

# 模型中可识别的动作目录
ALL_ACTIONS = REQUIRED_ACTIONS | OPTIONAL_ACTIONS


class ModelValidator:
    """校验用户导入的模型目录结构完整性。"""

    # 对外暴露常量
    REQUIRED_ACTIONS = REQUIRED_ACTIONS
    OPTIONAL_ACTIONS = OPTIONAL_ACTIONS
    SUPPORTED_IMAGE_EXTS = SUPPORTED_IMAGE_EXTS
    SUPPORTED_AUDIO_EXTS = SUPPORTED_AUDIO_EXTS

    @staticmethod
    def validate(model_dir: str) -> dict:
        """
        校验模型目录，返回校验报告。

        返回结构::

            {
                "valid": True | False,          # 整体是否通过（有 error 即为 False）
                "errors": ["缺少必需动作: Standby"],
                "warnings": ["动作 'love' 目录为空"],
                "has_walking": True | False,
                "voice_available": True | False,
                "actions_found": ["Standby", "love", ...],
                "actions_empty": ["sleep"],
                "image_count": 42,
                "audio_count": 4,
                "has_model_json": True | False,
                "model_name": "流萤",             # 从 model.json 读取（如果有）
            }
        """
        source = Path(model_dir)
        report: dict = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "has_walking": False,
            "voice_available": False,
            "actions_found": [],
            "actions_empty": [],
            "image_count": 0,
            "audio_count": 0,
            "has_model_json": False,
            "model_name": "",
        }

        # ── 源目录是否存在 ────────────────────────────────────
        if not source.is_dir():
            report["valid"] = False
            report["errors"].append(f"目录不存在: {model_dir}")
            return report

        # ── 检查 model.json ──────────────────────────────────
        model_json = source / "model.json"
        if model_json.is_file():
            report["has_model_json"] = True
            try:
                with open(model_json, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                report["model_name"] = meta.get("name", "")
            except (json.JSONDecodeError, OSError) as e:
                report["warnings"].append(f"model.json 解析失败: {e}")
        else:
            report["warnings"].append("未找到 model.json（建议提供角色元数据）")

        # ── 检查 actions/ 子目录 ──────────────────────────────
        actions_dir = source / "actions"
        if not actions_dir.is_dir():
            report["valid"] = False
            report["errors"].append("缺少 actions/ 目录")
            # 提前返回，因为不可能有任何动作
            return report

        for action in ALL_ACTIONS:
            action_path = actions_dir / action

            if not action_path.is_dir():
                # 目录完全不存在
                if action in REQUIRED_ACTIONS:
                    report["errors"].append(f"缺少必需动作: {action}")
                # 可选动作不报 error，只是不添加到 found 列表
                continue

            # 检查是否有有效图片
            images = ModelValidator._collect_images(action_path)
            if not images:
                report["actions_empty"].append(action)
                if action in REQUIRED_ACTIONS:
                    report["errors"].append(f"必需动作 '{action}' 目录中没有有效图片")
                else:
                    report["warnings"].append(f"可选动作 '{action}' 目录为空，对应功能将不可用")
            else:
                report["actions_found"].append(action)
                report["image_count"] += len(images)

        # ── 行走能力判断 ──────────────────────────────────────
        report["has_walking"] = ModelValidator.is_walkable(report)

        # ── 检查 voice/ 目录 ──────────────────────────────────
        voice_dir = source / "voice"
        if voice_dir.is_dir():
            audio_files = ModelValidator._collect_audio(voice_dir)
            report["audio_count"] = len(audio_files)
            if audio_files:
                report["voice_available"] = True
            else:
                report["warnings"].append("voice/ 目录中未找到有效音频文件")
        else:
            report["warnings"].append("未找到 voice/ 目录（语音功能不可用）")

        # ── 检查 icon/ 目录 ──────────────────────────────────
        icon_dir = source / "icon"
        if not icon_dir.is_dir():
            report["warnings"].append("未找到 icon/ 目录（将使用默认图标）")
        else:
            icons = list(icon_dir.iterdir())
            if not icons:
                report["warnings"].append("icon/ 目录为空（将使用默认图标）")

        # 汇总有效标志
        report["valid"] = len(report["errors"]) == 0
        logger.info(
            "校验结果: valid=%s, errors=%d, warnings=%d, images=%d, audio=%d",
            report["valid"], len(report["errors"]), len(report["warnings"]),
            report["image_count"], report["audio_count"],
        )
        return report

    @staticmethod
    def is_walkable(validation_result: dict) -> bool:
        """
        判断模型是否具备行走能力。

        条件: ``left`` 和 ``right`` 动作都存在且各自至少有一帧有效图片。
        """
        actions_found = set(validation_result.get("actions_found", []))
        actions_empty = set(validation_result.get("actions_empty", []))
        return "left" in actions_found and "right" in actions_found

    # ── 内部工具方法 ─────────────────────────────────────────

    @staticmethod
    def _collect_images(directory: Path) -> list[Path]:
        """收集目录中所有支持的图片文件。"""
        return [
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTS
        ]

    @staticmethod
    def _collect_audio(directory: Path) -> list[Path]:
        """递归收集目录中所有支持的音频文件。"""
        audio_files = []
        for p in directory.rglob("*"):
            if p.is_file() and p.suffix.lower() in SUPPORTED_AUDIO_EXTS:
                audio_files.append(p)
        return audio_files
