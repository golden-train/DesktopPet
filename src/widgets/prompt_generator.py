"""
AI 提示词生成对话框。

用户用自然语言描述角色特征，AI 自动生成结构化系统提示词，
提供预览、编辑和选用功能。
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QMessageBox, QWidget,
    QFrame, QSplitter, QScrollArea,
)

from src.ai.client import AIClient
from src.ai.client import _parse_env_file

logger = logging.getLogger(__name__)

# ── 样式 ──────────────────────────────────────────────────

_INPUT_STYLE = """
    QLineEdit, QTextEdit, QComboBox {
        background: #222; color: #e0e0e0;
        border: 1px solid #555; border-radius: 4px;
        padding: 6px 10px; font-size: 13px;
    }
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
        border: 1px solid #5ba3e6;
    }
    QComboBox::drop-down {
        border: none; width: 20px;
    }
    QComboBox::down-arrow {
        image: none; border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #888;
        margin-right: 6px;
    }
    QComboBox QAbstractItemView {
        background: #2a2a2a; color: #e0e0e0;
        selection-background-color: #3a6ea5;
        border: 1px solid #444;
    }
"""
_PREVIEW_STYLE = """
    QTextEdit {
        background: #1a1a2a; color: #ccc;
        border: 1px solid #444; border-radius: 6px;
        padding: 10px; font-size: 13px;
        font-family: 'Consolas', 'Microsoft YaHei', monospace;
    }
