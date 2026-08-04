# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 安全验证对话框
敏感操作前验证主密码
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt

from ui.style import (
    create_gradient_button, STYLE_LABEL_TITLE, STYLE_LINE_EDIT
)


class SecurityDialog(QDialog):
    """安全验证对话框"""

    def __init__(self, parent=None, title: str = "安全验证",
                 message: str = "请输入您的主密码以继续操作"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(350, 200)
        self.setModal(True)
        self._init_ui(title, message)

    def _init_ui(self, title: str, message: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 标题
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(STYLE_LABEL_TITLE)
        layout.addWidget(title_lbl)

        # 提示信息
        msg_lbl = QLabel(message)
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853;")
        layout.addWidget(msg_lbl)

        # 密码输入
        pwd_layout = QHBoxLayout()
        pwd_label = QLabel("主密码:")
        pwd_label.setFixedWidth(80)
        pwd_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(STYLE_LINE_EDIT)
        self.password_input.returnPressed.connect(self.accept)

        pwd_layout.addWidget(pwd_label)
        pwd_layout.addWidget(self.password_input)
        layout.addLayout(pwd_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = create_gradient_button("验证", 80, 35)
        ok_btn.clicked.connect(self.accept)

        cancel_btn = create_gradient_button("取消", 80, 35, "#8C7853", "#A8967A")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_password(self) -> str:
        return self.password_input.text()
