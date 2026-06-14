"""
技能预设管理器对话框。

管理 skills.json 中的 AI 角色技能预设。
支持新增、编辑、删除、调整顺序。
"""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QInputDialog,
)

from src.core.config import ConfigManager

logger = logging.getLogger(__name__)


class SkillManager(QDialog):
    """技能预设管理对话框。"""

    skills_changed = Signal()

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._skills: list[dict] = []

        self.setWindowTitle("管理技能预设")
        self.setMinimumSize(500, 420)
        self.resize(540, 460)

        self._load_skills()
        self._setup_ui()
        self._populate_list()
        from PySide6.QtCore import Signal

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("技能预设（第一个为默认技能）：", self)
        header.setStyleSheet("font-size: 13px; font-weight: bold; color: #ddd;")
        layout.addWidget(header)

        self._list = QListWidget(self)
        self._list.setStyleSheet("""
            QListWidget {
                background: #1e1e1e; color: #e0e0e0;
                border: 1px solid #333; border-radius: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidget::item:selected { background: #2a4a7a; color: #fff; }
            QListWidget::item:hover { background: #2a2a3a; }
        """)
        layout.addWidget(self._list, 1)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._add_btn = QPushButton("+ 新增", self)
        self._add_btn.setStyleSheet(self._btn_style("#2d5a2d", "#3d7a3d"))
        self._add_btn.clicked.connect(self._add_skill)
        btn_layout.addWidget(self._add_btn)

        self._edit_btn = QPushButton("编辑", self)
        self._edit_btn.setStyleSheet(self._btn_style("#3d3d3d", "#555"))
        self._edit_btn.clicked.connect(self._edit_skill)
        btn_layout.addWidget(self._edit_btn)

        self._del_btn = QPushButton("删除", self)
        self._del_btn.setStyleSheet(self._btn_style("#5a2d2d", "#7a3d3d"))
        self._del_btn.clicked.connect(self._delete_skill)
        btn_layout.addWidget(self._del_btn)

        btn_layout.addStretch()

        self._up_btn = QPushButton("上移", self)
        self._up_btn.setStyleSheet(self._btn_style("#3d3d3d", "#555"))
        self._up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(self._up_btn)

        self._down_btn = QPushButton("下移", self)
        self._down_btn.setStyleSheet(self._btn_style("#3d3d3d", "#555"))
        self._down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(self._down_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("关闭", self)
        close_btn.setStyleSheet(self._btn_style("#005fb8", "#0078d4", "#fff"))
        close_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(close_btn)

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

    def _load_skills(self) -> None:
        data = self._config.read("skills")
        self._skills = data.get("skills", [])

    def _populate_list(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for i, skill in enumerate(self._skills):
            label = skill.get("name", "?")
            if i == 0:
                label += "（默认）"
            preview = skill.get("prompt", "")[:40].replace("\n", " ")
            item = QListWidgetItem(label)
            item.setToolTip(preview)
            item.setData(Qt.UserRole, skill)
            self._list.addItem(item)
        self._list.blockSignals(False)

    def _add_skill(self) -> None:
        name, ok = QInputDialog.getText(self, "新增技能", "技能名称：")
        if not ok or not name.strip():
            return
        prompt, ok = QInputDialog.getMultiLineText(
            self, "编辑提示词", f"「{name}」的提示词："
        )
        if not ok or not prompt.strip():
            return
        self._skills.append({"name": name.strip(), "prompt": prompt.strip()})
        self._populate_list()

    def _edit_skill(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        skill = self._skills[row]
        name, ok = QInputDialog.getText(self, "编辑技能", "名称：", text=skill["name"])
        if not ok or not name.strip():
            return
        prompt, ok = QInputDialog.getMultiLineText(
            self, "编辑提示词", "内容：", text=skill["prompt"]
        )
        if not ok or not prompt.strip():
            return
        self._skills[row] = {"name": name.strip(), "prompt": prompt.strip()}
        self._populate_list()

    def _delete_skill(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        if len(self._skills) <= 1:
            QMessageBox.warning(self, "提示", "至少保留一个技能。")
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定删除「{self._skills[row]['name']}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self._skills.pop(row)
        self._populate_list()

    def _move_up(self) -> None:
        row = self._list.currentRow()
        if row <= 0:
            return
        self._skills[row], self._skills[row - 1] = self._skills[row - 1], self._skills[row]
        self._populate_list()
        self._list.setCurrentRow(row - 1)

    def _move_down(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._skills) - 1:
            return
        self._skills[row], self._skills[row + 1] = self._skills[row + 1], self._skills[row]
        self._populate_list()
        self._list.setCurrentRow(row + 1)

    def _save_and_close(self) -> None:
        self._config.write("skills", {"skills": self._skills})
        self.skills_changed.emit()
        self.accept()
