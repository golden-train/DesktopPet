"""
设置管理窗口。

使用 qfluentwidgets 的导航窗口，包含 AI 配置、显示设置、关于等页面。
API Key 等敏感信息写入 .env 文件（被 .gitignore 排除），确保安全性。
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QTextEdit, QMessageBox,
    QScrollArea, QFrame, QListWidget, QListWidgetItem,
    QStackedWidget, QSplitter,
)
from PySide6.QtGui import QFont

from qfluentwidgets import (
    MSFluentWindow, FluentIcon, SettingCardGroup,
    SwitchSettingCard, SettingCard, setTheme, Theme,
)

from src.core.config import ConfigManager
from src.window.main_window import MainWindow
from src.window.model_interface import ModelInterface
from src.ai.providers import PROVIDERS, get_provider_names, detect_provider
from src.widgets.prompt_manager import PromptManager
from src.widgets.skill_manager import SkillManager

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
        self.model_page = ModelInterface(self._config, self)
        self.settings_page = _SettingsPage(self._config, self._main_window, self)
        self.extend_page = _ExtendPage(self._config, self)
        self.ai_config_page = _AIConfigPage(self._config, self)
        self.help_page = _HelpPage(self)
        self.about_page = _AboutPage(self)

        # ── 注册导航项 ──────────────────────────────────────
        self.addSubInterface(self.home_page, FluentIcon.HOME, "主页")
        self.addSubInterface(self.model_page, FluentIcon.PEOPLE, "模型")
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "设置")
        self.addSubInterface(self.extend_page, FluentIcon.LEAF, "扩展")
        self.addSubInterface(self.ai_config_page, FluentIcon.ROBOT, "AI 配置")
        self.addSubInterface(self.help_page, FluentIcon.HELP, "帮助")
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

    def place_bottom(self) -> None:
        """将窗口底部对齐屏幕底部放置。"""
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen:
            self.move(
                max(0, screen.right() - self.width() - 40),
                max(0, screen.bottom() - self.height()),
            )

    def showEvent(self, event):
        super().showEvent(event)
        self.place_bottom()


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
            "桌面宠物 —— 一个常驻桌面的互动角色，支持 AI 对话和自由导入模型。\n\n"
            "功能导航：\n"
            "  • 设置 → 角色显示与音频\n"
            "  • AI 配置 → API Key / 模型 / 供应商\n"
            "  • 模型 → 选择模型，或者自定义一个模型\n"
            "  • 帮助 → 程序的使用方法，模型导入方法及要求\n"
            "  • 关于 → 版本与开源信息",
            self
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 13px; line-height: 1.6; color: #ccc;")
        self._content_layout.addWidget(info)
        self._content_layout.addStretch()


# ═══════════════════════════════════════════════════════════════
# 扩展管理页面（动态）
# ═══════════════════════════════════════════════════════════════

class _ExtendPage(_PageBase):
    """扩展管理页面——自动列出所有已发现的扩展。"""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__("扩展", "管理桌面宠物的扩展功能", parent)
        self._config = config
        self._extension_cards: list = []

        # 从注册表发现所有扩展
        from src.extends import ExtensionRegistry
        extensions = ExtensionRegistry.discover(config)

        if not extensions:
            self._content_layout.addWidget(
                QLabel("暂无扩展", self, styleSheet="color: #666; font-size: 12px;")
            )
            self._content_layout.addStretch()
            return

        for ext in extensions:
            group = SettingCardGroup(ext.icon + " " + ext.name, self)
            self._content_layout.addWidget(group)

            card = SwitchSettingCard(
                FluentIcon.POWER_BUTTON, ext.name, ext.description,
                configItem=None, parent=group,
            )
            card.switchButton.setChecked(ext.is_enabled())
            card.switchButton.checkedChanged.connect(
                lambda enabled, e=ext: self._on_extension_toggle(e, enabled)
            )
            group.addSettingCard(card)
            self._extension_cards.append(card)

        # ── 闲时语音（系统功能，非扩展） ────────────────────
        self._content_layout.addSpacing(16)
        idle_group = SettingCardGroup("闲时语音", self)
        self._content_layout.addWidget(idle_group)

        self._idle_card = SwitchSettingCard(
            FluentIcon.MUSIC, "随机闲时语音",
            "每隔一段时间自动播放随机语音",
            configItem=None, parent=idle_group,
        )
        self._idle_card.switchButton.setChecked(
            config.get("main", "is_play_idle_voice", False)
        )
        self._idle_card.switchButton.checkedChanged.connect(
            lambda c: config.set("main", "is_play_idle_voice", c)
        )
        idle_group.addSettingCard(self._idle_card)

        self._content_layout.addStretch()

    def _on_extension_toggle(self, ext, enabled: bool) -> None:
        """开关扩展时调用。"""
        ext.set_enabled(enabled)
        if enabled:
            ext.on_enable()
        else:
            ext.on_disable()
        logger.info("扩展 %s: %s", ext.name, "启用" if enabled else "禁用")


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

        # ── 主题设置 ────────────────────────────────────────
        current_theme = config.get("main", "theme", "dark")
        self._theme_card = SettingCard(
            FluentIcon.PALETTE, "界面主题",
            f"当前: {current_theme}", group,
        )
        self._theme_combo = QComboBox(self._theme_card)
        for label, value in [("深色模式", "dark"), ("浅色模式", "light"), ("跟随系统", "auto")]:
            self._theme_combo.addItem(label, value)
        self._theme_combo.setCurrentIndex(
            self._theme_combo.findData(current_theme)
        )
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self._theme_card.hBoxLayout.addStretch()
        self._theme_card.hBoxLayout.addWidget(self._theme_combo, 0, Qt.AlignRight)
        self._theme_card.hBoxLayout.addSpacing(16)
        group.addSettingCard(self._theme_card)

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

        # ── 闲时随机语音 ────────────────────────────────────
        idle_group = SettingCardGroup("闲时语音", self)
        self._content_layout.addWidget(idle_group)

        self._idle_voice_card = SwitchSettingCard(
            FluentIcon.MUSIC, "随机语音",
            "每隔一段时间自动触发随机语音", configItem=None, parent=idle_group,
        )
        self._idle_voice_card.switchButton.setChecked(
            config.get("main", "is_play_idle_voice", False)
        )
        self._idle_voice_card.switchButton.checkedChanged.connect(
            lambda c: config.set("main", "is_play_idle_voice", c)
        )
        idle_group.addSettingCard(self._idle_voice_card)

        # 间隔设置
        current_interval = config.get("main", "idle_voice_interval", 10)
        self._interval_card = SettingCard(
            FluentIcon.DATE_TIME, "语音间隔",
            f"当前: {current_interval} 分钟", idle_group,
        )
        self._interval_combo = QComboBox(self._interval_card)
        for label, mins in [("5 分钟", 5), ("10 分钟", 10), ("15 分钟", 15),
                            ("20 分钟", 20), ("30 分钟", 30), ("60 分钟", 60)]:
            self._interval_combo.addItem(label, mins)
        self._interval_combo.setCurrentIndex(
            self._interval_combo.findData(current_interval)
        )
        self._interval_combo.currentIndexChanged.connect(self._on_interval_changed)
        self._interval_card.hBoxLayout.addStretch()
        self._interval_card.hBoxLayout.addWidget(self._interval_combo, 0, Qt.AlignRight)
        self._interval_card.hBoxLayout.addSpacing(16)
        idle_group.addSettingCard(self._interval_card)

        # ── 启动设置 ────────────────────────────────────────
        startup_group = SettingCardGroup("启动", self)
        self._content_layout.addWidget(startup_group)

        is_autostart = self._is_autostart_enabled()
        self._autostart_card = SwitchSettingCard(
            FluentIcon.POWER_BUTTON, "开机自启",
            "开机后自动启动桌面宠物", configItem=None, parent=startup_group,
        )
        self._autostart_card.switchButton.setChecked(is_autostart)
        self._autostart_card.switchButton.checkedChanged.connect(
            self._on_autostart_toggled
        )
        startup_group.addSettingCard(self._autostart_card)

        self._content_layout.addStretch()

    def _on_autostart_toggled(self, enabled: bool) -> None:
        """切换开机自启。"""
        import sys
        import os

        app_path = ""
        if getattr(sys, "frozen", False):
            app_path = sys.executable
        else:
            # 开发模式：启动脚本路径
            app_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "..", "src", "main.py"
            ))

        key_name = "DesktopPet"
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            if enabled:
                winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, f'"{app_path}"')
                logger.info("开机自启已开启: %s", app_path)
            else:
                try:
                    winreg.DeleteValue(key, key_name)
                    logger.info("开机自启已关闭")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.warning("设置开机自启失败: %s", e)

    @staticmethod
    def _is_autostart_enabled() -> bool:
        """检查当前是否已设置开机自启。"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "DesktopPet")
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def _on_combo_changed(self, idx: int) -> None:
        _, value = _SCALE_OPTIONS[idx]
        label, _ = _SCALE_OPTIONS[idx]
        self._scaling_card.setContent(f"当前: {label}")
        self.scaling_changed.emit(value)

    def _on_interval_changed(self, idx: int) -> None:
        mins = self._interval_combo.itemData(idx)
        if mins:
            self._config.set("main", "idle_voice_interval", mins)
            self._interval_card.setContent(f"当前: {mins} 分钟")

    def _on_theme_changed(self, idx: int) -> None:
        theme_val = self._theme_combo.itemData(idx)
        if not theme_val:
            return
        self._config.set("main", "theme", theme_val)
        self._theme_card.setContent(f"当前: {theme_val}")

        # 应用主题
        theme_map = {"light": Theme.LIGHT, "dark": Theme.DARK, "auto": Theme.AUTO}
        qf_theme = theme_map.get(theme_val)
        if qf_theme is not None:
            setTheme(qf_theme)


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

        # ── 技能管理 ────────────────────────────────────────
        self._skill_btn = QPushButton("管理技能...", self)
        self._skill_btn.setStyleSheet("""
            QPushButton {
                background: #2d2d2d; color: #ccc;
                border: 1px solid #555; border-radius: 6px;
                padding: 8px 20px; font-size: 13px;
            }
            QPushButton:hover { background: #3d3d3d; color: #fff; }
        """)
        self._skill_btn.clicked.connect(self._open_skill_manager)
        # 添加到 model_group 下方
        self._content_layout.addWidget(self._skill_btn, 0, Qt.AlignLeft)

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

        self._generate_prompt_btn = QPushButton("AI 生成提示词...", self)
        self._generate_prompt_btn.setStyleSheet("""
            QPushButton {
                background: #1a4a6a; color: #5ba3e6;
                border: 1px solid #3a6a8a; border-radius: 4px;
                padding: 4px 12px; font-size: 12px;
            }
            QPushButton:hover { background: #2a5a7a; color: #7bc3ff; }
        """)
        self._generate_prompt_btn.clicked.connect(self._open_prompt_generator)
        self._prompt_card.hBoxLayout.addWidget(self._generate_prompt_btn, 0, Qt.AlignRight)
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
        """用户选择了提示词（来自 PromptManager 或 PromptGenerator），立即保存。"""
        self._current_prompt = prompt
        self._prompt_preview.setText(self._shorten_prompt(prompt))
        # 立即写入 .env，重启不丢失
        from src.ai.client import set_env
        set_env("AI_SYSTEM_PROMPT", prompt)
        self._mark_dirty()
        logger.info("已切换提示词")

    def _open_prompt_generator(self) -> None:
        """打开 AI 提示词生成器。"""
        if not self._check_ai_ready():
            QMessageBox.warning(self, "提示",
                "请先配置 AI 供应商和 API Key 后再使用提示词生成功能。")
            return

        # 创建临时 AIClient 用于生成
        from src.ai.client import AIClient
        client = AIClient()

        from src.widgets.prompt_generator import PromptGenerator
        dialog = PromptGenerator(client, self._current_prompt, self)
        dialog.prompt_selected.connect(self._on_prompt_changed)
        dialog.exec()

    @staticmethod
    def _check_ai_ready() -> bool:
        """检查 AI 客户端是否已可用（有 key、有 base_url）。"""
        from src.ai.client import _parse_env_file
        env = _parse_env_file()
        return bool(env.get("AI_API_KEY")) and bool(env.get("AI_API_BASE"))

    def _open_skill_manager(self) -> None:
        """打开技能预设管理对话框。"""
        dialog = SkillManager(self._config, self)
        dialog.skills_changed.connect(self._on_skills_changed)
        dialog.exec()

    def _on_skills_changed(self) -> None:
        """技能变更后刷新提示词预览。"""
        from src.ai.prompts import get_skill_prompt
        current = get_skill_prompt(self._config)
        if current != self._current_prompt:
            self._current_prompt = current
            self._prompt_preview.setText(self._shorten_prompt(current))
            self._mark_dirty()
            logger.info("技能已变更，提示词已同步")

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
# 帮助页面
# ═══════════════════════════════════════════════════════════════