"""
_LABEL_STYLE = "color: #e0e0e0; font-size: 13px; font-weight: bold; padding: 4px 0;"
_BTN_PRIMARY = """
    QPushButton {
        background: #005fb8; color: #fff; border: none;
        border-radius: 6px; padding: 8px 20px; font-size: 13px;
    }
    QPushButton:hover { background: #0078d4; }
    QPushButton:disabled { background: #444; color: #888; }
"""
_BTN_SECONDARY = """
    QPushButton {
        background: #3a3a3a; color: #ccc; border: 1px solid #555;
        border-radius: 6px; padding: 8px 20px; font-size: 13px;
    }
    QPushButton:hover { background: #4a4a4a; color: #fff; }
"""
_BTN_SUCCESS = """
    QPushButton {
        background: #2a7a3a; color: #fff; border: none;
        border-radius: 6px; padding: 8px 20px; font-size: 13px;
    }
    QPushButton:hover { background: #3a9a4a; }
"""

# ── 生成提示词模板 ─────────────────────────────────────────
GENERATION_PROMPT_TEMPLATE = """你是一个 AI 提示词生成助手。根据用户的角色描述，生成一个结构化的系统提示词。

用户输入：
- 角色名称：{name}
- 性格特征：{personality}
- 语气风格：{tone}
- 额外指令：{extra}

请在生成的提示词中包含以下要素：
1. 角色身份介绍
2. 性格特征描述
3. 语气风格要求
4. 行为规范（如：用简短语句回答、不主动提及自己是AI等）
5. 可选的 [动作名] 标记使用说明

直接输出提示词内容，不要包含任何额外说明、不要用代码块包裹。"""

# 语气风格选项
_TONE_OPTIONS = ["活泼", "沉稳", "冷峻", "可爱", "温柔", "傲娇", "幽默", "知性", "自定义"]


class PromptGenerator(QDialog):
    """AI 提示词生成对话框。"""

    prompt_selected = Signal(str)  # 用户确认的提示词

    def __init__(self, ai_client: AIClient, current_prompt: str = "", parent=None):
        super().__init__(parent)
        self._ai_client = ai_client
        self._current_prompt = current_prompt
        self._generated_prompt: str = ""
        self._is_editing: bool = False

        self.setWindowTitle("AI 提示词生成")
        self.setMinimumSize(720, 520)
        self.setAttribute(Qt.WA_QuitOnClose, False)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # ── 标题 ────────────────────────────────────────────
        title = QLabel("AI 提示词生成器", self)
        tf = QFont()
        tf.setPointSize(16)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet("color: #e0e0e0;")
        main_layout.addWidget(title)

        desc = QLabel("用自然语言描述角色特征，AI 自动生成结构化的系统提示词", self)
        desc.setStyleSheet("color: #888; font-size: 12px;")
        main_layout.addWidget(desc)

        main_layout.addSpacing(8)

        # ── 分割布局：左侧输入 / 右侧预览 ────────────────────
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #444; }")

        # ── 左侧：输入区 ────────────────────────────────────
        input_panel = QWidget(splitter)
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(0, 0, 12, 0)
        input_layout.setSpacing(8)
        input_panel.setStyleSheet(_INPUT_STYLE)

        # 角色名称
        name_label = QLabel("角色名称", input_panel)
        name_label.setStyleSheet(_LABEL_STYLE)
        input_layout.addWidget(name_label)
        self._name_input = QLineEdit(input_panel)
        self._name_input.setPlaceholderText("如：流萤、猫娘、AI 助手")
        input_layout.addWidget(self._name_input)

        # 性格特征
        personality_label = QLabel("性格特征", input_panel)
        personality_label.setStyleSheet(_LABEL_STYLE)
        input_layout.addWidget(personality_label)
        self._personality_input = QLineEdit(input_panel)
        self._personality_input.setPlaceholderText("如：温柔、活泼、有点傲娇、喜欢撒娇")
        input_layout.addWidget(self._personality_input)

        # 语气风格
        tone_label = QLabel("语气风格", input_panel)
        tone_label.setStyleSheet(_LABEL_STYLE)
        input_layout.addWidget(tone_label)
        self._tone_combo = QComboBox(input_panel)
        self._tone_combo.addItems(_TONE_OPTIONS)
        self._tone_combo.setCurrentText("活泼")
        self._tone_combo.setEditable(True)
        input_layout.addWidget(self._tone_combo)

        # 额外指令
        extra_label = QLabel("额外指令（可选）", input_panel)
        extra_label.setStyleSheet(_LABEL_STYLE)
        input_layout.addWidget(extra_label)
        self._extra_input = QTextEdit(input_panel)
        self._extra_input.setPlaceholderText("如：不要提自己是AI、使用颜文字、每句话不超过20字")
        self._extra_input.setMaximumHeight(100)
        self._extra_input.setStyleSheet("""
            QTextEdit {
                background: #222; color: #e0e0e0;
                border: 1px solid #555; border-radius: 4px;
                padding: 6px; font-size: 13px;
            }
        """)
        input_layout.addWidget(self._extra_input)

        input_layout.addSpacing(8)

        # 生成按钮
        self._generate_btn = QPushButton("🚀 生成提示词", input_panel)
        self._generate_btn.setStyleSheet(_BTN_PRIMARY)
        self._generate_btn.clicked.connect(self._generate)
        input_layout.addWidget(self._generate_btn)

        # 当前提示词（如果已有）
        if self._current_prompt:
            label = QLabel(f"当前: {self._shorten(self._current_prompt, 50)}", input_panel)
            label.setStyleSheet("color: #888; font-size: 11px; padding: 4px;")
            label.setWordWrap(True)
            input_layout.addWidget(label)

        input_layout.addStretch()

        # ── 右侧：预览区 ────────────────────────────────────
        preview_panel = QWidget(splitter)
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(12, 0, 0, 0)
        preview_layout.setSpacing(8)

        preview_header = QLabel("预览", preview_panel)
        preview_header.setStyleSheet(_LABEL_STYLE)
        preview_layout.addWidget(preview_header)

        self._preview = QTextEdit(preview_panel)
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("点击「生成提示词」后，AI 生成的提示词将显示在这里")
        self._preview.setStyleSheet(_PREVIEW_STYLE)
        preview_layout.addWidget(self._preview, 1)

        # 预览区底部的操作按钮
        preview_btn_layout = QHBoxLayout()
        preview_btn_layout.setSpacing(8)

        self._use_btn = QPushButton("✅ 使用此提示词", preview_panel)
        self._use_btn.setStyleSheet(_BTN_SUCCESS)
        self._use_btn.clicked.connect(self._on_use)
        self._use_btn.setEnabled(False)
        preview_btn_layout.addWidget(self._use_btn)

        self._regen_btn = QPushButton("🔄 重新生成", preview_panel)
        self._regen_btn.setStyleSheet(_BTN_SECONDARY)
        self._regen_btn.clicked.connect(self._generate)
        self._regen_btn.setEnabled(False)
        preview_btn_layout.addWidget(self._regen_btn)

        self._edit_btn = QPushButton("✏️ 手动编辑", preview_panel)
        self._edit_btn.setStyleSheet(_BTN_SECONDARY)
        self._edit_btn.clicked.connect(self._toggle_edit)
        self._edit_btn.setEnabled(False)
        preview_btn_layout.addWidget(self._edit_btn)

        preview_layout.addLayout(preview_btn_layout)

        # ── 加入分割器 ──────────────────────────────────────
        splitter.addWidget(input_panel)
        splitter.addWidget(preview_panel)
        splitter.setSizes([280, 420])
        main_layout.addWidget(splitter, 1)

        # ── 底部按钮 ────────────────────────────────────────
        bottom_layout = QHBoxLayout()

        token_label = QLabel("", self)
        token_label.setStyleSheet("color: #666; font-size: 11px;")
        self._token_label = token_label
        bottom_layout.addWidget(token_label)

        bottom_layout.addStretch()

        cancel_btn = QPushButton("取消", self)
        cancel_btn.setStyleSheet(_BTN_SECONDARY)
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        main_layout.addLayout(bottom_layout)

    # ── 生成 ────────────────────────────────────────────────

    def _generate(self) -> None:
        """调用 AI 生成提示词。"""
        name = self._name_input.text().strip()
        personality = self._personality_input.text().strip()
        tone = self._tone_combo.currentText().strip()
        extra = self._extra_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "提示", "请至少输入角色名称")
            return
        if not personality:
            QMessageBox.warning(self, "提示", "请描述角色性格特征")
            return

        prompt = GENERATION_PROMPT_TEMPLATE.format(
            name=name,
            personality=personality,
            tone=tone if tone != "自定义" else "用户自定义",
            extra=extra if extra else "无",
        )

        self._generate_btn.setEnabled(False)
        self._generate_btn.setText("生成中...")
        self._regen_btn.setEnabled(False)
        self._preview.setPlainText("正在生成提示词，请稍候...\n\n（这可能需要几秒钟）")

        messages = [{"role": "user", "content": prompt}]

        try:
            reply = self._ai_client.ask(messages)
            self._generated_prompt = reply.strip()
            self._preview.setPlainText(self._generated_prompt)
            self._preview.setReadOnly(True)
            self._is_editing = False
            self._edit_btn.setText("✏️ 手动编辑")

            # 启用操作按钮
            self._use_btn.setEnabled(True)
            self._regen_btn.setEnabled(True)
            self._edit_btn.setEnabled(True)

            # 估算 token（粗略：中文字符 * 2 + 其他 * 1.3）
            char_count = len(self._generated_prompt)
            est_tokens = int(char_count * 1.5)
            self._token_label.setText(f"估算 Token: ~{est_tokens} | 字符数: {char_count}")

            logger.info("提示词生成成功: %d 字符", char_count)

        except Exception as e:
            logger.error("提示词生成失败: %s", e)
            self._preview.setPlainText(f"生成失败: {e}\n\n请检查网络连接或 API 配置后重试。")
            self._regen_btn.setEnabled(True)

        finally:
            self._generate_btn.setEnabled(True)
            self._generate_btn.setText("🚀 生成提示词")

    # ── 编辑切换 ────────────────────────────────────────────

    def _toggle_edit(self) -> None:
        """切换预览区的只读/编辑模式。"""
        if not self._generated_prompt:
            return

        if self._is_editing:
            # 保存编辑
            self._generated_prompt = self._preview.toPlainText().strip()
            self._preview.setReadOnly(True)
            self._edit_btn.setText("✏️ 手动编辑")
            self._is_editing = False
            self._use_btn.setEnabled(True)
            logger.debug("已保存编辑后的提示词")
        else:
            # 进入编辑模式
            self._preview.setReadOnly(False)
            self._edit_btn.setText("💾 保存编辑")
            self._is_editing = True
            self._use_btn.setEnabled(False)

    # ── 使用 ────────────────────────────────────────────────

    def _on_use(self) -> None:
        """用户确认使用当前提示词。"""
        if self._is_editing:
            self._generated_prompt = self._preview.toPlainText().strip()
        text = self._generated_prompt or self._preview.toPlainText().strip()
        if text:
            self.prompt_selected.emit(text)
            self.accept()

    # ── 工具 ────────────────────────────────────────────────

    @staticmethod
    def _shorten(text: str, max_len: int = 60) -> str:
        text = text.replace("\n", " ")
        return text[:max_len] + "…" if len(text) > max_len else text

    @staticmethod
    def check_ai_ready() -> bool:
        """检查 AI 客户端是否已配置可用。"""
        env = _parse_env_file()
        return bool(env.get("AI_API_KEY")) and bool(env.get("AI_API_BASE"))
