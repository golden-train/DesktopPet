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
本项目源码采用 AGPL-v3 开源协议。依据协议规定，您可自由使用、修改、分发本项目代码；基于本代码创作的衍生作品，也必须沿用相同协议公开共享，并允许二次开发。若将代码部署后通过网络对外提供服务，需主动向使用者公开源代码及衍生代码。
请注意：项目内贴图、动画、音频等素材不适用 AGPL-v3 协议。未经原作者许可，任何人不得擅自使用、修改、分发上述版权素材。本项目内置素材仅作演示用途，未取得相关授权，请勿擅自转发。如涉及侵权，请联系我方进行删除。

！！使用须知 ⏱️：首次使用本项目需在此界面停留 15 秒，点击同意 ✅ 即代表您已完整阅读并认可以上全部条款。！！
...
"""

_DISCLAIMER = """
⚠️  免责声明
素材版权说明
本项目内所使用的角色图像、Live2D 模型、音频、美术贴图等各类素材，均为网络公开搜集所得，仅用于个人学习、研究与非商业交流用途。根据《中华人民共和国著作权法》相关规定，所有素材的著作权、肖像权及其他合法权利均归原创作方所有，本项目不持有上述素材的任何版权，亦未获得素材商用、二次分发、改编转授权等相关许可。
源码开源协议
本项目程序源代码单独遵循 AGPL-3.0 开源协议，任何人可依据该协议自由使用、修改、复制及分发源码。使用、二次分发或部署本项目时，请务必自行替换全部受版权保护的第三方素材，避免产生版权纠纷。
侵权处理与免责
本项目无意侵犯任何第三方合法权益。若相关权利方发现本项目内容存在侵权行为，请及时联系，将第一时间下架、删除对应内容。使用者因违规使用素材、违反开源协议、擅自商用等行为所产生的一切法律责任与经济纠纷，均由使用者自行承担，本项目及相关维护者不承担任何连带责任。
最后感谢所有原创创作者的优秀作品与付出。
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
