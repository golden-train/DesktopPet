"""
导入引导向导对话框。

分 6 步引导用户完成角色模型的导入。
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
        self._import_type: Optional[str] = None
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
        """选择导入类型。"""
        title = QLabel("请选择你要导入的模型类型：", self._content_widget)
        title.setStyleSheet(_TITLE_STYLE)
        self._content_layout.addWidget(title)

        desc = QLabel(
            "请选择包含 PNG 序列帧和 actions/ 目录的模型文件夹。",
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

        self._content_layout.addSpacing(16)

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

        desc = QLabel(
            "请选择包含模型文件的文件夹（包含 actions/ 的目录）。",
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
        """展示校验报告（全部内容放入独立结果框，避免布局干扰）。"""
        title = QLabel("校验结果", self._content_widget)
        title.setStyleSheet(_TITLE_STYLE)
        self._content_layout.addWidget(title)

        self._validation_report = ModelValidator.validate(self._source_dir)
        report = self._validation_report
        is_valid = report.get("valid", False)

        # ── 结果框 ───────────────────────────────────────────
        box = QFrame(self._content_widget)
        box.setStyleSheet("""
            QFrame {
                background: #1a1a2a; border: 1px solid #333;
                border-radius: 8px; padding: 16px;
            }
        """)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(16, 12, 16, 12)
        box_layout.setSpacing(8)

        # 状态 + 概览
        status_text = "✅ 校验通过" if is_valid else "❌ 校验未通过"
        status_color = "#4caf50" if is_valid else "#f44336"
        header = QLabel(status_text, box)
        header.setStyleSheet(f"font-size: 16px; color: {status_color}; font-weight: bold; padding: 0 0 4px 0;")
        box_layout.addWidget(header)

        overview = QLabel(
            f"发现 {report.get('image_count', 0)} 张图片, "
            f"{report.get('audio_count', 0)} 个音频文件, "
            f"{len(report.get('actions_found', []))} 个动作",
            box,
        )
        overview.setStyleSheet("color: #aaa; font-size: 12px; padding: 0 0 8px 0;")
        box_layout.addWidget(overview)

        # 分隔线
        sep = QFrame(box)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #333; padding: 0;")
        box_layout.addWidget(sep)

        # 错误列表（红色）
        for err in report.get("errors", []):
            el = QLabel(f"✗ {err}", box)
            el.setStyleSheet("color: #f44336; font-size: 13px; padding: 4px 0;")
            el.setWordWrap(True)
            box_layout.addWidget(el)

        # 警告列表（黄色）
        for warn in report.get("warnings", []):
            wl = QLabel(f"⚠ {warn}", box)
            wl.setStyleSheet("color: #ff9800; font-size: 13px; padding: 4px 0;")
            wl.setWordWrap(True)
            box_layout.addWidget(wl)

        # 如果有错误或警告，添加分隔
        if report.get("errors") or report.get("warnings"):
            sep2 = QFrame(box)
            sep2.setFrameShape(QFrame.HLine)
            sep2.setStyleSheet("color: #333; padding: 0;")
            box_layout.addWidget(sep2)

        # 动作列表
        if report.get("actions_found"):
            al = QLabel(
                f"已发现动作: {', '.join(report['actions_found'])}",
                box,
            )
            al.setStyleSheet("color: #4caf50; font-size: 13px; padding: 2px 0;")
            al.setWordWrap(True)
            box_layout.addWidget(al)

        if report.get("actions_empty"):
            el = QLabel(
                f"空动作目录: {', '.join(report['actions_empty'])}",
                box,
            )
            el.setStyleSheet("color: #ff9800; font-size: 13px; padding: 2px 0;")
            el.setWordWrap(True)
            box_layout.addWidget(el)

        # 详细信息
        info_lines = []
        if report.get("has_model_json"):
            name_text = report.get("model_name", "")
            info_lines.append(f"✓ 存在 model.json ({name_text})" if name_text else "✓ 存在 model.json")
        info_lines.append("🚶 支持行走" if report.get("has_walking") else "🚶 不支持行走（缺少 left/right）")
        info_lines.append("🎤 有语音包" if report.get("voice_available") else "🎤 无语音包")

        info_label = QLabel("\n".join(info_lines), box)
        info_label.setStyleSheet("color: #bbb; font-size: 13px; padding: 4px 0; line-height: 1.6;")
        box_layout.addWidget(info_label)

        self._content_layout.addWidget(box, 1)  # stretch=1 占满空间
        self._content_layout.addStretch(0)

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
            result = ModelImporter.import_model(
                self._source_dir, target_id, self._config,
                display_name=display_name,
            )

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
        if not self._import_result:
            return
        model_id = self._import_result if isinstance(self._import_result, str) else self._import_result.get("id", "")
        if model_id:
            ModelRegistry.set_default(self._config, model_id)
            self.model_imported.emit(model_id)
            QMessageBox.information(self, "成功", f"已将模型「{model_id}」设为当前角色。")

    def _on_finish(self) -> None:
        """完成导入，关闭向导。"""
        if not self._import_result:
            return
        model_id = self._import_result if isinstance(self._import_result, str) else self._import_result.get("id", "")
        if model_id:
            self.model_imported.emit(model_id)
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
