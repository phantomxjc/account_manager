# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 修改密码对话框
含实时强度检测、二次确认、事务回滚
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt

from ui.style import create_gradient_button, STYLE_LINE_EDIT, STYLE_LABEL_TITLE
from core.password_manager import PasswordManager


class ChangePasswordDialog(QDialog):
    """修改密码对话框"""

    def __init__(self, parent=None, password_manager: PasswordManager = None):
        super().__init__(parent)
        self.pm = password_manager
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("修改密码")
        self.setFixedSize(500, 450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # 标题
        title = QLabel("修改主密码")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(STYLE_LABEL_TITLE)
        layout.addWidget(title)

        # 当前密码
        cur_layout = QHBoxLayout()
        cur_label = QLabel("当前密码:")
        cur_label.setFixedWidth(100)
        cur_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.cur_pwd = QLineEdit()
        self.cur_pwd.setEchoMode(QLineEdit.Password)
        self.cur_pwd.setStyleSheet(STYLE_LINE_EDIT)
        cur_layout.addWidget(cur_label)
        cur_layout.addWidget(self.cur_pwd)
        layout.addLayout(cur_layout)

        # 新密码
        new_layout = QHBoxLayout()
        new_label = QLabel("新密码:")
        new_label.setFixedWidth(100)
        new_label.setStyleSheet(cur_label.styleSheet())
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.textChanged.connect(self._on_new_pwd_changed)
        self.new_pwd.setStyleSheet(STYLE_LINE_EDIT)
        new_layout.addWidget(new_label)
        new_layout.addWidget(self.new_pwd)
        layout.addLayout(new_layout)

        # 强度提示
        self.strength_lbl = QLabel("")
        self.strength_lbl.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 12px;")
        layout.addWidget(self.strength_lbl)

        # 确认新密码
        confirm_layout = QHBoxLayout()
        confirm_label = QLabel("确认新密码:")
        confirm_label.setFixedWidth(100)
        confirm_label.setStyleSheet(cur_label.styleSheet())
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd.textChanged.connect(self._on_confirm_changed)
        self.confirm_pwd.setStyleSheet(STYLE_LINE_EDIT)
        self.confirm_pwd.returnPressed.connect(self._do_change)
        confirm_layout.addWidget(confirm_label)
        confirm_layout.addWidget(self.confirm_pwd)
        layout.addLayout(confirm_layout)

        # 匹配提示
        self.match_lbl = QLabel("")
        self.match_lbl.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 12px;")
        layout.addWidget(self.match_lbl)

        # 要求说明
        req = QLabel("""
        <span style='font-family: "Microsoft YaHei"; font-size: 11px; color: #8C7853;'>
        • 密码长度至少8位<br>
        • 包含大写字母、小写字母和数字<br>
        • 建议使用特殊字符增强安全性
        </span>
        """)
        req.setWordWrap(True)
        layout.addWidget(req)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.change_btn = create_gradient_button("确认修改", 100, 35)
        self.change_btn.clicked.connect(self._do_change)
        self.change_btn.setEnabled(False)

        cancel_btn = create_gradient_button("取消", 100, 35, "#8C7853", "#A8967A")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.change_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    # ==================== 验证逻辑 ====================

    def _on_new_pwd_changed(self):
        pwd = self.new_pwd.text()
        if len(pwd) < 8:
            self.strength_lbl.setText("❌ 密码长度至少8位")
            self.strength_lbl.setStyleSheet("color: #FF6B6B; font-family: 'Microsoft YaHei';")
            self._update_btn_state()
            return

        has_u = any(c.isupper() for c in pwd)
        has_l = any(c.islower() for c in pwd)
        has_d = any(c.isdigit() for c in pwd)

        if not (has_u and has_l and has_d):
            self.strength_lbl.setText("❌ 需包含大小写字母和数字")
            self.strength_lbl.setStyleSheet("color: #FF6B6B; font-family: 'Microsoft YaHei';")
            self._update_btn_state()
            return

        score = 0
        if len(pwd) >= 12:
            score += 1
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for c in pwd):
            score += 1

        if score >= 1:
            self.strength_lbl.setText("✅ 密码强度：强")
            self.strength_lbl.setStyleSheet("color: #51CF66; font-family: 'Microsoft YaHei';")
        else:
            self.strength_lbl.setText("⚠️ 密码强度：中")
            self.strength_lbl.setStyleSheet("color: #FCC419; font-family: 'Microsoft YaHei';")
        self._update_btn_state()

    def _on_confirm_changed(self):
        new = self.new_pwd.text()
        confirm = self.confirm_pwd.text()

        if not new:
            self.match_lbl.setText("")
            self.change_btn.setEnabled(False)
            return

        if new == confirm:
            self.match_lbl.setText("✅ 密码匹配")
            self.match_lbl.setStyleSheet("color: #51CF66; font-family: 'Microsoft YaHei';")
        else:
            self.match_lbl.setText("❌ 密码不匹配")
            self.match_lbl.setStyleSheet("color: #FF6B6B; font-family: 'Microsoft YaHei';")
        self._update_btn_state()

    def _update_btn_state(self):
        """密码强度合格 + 两次输入一致 → 启用按钮"""
        pwd = self.new_pwd.text()
        ok_len = len(pwd) >= 8
        ok_types = any(c.isupper() for c in pwd) and any(c.islower() for c in pwd) and any(c.isdigit() for c in pwd)
        match = pwd == self.confirm_pwd.text() and bool(pwd)

        self.change_btn.setEnabled(ok_len and ok_types and match)

    # ==================== 执行修改 ====================

    def _do_change(self):
        cur = self.cur_pwd.text().strip()
        new = self.new_pwd.text().strip()
        confirm = self.confirm_pwd.text().strip()

        if not cur:
            QMessageBox.warning(self, "输入错误", "请输入当前密码")
            self.cur_pwd.setFocus()
            return
        if not new:
            QMessageBox.warning(self, "输入错误", "请输入新密码")
            self.new_pwd.setFocus()
            return
        if new != confirm:
            QMessageBox.warning(self, "输入错误", "两次输入的新密码不一致")
            self.confirm_pwd.setFocus()
            return
        if cur == new:
            QMessageBox.warning(self, "密码重复", "新密码不能与当前密码相同")
            self.new_pwd.clear()
            self.confirm_pwd.clear()
            self.new_pwd.setFocus()
            return

        # 验证当前密码
        if not self.pm.verify_master_password(cur):
            QMessageBox.warning(self, "验证失败", "当前密码错误")
            self.cur_pwd.clear()
            self.cur_pwd.setFocus()
            return

        # 执行修改
        ok, msg = self.pm.change_password(cur, new)
        if ok:
            QMessageBox.information(self, "修改成功", "密码修改成功")
            self.accept()
        else:
            QMessageBox.critical(self, "修改失败", msg)
