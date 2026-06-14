"""
提示词管理与动作标记常量。

提供 ANIMATION_MARKERS 定义、系统提示词加载、消息组装等功能。
"""

import logging
from typing import Optional

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)

# ── 动作标记（AI 回复中嵌入 [动作名] 来触发角色动画）──────
ANIMATION_MARKERS = {
    "eat": "吃东西",
    "love": "比心/爱心",
    "sleep": "睡觉",
    "Standby": "待机/站立",
    "mention": "蹭蹭/引起注意",
    "discomfort": "不舒服",
    "left": "向左走",
    "right": "向右走",
}

_MARKER_INSTRUCTION = (
    "\n\n你可以在回复中插入动作标记来表现情绪，格式为 [动作名]。"
    "常用的动作有："
    f"{', '.join(f'[{k}]{v}' for k, v in ANIMATION_MARKERS.items())}。"
    "你也可以使用其他自定义动作名。"
    "多个标记时只取第一个。"
)


def get_skill_prompt(config: ConfigManager, skill_name: Optional[str] = None) -> str:
    """获取系统提示词。

    优先级：
    1. ``.env`` 中的 ``AI_SYSTEM_PROMPT``（AI 配置页保存的）
    2. ``skills.json`` 中指定名称的技能
    3. ``skills.json`` 中第一个技能（默认）
    """
    # 优先使用 .env 中保存的提示词（AI 配置页 → 保存配置）
    from src.ai.client import _parse_env_file
    env = _parse_env_file()
    env_prompt = env.get("AI_SYSTEM_PROMPT", "").strip()
    if env_prompt:
        return env_prompt

    # 回退到 skills.json
    skills_data = config.read("skills")
    skills = skills_data.get("skills", [])
    if not skills:
        logger.warning("skills.json 中没有技能预设")
        return "你是桌面宠物流萤，请用简短活泼的语气回答。"

    if skill_name:
        for s in skills:
            if s["name"] == skill_name:
                return s["prompt"]

    # 默认取第一个
    return skills[0]["prompt"]


def get_default_skill_name(config: ConfigManager) -> str:
    """返回默认技能名称。"""
    skills = config.read("skills").get("skills", [])
    return skills[0]["name"] if skills else "流萤"


def build_messages(history: list[dict], system_prompt: str) -> list[dict]:
    """构建发送给 API 的消息列表。

    在系统提示词末尾追加动作标记说明。
    """
    system_content = system_prompt + _MARKER_INSTRUCTION
    messages = [{"role": "system", "content": system_content}]
    messages.extend(history)
    return messages