class _HelpPage(_PageBase):
    """帮助页面——可选择子项，底部附 Issues 链接。"""

    _TOPICS = [
        ("📖 总体使用说明", "基本操作 / 右键菜单 / AI 对话 / 语音系统"),
        ("🧑 像素小人导入", "Standby 必需 / 动作目录 / 语音包 / model.json"),
        ("🔧 常见问题", "导入失败 / 行走灰色 / 不显示 / 语音不播"),
    ]

    def __init__(self, parent=None):
        super().__init__("帮助", "选择一个主题查看详细说明", parent)

        # ── 左右分割 ─────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #444; }")

        # ── 左侧：主题列表 ───────────────────────────────────
        self._list = QListWidget(splitter)
        self._list.setFrameShape(QFrame.NoFrame)
        self._list.setMaximumWidth(200)
        self._list.setMinimumWidth(150)
        self._list.setStyleSheet("""
            QListWidget {
                background: transparent; color: #ccc;
                font-size: 13px; border: none; outline: none;
            }
            QListWidget::item {
                padding: 14px 16px; border-radius: 6px; margin: 2px 0;
            }
            QListWidget::item:selected {
                background: #3a6ea5; color: #fff;
            }
            QListWidget::item:hover:!selected {
                background: #2a2a3a;
            }
        """)
        for i, (title, desc) in enumerate(self._TOPICS):
            item = QListWidgetItem(title)
            item.setToolTip(desc)
            item.setSizeHint(QSize(0, 50))
            self._list.addItem(item)
        self._list.setCurrentRow(0)

        # ── 右侧：QStackedWidget ─────────────────────────────
        right_panel = QWidget(splitter)
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(0)

        self._stack = QStackedWidget(right_panel)
        self._stack.setStyleSheet("background: transparent;")

        pages = [
            self._page_usage,
            self._page_pixel_import,
            self._page_faq,
        ]
        for i, build_fn in enumerate(pages):
            page = self._build_page(build_fn)
            self._stack.addWidget(page)

        rp_layout.addWidget(self._stack, 1)

        # ── 底部：GitHub Issues ──────────────────────────────
        footer = QFrame(right_panel)
        footer.setFixedHeight(40)
        footer.setStyleSheet("background: transparent; border-top: 1px solid #333;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 4, 12, 4)
        issue_link = QLabel(
            '💡 遇到问题或有建议？请提交 '
            '<a href="https://github.com/golden-train/DesktopPet/issues" '
            'style="color: #5ba3e6; text-decoration: none;">GitHub Issues</a>',
            footer,
        )
        issue_link.setOpenExternalLinks(True)
        issue_link.setStyleSheet("color: #888; font-size: 12px;")
        fl.addWidget(issue_link)
        fl.addStretch()
        rp_layout.addWidget(footer)

        # ── 组装 ─────────────────────────────────────────────
        splitter.addWidget(self._list)
        splitter.addWidget(right_panel)
        splitter.setSizes([170, 500])
        self._content_layout.addWidget(splitter, 1)

        # 连接信号
        self._list.currentRowChanged.connect(self._on_topic_changed)


    # ── 构建页面 ────────────────────────────────────────────

    def _build_page(self, content_builder) -> QWidget:
        page = QWidget(self._stack)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; }"
            "QScrollBar:vertical { width: 6px; }"
        )
        inner = QWidget(scroll)
        inner.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(inner)
        cl.setContentsMargins(8, 4, 16, 4)
        cl.setSpacing(12)

        content_builder(cl, inner)

        cl.addStretch()
        scroll.setWidget(inner)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return page

    # ── 第1页：总体使用说明 ───────────────────────────────

    def _page_usage(self, cl, parent):
        cl.addWidget(self._sub_title("基本操作"))
        cl.addWidget(self._text(
            "• 鼠标左键点击角色 → 触发互动动画（上半区比心，下半区蹭蹭）<br>"
            "• 鼠标左键拖拽 → 移动角色到任意位置<br>"
            "• 鼠标右键 → 弹出功能菜单<br>"
            "• 鼠标滚轮或双击 → 触发特殊动作"
        ))
        cl.addWidget(self._sub_title("右键菜单"))
        cl.addWidget(self._text(
            "• 打开聊天 → 与 AI 角色对话（需先配置 API Key）<br>"
            "• 自由行走 → 角色在屏幕边缘自动来回行走<br>"
            "• 设置... → 打开详细设置窗口<br>"
            "• 退出 → 关闭程序"
        ))
        cl.addWidget(self._sub_title("AI 对话"))
        cl.addWidget(self._text(
            "1. 右键 → 设置 → AI 配置，填写 API Key 和接口地址<br>"
            "2. 右键 → 打开聊天，即可与角色对话<br>"
            "3. AI 回复中嵌入 [动作名] 可自动触发角色动画<br>"
            "4. 在 AI 配置页可使用「AI 生成提示词」快速创建角色设定"
        ))
        cl.addWidget(self._sub_title("语音系统"))
        cl.addWidget(self._text(
            "• 设置 → 音频 → 开启启动/关闭语音<br>"
            "• 扩展 → 电池语音 → 插入/拔掉电源时自动播报<br>"
            "• 扩展 → 闲时语音 → 角色每隔一段时间随机说话"
        ))

    # ── 第2页：像素小人导入 ───────────────────────────────

    def _page_pixel_import(self, cl, parent):
        cl.addWidget(self._text(
            "在 设置 → 模型 → 导入新角色，选择包含以下结构的文件夹："
        ))
        cl.addWidget(self._code(
            "你的模型/\n"
            "├── actions/          ← 必需\n"
            "│   ├── Standby/      ← 必需（待机动画）\n"
            "│   │   ├── 0.png\n"
            "│   │   └── 1.png\n"
            "│   ├── love/         ← 可选\n"
            "│   ├── left/         ← 可选（与 right 同时存在才支持行走）\n"
            "│   └── right/        ← 可选\n"
            "├── model.json        ← 推荐（角色元数据）\n"
            "├── icon/icon.png     ← 可选（缩略图）\n"
            "└── voice/            ← 可选（语音包）"
        ))
        cl.addWidget(self._text(
            "支持 PNG/JPG/WebP/GIF 图片格式，WAV/MP3/Ogg 音频格式。<br>"
            "导入后可在模型页面切换角色，不支持行走的角色会自动禁用行走菜单。"
        ))
        cl.addWidget(self._sub_title("model.json 模板"))
        cl.addWidget(self._code(
            "{\n"
            '    "name": "角色名",\n'
            '    "version": "1.0",\n'
            '    "author": "作者",\n'
            '    "description": "简短描述",\n'
            '    "has_walking": true\n'
            "}"
        ))
        cl.addWidget(self._text(
            "将以上内容保存为 ``model.json`` 放在模型根目录，导入时系统自动读取角色信息。"
        ))

    # ── 第4页：常见问题 ───────────────────────────────────

    def _page_faq(self, cl, parent):
        cl.addWidget(self._text(
            "<b>导入提示缺少 Standby？</b><br>"
            "actions/Standby/ 目录是必需的，放入至少一张 PNG 图片。<br><br>"
            "<b>行走菜单灰色不可用？</b><br>"
            "角色缺少 left 和 right 动作目录，只有两者都有才支持行走。<br><br>"
            "<b>导入后不显示？</b><br>"
            "检查图片格式（PNG/JPG/WebP），尝试在设置中调整缩放倍数。<br><br>"
            "<b>自定义语音不播放？</b><br>"
            "使用 .wav 格式（兼容性最好），确保文件放在对应目录下。"
        ))

    # ── 信号 ────────────────────────────────────────────────

    def _on_topic_changed(self, row: int) -> None:
        if 0 <= row < self._stack.count():
            self._stack.setCurrentIndex(row)

    # ── 样式辅助 ────────────────────────────────────────────

    @staticmethod
    def _sub_title(text: str) -> QLabel:
        lbl = QLabel(text)
        tf = QFont()
        tf.setPointSize(13)
        tf.setBold(True)
        lbl.setFont(tf)
        lbl.setStyleSheet("color: #5ba3e6; padding: 4px 0;")
        return lbl

    @staticmethod
    def _text(html: str) -> QLabel:
        lbl = QLabel(html)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #bbb; font-size: 13px; line-height: 1.7;")
        return lbl

    @staticmethod
    def _code(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            "color: #8ab4f8; font-size: 12px; font-family: Consolas, monospace;"
            "background: #1a1a2a; border: 1px solid #333; border-radius: 6px;"
            "padding: 12px; line-height: 1.5;"
        )
        return lbl


# ═══════════════════════════════════════════════════════════════
# 关于页面
# ═══════════════════════════════════════════════════════════════

class _AboutPage(_PageBase):
    def __init__(self, parent=None):
        super().__init__("关于", "DesktopPet 项目信息", parent)
        info = QLabel(self)
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        info.setText(
            "DesktopPet v1.0.0"
            "基于 PySide6 + qfluentwidgets + OpenAI SDK 构建<br>"
            "遵循 AGPL 协议开源<br><br>"
            'GitHub项目地址: <a href="https://github.com/golden-train/DesktopPet" '
            'style="color: #5ba3e6; text-decoration: none;">'
            "github.com/golden-train/DesktopPet</a>"
            "本项目灵感来源于Github PYmili老师https://github.com/PYmili/MyFlowingFireflyWife项目，但是技术路线不完全相同，同时在其已经实现的基础上增加了许多新功能同时适配了AI对话"

        )
        info.setStyleSheet("font-size: 13px; color: #ccc;")
        self._content_layout.addWidget(info)
        self._content_layout.addStretch()
