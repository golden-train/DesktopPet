"""
首次运行许可协议弹窗。

显示 AGPL-3.0 协议 + 免责声明，需停留 15 秒后用户方可同意。
同意后写入配置，下次不再弹出。
"""

import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar,
)

logger = logging.getLogger(__name__)

_LICENSE_TEXT = """
                    GNU AFFERO GENERAL PUBLIC LICENSE
                       Version 3, 19 November 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.

                            Preamble

  The GNU Affero General Public License is a free, copyleft license for
software and other kinds of works, specifically designed to ensure
cooperation with the community in the case of network server software.

...
"""

_DISCLAIMER = """
⚠️  免责声明

本项目所使用的所有角色图片、Live2D 模型、音频等素材均来自网络搜集，
仅用于个人学习和交流，不遵循任何开源协议。

源码部分遵循 AGPL-3.0 协议开源，可自由使用、修改和分发，
但请自行替换所有受版权保护的贴图素材。

如涉及侵权，请联系删除。感谢所有创作者的作品。
"""


class LicenseDialog(QDialog):
    """许可协议弹窗——15 秒后才能同意。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("许可协议")
        self.setFixedSize(600, 480)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标题
        title = QLabel("DesktopPet - 许可协议", self)
        tf = QFont()
        tf.setPointSize(16)
        tf.setBold(True)
        title.setFont(tf)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 协议内容
        self._text = QTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setStyleSheet("""
            QTextEdit {
                background: #1a1a2e; color: #c0c0e0;
                border: 1px solid #444; border-radius: 6px;
                padding: 12px; font-size: 12px;
            }
        """)
        self._text.setText(_LICENSE_TEXT + "\n\n" + _DISCLAIMER)
        layout.addWidget(self._text, 1)

        # 倒计时
        self._countdown = 15
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 15)
        self._progress.setValue(15)
        self._progress.setTextVisible(True)
        self._progress.setFormat(f"请阅读协议… {self._countdown} 秒")
        self._progress.setStyleSheet("""
            QProgressBar {
                background: #333; border: none; border-radius: 4px;
                height: 20px; text-align: center; color: #ccc;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3a6ea5, stop:1 #5ba3e6);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._progress)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._decline_btn = QPushButton("退出", self)
        self._decline_btn.setStyleSheet("""
            QPushButton { background: #5a2d2d; color: #ccc;
                border: none; border-radius: 6px; padding: 8px 24px; }
            QPushButton:hover { background: #7a3d3d; }
        """)
        self._decline_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._decline_btn)

        self._accept_btn = QPushButton(f"同意 ({self._countdown}s)", self)
        self._accept_btn.setEnabled(False)
        self._accept_btn.setStyleSheet("""
            QPushButton { background: #2d5a2d; color: #ccc;
                border: none; border-radius: 6px; padding: 8px 24px; }
            QPushButton:hover { background: #3d7a3d; }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self._accept_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._accept_btn)

        layout.addLayout(btn_layout)

        # 倒计时定时器
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._countdown -= 1
        self._progress.setValue(self._countdown)
        self._progress.setFormat(f"请阅读协议… {self._countdown} 秒")
        if self._countdown <= 0:
            self._timer.stop()
            self._progress.setVisible(False)
            self._accept_btn.setEnabled(True)
            self._accept_btn.setText("同意")
