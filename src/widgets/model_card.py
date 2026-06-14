"""
模型预览卡片组件。

在模型管理页面展示单个模型的缩略图、名称、状态和能力标识。
"""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QFont, QAction
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QMenu,
    QWidget, QSizePolicy,
)

logger = logging.getLogger(__name__)

# 默认缩略图尺寸
_THUMB_SIZE = 80

# 卡片样式
_CARD_STYLE = """
ModelCard {
    background: #2d2d2d;
    border: 2px solid transparent;
    border-radius: 10px;
    padding: 12px;
}
ModelCard:hover {
    background: #353535;
    border: 2px solid #4a6fa5;
}
ModelCard[active="true"] {
    background: #2a3a4a;
    border: 2px solid #5ba3e6;
}
"""

_ACTIVE_BADGE_STYLE = "background: #5ba3e6; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 8px;"
_NAME_STYLE = "color: #e0e0e0; font-size: 13px; font-weight: bold;"
_CAP_ICON_STYLE = "color: #888; font-size: 11px;"
_CAP_ACTIVE_STYLE = "color: #5ba3e6; font-size: 11px;"


class ModelCard(QFrame):
    """单个模型的预览卡片组件。"""

    # 左键单击切换到此模型
    clicked = Signal(str)
    # 右键菜单请求
    context_requested = Signal(str, object)  # model_id, QPoint

    def __init__(self, model_info: dict, is_active: bool = False, parent=None):
        """
        :param model_info: 模型信息字典（id, name, has_walking, voice_available, has_icon 等）
        :param is_active: 当前是否正在使用此模型
        """
        super().__init__(parent)
        self._model_id = model_info.get("id", "")
        self._model_info = model_info
        self._is_active = is_active

        self.setProperty("active", "true" if is_active else "false")
        self.setStyleSheet(_CARD_STYLE)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(120, 140)

        self._setup_ui(model_info, is_active)

    def _setup_ui(self, info: dict, is_active: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # ── 缩略图 ──────────────────────────────────────────
        thumb_data = self._resolve_thumbnail(info)
        thumb_label = QLabel(self)
        thumb_label.setFixedSize(_THUMB_SIZE, _THUMB_SIZE)
        thumb_label.setAlignment(Qt.AlignCenter)

        if thumb_data:
            pixmap = QPixmap(thumb_data)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    _THUMB_SIZE, _THUMB_SIZE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                )
                thumb_label.setPixmap(pixmap)
            else:
                thumb_label.setText("📷")
                thumb_label.setStyleSheet("font-size: 32px;")
        else:
            thumb_label.setText("📷")
            thumb_label.setStyleSheet("font-size: 32px;")

        # 圆形遮罩效果
        thumb_label.setStyleSheet(thumb_label.styleSheet() + """
            border-radius: 8px;
            background: #3a3a3a;
        """)
        layout.addWidget(thumb_label, 0, Qt.AlignCenter)

        # ── 名称 ────────────────────────────────────────────
        name_label = QLabel(info.get("name", info.get("id", "未知")), self)
        name_label.setStyleSheet(_NAME_STYLE)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(False)
        layout.addWidget(name_label, 0, Qt.AlignCenter)

        # ── 状态行 ──────────────────────────────────────────
        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        status_layout.setAlignment(Qt.AlignCenter)

        # 能力标识
        if info.get("has_walking", False):
            walk_label = QLabel("🚶", self)
            walk_label.setToolTip("支持行走")
            walk_label.setStyleSheet("font-size: 14px;")
            status_layout.addWidget(walk_label)

        if info.get("voice_available", False):
            voice_label = QLabel("🎤", self)
            voice_label.setToolTip("支持语音")
            voice_label.setStyleSheet("font-size: 14px;")
            status_layout.addWidget(voice_label)

        # 使用中标识
        if is_active:
            active_label = QLabel("使用中", self)
            active_label.setStyleSheet(_ACTIVE_BADGE_STYLE)
            status_layout.addWidget(active_label)

        status_widget = QWidget(self)
        status_widget.setLayout(status_layout)
        layout.addWidget(status_widget, 0, Qt.AlignCenter)

    # ── 鼠标事件 ────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and not self._is_active:
            self.clicked.emit(self._model_id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event) -> None:
        """右键弹出模型操作菜单。"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2a2a2a; color: #e0e0e0;
                border: 1px solid #444; border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px; border-radius: 4px;
            }
            QMenu::item:selected { background: #3a6ea5; color: #fff; }
            QMenu::separator {
                height: 1px; background: #444; margin: 4px 8px;
            }
        """)

        act_switch = QAction("设为当前角色", menu)
        act_switch.triggered.connect(lambda: self.clicked.emit(self._model_id))
        if self._is_active:
            act_switch.setEnabled(False)
        menu.addAction(act_switch)

        act_reimport = QAction("重新导入...", menu)
        act_reimport.triggered.connect(self._on_reimport)
        if self._model_info.get("source_type") != "user_imported":
            act_reimport.setEnabled(False)
        menu.addAction(act_reimport)

        menu.addSeparator()

        act_test = QAction("测试动作...", menu)
        act_test.triggered.connect(self._on_test_actions)
        menu.addAction(act_test)

        act_detail = QAction("查看详情", menu)
        act_detail.triggered.connect(self._on_show_detail)
        menu.addAction(act_detail)

        act_remove = QAction("从注册表移除", menu)
        act_remove.triggered.connect(self._on_remove)
        if self._model_info.get("source_type") != "user_imported":
            act_remove.setEnabled(False)
        menu.addAction(act_remove)

        menu.exec(event.globalPos())

    # ── 内部菜单动作 ────────────────────────────────────────

    def _on_reimport(self) -> None:
        """重新导入：发出切换到当前 ID 的导入流程信号。"""
        # 由外部 ImportWizard 处理
        self.context_requested.emit(self._model_id + ":reimport", self.mapToGlobal(self.rect().center()))

    def _on_remove(self) -> None:
        """从注册表移除。"""
        self.context_requested.emit(self._model_id + ":remove", self.mapToGlobal(self.rect().center()))

    def _on_test_actions(self) -> None:
        """打开动作测试面板。"""
        self.context_requested.emit(self._model_id + ":actions", self.mapToGlobal(self.rect().center()))

    def _on_show_detail(self) -> None:
        """展示模型详情。"""
        self.context_requested.emit(self._model_id + ":detail", self.mapToGlobal(self.rect().center()))

    # ── 工具方法 ────────────────────────────────────────────

    @staticmethod
    def _resolve_thumbnail(info: dict) -> str | None:
        """解析模型缩略图路径。"""
        from src.core.paths import BUNDLE_DIR, USER_DIR

        # 如果有明确的缩略图路径
        thumb = info.get("thumbnail", "")
        if thumb:
            if Path(thumb).is_absolute():
                return thumb if Path(thumb).exists() else None
            base = BUNDLE_DIR if info.get("source_type") == "bundled" else USER_DIR
            path = base / thumb
            return str(path) if path.exists() else None

        # 尝试从 dir/icon/icon.png 查找
        raw_dir = info.get("dir", "")
        if not raw_dir:
            return None

        base = BUNDLE_DIR if info.get("source_type") == "bundled" else USER_DIR
        model_dir = base / raw_dir
        for candidate in ["icon/icon.png", "icon.png", "icon/icon.ico"]:
            path = model_dir / candidate
            if path.exists():
                return str(path)
        return None

    # ── 活动状态更新 ────────────────────────────────────────

    def set_active(self, active: bool) -> None:
        """更新卡片的活动状态。"""
        self._is_active = active
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        # 重新构建 UI 更新状态标识
        self._clear_layout()
        self._setup_ui(self._model_info, active)

    def _clear_layout(self) -> None:
        """清除布局中的所有子控件。"""
        layout = self.layout()
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    @property
    def model_id(self) -> str:
        return self._model_id
