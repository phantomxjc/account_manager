# -*- coding: utf-8 -*-
"""登录窗口：账号登录 / 注册，记住账号（两级：默认只记账号，密码可额外勾选）。"""
from PyQt5.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QCheckBox, QGroupBox, QMessageBox,
                             QApplication)
from PyQt5.QtCore import Qt, pyqtSignal

from ..config import save_remembered, load_remembered, clear_remembered
from ..style import ChineseStyle
from ..icon import get_app_icon


class LoginWindow(QDialog):
    """登录窗口"""

    login_success = pyqtSignal(str)  # 登录成功信号

    def __init__(self, password_manager):
        super().__init__()
        self.pm = password_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("墨香 - 登录")
        self.setFixedSize(420, 460)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(get_app_icon())

        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("main_widget")
        self.main_widget.setStyleSheet("""
            #main_widget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #F8F4E9, stop:1 #F0E9D9);
                border-radius: 15px;
                border: 1px solid #D9C7A7;
            }
        """)

        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(15)

        title_layout = QVBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)

        deco_label = QLabel("❀❀❀❀")
        deco_label.setAlignment(Qt.AlignCenter)
        deco_label.setStyleSheet("font-size: 32px; color: #A64D37;")
        title_layout.addWidget(deco_label)

        title_label = QLabel("墨香账号平台")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #654321;
                font-family: "Microsoft YaHei";
                margin-bottom: 2px;
            }
        """)
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("安全存储 · 优雅管理")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 14px; color: #8C7853;")
        title_layout.addWidget(subtitle_label)

        layout.addLayout(title_layout)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)

        username_group = QGroupBox()
        username_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #D9C7A7;
                border-radius: 10px;
                padding: 6px 10px;
                background: rgba(255, 255, 255, 0.7);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #8C7853;
            }
        """)
        username_group.setTitle("用户名")

        username_layout = QHBoxLayout(username_group)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #654321;
                min-height: 26px;
                max-height: 30px;
                padding: 2px 0px;
            }
        """)
        username_layout.addWidget(self.username_input)

        form_layout.addWidget(username_group)

        password_group = QGroupBox()
        password_group.setStyleSheet(username_group.styleSheet())
        password_group.setTitle("密码")

        password_layout = QHBoxLayout(password_group)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self.username_input.styleSheet())
        password_layout.addWidget(self.password_input)

        form_layout.addWidget(password_group)

        layout.addLayout(form_layout)

        # 记住账号 / 记住密码（两级：默认只记账号，密码需额外勾选）
        remember_layout = QHBoxLayout()
        remember_layout.setSpacing(20)
        self.remember_user_checkbox = QCheckBox("记住账号")
        self.remember_user_checkbox.setChecked(True)  # 默认勾选，只记账号
        self.remember_user_checkbox.setStyleSheet(
            "font-family: 'Microsoft YaHei'; color: #8C7853; spacing: 6px;")
        self.remember_pwd_checkbox = QCheckBox("记住密码")
        self.remember_pwd_checkbox.setStyleSheet(
            "font-family: 'Microsoft YaHei'; color: #8C7853; spacing: 6px;")
        self.remember_pwd_checkbox.setEnabled(False)  # 未勾选记账号时禁用
        remember_layout.addWidget(self.remember_user_checkbox, 0, Qt.AlignLeft)
        remember_layout.addWidget(self.remember_pwd_checkbox, 0, Qt.AlignLeft)
        remember_layout.addStretch()
        layout.addLayout(remember_layout)

        self.remember_user_checkbox.toggled.connect(self._on_remember_user_toggled)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        self.login_btn = ChineseStyle.create_gradient_button("登录", 120, 40)
        self.login_btn.clicked.connect(self.login)

        self.register_btn = ChineseStyle.create_gradient_button("注册", 120, 40, "#8C7853", "#A8967A")
        self.register_btn.clicked.connect(self.register)

        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.register_btn)

        layout.addLayout(button_layout)

        footer_label = QLabel("· 安全第一 · 隐私至上 ·")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("font-size: 12px; color: #8C7853;")
        layout.addWidget(footer_label)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.password_input.returnPressed.connect(self.login)
        self.center_window()

    def center_window(self):
        """窗口居中显示"""
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def _on_remember_user_toggled(self, checked):
        """取消「记住账号」时，禁用并取消「记住密码」"""
        self.remember_pwd_checkbox.setEnabled(checked)
        if not checked:
            self.remember_pwd_checkbox.setChecked(False)

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名和密码")
            return

        success, message = self.pm.login(username, password)
        if success:
            if self.remember_user_checkbox.isChecked():
                save_remembered(
                    username,
                    remember_pwd=self.remember_pwd_checkbox.isChecked(),
                    master_password=password)
            else:
                clear_remembered()
            self.login_success.emit(username)
            self.hide()
        else:
            QMessageBox.critical(self, "登录失败", message)

    def register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名和密码")
            return

        success, message = self.pm.register_user(username, password)
        if success:
            QMessageBox.information(self, "注册成功", "账号注册成功，请登录")
            self.password_input.clear()
        else:
            QMessageBox.critical(self, "注册失败", message)

    def show_login(self):
        """显示登录窗口；若已记住账号则自动填充（默认只记账号，密码需额外勾选）"""
        self.username_input.clear()
        self.password_input.clear()
        self.remember_user_checkbox.setChecked(True)  # 默认只记账号
        self.remember_pwd_checkbox.setChecked(False)
        uname, pwd = load_remembered()
        if uname:
            self.username_input.setText(uname)
            self.remember_user_checkbox.setChecked(True)
            if pwd:
                self.password_input.setText(pwd)
                self.remember_pwd_checkbox.setChecked(True)
        # 同步「记住密码」可用状态（依赖「记住账号」是否勾选）
        self.remember_pwd_checkbox.setEnabled(self.remember_user_checkbox.isChecked())
        self.show()
        self.raise_()
        self.activateWindow()
