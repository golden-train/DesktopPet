"""
模型管理页面。

管理窗口中「模型」导航页，显示已导入的像素角色模型和 Live2D 模型，
支持切换、删除、查看详情等操作。
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QMessageBox, QDialog, QSizePolicy,
    QGroupBox,
)

from src.core.config import ConfigManager
from src.model.registry import ModelRegistry
from src.model.importer import ModelImporter
from src.widgets.model_card import ModelCard

logger = logging.getLogger(__name__)

# ── 样式 ──────────────────────────────────────────────────

_SECTION_TITLE_STYLE = "font-size: 15px; font-weight: bold; color: #e0e0e0; padding: 8px 0;"
_EMPTY_STYLE = "color: #666; font-size: 12px; padding: 16px;"
_ACTION_BTN_STYLE = """
    QPushButton {
        background: #3a3a3a; color: #ccc; border: 1px solid #555;
        border-radius: 6px; padding: 6px 16px; font-size: 12px;
    }
    QPushButton:hover { background: #4a4a4a; color: #fff; }
"""
_IMPORT_BTN_STYLE = """
    QPushButton {
        background: #005fb8; color: #fff; border: none;
        border-radius: 6px; padding: 6px 16px; font-size: 12px;
    }
    QPushButton:hover { background: #0078d4; }
"""


class ModelInterface(QWidget):
    """模型管理页面——角色模型 + Live2D 模型的统一管理入口。"""

    # 切换模型信号，参数: model_id
    model_switched = Signal(str)
    # 导入完成信号，参数: model_id
    model_imported = Signal(str)
    # 动作测试信号，参数: model_id, action_name
    action_test_requested = Signal(str, str)

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config

        self.setObjectName("ModelInterface")

        # ── 主布局 ──────────────────────────────────────────
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(8)

        # 标题
        title = QLabel("模型", self)
        tf = QFont()
        tf.setPointSize(18)
        tf.setBold(True)
        title.setFont(tf)
        main_layout.addWidget(title)

        subtitle = QLabel("管理桌面宠物的角色模型与 Live2D 模型", self)
        subtitle.setStyleSheet("color: #888; font-size: 12px;")
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(8)

        # ── 滚动内容区 ──────────────────────────────────────
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }"
                             "QScrollBar:vertical { width: 6px; }")

        self._content = QWidget(scroll)
        self._content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(16)
        scroll.setWidget(self._content)

        main_layout.addWidget(scroll, 1)

        # ── 刷新时重建内容 ──────────────────────────────────
        self._build_content()

    # ── 内容构建 ────────────────────────────────────────────

    def _build_content(self) -> None:
        """清空并重建整个页面内容。"""
        self._clear_layout()

        # ── 角色模型区域 ────────────────────────────────────
        self._build_pixel_section()

        self._content_layout.addSpacing(16)

        # ── Live2D 模型区域 ────────────────────────────────
        self._build_live2d_section()

        self._content_layout.addStretch()

    def _clear_layout(self) -> None:
        """清除布局中所有子控件。"""
        layout = self._content_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ── 像素角色模型区域 ────────────────────────────────────

    def _build_pixel_section(self) -> None:
        """构建像素角色模型区域。"""
        # ── 标题行 ──────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        section_title = QLabel("🧑 角色模型", self._content)
        section_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0;")
        header_layout.addWidget(section_title)

        header_layout.addStretch()

        import_btn = QPushButton("+ 导入新角色", self._content)
        import_btn.setStyleSheet(_IMPORT_BTN_STYLE)
        import_btn.clicked.connect(self._on_import_pixel)
        header_layout.addWidget(import_btn)

        self._content_layout.addLayout(header_layout)

        # ── 模型卡片列表 ────────────────────────────────────
        models = ModelRegistry.load(self._config)
        if not models:
            empty = QLabel("暂无角色模型", self._content)
            empty.setStyleSheet(_EMPTY_STYLE)
            self._content_layout.addWidget(empty)
            return

        current = ModelRegistry.get_default(self._config)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(0, 4, 0, 4)

        for info in models:
            is_active = info["id"] == current
            card = ModelCard(info, is_active, self._content)
            card.clicked.connect(self._on_card_clicked)
            card.context_requested.connect(self._on_card_context)
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        self._content_layout.addLayout(cards_layout)

    # ── Live2D 模型区域 ────────────────────────────────────

    def _build_live2d_section(self) -> None:
        """构建 Live2D 模型区域。"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        section_title = QLabel("🎭 Live2D 模型", self._content)
        section_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0;")
        header_layout.addWidget(section_title)

        header_layout.addStretch()

        import_btn = QPushButton("+ 导入新模型", self._content)
        import_btn.setStyleSheet(_IMPORT_BTN_STYLE)
        import_btn.clicked.connect(self._on_import_live2d)
        header_layout.addWidget(import_btn)

        self._content_layout.addLayout(header_layout)

        # ── 加载 Live2D 模型列表 ────────────────────────────
        live2d_models = self._load_live2d_models()
        if not live2d_models:
            empty = QLabel("暂无 Live2D 模型", self._content)
            empty.setStyleSheet(_EMPTY_STYLE)
            self._content_layout.addWidget(empty)
            return

        current_live2d = self._config.get("live2d", "current_model", "firefly")
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(0, 4, 0, 4)

        for info in live2d_models:
            is_active = info.get("id") == current_live2d
            # Live2D 模型信息适配 ModelCard 格式
            card_info = {
                "id": info.get("id", ""),
                "name": info.get("name", ""),
                "source_type": info.get("source_type", "bundled"),
                "has_walking": False,  # Live2D 不支持行走
                "voice_available": False,
                "has_icon": bool(info.get("thumbnail")),
                "thumbnail": info.get("thumbnail", ""),
                "dir": f"data/live2d/static/live2d-model/{info.get('model_dir', '')}/",
            }
            card = ModelCard(card_info, is_active, self._content)
            card.clicked.connect(self._on_live2d_card_clicked)
            card.context_requested.connect(self._on_live2d_context)
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        self._content_layout.addLayout(cards_layout)

    def _load_live2d_models(self) -> list[dict]:
        """从 live2d.json 和 custom_live2d.json 加载所有 Live2D 模型。"""
        # 从 live2d.json 加载系统内置
        live2d_cfg = self._config.read("live2d")
        bundled = live2d_cfg.get("models", {})
        models = []
        for mid, minfo in bundled.items():
            models.append({
                "id": mid,
                "name": minfo.get("name", mid),
                "source_type": "bundled",
                "model_dir": minfo.get("model_dir", ""),
                "model_file": minfo.get("model_file", ""),
                "thumbnail": "",
            })

        # 从 custom_live2d.json 加载用户导入
        custom = self._config.read("custom_live2d")
        for minfo in custom.get("models", []):
            # 避免重复（优先用 custom 中的信息覆盖 bundled）
            existing = [m for m in models if m["id"] == minfo.get("id")]
            if existing:
                idx = models.index(existing[0])
                models[idx] = {
                    "id": minfo["id"],
                    "name": minfo.get("name", minfo["id"]),
                    "source_type": minfo.get("source_type", "user_imported"),
                    "model_dir": minfo.get("model_dir", ""),
                    "model_file": minfo.get("model_file", ""),
                    "thumbnail": minfo.get("thumbnail", ""),
                }
            else:
                models.append({
                    "id": minfo["id"],
                    "name": minfo.get("name", minfo["id"]),
                    "source_type": minfo.get("source_type", "user_imported"),
                    "model_dir": minfo.get("model_dir", ""),
                    "model_file": minfo.get("model_file", ""),
                    "thumbnail": minfo.get("thumbnail", ""),
                })

        return models

    # ── 卡片交互 ────────────────────────────────────────────

    def _on_card_clicked(self, model_id: str) -> None:
        """像素角色卡片点击：切换模型。"""
        self._switch_pixel_model(model_id)

    def _on_live2d_card_clicked(self, model_id: str) -> None:
        """Live2D 卡片点击：切换模型。"""
        self._switch_live2d_model(model_id)

    def _on_card_context(self, context: str, pos) -> None:
        """处理像素角色卡片的右键菜单动作。"""
        if context.endswith(":reimport"):
            model_id = context[:-9]
            self._reimport_model(model_id)
        elif context.endswith(":remove"):
            model_id = context[:-7]
            self._remove_model(model_id)
        elif context.endswith(":detail"):
            model_id = context[:-7]
            self._show_detail(model_id)
        elif context.endswith(":actions"):
            model_id = context[:-8]
            self._show_action_test(model_id)

    def _on_live2d_context(self, context: str, pos) -> None:
        """处理 Live2D 卡片的右键菜单动作。"""
        if context.endswith(":remove"):
            model_id = context[:-7]
            self._remove_live2d_model(model_id)
        elif context.endswith(":detail"):
            model_id = context[:-7]
            self._show_live2d_detail(model_id)

    # ── 切换模型 ────────────────────────────────────────────

    def _switch_pixel_model(self, model_id: str) -> None:
        """切换像素角色。"""
        current = ModelRegistry.get_default(self._config)
        if model_id == current:
            return
        ModelRegistry.set_default(self._config, model_id)
        self.model_switched.emit(model_id)
        logger.info("切换像素角色: %s", model_id)
        self._build_content()  # 刷新以更新 "使用中" 标识

    def _switch_live2d_model(self, model_id: str) -> None:
        """切换 Live2D 模型。"""
        current = self._config.get("live2d", "current_model", "firefly")
        if model_id == current:
            return
        self._config.set("live2d", "current_model", model_id)
        logger.info("切换 Live2D 模型: %s", model_id)
        self._build_content()

    # ── 导入 ────────────────────────────────────────────────

    def _on_import_pixel(self) -> None:
        """打开像素角色导入向导。"""
        from src.window.import_wizard import ImportWizard
        dialog = ImportWizard(self._config, self)
        dialog.model_imported.connect(self._on_import_done)
        dialog.exec()

    def _on_import_live2d(self) -> None:
        """打开 Live2D 导入向导。"""
        # Phase 4 实现完整 Live2D 导入，当前使用占位
        from src.window.import_wizard import ImportWizard
        dialog = ImportWizard(self._config, self)
        dialog.model_imported.connect(self._on_import_done)
        dialog.exec()

    def _on_import_done(self, model_id: str) -> None:
        """导入完成后刷新页面并通知。"""
        self.model_imported.emit(model_id)
        self._build_content()
        logger.info("模型导入完成，已刷新页面: %s", model_id)

    def _reimport_model(self, model_id: str) -> None:
        """打开导入向导并预填 ID。"""
        # 获取当前模型信息以获取源目录
        model_info = ModelRegistry.get_by_id(self._config, model_id)
        if not model_info:
            QMessageBox.warning(self, "提示", f"找不到模型: {model_id}")
            return

        # 提示用户重新选择源目录
        from PySide6.QtWidgets import QFileDialog
        source_dir = QFileDialog.getExistingDirectory(
            self, f"选择 {model_info.get('name', model_id)} 的源目录", "",
        )
        if not source_dir:
            return

        try:
            result = ModelImporter.import_model(
                source_dir, model_id, self._config,
                display_name=model_info.get("name", model_id),
            )
            self.model_imported.emit(model_id)
            self._build_content()
            QMessageBox.information(self, "成功",
                f"模型「{result.get('name', model_id)}」已重新导入。")
        except ValueError as e:
            QMessageBox.warning(self, "导入失败", str(e))

    # ── 删除 ────────────────────────────────────────────────

    def _remove_model(self, model_id: str) -> None:
        """从注册表移除角色模型。如果删除的是当前模型，自动切回 firefly。"""
        model_info = ModelRegistry.get_by_id(self._config, model_id)
        if not model_info:
            return

        name = model_info.get("name", model_id)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要从注册表移除「{name}」吗？\n\n"
            f"这将删除该模型的资源文件。\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 检查是否正在删除当前使用的模型
        current = ModelRegistry.get_default(self._config)
        was_current = (current == model_id)

        success = ModelImporter.remove_model(model_id, self._config)
        if success:
            # 如果删除的是当前模型，切回 firefly
            if was_current:
                ModelRegistry.set_default(self._config, "firefly")
                self.model_switched.emit("firefly")
                logger.info("当前模型已删除，自动切换到 firefly")
            self._build_content()
            logger.info("已删除模型: %s", model_id)
        else:
            QMessageBox.warning(self, "删除失败",
                "无法删除此模型。系统内置模型不可删除，或模型正在使用中。")

    def _remove_live2d_model(self, model_id: str) -> None:
        """从 Live2D 注册表移除模型。"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要从注册表移除 Live2D 模型「{model_id}」吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # 从 custom_live2d.json 移除
        data = self._config.read("custom_live2d")
        models = data.get("models", [])
        filtered = [m for m in models if m.get("id") != model_id]
        if len(filtered) == len(models):
            QMessageBox.warning(self, "提示", "系统内置 Live2D 模型不可删除。")
            return
        self._config.write("custom_live2d", {"models": filtered})
        import shutil
        from src.core.paths import LIVE2D_DIR
        model_dir = LIVE2D_DIR / "static" / "live2d-model" / model_id
        if model_dir.exists():
            shutil.rmtree(model_dir)
        self._build_content()

    # ── 详情 ────────────────────────────────────────────────

    def _show_detail(self, model_id: str) -> None:
        """显示角色模型详情。"""
        model_info = ModelRegistry.get_by_id(self._config, model_id)
        if not model_info:
            QMessageBox.warning(self, "提示", f"找不到模型: {model_id}")
            return

        detail_text = (
            f"模型 ID: {model_info.get('id', '')}\n"
            f"名称: {model_info.get('name', '')}\n"
            f"类型: {'系统内置' if model_info.get('source_type') == 'bundled' else '用户导入'}\n"
            f"资源目录: {model_info.get('dir', '')}\n"
            f"动作: {', '.join(model_info.get('actions', []))}\n"
            f"支持行走: {'是' if model_info.get('has_walking') else '否'}\n"
            f"支持语音: {'是' if model_info.get('voice_available') else '否'}\n"
        )
        if model_info.get("description"):
            detail_text += f"\n描述: {model_info['description']}"
        if model_info.get("registered_at"):
            detail_text += f"\n注册时间: {model_info['registered_at']}"

        QMessageBox.information(self, f"模型详情 - {model_info.get('name', '')}", detail_text)

    # ── 动作测试 ────────────────────────────────────────────

    def _show_action_test(self, model_id: str) -> None:
        """打开动作测试对话框，显示模型的所有动作并提供执行按钮。"""
        model_info = ModelRegistry.get_by_id(self._config, model_id)
        if not model_info:
            QMessageBox.warning(self, "提示", f"找不到模型: {model_id}")
            return

        actions = model_info.get("actions", [])
        if not actions:
            QMessageBox.information(self, "提示", "该模型没有可测试的动作。")
            return

        dialog = _ActionTestDialog(model_info, self)
        dialog.action_triggered.connect(
            lambda action: self.action_test_requested.emit(model_id, action)
        )
        dialog.exec()

    def _show_live2d_detail(self, model_id: str) -> None:
        """显示 Live2D 模型详情。"""
        models = self._load_live2d_models()
        info = next((m for m in models if m["id"] == model_id), None)
        if not info:
            QMessageBox.warning(self, "提示", f"找不到模型: {model_id}")
            return

        detail_text = (
            f"模型 ID: {info.get('id', '')}\n"
            f"名称: {info.get('name', '')}\n"
            f"类型: {'系统内置' if info.get('source_type') == 'bundled' else '用户导入'}\n"
            f"模型目录: {info.get('model_dir', '')}\n"
            f"模型文件: {info.get('model_file', '')}\n"
        )

        QMessageBox.information(self, f"Live2D 详情 - {info.get('name', '')}", detail_text)

    # ── 外部刷新 ────────────────────────────────────────────

    def refresh(self) -> None:
        """外部调用：刷新模型列表。"""
        self._build_content()
        logger.debug("模型页面已刷新")


# ═══════════════════════════════════════════════════════════════
# 动作测试对话框
# ═══════════════════════════════════════════════════════════════

class _ActionTestDialog(QDialog):
    """显示模型的所有动作，提供执行按钮用于测试。"""

    action_triggered = Signal(str)  # action_name

    def __init__(self, model_info: dict, parent=None):
        super().__init__(parent)
        model_name = model_info.get("name", model_info.get("id", "未知"))
        self.setWindowTitle(f"动作测试 - {model_name}")
        self.setMinimumSize(320, 250)
        self.setAttribute(Qt.WA_QuitOnClose, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 标题
        title = QLabel(f"「{model_name}」的动作列表", self)
        tf = QFont()
        tf.setPointSize(14)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(title)

        desc = QLabel("点击按钮执行对应动作，验证动作效果：", self)
        desc.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(desc)

        # 动作按钮网格
        actions = model_info.get("actions", [])
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        btn_style = """
            QPushButton {
                background: #2d2d2d; color: #e0e0e0;
                border: 1px solid #555; border-radius: 6px;
                padding: 10px 16px; font-size: 14px;
                text-align: left;
            }
            QPushButton:hover {
                background: #3a6ea5; color: #fff;
                border: 1px solid #5ba3e6;
            }
        """

        for action in actions:
            btn = QPushButton(f"▶ {action}", self)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, a=action: self._on_test_action(a))
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        # 底部提示
        note = QLabel("💡 执行动作后，切换回主窗口查看角色动画效果。", self)
        note.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(note)

    def _on_test_action(self, action: str) -> None:
        """触发动作测试。"""
        self.action_triggered.emit(action)
