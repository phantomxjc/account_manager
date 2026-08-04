# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 登录 / 注册窗口
"""

from PyQt5.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal

from ui.style import (
    create_gradient_button, STYLE_LINE_EDIT, STYLE_LOGIN_WIDGET
)
from ui.security_dialog import SecurityDialog
from core.password_manager import PasswordManager


class LoginWindow(QDialog):
    """登录窗口"""

    login_success = pyqtSignal(str)

    def __init__(self, password_manager: PasswordManager):
        super().__init__()
        self.pm = password_manager
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("墨香 - 登录")
        self.setFixedSize(500, 500)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 主容器
        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("main_widget")
        self.main_widget.setStyleSheet(STYLE_LOGIN_WIDGET)

        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # ===== 标题区 =====
        deco = QLabel("❀❀❀❀")
        deco.setAlignment(Qt.AlignCenter)
        deco.setStyleSheet("font-size: 40px; color: #A64D37;")
        layout.addWidget(deco)

        title = QLabel("墨香账号平台")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #654321;
                font-family: "Microsoft YaHei";
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(title)

        subtitle = QLabel("安全存储 · 优雅管理")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #8C7853;")
        layout.addWidget(subtitle)

        # ===== 表单区 =====
        # 用户名
        user_group = QGroupBox("用户名")
        user_group.setStyleSheet(self._group_box_style())
        user_layout = QHBoxLayout(user_group)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setStyleSheet(self._transparent_line_edit())
        user_layout.addWidget(self.username_input)

        # 密码
        pwd_group = QGroupBox("密码")
        pwd_group.setStyleSheet(self._group_box_style())
        pwd_layout = QHBoxLayout(pwd_group)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self._transparent_line_edit())
        self.password_input.returnPressed.connect(self._on_login)
        pwd_layout.addWidget(self.password_input)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        form_layout.addWidget(user_group)
        form_layout.addWidget(pwd_group)
        layout.addLayout(form_layout)

        # ===== 按钮区 =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        self.login_btn = create_gradient_button("登录", 120, 40)
        self.login_btn.clicked.connect(self._on_login)

        self.register_btn = create_gradient_button("注册", 120, 40, "#8C7853", "#A8967A")
        self.register_btn.clicked.connect(self._on_register)

        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        layout.addLayout(btn_layout)

        # 底部
        footer = QLabel("· 安全第一 · 隐私至上 ·")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("font-size: 12px; color: #8C7853;")
        layout.addWidget(footer)

        # 外层布局
        outer = QVBoxLayout(self)
        outer.addWidget(self.main_widget)
        outer.setContentsMargins(20, 20, 20, 20)

    # ==================== 事件处理 ====================

    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名和密码")
            return

        ok, msg = self.pm.login(username, password)
        if ok:
            self.login_success.emit(username)
            self.hide()
        else:
            QMessageBox.critical(self, "登录失败", msg)

    def _on_register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名和密码")
            return

        ok, msg = self.pm.register_user(username, password)
        if ok:
            QMessageBox.information(self, "注册成功", "账号注册成功，请登录")
            self.password_input.clear()
        else:
            QMessageBox.critical(self, "注册失败", msg)

    def show_login(self):
        """重新显示登录窗口并清空输入"""
        self.username_input.clear()
        self.password_input.clear()
        self.show()
        self.raise_()
        self.activateWindow()

    # ==================== 内部样式辅助 ====================

    def _group_box_style(self) -> str:
        return """
            QGroupBox {
                border: 1px solid #D9C7A7;
                border-radius: 10px;
                padding: 10px;
                background: rgba(255, 255, 255, 0.7);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #8C7853;
            }
        """

    def _transparent_line_edit(self) -> str:
        return """
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #654321;
            }
        """
