"""
AI 供应商预设。

收录常见大模型供应商的 API 接入信息（OpenAI 兼容格式）。
"""

from typing import NamedTuple


class ProviderInfo(NamedTuple):
    name: str
    base_url: str
    models: list[str]
    note: str = ""


# ── 供应商预设 ──────────────────────────────────────────────
# 参考各厂商官方文档整理的 OpenAI 兼容端点

PROVIDERS: dict[str, ProviderInfo] = {
    "OpenAI": ProviderInfo(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        note="需境外网络环境",
    ),
    "DeepSeek": ProviderInfo(
        name="DeepSeek",
        base_url="https://api.deepseek.com",
        models=["deepseek-chat", "deepseek-reasoner"],
    ),
    "月之暗面 (Moonshot)": ProviderInfo(
        name="月之暗面 (Moonshot)",
        base_url="https://api.moonshot.cn/v1",
        models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    ),
    "智谱 (GLM)": ProviderInfo(
        name="智谱 (GLM)",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        models=["glm-4-plus", "glm-4-air", "glm-4-flash", "glm-4v-plus"],
        note="需智谱开放平台 API Key",
    ),
    "通义千问 (Qwen)": ProviderInfo(
        name="通义千问 (Qwen)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=["qwen-plus", "qwen-max", "qwen-turbo", "qwen2.5-72b-instruct"],
    ),
    "SiliconFlow": ProviderInfo(
        name="SiliconFlow",
        base_url="https://api.siliconflow.cn/v1",
        models=[
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-72B-Instruct",
            "THUDM/glm-4-9b-chat",
        ],
        note="硅基流动，提供多种开源模型",
    ),
    "Groq": ProviderInfo(
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        models=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        note="需境外网络环境",
    ),
}


def get_provider_names() -> list[str]:
    """返回所有预设供应商名称（按固定顺序）。"""
    return list(PROVIDERS.keys())


def detect_provider(base_url: str) -> str | None:
    """根据 base_url 自动匹配供应商名称，匹配不到返回 None。"""
    for name, info in PROVIDERS.items():
        if info.base_url.rstrip("/") == base_url.rstrip("/"):
            return name
    return None
