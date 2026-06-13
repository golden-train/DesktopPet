"""
提示词管理器对话框。

管理默认提示词（来自 skills.json）和自定义提示词（custom_prompts.json）。
支持新增、编辑、删除、选择当前使用的提示词。
自定义提示词始终保存在用户可写目录中。
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QMessageBox, QInputDialog, QFrame, QSizePolicy,
)
from PySide6.QtGui import QFont

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)

_CUSTOM_CFG = "custom_prompts"


class PromptManager(QDialog):
    """提示词管理对话框。"""

    prompt_selected = Signal(str)  # 用户选中的提示词文本

    def __init__(self, config: ConfigManager, current_prompt: str = "", parent=None):
        super().__init__(parent)
        self._config = config
        self._current_prompt = current_prompt
        self._custom_prompts: list[dict] = []
        self._default_prompts: list[dict] = []

        self.setWindowTitle("管理提示词")
        self.setMinimumSize(560, 480)
        self.resize(600, 540)

        self._load_prompts()
        self._setup_ui()
        self._populate_list()

    # ── UI ──────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 当前提示词（只读预览）
        current_label = QLabel("当前使用：", self)
        cf = QFont()
        cf.setBold(True)
        current_label.setFont(cf)
        layout.addWidget(current_label)

        self._preview = QTextEdit(self)
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(90)
        self._preview.setStyleSheet("""
            QTextEdit {
                background: #1a1a2e; color: #c0c0e0;
                border: 1px solid #444; border-radius: 6px;
                padding: 8px; font-size: 12px;
            }
        """)
        self._preview.setText(self._current_prompt)
        layout.addWidget(self._preview)

        # 分隔线
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border: none; border-top: 1px solid #444;")
        layout.addWidget(sep)

        # 提示词列表
        list_label = QLabel("提示词库（点击选中即切换）：", self)
        list_label.setFont(cf)
        layout.addWidget(list_label)

        self._list = QListWidget(self)
        self._list.setStyleSheet("""
            QListWidget {
                background: #1e1e1e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidget::item:selected {
                background: #2a4a7a; color: #fff;
            }
            QListWidget::item:hover {
                background: #2a2a3a;
            }
        """)
        self._list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list, 1)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._add_btn = QPushButton("+ 新增", self)
        self._add_btn.setStyleSheet(self._btn_style("#2d5a2d", "#3d7a3d"))
        self._add_btn.clicked.connect(self._add_prompt)
        btn_layout.addWidget(self._add_btn)

        self._edit_btn = QPushButton("编辑", self)
        self._edit_btn.setStyleSheet(self._btn_style("#3d3d3d", "#555"))
        self._edit_btn.clicked.connect(self._edit_prompt)
        btn_layout.addWidget(self._edit_btn)

        self._del_btn = QPushButton("删除", self)
        self._del_btn.setStyleSheet(self._btn_style("#5a2d2d", "#7a3d3d"))
        self._del_btn.clicked.connect(self._delete_prompt)
        btn_layout.addWidget(self._del_btn)

        btn_layout.addStretch()

        self._apply_btn = QPushButton("保存并应用", self)
        self._apply_btn.setStyleSheet(self._btn_style("#005fb8", "#0078d4", "#fff"))
        self._apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(self._apply_btn)

        self._cancel_btn = QPushButton("取消", self)
        self._cancel_btn.setStyleSheet(self._btn_style("#3d3d3d", "#555"))
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

    @staticmethod
    def _btn_style(bg: str, hover: str, text: str = "#ccc") -> str:
        return f"""
            QPushButton {{
                background: {bg}; color: {text};
                border: none; border-radius: 6px;
                padding: 6px 16px; font-size: 12px;
            }}
            QPushButton:hover {{ background: {hover}; }}
        """

    # ── 数据加载 ────────────────────────────────────────────

    def _load_prompts(self) -> None:
        """从 skills.json 加载默认提示词，从 custom_prompts.json 加载自定义。"""
        skills_data = self._config.read("skills")
        self._default_prompts = skills_data.get("skills", [])

        custom_data = self._config.read(_CUSTOM_CFG)
        self._custom_prompts = custom_data.get("custom_prompts", []) if custom_data else []

    def _prompts_all(self) -> list[dict]:
        """合并默认 + 自定义，返回完整提示词列表。"""
        items = []
        for s in self._default_prompts:
            items.append({**s, "_type": "默认", "_editable": False})
        for c in self._custom_prompts:
            items.append({**c, "_type": "自定义", "_editable": True})
        # 标记当前选中的
        for item in items:
            item["_selected"] = (item["prompt"] == self._current_prompt)
        return items

    def _populate_list(self) -> None:
        """填充列表。"""
        self._list.blockSignals(True)
        self._list.clear()

        selected_row = 0
        for i, item in enumerate(self._prompts_all()):
            label = f"[{item['_type']}] {item['name']}"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.UserRole, item)
            # 显示前 50 个字符的预览
            preview = item["prompt"][:50].replace("\n", " ")
            list_item.setToolTip(preview)
            self._list.addItem(list_item)
            if item.get("_selected"):
                selected_row = i

        self._list.blockSignals(False)
        if self._list.count() > 0:
            self._list.setCurrentRow(selected_row)

    # ── 交互 ────────────────────────────────────────────────

    def _on_selection_changed(self, row: int) -> None:
        """列表选中项变更时更新预览。"""
        if row < 0:
            return
        item = self._list.item(row)
        if not item:
            return
        data = item.data(Qt.UserRole)
        if data:
            self._preview.setText(data["prompt"])

    def _add_prompt(self) -> None:
        """新增自定义提示词：弹出对话框输入名称和内容。"""
        name, ok = QInputDialog.getText(self, "新增提示词", "请输入提示词名称：")
        if not ok or not name.strip():
            return
        prompt, ok = QInputDialog.getMultiLineText(
            self, "编辑提示词内容", f"请输入「{name}」的提示词内容："
        )
        if not ok or not prompt.strip():
            return

        self._custom_prompts.append({"name": name.strip(), "prompt": prompt.strip()})
        self._save_custom()
        self._populate_list()
        logger.info("已新增自定义提示词: %s", name)

    def _edit_prompt(self) -> None:
        """编辑选中的提示词。"""
        row = self._list.currentRow()
        if row < 0:
            return
        data = self._list.item(row).data(Qt.UserRole)
        if not data:
            return
        if not data.get("_editable"):
            QMessageBox.information(self, "提示", "默认提示词不可编辑，请先复制到自定义。")
            return

        name, ok = QInputDialog.getText(self, "编辑提示词", "名称：", text=data["name"])
        if not ok or not name.strip():
            return
        prompt, ok = QInputDialog.getMultiLineText(
            self, "编辑提示词内容", "内容：", text=data["prompt"]
        )
        if not ok or not prompt.strip():
            return

        # 更新自定义列表
        for c in self._custom_prompts:
            if c["name"] == data["name"] and c["prompt"] == data["prompt"]:
                c["name"] = name.strip()
                c["prompt"] = prompt.strip()
                break

        self._save_custom()
        self._populate_list()
        logger.info("已编辑提示词: %s", name)

    def _delete_prompt(self) -> None:
        """删除选中的自定义提示词。"""
        row = self._list.currentRow()
        if row < 0:
            return
        data = self._list.item(row).data(Qt.UserRole)
        if not data:
            return
        if not data.get("_editable"):
            QMessageBox.information(self, "提示", "默认提示词不可删除。")
            return

        reply = QMessageBox.question(
            self, "确认删除", f"确定删除提示词「{data['name']}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self._custom_prompts = [
            c for c in self._custom_prompts
            if not (c["name"] == data["name"] and c["prompt"] == data["prompt"])
        ]
        self._save_custom()
        self._populate_list()
        logger.info("已删除提示词: %s", data["name"])

    # ── 持久化 ──────────────────────────────────────────────

    def _save_custom(self) -> None:
        """将自定义提示词保存到 custom_prompts.json（用户可写目录）。"""
        self._config.write(_CUSTOM_CFG, {"custom_prompts": self._custom_prompts})

    # ── 应用 ────────────────────────────────────────────────

    def _apply(self) -> None:
        """应用选中的提示词并关闭。"""
        row = self._list.currentRow()
        if row < 0:
            return
        data = self._list.item(row).data(Qt.UserRole)
        if data:
            self._current_prompt = data["prompt"]
            self.prompt_selected.emit(data["prompt"])
            self.accept()
