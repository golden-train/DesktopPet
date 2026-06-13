"""
设置管理窗口。

使用 qfluentwidgets 的导航窗口，包含 AI 配置、显示设置、关于等页面。
API Key 等敏感信息写入 .env 文件（被 .gitignore 排除），确保安全性。
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QTextEdit, QMessageBox,
)
from PySide6.QtGui import QFont

from qfluentwidgets import (
    MSFluentWindow, FluentIcon, SettingCardGroup,
    SwitchSettingCard, SettingCard,
)

from src.core.config import ConfigManager
from src.window.main_window import MainWindow
from src.ai.providers import PROVIDERS, get_provider_names, detect_provider
from src.widgets.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

# 缩放选项：标签 → 倍数
_SCALE_OPTIONS = [
    ("极小 (0.25x)", 0.25),
    ("小 (0.5x)", 0.5),
    ("较小 (0.75x)", 0.75),
    ("原始大小", 1.0),
    ("1.5 倍", 1.5),
    ("2 倍", 2.0),
    ("3 倍", 3.0),
    ("4 倍", 4.0),
    ("6 倍", 6.0),
    ("8 倍", 8.0),
]


class ManagementWindow(MSFluentWindow):
    """设置管理窗口。"""

    # AI 配置变更时发出，通知主控制器重载 AIClient
    ai_config_changed = Signal()

    def __init__(self, config: ConfigManager, main_window: Optional[MainWindow] = None):
        super().__init__()
        self._config = config
        self._main_window = main_window

        self.setWindowTitle("桌面宠物 - 设置")
        self.setMinimumSize(760, 580)
        # 关闭此窗口不应退出程序
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.home_page = _HomePage(self)
        self.settings_page = _SettingsPage(self._config, self._main_window, self)
        self.ai_config_page = _AIConfigPage(self._config, self)
        self.about_page = _AboutPage(self)

        # ── 注册导航项 ──────────────────────────────────────
        self.addSubInterface(self.home_page, FluentIcon.HOME, "主页")
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "设置")
        self.addSubInterface(self.ai_config_page, FluentIcon.ROBOT, "AI 配置")
        self.addSubInterface(self.about_page, FluentIcon.INFO, "关于")

        # ── 信号连接 ────────────────────────────────────────
        self.settings_page.scaling_changed.connect(self._on_scaling_changed)
        self.ai_config_page.config_saved.connect(self._on_ai_config_saved)

    def _on_scaling_changed(self, value: float) -> None:
        if self._main_window:
            self._main_window.set_scaling(value)
        self._config.set("main", "scaling", value)

    def _on_ai_config_saved(self) -> None:
        """AI 配置保存后重载主控制器的 AIClient。"""
        self.ai_config_changed.emit()

    def center_on_screen(self) -> None:
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen:
            self.move(
                screen.center().x() - self.width() // 2,
                screen.center().y() - self.height() // 2,
            )

    def showEvent(self, event):
        super().showEvent(event)
        self.center_on_screen()


# ═══════════════════════════════════════════════════════════════
# 页面基类
# ═══════════════════════════════════════════════════════════════

class _PageBase(QWidget):
    """页面基类——带标题头。"""

    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setObjectName(title)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(32, 24, 32, 24)
        self._layout.setSpacing(16)

        title_label = QLabel(title, self)
        tf = QFont()
        tf.setPointSize(18)
        tf.setBold(True)
        title_label.setFont(tf)
        self._layout.addWidget(title_label)

        if subtitle:
            sub = QLabel(subtitle, self)
            sub.setStyleSheet("color: #888; font-size: 12px;")
            self._layout.addWidget(sub)

        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(12)
        self._layout.addLayout(self._content_layout)


# ═══════════════════════════════════════════════════════════════
# 主页
# ═══════════════════════════════════════════════════════════════

class _HomePage(_PageBase):
    def __init__(self, parent=None):
        super().__init__("主页", "欢迎使用桌面宠物", parent)
        info = QLabel(
            "桌面宠物 —— 一个常驻桌面的互动角色，支援 AI 对话、Live2D 模型、电池状态语音提醒。\n\n"
            "当前阶段：Phase 3 — AI 对话\n\n"
            "功能导航：\n"
            "  • 设置 → 角色显示与音频\n"
            "  • AI 配置 → API Key / 模型 / 供应商\n"
            "  • 关于 → 版本与开源信息",
            self
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 13px; line-height: 1.6; color: #ccc;")
        self._content_layout.addWidget(info)
        self._content_layout.addStretch()


# ═══════════════════════════════════════════════════════════════
# 设置页面
# ═══════════════════════════════════════════════════════════════

class _SettingsPage(_PageBase):
    """设置页面——人物缩放、音频开关。"""

    scaling_changed = Signal(float)

    def __init__(self, config: ConfigManager, main_window: Optional[MainWindow],
                 parent=None):
        super().__init__("设置", "调整桌面宠物的显示与行为", parent)
        self._config = config

        # ── 显示设置 ────────────────────────────────────────
        group = SettingCardGroup("显示", self)
        self._content_layout.addWidget(group)

        current_scale = config.get("main", "scaling", 1.0)
        scale_label = {v: k for k, v in _SCALE_OPTIONS}
        closest = min(_SCALE_OPTIONS, key=lambda x: abs(x[1] - current_scale))

        self._scaling_card = SettingCard(
            FluentIcon.ZOOM, "人物缩放",
            f"当前: {scale_label.get(closest[1], closest[1])}", group,
        )
        self._scaling_combo = QComboBox(self._scaling_card)
        for label, _ in _SCALE_OPTIONS:
            self._scaling_combo.addItem(label)
        self._scaling_combo.setCurrentText(scale_label.get(closest[1], "原始大小"))
        self._scaling_combo.currentIndexChanged.connect(self._on_combo_changed)
        self._scaling_card.hBoxLayout.addStretch()
        self._scaling_card.hBoxLayout.addWidget(self._scaling_combo, 0, Qt.AlignRight)
        self._scaling_card.hBoxLayout.addSpacing(16)
        group.addSettingCard(self._scaling_card)

        # ── 音频设置 ────────────────────────────────────────
        audio_group = SettingCardGroup("音频", self)
        self._content_layout.addWidget(audio_group)

        self._voice_start_card = SwitchSettingCard(
            FluentIcon.VOLUME, "启动音频",
            "每次启动时播放问候语音", configItem=None, parent=audio_group,
        )
        self._voice_start_card.switchButton.setChecked(
            config.get("main", "is_play_VoiceOnStart", False)
        )
        self._voice_start_card.switchButton.checkedChanged.connect(
            lambda c: config.set("main", "is_play_VoiceOnStart", c)
        )
        audio_group.addSettingCard(self._voice_start_card)

        self._voice_close_card = SwitchSettingCard(
            FluentIcon.MUTE, "关闭音频",
            "关闭时播放告别语音", configItem=None, parent=audio_group,
        )
        self._voice_close_card.switchButton.setChecked(
            config.get("main", "is_play_VoiceOnClose", False)
        )
        self._voice_close_card.switchButton.checkedChanged.connect(
            lambda c: config.set("main", "is_play_VoiceOnClose", c)
        )
        audio_group.addSettingCard(self._voice_close_card)

        self._content_layout.addStretch()

    def _on_combo_changed(self, idx: int) -> None:
        _, value = _SCALE_OPTIONS[idx]
        label, _ = _SCALE_OPTIONS[idx]
        self._scaling_card.setContent(f"当前: {label}")
        self.scaling_changed.emit(value)


# ═══════════════════════════════════════════════════════════════
# AI 配置页面
# ═══════════════════════════════════════════════════════════════

class _AIConfigPage(_PageBase):
    """AI 配置页面——供应商、API Key、模型、系统提示词。"""

    config_saved = Signal()

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__("AI 配置", "配置 AI 对话的供应商、模型与密钥", parent)
        self._config = config
        self._saved = False  # 标记是否有未保存变更

        # ── 读取当前 .env 值 ────────────────────────────────
        from src.ai.client import _parse_env_file
        env = _parse_env_file()
        current_key = env.get("AI_API_KEY", "")
        current_base = env.get("AI_API_BASE", "https://api.deepseek.com")
        current_model = env.get("AI_MODEL", "deepseek-chat")

        # ── 供应商 ──────────────────────────────────────────
        provider_group = SettingCardGroup("AI 供应商", self)
        self._content_layout.addWidget(provider_group)

        self._provider_card = SettingCard(
            FluentIcon.ROBOT, "供应商",
            "选择后自动填写 API 地址和推荐模型", provider_group,
        )
        self._provider_combo = QComboBox(self._provider_card)
        provider_names = get_provider_names()
        self._provider_combo.addItems(provider_names)
        self._provider_combo.addItem("自定义")
        # 自动匹配
        matched = detect_provider(current_base)
        if matched:
            self._provider_combo.setCurrentText(matched)
        else:
            self._provider_combo.setCurrentText("自定义")
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        self._provider_card.hBoxLayout.addStretch()
        self._provider_card.hBoxLayout.addWidget(self._provider_combo, 0, Qt.AlignRight)
        self._provider_card.hBoxLayout.addSpacing(16)
        provider_group.addSettingCard(self._provider_card)

        # ── API Key ─────────────────────────────────────────
        api_group = SettingCardGroup("身份认证", self)
        self._content_layout.addWidget(api_group)

        self._key_card = SettingCard(
            FluentIcon.CODE, "API Key",
            "存储在 .env 文件中，不会被 Git 追踪", api_group,
        )
        self._key_input = QLineEdit(self._key_card)
        self._key_input.setPlaceholderText("sk-xxx...")
        self._key_input.setEchoMode(QLineEdit.Password)
        self._key_input.setText(self._mask_key(current_key) if current_key else "")
        self._key_input.setMinimumWidth(260)
        self._key_input.textChanged.connect(self._mark_dirty)
        self._key_card.hBoxLayout.addStretch()
        self._key_card.hBoxLayout.addWidget(self._key_input, 0, Qt.AlignRight)
        self._key_card.hBoxLayout.addSpacing(16)
        api_group.addSettingCard(self._key_card)

        # ── API 地址 ────────────────────────────────────────
        self._url_card = SettingCard(
            FluentIcon.LINK, "API 地址",
            "OpenAI 兼容接口地址", api_group,
        )
        self._url_input = QLineEdit(self._url_card)
        self._url_input.setText(current_base)
        self._url_input.setMinimumWidth(360)
        self._url_input.textChanged.connect(self._mark_dirty)
        self._url_card.hBoxLayout.addStretch()
        self._url_card.hBoxLayout.addWidget(self._url_input, 0, Qt.AlignRight)
        self._url_card.hBoxLayout.addSpacing(16)
        api_group.addSettingCard(self._url_card)

        # ── 模型 ────────────────────────────────────────────
        model_group = SettingCardGroup("模型", self)
        self._content_layout.addWidget(model_group)

        self._model_card = SettingCard(
            FluentIcon.CHAT, "模型名称",
            "选择或手动输入模型 ID", model_group,
        )
        self._model_combo = QComboBox(self._model_card)
        self._model_combo.setEditable(True)
        self._model_combo.setInsertPolicy(QComboBox.NoInsert)
        self._model_combo.setMinimumWidth(240)
        self._populate_models(current_base, current_model)
        self._model_combo.currentTextChanged.connect(self._mark_dirty)
        self._model_card.hBoxLayout.addStretch()
        self._model_card.hBoxLayout.addWidget(self._model_combo, 0, Qt.AlignRight)
        self._model_card.hBoxLayout.addSpacing(16)
        model_group.addSettingCard(self._model_card)

        # ── 系统提示词 ──────────────────────────────────────
        from src.ai.prompts import get_skill_prompt
        self._current_prompt = env.get("AI_SYSTEM_PROMPT", "")
        if not self._current_prompt:
            self._current_prompt = get_skill_prompt(self._config)

        prompt_group = SettingCardGroup("系统提示词", self)
        self._content_layout.addWidget(prompt_group)

        self._prompt_card = SettingCard(
            FluentIcon.EDIT, "系统提示词",
            "定义 AI 的角色和行为风格（点击管理可新增自定义提示词）",
            prompt_group,
        )
        # 提示词预览（显示前 60 字）
        self._prompt_preview = QLabel(self._shorten_prompt(self._current_prompt), self)
        self._prompt_preview.setStyleSheet("color: #aaa; font-size: 12px; padding: 4px;")
        self._prompt_preview.setMaximumWidth(300)
        self._prompt_card.hBoxLayout.addStretch()
        self._prompt_card.hBoxLayout.addWidget(self._prompt_preview, 0, Qt.AlignRight)

        self._manage_prompt_btn = QPushButton("管理提示词...", self)
        self._manage_prompt_btn.setStyleSheet("""
            QPushButton {
                background: #2d2d2d; color: #ccc;
                border: 1px solid #555; border-radius: 4px;
                padding: 4px 12px; font-size: 12px;
            }
            QPushButton:hover { background: #3d3d3d; color: #fff; }
        """)
        self._manage_prompt_btn.clicked.connect(self._open_prompt_manager)
        self._prompt_card.hBoxLayout.addWidget(self._manage_prompt_btn, 0, Qt.AlignRight)
        self._prompt_card.hBoxLayout.addSpacing(16)
        prompt_group.addSettingCard(self._prompt_card)

        # ── 操作按钮 ────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._test_btn = QPushButton("测试连接", self)
        self._test_btn.setStyleSheet("""
            QPushButton { background:#2d2d2d; color:#ccc; border:1px solid #555;
                          border-radius:6px; padding:8px 24px; font-size:13px; }
            QPushButton:hover { background:#3d3d3d; color:#fff; }
        """)
        self._test_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(self._test_btn)

        self._save_btn = QPushButton("保存配置", self)
        self._save_btn.setStyleSheet("""
            QPushButton { background:#005fb8; color:white; border:none;
                          border-radius:6px; padding:8px 24px; font-size:13px; }
            QPushButton:hover { background:#0078d4; }
        """)
        self._save_btn.clicked.connect(self._save_config)
        btn_layout.addWidget(self._save_btn)
        self._content_layout.addLayout(btn_layout)

        self._content_layout.addStretch()

    # ── 供应商切换 ──────────────────────────────────────────

    def _on_provider_changed(self, name: str) -> None:
        if name == "自定义":
            return
        info = PROVIDERS.get(name)
        if not info:
            return
        self._url_input.setText(info.base_url)
        self._populate_models(info.base_url, info.models[0] if info.models else "")

    def _populate_models(self, base_url: str, selected: str) -> None:
        """填充模型下拉列表，尽量保留当前选中值。"""
        self._model_combo.blockSignals(True)
        self._model_combo.clear()

        # 查找匹配供应商的推荐模型
        for info in PROVIDERS.values():
            if info.base_url.rstrip("/") == base_url.rstrip("/"):
                for m in info.models:
                    self._model_combo.addItem(m)
                break
        # 如果当前模型不在列表中，也加上
        if selected and self._model_combo.findText(selected) == -1:
            self._model_combo.addItem(selected)
        if selected:
            self._model_combo.setCurrentText(selected)
        elif self._model_combo.count() > 0:
            self._model_combo.setCurrentIndex(0)
        self._model_combo.blockSignals(False)

    # ── API Key 安全显示 ────────────────────────────────────

    @staticmethod
    @staticmethod
    def _shorten_prompt(prompt: str, max_len: int = 60) -> str:
        """截断提示词用于预览显示。"""
        text = prompt.replace("\n", " ")
        return text[:max_len] + "…" if len(text) > max_len else text

    def _open_prompt_manager(self) -> None:
        """打开提示词管理对话框。"""
        dialog = PromptManager(self._config, self._current_prompt, self)
        dialog.prompt_selected.connect(self._on_prompt_changed)
        dialog.exec()

    def _on_prompt_changed(self, prompt: str) -> None:
        """用户从 PromptManager 选择了提示词。"""
        self._current_prompt = prompt
        self._prompt_preview.setText(self._shorten_prompt(prompt))
        self._mark_dirty()
        logger.info("已切换提示词")

    @staticmethod
    def _mask_key(key: str) -> str:
        """脱敏显示：sk-abc...xyz"""
        if len(key) > 12:
            return key[:7] + "..." + key[-4:]
        return key if len(key) <= 4 else key[:3] + "..."

    # ── 保存 ────────────────────────────────────────────────

    def _mark_dirty(self):
        self._saved = True

    def _save_config(self) -> None:
        """将 AI 配置写入 .env（安全区域，不被 Git 追踪）。"""
        from src.ai.client import set_env

        key_value = self._key_input.text().strip()
        url_value = self._url_input.text().strip()
        model_value = self._model_combo.currentText().strip()
        prompt_value = self._current_prompt.strip()

        if not url_value:
            QMessageBox.warning(self, "提示", "API 地址不能为空")
            return
        if not model_value:
            QMessageBox.warning(self, "提示", "模型名称不能为空")
            return

        # 只写入 .env，绝不写入 JSON 配置
        if key_value:
            # 如果输入的是脱敏值（含...），说明没改过，不要覆盖
            if "..." not in key_value or len(key_value) < 12:
                set_env("AI_API_KEY", key_value)
            else:
                logger.info("API Key 未变更，跳过写入")

        set_env("AI_API_BASE", url_value)
        set_env("AI_MODEL", model_value)
        if prompt_value:
            set_env("AI_SYSTEM_PROMPT", prompt_value)

        self._saved = False
        QMessageBox.information(self, "成功", "AI 配置已保存！")
        self.config_saved.emit()

    # ── 测试连接 ────────────────────────────────────────────

    def _test_connection(self) -> None:
        """用当前输入尝试一次简单 API 调用验证连通性。"""
        base = self._url_input.text().strip()
        model = self._model_combo.currentText().strip()
        key = self._key_input.text().strip()

        if not base or not model:
            QMessageBox.warning(self, "提示", "请先填写 API 地址和模型名称")
            return
        if not key or "..." in key:
            from src.ai.client import _parse_env_file
            env = _parse_env_file()
            key = env.get("AI_API_KEY", "")
            if not key:
                QMessageBox.warning(self, "提示", "请填写 API Key")
                return

        from openai import OpenAI
        self._test_btn.setEnabled(False)
        self._test_btn.setText("测试中…")
        QMessageBox.information(self, "测试", "正在测试连接，这可能需要几秒钟…")

        try:
            client = OpenAI(api_key=key, base_url=base)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "你好，回复一个'ok'即可"}],
                timeout=15,
            )
            reply = response.choices[0].message.content or ""
            QMessageBox.information(
                self, "连接成功", f"AI 服务连接正常！\n模型回复: {reply[:60]}"
            )
        except Exception as e:
            QMessageBox.warning(self, "连接失败", f"无法连接 AI 服务:\n{e}")
        finally:
            self._test_btn.setEnabled(True)
            self._test_btn.setText("测试连接")


# ═══════════════════════════════════════════════════════════════
# 关于页面
# ═══════════════════════════════════════════════════════════════

class _AboutPage(_PageBase):
    def __init__(self, parent=None):
        super().__init__("关于", "DesktopPet 项目信息", parent)
        info = QLabel(
            "DesktopPet v0.3.0 — Phase 3\n\n"
            "基于 PySide6 + qfluentwidgets + OpenAI SDK 构建\n"
            "遵循 GPL 协议开源\n\n"
            "GitHub: https://github.com/your/DesktopPet",
            self
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 13px; color: #ccc;")
        self._content_layout.addWidget(info)
        self._content_layout.addStretch()
