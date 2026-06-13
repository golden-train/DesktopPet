"""
AI 对话窗口。

独立的聊天界面，支持发送消息、快捷提问、角色动画触发。
使用 QThread + ChatSignal 进行异步 AI 调用。
"""

import logging

from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel,
)
from PySide6.QtGui import QFont

from src.ai.client import AIClient, ChatSignal, chat_async
from src.ai.prompts import build_messages, get_skill_prompt

logger = logging.getLogger(__name__)

# 预设快捷问题
_PRESET_QUESTIONS = [
    "今天心情怎么样？",
    "讲个笑话吧",
    "我回来了",
    "晚安",
]


class ChatWindow(QWidget):
    """独立的 AI 对话窗口。"""

    # 收到 AI 回复时发出（含原始文本，由控制器解析动作标记）
    reply_ready = Signal(str)
    # 窗口关闭时发出
    window_closed = Signal()
    # 窗口移动时发出
    window_moved = Signal()

    def __init__(self, ai_client: AIClient, config, parent=None):
        super().__init__(parent)
        self._ai = ai_client
        self._config = config
        self._history: list[dict] = []
        self._thinking = False

        # 角色名：从 skills.json 默认技能获取，兼容后续自定义
        from src.ai.prompts import get_default_skill_name
        self._character_name = get_default_skill_name(config)

        self.setWindowTitle(f"✦ 与 {self._character_name} 聊天 ✦")
        self.setMinimumSize(400, 500)
        self.resize(440, 560)
        self.setAttribute(Qt.WA_QuitOnClose, False)

        # ── UI ──────────────────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题
        title = QLabel(f"✦ 与 {self._character_name} 聊天 ✦", self)
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # 聊天记录
        self._display = QTextEdit(self)
        self._display.setReadOnly(True)
        self._display.setPlaceholderText("开始和桌面宠物聊天吧……")
        self._display.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 6px;
                padding: 8px; font-size: 13px;
            }
        """)
        layout.addWidget(self._display, 1)

        # 快捷按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        for text in _PRESET_QUESTIONS:
            btn = QPushButton(text, self)
            btn.setStyleSheet("""
                QPushButton {
                    background: #2d2d2d; color: #ccc;
                    border: 1px solid #444; border-radius: 12px;
                    padding: 4px 10px; font-size: 11px;
                }
                QPushButton:hover { background: #3d3d3d; color: #fff; }
            """)
            btn.clicked.connect(lambda checked, t=text: self.send_message(t))
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("输入消息…")
        self._input.setStyleSheet("""
            QLineEdit {
                background: #1e1e1e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 6px;
                padding: 6px 10px; font-size: 13px;
            }
        """)
        self._input.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self._input, 1)

        self._send_btn = QPushButton("发送", self)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: #005fb8; color: white;
                border: none; border-radius: 6px;
                padding: 6px 18px; font-size: 13px;
            }
            QPushButton:hover { background: #0078d4; }
            QPushButton:disabled { background: #555; color: #999; }
        """)
        self._send_btn.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self._send_btn)

        layout.addLayout(input_layout)

        # ── 跨线程信号 ──────────────────────────────────────
        self._chat_signal = ChatSignal()
        self._chat_signal.reply_received.connect(self._on_reply)
        self._chat_signal.error_occurred.connect(self._on_error)

        # ── 启动问候 ────────────────────────────────────────
        self._append_message("系统", "你好呀，我是你的桌面宠物！有什么想聊的吗？(◕‿◕)")

    # ── 发送消息 ────────────────────────────────────────────

    def send_message(self, text: str) -> None:
        """发送消息（外部调用或按钮触发）。"""
        text = text.strip()
        if not text or self._thinking:
            return

        self._append_message("用户", text)
        self._history.append({"role": "user", "content": text})

        # 显示"正在思考…"
        self._thinking = True
        self._set_input_enabled(False)
        self._append_message(self._character_name, "……正在思考……")

        # 构建消息列表
        skill_prompt = get_skill_prompt(self._config)
        messages = build_messages(self._history, skill_prompt)

        # 启动后台线程
        self._thread = QThread(self)
        self._worker = _ChatWorker(self._ai, messages, self._chat_signal)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_reply(self, reply: str) -> None:
        """收到 AI 回复。"""
        self._thinking = False
        self._set_input_enabled(True)

        # 替换"正在思考…"占位
        self._remove_thinking_placeholder()
        self._append_message(self._character_name, reply)
        self._history.append({"role": "assistant", "content": reply})

        # 通知控制器解析动作标记
        self.reply_ready.emit(reply)

    def _on_error(self, error_msg: str) -> None:
        """AI 请求出错。"""
        self._thinking = False
        self._set_input_enabled(True)
        self._remove_thinking_placeholder()
        self._append_message("系统", f"（{error_msg}）")

    # ── UI 辅助 ────────────────────────────────────────────

    def _append_message(self, sender: str, text: str) -> None:
        """追加一条消息到聊天记录。"""
        color = {"用户": "#7ec8e3", self._character_name: "#ff9eb5", "系统": "#888"}.get(sender, "#ccc")
        # 对消息内容做 HTML 转义
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = f'<p style="margin:4px 0"><b style="color:{color}">{sender}</b> {safe}</p>'
        self._display.append(html)
        scrollbar = self._display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _remove_thinking_placeholder(self) -> None:
        """移除最后一条"正在思考…"占位。"""
        from PySide6.QtGui import QTextCursor
        cursor = self._display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        if "正在思考" in cursor.selectedText():
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _set_input_enabled(self, enabled: bool) -> None:
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        if enabled:
            self._input.setFocus()

    def _on_send_clicked(self) -> None:
        self.send_message(self._input.text())
        self._input.clear()

    # ── 生命周期 ────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if hasattr(self, "_thread") and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1000)
        self.window_closed.emit()
        super().closeEvent(event)

    def moveEvent(self, event) -> None:
        """窗口拖动时发出信号，让角色跟随。"""
        super().moveEvent(event)
        self.window_moved.emit()


# ═══════════════════════════════════════════════════════════════
# 后台工作器
# ═══════════════════════════════════════════════════════════════

class _ChatWorker(QObject):
    """在后台线程调用 AI 的工作器（QObject + moveToThread 模式）。"""
    finished = Signal()

    def __init__(self, ai_client: AIClient, messages: list[dict],
                 chat_signal: ChatSignal, parent=None):
        super().__init__(parent)
        self._ai = ai_client
        self._messages = messages
        self._signal = chat_signal

    def run(self) -> None:
        """在线程中执行（由 thread.started 触发）。"""
        try:
            reply = self._ai.ask(self._messages)
            self._signal.reply_received.emit(reply)
        except Exception as e:
            logger.error("ChatWorker 异常: %s", e)
            self._signal.error_occurred.emit(str(e))
        finally:
            self.finished.emit()
