# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 记录编辑对话框（新增 / 编辑）
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QTextEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt

from ui.style import create_gradient_button, STYLE_LINE_EDIT, STYLE_TEXT_EDIT, STYLE_LABEL_TITLE
from ui.security_dialog import SecurityDialog


class RecordDialog(QDialog):
    """新增 / 编辑记录对话框"""

    def __init__(self, parent=None, title: str = "新增记录",
                 record: dict = None, main_window=None):
        super().__init__(parent)
        self.record = record or {}
        self.result_data = None
        self.main_window = main_window
        self._pwd_visible = False
        self._init_ui(title)

    def _init_ui(self, title: str):
        self.setWindowTitle(title)
        self.setFixedSize(500, 450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 标题
        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(STYLE_LABEL_TITLE)
        layout.addWidget(t)

        # 网站名称
        row1 = QHBoxLayout()
        lbl1 = QLabel("网站名称:")
        lbl1.setFixedWidth(80)
        lbl1.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.site_input = QLineEdit()
        self.site_input.setText(self.record.get("网站名称", ""))
        self.site_input.setStyleSheet(STYLE_LINE_EDIT)
        row1.addWidget(lbl1)
        row1.addWidget(self.site_input)
        layout.addLayout(row1)

        # 网址
        row2 = QHBoxLayout()
        lbl2 = QLabel("网址:")
        lbl2.setFixedWidth(80)
        lbl2.setStyleSheet(lbl1.styleSheet())
        self.url_input = QLineEdit()
        self.url_input.setText(self.record.get("网址", ""))
        self.url_input.setStyleSheet(STYLE_LINE_EDIT)
        row2.addWidget(lbl2)
        row2.addWidget(self.url_input)
        layout.addLayout(row2)

        # 账号
        row3 = QHBoxLayout()
        lbl3 = QLabel("账号:")
        lbl3.setFixedWidth(80)
        lbl3.setStyleSheet(lbl1.styleSheet())
        self.user_input = QLineEdit()
        self.user_input.setText(self.record.get("账号", ""))
        self.user_input.setStyleSheet(STYLE_LINE_EDIT)
        row3.addWidget(lbl3)
        row3.addWidget(self.user_input)
        layout.addLayout(row3)

        # 密码 + 显示/隐藏
        row4 = QHBoxLayout()
        lbl4 = QLabel("密码:")
        lbl4.setFixedWidth(80)
        lbl4.setStyleSheet(lbl1.styleSheet())

        self.pwd_input = QLineEdit()
        self.pwd_input.setText(self.record.get("密码", ""))
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setStyleSheet(STYLE_LINE_EDIT)

        self.toggle_btn = QPushButton("显示")
        self.toggle_btn.setFixedWidth(60)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: #8C7853; color: white;
                border-radius: 5px; font-family: "Microsoft YaHei"; font-size: 12px;
            }
            QPushButton:hover { background: #A8967A; }
        """)
        self.toggle_btn.clicked.connect(self._toggle_password)

        row4.addWidget(lbl4)
        row4.addWidget(self.pwd_input)
        row4.addWidget(self.toggle_btn)
        layout.addLayout(row4)

        # 备注
        notes_label = QLabel("备注:")
        notes_label.setStyleSheet(lbl1.styleSheet())
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        self.notes_input.setStyleSheet(STYLE_TEXT_EDIT)
        self.notes_input.setText(self.record.get("备注", ""))

        notes_v = QVBoxLayout()
        notes_v.addWidget(notes_label)
        notes_v.addWidget(self.notes_input)
        layout.addLayout(notes_v)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = create_gradient_button("确定", 100, 35)
        ok_btn.clicked.connect(self._on_accept)

        cancel_btn = create_gradient_button("取消", 100, 35, "#8C7853", "#A8967A")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    # ==================== 交互逻辑 ====================

    def _toggle_password(self):
        if not self._pwd_visible:
            # 编辑已有记录时，需验证主密码
            if self.main_window and self.record.get("id"):
                dlg = SecurityDialog(self, "安全验证", "查看密码需要验证您的主密码")
                if dlg.exec_() != QDialog.Accepted:
                    return
                if not self.main_window.pm.verify_master_password(dlg.get_password()):
                    QMessageBox.warning(self, "验证失败", "主密码错误，无法查看密码")
                    return
            self.pwd_input.setEchoMode(QLineEdit.Normal)
            self.toggle_btn.setText("隐藏")
            self._pwd_visible = True
        else:
            self.pwd_input.setEchoMode(QLineEdit.Password)
            self.toggle_btn.setText("显示")
            self._pwd_visible = False

    def _on_accept(self):
        site = self.site_input.text().strip()
        if not site:
            QMessageBox.warning(self, "输入错误", "请输入网站名称")
            return

        self.result_data = {
            "网站名称": site,
            "网址":     self.url_input.text().strip(),
            "账号":     self.user_input.text().strip(),
            "密码":     self.pwd_input.text(),
            "备注":     self.notes_input.toPlainText().strip(),
        }
        super().accept()
