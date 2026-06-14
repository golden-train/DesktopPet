"""
导入引导向导对话框。

分 6 步引导用户完成角色模型或 Live2D 模型的导入。
"""

import logging
import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QTextEdit, QLineEdit,
    QWidget, QFrame, QMessageBox, QSizePolicy, QScrollArea,
)

from src.core.config import ConfigManager
from src.model.validator import ModelValidator
from src.model.importer import ModelImporter
from src.model.registry import ModelRegistry

logger = logging.getLogger(__name__)

# ── 样式 ──────────────────────────────────────────────────

_STEP_LABEL_STYLE = """
    font-size: 14px; font-weight: bold; color: #5ba3e6;
    padding: 4px 0;
"""
_TITLE_STYLE = "font-size: 16px; font-weight: bold; color: #e0e0e0;"
_DESC_STYLE = "color: #999; font-size: 12px; margin: 4px 0;"
_CARD_STYLE = """
    QFrame {{
        background: {bg}; border: 2px solid {border};
        border-radius: 10px; padding: 20px;
    }}
    QFrame:hover {{
        border: 2px solid #5ba3e6;
    }}
"""
_CARD_SELECTED = "#2a3a4a"
_CARD_NORMAL = "#2d2d2d"
_BORDER_SELECTED = "#5ba3e6"
_BORDER_NORMAL = "transparent"

_BTN_PRIMARY = """
    QPushButton {
        background: #005fb8; color: #fff; border: none;
        border-radius: 6px; padding: 8px 24px; font-size: 13px;
    }
    QPushButton:hover { background: #0078d4; }
    QPushButton:disabled { background: #444; color: #888; }
"""
_BTN_SECONDARY = """
    QPushButton {
        background: #3a3a3a; color: #ccc; border: 1px solid #555;
        border-radius: 6px; padding: 8px 24px; font-size: 13px;
    }
    QPushButton:hover { background: #4a4a4a; color: #fff; }
    QPushButton:disabled { background: #2a2a2a; color: #666; }
"""
_BTN_DANGER = """
    QPushButton {
        background: #8a2a2a; color: #fff; border: none;
        border-radius: 6px; padding: 8px 24px; font-size: 13px;
    }
    QPushButton:hover { background: #aa3a3a; }
"""
_PROGRESS_STYLE = """
    QProgressBar {
        border: 1px solid #555; border-radius: 6px;
        background: #2d2d2d; text-align: center;
        color: #ccc; font-size: 12px; height: 20px;
    }
    QProgressBar::chunk {
        background: #5ba3e6; border-radius: 5px;
    }
"""
_VALID_GREEN = "color: #4caf50; font-size: 13px;"
_VALID_YELLOW = "color: #ff9800; font-size: 13px;"
_VALID_RED = "color: #f44336; font-size: 13px;"


