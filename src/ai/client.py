"""
AI 客户端模块。

封装 OpenAI SDK，支持任意兼容 API（DeepSeek / OpenAI / 等）。
提供同步调用和异步线程两种使用方式。
"""

import os
import logging
from typing import Optional
from pathlib import Path

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from PySide6.QtCore import QObject, Signal

from src.core.paths import ENV_PATH

logger = logging.getLogger(__name__)

# ── .env 键名 ───────────────────────────────────────────────
_ENV_KEYS = {
    "api_key": "AI_API_KEY",
    "base_url": "AI_API_BASE",
    "model": "AI_MODEL",
    "system_prompt": "AI_SYSTEM_PROMPT",
}


def _parse_env_file() -> dict[str, str]:
    """解析 ``.env`` 文件，返回键值字典。

    优先读用户目录（USER_DIR/.env），开发模式下回退到项目根目录。
    """
    candidates = []
    if ENV_PATH.exists():
        candidates.append(ENV_PATH)
    else:
        # 开发兼容：检查项目根目录
        from src.core.paths import BUNDLE_DIR
        root_env = BUNDLE_DIR / ".env"
        if root_env.exists():
            candidates.append(root_env)

    if not candidates:
        return {}

    result = {}
    for env_path in candidates:
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    result[key.strip()] = value.strip()
        except OSError as e:
            logger.error("读取 .env 失败: %s", e)
    return result


def set_env(key: str, value: str) -> None:
    """安全地写入 ``.env`` 文件中的单个键值对。

    保留所有注释和其他已有配置；如果键已存在则替换值，否则追加到末尾。
    """
    env_path = ENV_PATH

    if not env_path.exists():
        # 文件不存在则创建
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"{key}={value}\n")
            logger.info("已创建 .env 并写入 %s", key)
        except OSError as e:
            logger.error("创建 .env 失败: %s", e)
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        logger.error("读取 .env 失败: %s", e)
        return

    key_prefix = f"{key}="
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(key_prefix):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info("已更新 .env: %s", key)
    except OSError as e:
        logger.error("写入 .env 失败: %s", e)


class AIClient:
    """AI API 调用封装。"""

    def __init__(self):
        self._client: Optional[OpenAI] = None
        self.reload_config()

    def reload_config(self) -> None:
        """重新读取 ``.env`` 并重建 OpenAI 客户端。"""
        env = _parse_env_file()
        self.api_key: str = env.get("AI_API_KEY", "")
        self.base_url: str = env.get("AI_API_BASE", "https://api.deepseek.com")
        self.model: str = env.get("AI_MODEL", "deepseek-chat")
        self._client = None  # 强制下次重建
        logger.info("AI 配置已重载: model=%s, base=%s", self.model, self.base_url)

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("未配置 AI_API_KEY，请填写 .env 文件")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def ask(self, messages: list[dict], timeout: int = 30) -> str:
        """发送对话请求，返回 AI 回复文本（同步阻塞）。"""
        try:
            logger.debug("AI 请求: %s, %d 条消息", self.model, len(messages))
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                timeout=timeout,
            )
            reply = response.choices[0].message.content or ""
            logger.debug("AI 回复: %s", reply[:80])
            return reply
        except RateLimitError as e:
            logger.error("AI 请求频率限制: %s", e)
            return "（AI 服务繁忙，请稍后再试）"
        except APITimeoutError as e:
            logger.error("AI 请求超时: %s", e)
            return "（AI 请求超时，请检查网络连接）"
        except APIError as e:
            logger.error("AI API 错误: %s", e)
            return f"（AI 服务出错: {e}）"
        except Exception as e:
            logger.error("AI 请求异常: %s", e)
            return f"（AI 请求失败: {e}）"


# ── 异步支持 ────────────────────────────────────────────────

class ChatSignal(QObject):
    """用于跨线程信号传递（需要在主线程创建）。"""
    reply_received = Signal(str)
    error_occurred = Signal(str)


def chat_async(ai_client: AIClient, messages: list[dict], signal: ChatSignal):
    """在后台线程调用 AI，完成后通过信号通知主线程。"""
    try:
        reply = ai_client.ask(messages)
        signal.reply_received.emit(reply)
    except Exception as e:
        logger.error("chat_async 异常: %s", e)
        signal.error_occurred.emit(str(e))