class ImportWizard(QDialog):
    """分步引导用户完成模型导入的向导对话框。"""

    # 导入完成信号，参数: model_id
    model_imported = Signal(str)

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._current_step: int = 0  # 0-based
        self._max_steps: int = 6

        # 状态数据
        self._import_type: Optional[str] = None  # "pixel" | "live2d"
        self._source_dir: str = ""
        self._validation_report: dict = {}
        self._target_id: str = ""
        self._import_result: Optional[dict] = None

        self.setWindowTitle("导入模型")
        self.setMinimumSize(640, 520)
        self.setAttribute(Qt.WA_QuitOnClose, False)

        self._setup_ui()
        self._render_step(0)

    # ── UI 初始化 ───────────────────────────────────────────

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # ── 步骤指示器 ──────────────────────────────────────
        self._step_label = QLabel("步骤 1 / 6", self)
        self._step_label.setStyleSheet(_STEP_LABEL_STYLE)
        main_layout.addWidget(self._step_label)

        # ── 内容区（滚轮支持） ───────────────────────────────
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self._content_widget = QWidget(scroll)
        self._content_widget.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 8, 0)
        self._content_layout.setSpacing(16)
        scroll.setWidget(self._content_widget)
        main_layout.addWidget(scroll, 1)

        # ── 底部按钮区 ──────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._back_btn = QPushButton("上一步", self)
        self._back_btn.setStyleSheet(_BTN_SECONDARY)
        self._back_btn.clicked.connect(self._on_back)
        btn_layout.addWidget(self._back_btn)

        btn_layout.addStretch()

        self._cancel_btn = QPushButton("取消", self)
        self._cancel_btn.setStyleSheet(_BTN_SECONDARY)
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        self._next_btn = QPushButton("下一步", self)
        self._next_btn.setStyleSheet(_BTN_PRIMARY)
        self._next_btn.clicked.connect(self._on_next)
        btn_layout.addWidget(self._next_btn)

        main_layout.addLayout(btn_layout)

    # ── 步骤渲染 ────────────────────────────────────────────

    def _clear_content(self) -> None:
        """清空内容区。"""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_step(self, step: int) -> None:
        """渲染指定步骤的内容。"""
        self._current_step = step
        self._step_label.setText(f"步骤 {step + 1} / {self._max_steps}")
        self._clear_content()

        # 更新按钮状态
        self._back_btn.setEnabled(step > 0)
        is_last = step == self._max_steps - 1
        self._next_btn.setText("完成" if is_last else "下一步")

        steps = [
            self._render_step1_select_type,
            self._render_step2_select_dir,
            self._render_step3_validate,
            self._render_step4_confirm,
            self._render_step5_progress,
            self._render_step6_complete,
        ]
        if 0 <= step < len(steps):
            steps[step]()

    # ── Step 1: 选择类型 ────────────────────────────────────

    def _render_step1_select_type(self) -> None:
        """选择导入类型：像素小人 / Live2D 模型。"""
        title = QLabel("请选择你要导入的模型类型：", self._content_widget)
        title.setStyleSheet(_TITLE_STYLE)
        self._content_layout.addWidget(title)

        desc = QLabel(
            "不同类型的模型有不同的目录结构和资源要求。",
            self._content_widget
        )
        desc.setStyleSheet(_DESC_STYLE)
        self._content_layout.addWidget(desc)

        self._content_layout.addSpacing(16)

        # 像素小人卡片
        pixel_card = QFrame(self._content_widget)
        pixel_card.setCursor(Qt.PointingHandCursor)
        pixel_card.setProperty("type", "pixel")
        pixel_card.setStyleSheet(_CARD_STYLE.format(
            bg=_CARD_SELECTED if self._import_type == "pixel" else _CARD_NORMAL,
            border=_BORDER_SELECTED if self._import_type == "pixel" else _BORDER_NORMAL,
        ))
        pixel_layout = QVBoxLayout(pixel_card)

        pixel_title = QLabel("🧑 像素小人角色", pixel_card)
        pixel_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0;")
        pixel_layout.addWidget(pixel_title)

        pixel_requirements = QLabel(
            "需要准备:\n"
            "  • PNG/WebP 序列帧文件夹\n"
            "  • Standby 动作目录（必需）\n"
            "  • WAV/MP3/Ogg 语音包（可选）\n"
            "  • model.json 元数据（推荐）",
            pixel_card,
        )
        pixel_requirements.setStyleSheet("color: #aaa; font-size: 12px; line-height: 1.6;")
        pixel_layout.addWidget(pixel_requirements)

        pixel_card.mousePressEvent = lambda e, t="pixel": self._select_type(t)
        self._content_layout.addWidget(pixel_card)

        self._content_layout.addSpacing(8)

        # Live2D 卡片
        live2d_card = QFrame(self._content_widget)
        live2d_card.setCursor(Qt.PointingHandCursor)
        live2d_card.setProperty("type", "live2d")
        live2d_card.setStyleSheet(_CARD_STYLE.format(
            bg=_CARD_SELECTED if self._import_type == "live2d" else _CARD_NORMAL,
            border=_BORDER_SELECTED if self._import_type == "live2d" else _BORDER_NORMAL,
        ))
        l2d_layout = QVBoxLayout(live2d_card)

        l2d_title = QLabel("🎭 Live2D 模型", live2d_card)
        l2d_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0;")
        l2d_layout.addWidget(l2d_title)

        l2d_requirements = QLabel(
            "需要准备:\n"
            "  • .model3.json 配置文件\n"
            "  • 贴图文件（.png/.jpg）\n"
            "  • 动作 .motion3.json（可选）\n"
            "  • 语音文件（可选）",
            live2d_card,
        )
        l2d_requirements.setStyleSheet("color: #aaa; font-size: 12px; line-height: 1.6;")
        l2d_layout.addWidget(l2d_requirements)

        live2d_card.mousePressEvent = lambda e, t="live2d": self._select_type(t)
        self._content_layout.addWidget(live2d_card)

        self._content_layout.addSpacing(8)

        note = QLabel(
            "⚠ 注意：像素小人角色和 Live2D 模型是不同类型，导入后不能混用。",
            self._content_widget,
        )
        note.setStyleSheet("color: #ff9800; font-size: 12px;")
        self._content_layout.addWidget(note)

        self._content_layout.addStretch()

        # 下一步按钮状态
        self._next_btn.setEnabled(self._import_type is not None)

    def _select_type(self, import_type: str) -> None:
        """选择导入类型。"""
        self._import_type = import_type
        logger.debug("选择导入类型: %s", import_type)
        # 重新渲染以更新高亮
        self._render_step(self._current_step)

    # ── Step 2: 选择源目录 ──────────────────────────────────

    def _render_step2_select_dir(self) -> None:
        """选择源目录。"""
        title = QLabel("选择模型源目录", self._content_widget)
        title.setStyleSheet(_TITLE_STYLE)
        self._content_layout.addWidget(title)

        type_label = {
            "pixel": "像素小人角色",
            "live2d": "Live2D 模型",
        }
        desc = QLabel(
            f"当前类型: {type_label.get(self._import_type, '未知')}\n"
            "请选择包含模型文件的文件夹（包含 actions/ 或 .model3.json 的目录）。",
            self._content_widget,
        )
        desc.setStyleSheet(_DESC_STYLE)
        desc.setWordWrap(True)
        self._content_layout.addWidget(desc)

        self._content_layout.addSpacing(16)

        # 目录选择
        dir_layout = QHBoxLayout()
        self._dir_path_label = QLabel(
            self._source_dir if self._source_dir else "尚未选择...",
            self._content_widget,
        )
        self._dir_path_label.setStyleSheet(
            "color: #aaa; font-size: 12px; padding: 8px; "
            "background: #222; border: 1px solid #444; border-radius: 4px;"
        )
        self._dir_path_label.setWordWrap(True)
        dir_layout.addWidget(self._dir_path_label, 1)

        browse_btn = QPushButton("浏览...", self._content_widget)
        browse_btn.setStyleSheet(_BTN_SECONDARY)
        browse_btn.clicked.connect(self._on_browse_dir)
        dir_layout.addWidget(browse_btn)
        self._content_layout.addLayout(dir_layout)

        # 提示信息
        hint = QLabel(
            "提示：你可以将模型文件夹放在任意位置，系统会复制到应用数据目录。",
            self._content_widget,
        )
        hint.setStyleSheet("color: #666; font-size: 11px;")
        hint.setWordWrap(True)
        self._content_layout.addWidget(hint)

        self._content_layout.addStretch()

        self._next_btn.setEnabled(bool(self._source_dir))

    def _on_browse_dir(self) -> None:
        """浏览并选择源目录。"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择模型源目录", "",
            QFileDialog.ShowDirsOnly,
        )
        if dir_path:
            self._source_dir = dir_path
            self._dir_path_label.setText(dir_path)
            self._next_btn.setEnabled(True)
            logger.debug("选择源目录: %s", dir_path)

    # ── Step 3: 校验结果 ────────────────────────────────────

    def _render_step3_validate(self) -> None:
        """展示校验报告。"""
        title = QLabel("校验结果", self._content_widget)
        title.setStyleSheet(_TITLE_STYLE)
        self._content_layout.addWidget(title)

        # 进行校验
        self._validation_report = ModelValidator.validate(self._source_dir)
        report = self._validation_report
        is_valid = report.get("valid", False)

        # 状态图标
        if is_valid:
            status = QLabel("✅ 校验通过", self._content_widget)
            status.setStyleSheet("font-size: 16px; color: #4caf50; font-weight: bold;")
        else:
            status = QLabel("❌ 校验未通过", self._content_widget)
            status.setStyleSheet("font-size: 16px; color: #f44336; font-weight: bold;")
        self._content_layout.addWidget(status)

        # 概览信息
        overview = QLabel(
            f"发现 {report.get('image_count', 0)} 张图片, "
            f"{report.get('audio_count', 0)} 个音频文件, "
            f"{len(report.get('actions_found', []))} 个动作",
            self._content_widget,
        )
        overview.setStyleSheet(_DESC_STYLE)
        self._content_layout.addWidget(overview)

        self._content_layout.addSpacing(12)

        # 错误列表（红色）
        for err in report.get("errors", []):
            err_label = QLabel(f"✗ {err}", self._content_widget)
            err_label.setStyleSheet(_VALID_RED + "padding: 2px 0;")
            err_label.setWordWrap(True)
            err_label.setMinimumHeight(20)
            self._content_layout.addWidget(err_label)

        # 警告列表（黄色）
        for warn in report.get("warnings", []):
            warn_label = QLabel(f"⚠ {warn}", self._content_widget)
            warn_label.setStyleSheet(_VALID_YELLOW + "padding: 2px 0;")
            warn_label.setWordWrap(True)
            warn_label.setMinimumHeight(20)
            self._content_layout.addWidget(warn_label)

        # 动作列表
        if report.get("actions_found"):
            self._content_layout.addSpacing(8)
            actions_label = QLabel(
                f"已发现动作: {', '.join(report['actions_found'])}",
                self._content_widget,
            )
            actions_label.setStyleSheet(_VALID_GREEN + "padding: 4px 0;")
            actions_label.setWordWrap(True)
            self._content_layout.addWidget(actions_label)

        if report.get("actions_empty"):
            empty_label = QLabel(
                f"空动作目录: {', '.join(report['actions_empty'])}",
                self._content_widget,
            )
            empty_label.setStyleSheet(_VALID_YELLOW + "padding: 2px 0;")
            empty_label.setWordWrap(True)
            self._content_layout.addWidget(empty_label)

        self._content_layout.addSpacing(8)

        if report.get("has_model_json"):
            name_text = report.get("model_name", "")
            name_info = f" (名称: {name_text})" if name_text else ""
            json_label = QLabel(f"✓ 存在 model.json{name_info}", self._content_widget)
            json_label.setStyleSheet(_VALID_GREEN + "padding: 4px 0;")
            self._content_layout.addWidget(json_label)

        # 行走能力
        walk_text = "🚶 支持行走" if report.get("has_walking") else "🚶 不支持行走（缺少 left/right）"
        walk_label = QLabel(walk_text, self._content_widget)
        walk_label.setStyleSheet((_VALID_GREEN if report.get("has_walking") else _VALID_YELLOW) + "padding: 4px 0;")
        self._content_layout.addWidget(walk_label)

        # 语音
        voice_text = "🎤 有语音包" if report.get("voice_available") else "🎤 无语音包"
        voice_label = QLabel(voice_text, self._content_widget)
        voice_label.setStyleSheet((_VALID_GREEN if report.get("voice_available") else _VALID_YELLOW) + "padding: 4px 0;")
        self._content_layout.addWidget(voice_label)

        self._content_layout.addStretch()

        self._next_btn.setEnabled(is_valid)

    # ── Step 4: 确认导入 ────────────────────────────────────

    def _render_step4_confirm(self) -> None:
        """确认导入详情。"""
        title = QLabel("确认导入", self._content_widget)
        title.setStyleSheet(_TITLE_STYLE)
        self._content_layout.addWidget(title)

        desc = QLabel("请确认以下信息，自定义目标 ID：", self._content_widget)
        desc.setStyleSheet(_DESC_STYLE)
        self._content_layout.addWidget(desc)

        self._content_layout.addSpacing(12)

        # 源目录信息
        src_widget = QFrame(self._content_widget)
        src_widget.setStyleSheet(
            "background: #1a1a2a; border: 1px solid #333; border-radius: 6px; padding: 10px;"
        )
        src_layout = QVBoxLayout(src_widget)
        src_layout.setContentsMargins(0, 0, 0, 0)
        src_layout.setSpacing(4)

        src_info = QLabel(f"源目录: {self._source_dir}", src_widget)
        src_info.setStyleSheet("color: #ccc; font-size: 12px;")
        src_info.setWordWrap(True)
        src_layout.addWidget(src_info)

        report = self._validation_report
        summary = QLabel(
            f"{report.get('image_count', 0)} 张图片, "
            f"{report.get('audio_count', 0)} 个音频文件, "
            f"{len(report.get('actions_found', []))} 个动作",
            src_widget,
        )
        summary.setStyleSheet("color: #aaa; font-size: 12px;")
        src_layout.addWidget(summary)

        self._content_layout.addWidget(src_widget)
        self._content_layout.addSpacing(16)

        # 目标 ID 输入
        id_layout = QHBoxLayout()
        id_label = QLabel("目标 ID:", self._content_widget)
        id_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        id_layout.addWidget(id_label)

        default_id = self._validation_report.get("model_name", "") or Path(self._source_dir).name
        # 清理非法字符
        import re
        default_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', default_id)

        self._id_input = QLineEdit(self._content_widget)
        self._id_input.setText(self._target_id or default_id)
        self._id_input.setPlaceholderText("仅支持字母、数字、下划线、短横线")
        self._id_input.setStyleSheet(
            "background: #222; color: #e0e0e0; border: 1px solid #555; "
            "border-radius: 4px; padding: 6px 10px; font-size: 13px;"
        )
        self._id_input.textChanged.connect(self._on_id_changed)
        id_layout.addWidget(self._id_input, 1)
        self._content_layout.addLayout(id_layout)

        self._id_error = QLabel("", self._content_widget)
        self._id_error.setStyleSheet(_VALID_RED)
        self._content_layout.addWidget(self._id_error)

        # 显示名输入
        name_layout = QHBoxLayout()
        name_label = QLabel("显示名称:", self._content_widget)
        name_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        name_layout.addWidget(name_label)

        self._name_input = QLineEdit(self._content_widget)
        default_name = self._validation_report.get("model_name", "") or Path(self._source_dir).name
        self._name_input.setText(self._import_result.get("name", default_name) if self._import_result else default_name)
        self._name_input.setStyleSheet(
            "background: #222; color: #e0e0e0; border: 1px solid #555; "
            "border-radius: 4px; padding: 6px 10px; font-size: 13px;"
        )
        name_layout.addWidget(self._name_input, 1)
        self._content_layout.addLayout(name_layout)

        self._content_layout.addSpacing(8)

        # 提示
        note = QLabel(
            "导入后，源目录的文件将复制到应用数据目录。\n"
            "如果已存在同 ID 的模型，将被覆盖。",
            self._content_widget,
        )
        note.setStyleSheet("color: #ff9800; font-size: 11px;")
        note.setWordWrap(True)
        self._content_layout.addWidget(note)

        self._content_layout.addStretch()

        self._validate_id_input()

    def _on_id_changed(self, text: str) -> None:
        self._target_id = text
        self._validate_id_input()

    def _validate_id_input(self) -> None:
        import re
        tid = self._target_id.strip()
        if not tid:
            self._id_error.setText("ID 不能为空")
            self._next_btn.setEnabled(False)
        elif not re.match(r'^[a-zA-Z0-9_\-]+$', tid):
            self._id_error.setText("ID 只能包含字母、数字、下划线、短横线")
            self._next_btn.setEnabled(False)
        else:
            self._id_error.setText("")
            self._next_btn.setEnabled(True)

    # ── Step 5: 导入进度 ────────────────────────────────────

    def _render_step5_progress(self) -> None:
        """执行导入并显示进度。"""
        title = QLabel("正在导入...", self._content_widget)
        title.setStyleSheet(_TITLE_STYLE)
        self._content_layout.addWidget(title)

        self._content_layout.addSpacing(16)

        self._progress_bar = QProgressBar(self._content_widget)
        self._progress_bar.setRange(0, 0)  # 不确定模式
        self._progress_bar.setStyleSheet(_PROGRESS_STYLE)
        self._progress_bar.setMinimumHeight(24)
        self._content_layout.addWidget(self._progress_bar)

        self._progress_status = QLabel("正在复制文件...", self._content_widget)
        self._progress_status.setStyleSheet("color: #aaa; font-size: 12px;")
        self._content_layout.addWidget(self._progress_status)

        self._content_layout.addStretch()

        # 禁用按钮
        self._back_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        self._next_btn.setEnabled(False)

        # 延迟一帧启动导入（让 UI 先刷新）
        QTimer.singleShot(100, self._do_import)

    def _do_import(self) -> None:
        """在后台执行导入（当前线程，但 UI 已刷新）。"""
        target_id = self._target_id.strip()
        display_name = self._name_input.text().strip() or target_id

        try:
            if self._import_type == "pixel":
                result = ModelImporter.import_model(
                    self._source_dir, target_id, self._config,
                    display_name=display_name,
                )
            elif self._import_type == "live2d":
                # Live2D 导入（暂用占位，Phase 4 实现）
                result = self._import_live2d_placeholder(target_id, display_name)
            else:
                raise ValueError(f"未知导入类型: {self._import_type}")

            self._import_result = result
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(100)
            self._progress_status.setText("导入完成！")

            QTimer.singleShot(500, self._go_to_step6)

        except Exception as e:
            logger.error("导入失败: %s", e)
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(0)
            self._progress_status.setText(f"导入失败: {e}")
            self._progress_status.setStyleSheet("color: #f44336; font-size: 12px;")

            # 恢复按钮
            self._back_btn.setEnabled(True)
            self._cancel_btn.setEnabled(True)
            self._next_btn.setText("返回重试")
            self._next_btn.setEnabled(True)
            self._next_btn.clicked.disconnect()
            self._next_btn.clicked.connect(lambda: self._render_step(3))

    def _import_live2d_placeholder(self, target_id: str, display_name: str) -> dict:
        """
        Live2D 导入占位实现。
        在 Phase 4 中会被替换为真正的 Live2DImporter。
        """
        raise NotImplementedError("Live2D 导入功能将在后续版本实现")

    def _go_to_step6(self) -> None:
        """自动跳转到步骤 6。"""
        self._back_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setText("关闭")
        self._render_step(5)

    # ── Step 6: 完成 ────────────────────────────────────────

    def _render_step6_complete(self) -> None:
        """导入完成页。"""
        title = QLabel("导入完成 🎉", self._content_widget)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4caf50;")
        self._content_layout.addWidget(title)

        self._content_layout.addSpacing(12)

        result = self._import_result or {}
        info_text = (
            f"模型名称: {result.get('name', '未知')}\n"
            f"模型 ID: {result.get('id', '')}\n"
            f"动作数量: {len(result.get('actions', []))}\n"
            f"支持行走: {'是' if result.get('has_walking') else '否'}\n"
            f"支持语音: {'是' if result.get('voice_available') else '否'}"
        )
        info = QLabel(info_text, self._content_widget)
        info.setStyleSheet("color: #ccc; font-size: 13px; line-height: 1.6;")
        info.setWordWrap(True)
        self._content_layout.addWidget(info)

        self._content_layout.addSpacing(16)

        # 设为当前角色按钮
        set_btn = QPushButton("设为当前角色", self._content_widget)
        set_btn.setStyleSheet(_BTN_PRIMARY)
        set_btn.clicked.connect(self._on_set_current)
        self._content_layout.addWidget(set_btn)

        self._content_layout.addStretch()

        # 完成按钮直接发送信号并关闭
        self._next_btn.setText("完成")
        self._next_btn.setEnabled(True)
        self._next_btn.clicked.disconnect()
        self._next_btn.clicked.connect(self._on_finish)

    def _on_set_current(self) -> None:
        """设置导入的模型为当前角色。"""
        if self._import_result:
            ModelRegistry.set_default(self._config, self._import_result["id"])
            self.model_imported.emit(self._import_result["id"])
            QMessageBox.information(self, "成功",
                f"已将「{self._import_result.get('name', '')}」设为当前角色。")

    def _on_finish(self) -> None:
        """完成导入，关闭向导。"""
        if self._import_result:
            self.model_imported.emit(self._import_result["id"])
        self.accept()

    # ── 导航按钮 ────────────────────────────────────────────

    def _on_next(self) -> None:
        """点击下一步/完成。"""
        if self._current_step == self._max_steps - 1:
            # 完成步骤
            self._on_finish()
        else:
            self._render_step(self._current_step + 1)

    def _on_back(self) -> None:
        """点击上一步。"""
        if self._current_step > 0:
            self._render_step(self._current_step - 1)
