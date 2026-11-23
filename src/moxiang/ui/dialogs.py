# -*- coding: utf-8 -*-
"""对话框集合与后台线程：安全验证、修改密码、密码生成器、记录编辑、
Excel/CSV 导入、数据导出、空闲锁定设置、分享，网络类型管理，以及导入线程。"""
import io
import os
import zipfile
import pandas as pd
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QLineEdit, QPushButton, QTextEdit,
                             QComboBox, QRadioButton, QButtonGroup, QProgressBar,
                             QFileDialog, QListWidget, QListWidgetItem, QMessageBox,
                             QSpinBox, QCheckBox, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QRect
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle

from ..config import (BASE_DIR, DEFAULT_IDLE_MINUTES,
                      load_network_types, save_network_types, fallback_network_type)
from ..style import ChineseStyle
from ..icon import get_app_icon
from ..database import _read_import_dataframe
from ..netcheck import detect_network_type


class CardItemDelegate(QStyledItemDelegate):
    """卡片化列表项绘制：左侧色点/序号徽章 + 主文字 + 右侧计数胶囊。
    通过 item.setData(Qt.UserRole, ...) 传入配置字典：
      dot: 圆点颜色 / badge: 序号文字 / count: 右侧胶囊文字 / accent: 选中竖线色
    """
    def __init__(self, accent=None, parent=None):
        super().__init__(parent)
        self.accent = QColor(accent or "#A64D37")

    def paint(self, painter, option, index):
        cfg = index.data(Qt.UserRole) or {}
        rect = option.rect
        painter.save()
        # 选中态背景 + 左侧强调竖线
        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, QColor("#F0DBCB"))
            painter.fillRect(QRect(rect.left(), rect.top() + 4, 3, rect.height() - 8), self.accent)
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(rect, QColor("#F7F1E6"))

        text_color = QColor("#6B4423" if (option.state & QStyle.State_Selected) else "#5A4632")
        x = rect.left() + 12
        cy = rect.center().y()

        # 左侧：彩色圆点 或 序号徽章
        dot = cfg.get("dot")
        badge = cfg.get("badge")
        if dot:
            painter.setBrush(QColor(dot))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRect(x, cy - 4, 8, 8))
            x += 18
        elif badge:
            br = QRect(x, cy - 9, 18, 18)
            painter.setBrush(QColor(self.accent if (option.state & QStyle.State_Selected) else "#EDE0D0"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(br, 4, 4)
            painter.setPen(QColor("white" if (option.state & QStyle.State_Selected) else "#8C7853"))
            f = QFont("Microsoft YaHei", 8)
            painter.setFont(f)
            painter.drawText(br, Qt.AlignCenter, str(badge))
            x += 26

        # 主文字
        painter.setPen(text_color)
        f = QFont("Microsoft YaHei", 10, QFont.Bold if (option.state & QStyle.State_Selected) else QFont.Normal)
        painter.setFont(f)
        main = str(cfg.get("text", ""))
        fm = painter.fontMetrics()
        painter.drawText(QRect(x, rect.top(), fm.width(main), rect.height()), Qt.AlignVCenter, main)
        x += fm.width(main) + 10

        # 右侧计数胶囊
        count = cfg.get("count")
        if count:
            ct = str(count)
            cf = QFont("Microsoft YaHei", 9)
            painter.setFont(cf)
            cm = painter.fontMetrics()
            cw = cm.width(ct) + 18
            ch = 20
            cr = QRect(rect.right() - cw - 12, cy - ch // 2, cw, ch)
            painter.setBrush(QColor("#E8DCC8" if (option.state & QStyle.State_Selected) else "#F0E8DA"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(cr, ch // 2, ch // 2)
            painter.setPen(QColor("#7A5C3A"))
            painter.drawText(cr, Qt.AlignCenter, ct)
        painter.restore()


class DetectNetThread(QThread):
    """后台识别网址所属网络类型（DNS 探测可能阻塞，放线程里跑）"""
    detect_done = pyqtSignal(str, str)   # (识别类型, 依据说明)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        ntype, reason = detect_network_type(self.url)
        self.detect_done.emit(ntype, reason)


class SecurityDialog(QDialog):
    """安全验证对话框"""

    def __init__(self, parent=None, title="安全验证", message="请输入您的主密码以继续操作"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(350, 200)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        ChineseStyle.add_dialog_accent(self)

        title_label = QLabel(title)
        ChineseStyle.set_dialog_title(title_label)
        layout.addWidget(title_label)

        hint = ChineseStyle.make_hint_bar(message)
        hint.setAlignment(Qt.AlignLeft)
        layout.addWidget(hint)

        password_layout = QHBoxLayout()
        password_label = QLabel("主密码:")
        password_label.setFixedWidth(80)
        password_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
            }
        """)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = ChineseStyle.primary_button("验证", 80, 34)
        ok_btn.clicked.connect(self.accept)

        cancel_btn = ChineseStyle.secondary_button("取消", 80, 34)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.password_input.returnPressed.connect(self.accept)

    def get_password(self):
        return self.password_input.text()


class ChangePasswordDialog(QDialog):
    """修改密码对话框"""

    def __init__(self, parent=None, password_manager=None):
        super().__init__(parent)
        self.pm = password_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("修改密码")
        self.setFixedSize(500, 450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        ChineseStyle.add_dialog_accent(self)

        # 标题
        title_label = QLabel("修改主密码")
        ChineseStyle.set_dialog_title(title_label)
        layout.addWidget(title_label)

        # 当前密码
        current_pwd_layout = QHBoxLayout()
        current_pwd_label = QLabel("当前密码:")
        current_pwd_label.setFixedWidth(100)
        current_pwd_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.current_pwd_input = QLineEdit()
        self.current_pwd_input.setEchoMode(QLineEdit.Password)
        self.current_pwd_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
            }
        """)
        current_pwd_layout.addWidget(current_pwd_label)
        current_pwd_layout.addWidget(self.current_pwd_input)
        layout.addLayout(current_pwd_layout)

        # 新密码
        new_pwd_layout = QHBoxLayout()
        new_pwd_label = QLabel("新密码:")
        new_pwd_label.setFixedWidth(100)
        new_pwd_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setEchoMode(QLineEdit.Password)
        self.new_pwd_input.textChanged.connect(self.validate_password_strength)
        self.new_pwd_input.setStyleSheet(self.current_pwd_input.styleSheet())
        new_pwd_layout.addWidget(new_pwd_label)
        new_pwd_layout.addWidget(self.new_pwd_input)
        layout.addLayout(new_pwd_layout)

        # 密码强度指示器
        self.strength_label = QLabel("")
        self.strength_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 12px;")
        layout.addWidget(self.strength_label)

        # 确认新密码
        confirm_pwd_layout = QHBoxLayout()
        confirm_pwd_label = QLabel("确认新密码:")
        confirm_pwd_label.setFixedWidth(100)
        confirm_pwd_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setEchoMode(QLineEdit.Password)
        self.confirm_pwd_input.textChanged.connect(self.check_password_match)
        self.confirm_pwd_input.setStyleSheet(self.current_pwd_input.styleSheet())
        confirm_pwd_layout.addWidget(confirm_pwd_label)
        confirm_pwd_layout.addWidget(self.confirm_pwd_input)
        layout.addLayout(confirm_pwd_layout)

        # 密码匹配指示器
        self.match_label = QLabel("")
        self.match_label.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 12px;")
        layout.addWidget(self.match_label)

        # 密码要求说明
        requirements_label = QLabel("""
        <span style='font-family: "Microsoft YaHei"; font-size: 11px; color: #8C7853;'>
        • 密码长度至少8位<br>
        • 包含大写字母、小写字母和数字<br>
        • 建议使用特殊字符增强安全性
        </span>
        """)
        requirements_label.setWordWrap(True)
        layout.addWidget(requirements_label)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.change_btn = ChineseStyle.primary_button("确认修改", 100, 34)
        self.change_btn.clicked.connect(self.change_password)
        self.change_btn.setEnabled(False)  # 初始禁用

        cancel_btn = ChineseStyle.secondary_button("取消", 100, 34)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.change_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        # 连接回车键
        self.confirm_pwd_input.returnPressed.connect(self.change_password)

    def validate_password_strength(self):
        """验证密码强度"""
        password = self.new_pwd_input.text()

        if len(password) < 8:
            self.strength_label.setText("❌ 密码长度至少8位")
            self.strength_label.setStyleSheet("color: #FF6B6B; font-family: 'Microsoft YaHei';")
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            self.strength_label.setText("❌ 需包含大小写字母和数字")
            self.strength_label.setStyleSheet("color: #FF6B6B; font-family: 'Microsoft YaHei';")
            return False

        # 评估密码强度
        strength = 0
        if len(password) >= 12:
            strength += 1
        if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for c in password):
            strength += 1

        if strength >= 1:
            self.strength_label.setText("✅ 密码强度：强")
            self.strength_label.setStyleSheet("color: #51CF66; font-family: 'Microsoft YaHei';")
        else:
            self.strength_label.setText("⚠️ 密码强度：中")
            self.strength_label.setStyleSheet("color: #FCC419; font-family: 'Microsoft YaHei';")

        return True

    def check_password_match(self):
        """检查密码是否匹配"""
        new_pwd = self.new_pwd_input.text()
        confirm_pwd = self.confirm_pwd_input.text()

        if not new_pwd:
            self.match_label.setText("")
            self.change_btn.setEnabled(False)
            return False

        if new_pwd == confirm_pwd:
            self.match_label.setText("✅ 密码匹配")
            self.match_label.setStyleSheet("color: #51CF66; font-family: 'Microsoft YaHei';")
            # 只有在密码强度合格且匹配时才启用按钮
            if self.validate_password_strength():
                self.change_btn.setEnabled(True)
            return True
        else:
            self.match_label.setText("❌ 密码不匹配")
            self.match_label.setStyleSheet("color: #FF6B6B; font-family: 'Microsoft YaHei';")
            self.change_btn.setEnabled(False)
            return False

    def change_password(self):
        """执行密码修改"""
        current_password = self.current_pwd_input.text().strip()
        new_password = self.new_pwd_input.text().strip()
        confirm_password = self.confirm_pwd_input.text().strip()

        # 验证输入
        if not current_password:
            QMessageBox.warning(self, "输入错误", "请输入当前密码")
            self.current_pwd_input.setFocus()
            return

        if not new_password:
            QMessageBox.warning(self, "输入错误", "请输入新密码")
            self.new_pwd_input.setFocus()
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "输入错误", "新密码和确认密码不匹配")
            self.confirm_pwd_input.setFocus()
            return

        if not self.validate_password_strength():
            QMessageBox.warning(self, "密码强度不足", "请按照要求设置更强的密码")
            self.new_pwd_input.setFocus()
            return

        # 验证当前密码
        if not self.pm.verify_master_password(current_password):
            QMessageBox.warning(self, "验证失败", "当前密码错误")
            self.current_pwd_input.clear()
            self.current_pwd_input.setFocus()
            return

        # 检查新密码是否与旧密码相同
        if current_password == new_password:
            QMessageBox.warning(self, "密码重复", "新密码不能与当前密码相同")
            self.new_pwd_input.clear()
            self.confirm_pwd_input.clear()
            self.new_pwd_input.setFocus()
            return

        # 执行密码修改
        try:
            success, message = self.pm.change_password(current_password, new_password)
            if success:
                QMessageBox.information(self, "修改成功", "密码修改成功")
                self.accept()
            else:
                QMessageBox.critical(self, "修改失败", message)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"修改密码时发生错误: {str(e)}")


class PasswordGeneratorDialog(QDialog):
    """强密码生成器对话框（功能2）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("密码生成器")
        self.setFixedSize(460, 330)
        self.setWindowIcon(get_app_icon())
        self.generated = ""
        self.init_ui()

    def init_ui(self):
        import secrets
        import string
        self._secrets = secrets
        self._string = string

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        ChineseStyle.add_dialog_accent(self)

        title = QLabel("强密码生成器")
        ChineseStyle.set_dialog_title(title)
        layout.addWidget(title)
        layout.addWidget(ChineseStyle.make_subtitle("生成高强度随机密码"))

        # 长度
        len_layout = QHBoxLayout()
        len_label = QLabel("长度:")
        len_label.setFixedWidth(50)
        len_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.len_spin = QSpinBox()
        self.len_spin.setRange(8, 64)
        self.len_spin.setValue(16)
        self.len_spin.setStyleSheet("font-family: 'Microsoft YaHei';")
        len_layout.addWidget(len_label)
        len_layout.addWidget(self.len_spin)
        len_layout.addStretch()
        layout.addLayout(len_layout)

        # 字符类型
        opt_label = QLabel("包含字符:")
        opt_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321; font-weight: bold;")
        layout.addWidget(opt_label)
        self.cb_upper = QCheckBox("大写字母 (A-Z)")
        self.cb_lower = QCheckBox("小写字母 (a-z)")
        self.cb_digit = QCheckBox("数字 (0-9)")
        self.cb_symbol = QCheckBox("符号 (!@#$...)")
        self.cb_upper.setChecked(True)
        self.cb_lower.setChecked(True)
        self.cb_digit.setChecked(True)
        self.cb_symbol.setChecked(True)
        for cb in (self.cb_upper, self.cb_lower, self.cb_digit, self.cb_symbol):
            cb.setStyleSheet("font-family: 'Microsoft YaHei';")
            layout.addWidget(cb)

        # 生成结果
        self.result_edit = QLineEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 6px;
                font-family: 'Consolas','Microsoft YaHei';
                font-size: 13px;
                color: #654321;
            }
        """)
        layout.addWidget(self.result_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        regen_btn = ChineseStyle.tool_button("重新生成")
        regen_btn.clicked.connect(self.generate)
        copy_btn = ChineseStyle.tool_button("复制")
        copy_btn.clicked.connect(self.copy_password)
        use_btn = ChineseStyle.primary_button("使用此密码", 110, 34)
        use_btn.clicked.connect(self.accept)
        cancel_btn = ChineseStyle.secondary_button("取消", 90, 34)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(regen_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(use_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.generate()

    def generate(self):
        """使用密码学安全随机数生成密码"""
        import secrets
        import string
        length = self.len_spin.value()
        pool = ""
        if self.cb_upper.isChecked():
            pool += string.ascii_uppercase
        if self.cb_lower.isChecked():
            pool += string.ascii_lowercase
        if self.cb_digit.isChecked():
            pool += string.digits
        if self.cb_symbol.isChecked():
            pool += "!@#$%^&*()-_=+[]{};:,.<>?/"
        if not pool:
            pool = string.ascii_letters + string.digits
        self.generated = "".join(secrets.choice(pool) for _ in range(length))
        self.result_edit.setText(self.generated)

    def copy_password(self):
        from PyQt5.QtWidgets import QApplication
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.generated)
            QMessageBox.information(self, "已复制", "密码已复制到剪贴板")

    def get_password(self):
        return self.generated


class RecordDialog(QDialog):
    """记录编辑对话框"""

    def __init__(self, parent=None, title="", record=None, main_window=None):
        super().__init__(parent)
        self.record = record or {}
        self.result_data = None
        self.main_window = main_window
        self.password_visible = False
        self.init_ui(title)

    def init_ui(self, title):
        self.setWindowTitle(title)
        self.setFixedSize(500, 530)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        ChineseStyle.add_dialog_accent(self)

        title_label = QLabel(title)
        ChineseStyle.set_dialog_title(title_label)
        layout.addWidget(title_label)

        form_layout = QVBoxLayout()

        site_name_layout = QHBoxLayout()
        site_name_label = QLabel("网站名称:")
        site_name_label.setFixedWidth(80)
        site_name_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.site_name_input = QLineEdit()
        self.site_name_input.setText(self.record.get("网站名称", ""))
        self.site_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
            }
        """)
        site_name_layout.addWidget(site_name_label)
        site_name_layout.addWidget(self.site_name_input)
        form_layout.addLayout(site_name_layout)

        url_layout = QHBoxLayout()
        url_label = QLabel("网址:")
        url_label.setFixedWidth(80)
        url_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.url_input = QLineEdit()
        self.url_input.setText(self.record.get("网址", ""))
        self.url_input.setStyleSheet(self.site_name_input.styleSheet())
        self.detect_btn = ChineseStyle.tool_button("自动识别", 76, 30)
        self.detect_btn.clicked.connect(self.auto_detect_ntype)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.detect_btn)
        form_layout.addLayout(url_layout)

        # 自动识别结果提示条
        self.detect_label = QLabel("")
        self.detect_label.setStyleSheet(
            "font-family: 'Microsoft YaHei'; color: #3b6d11; font-size: 11px; padding-left: 80px;")
        self.detect_label.setVisible(False)
        form_layout.addWidget(self.detect_label)

        username_layout = QHBoxLayout()
        username_label = QLabel("账号:")
        username_label.setFixedWidth(80)
        username_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.username_input = QLineEdit()
        self.username_input.setText(self.record.get("账号", ""))
        self.username_input.setStyleSheet(self.site_name_input.styleSheet())
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        form_layout.addLayout(username_layout)

        password_layout = QHBoxLayout()
        password_label = QLabel("密码:")
        password_label.setFixedWidth(80)
        password_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")

        self.password_input = QLineEdit()
        self.password_input.setText(self.record.get("密码", ""))
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self.site_name_input.styleSheet())

        self.toggle_password_btn = ChineseStyle.tool_button("显示", 60, 30)
        self.toggle_password_btn.clicked.connect(self.toggle_password_visibility)

        self.gen_password_btn = ChineseStyle.tool_button("生成", 60, 30)
        self.gen_password_btn.clicked.connect(self.open_generator)

        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.toggle_password_btn)
        password_layout.addWidget(self.gen_password_btn)
        form_layout.addLayout(password_layout)

        # 网络类型（下拉，选项来自类型管理字典）
        ntype_layout = QHBoxLayout()
        ntype_label = QLabel("网络类型:")
        ntype_label.setFixedWidth(80)
        ntype_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.ntype_combo = QComboBox()
        self.ntype_combo.addItems(load_network_types())
        current_type = self.record.get("网络类型", "")
        if current_type and self.ntype_combo.findText(current_type) < 0:
            self.ntype_combo.addItem(current_type)   # 老类型已被删除时仍可显示
        if current_type:
            self.ntype_combo.setCurrentText(current_type)
        self.ntype_combo.setStyleSheet(self.site_name_input.styleSheet())
        ntype_layout.addWidget(ntype_label)
        ntype_layout.addWidget(self.ntype_combo)
        form_layout.addLayout(ntype_layout)

        notes_layout = QVBoxLayout()
        notes_label = QLabel("备注:")
        notes_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        self.notes_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
            }
        """)
        self.notes_input.setText(self.record.get("备注", ""))
        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(self.notes_input)
        form_layout.addLayout(notes_layout)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = ChineseStyle.primary_button("确定", 100, 34)
        ok_btn.clicked.connect(self.accept)

        cancel_btn = ChineseStyle.secondary_button("取消", 100, 34)
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def auto_detect_ntype(self):
        """自动识别网址所属网络类型，识别结果填入类型下拉"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "网址为空", "请先填写网址再识别。")
            return
        self.detect_btn.setEnabled(False)
        self.detect_btn.setText("识别中…")
        self._detect_thread = DetectNetThread(url, self)
        self._detect_thread.detect_done.connect(self._on_detect_done)
        self._detect_thread.start()

    def _on_detect_done(self, ntype, reason):
        """识别完成：自动填入下拉（类型字典里没有则自动补录）"""
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText("自动识别")
        if not ntype:
            self.detect_label.setText(f"无法识别：{reason}")
            self.detect_label.setVisible(True)
            return

        # 类型字典里没有的识别结果自动补录
        types = load_network_types()
        if ntype not in types:
            types.append(ntype)
            save_network_types(types)
            self.ntype_combo.addItem(ntype)

        self.ntype_combo.setCurrentText(ntype)
        self.detect_label.setText(f"识别为「{ntype}」：{reason}（可手动修改）")
        self.detect_label.setVisible(True)

    def toggle_password_visibility(self):
        """切换密码显示/隐藏状态"""
        if not self.password_visible:
            if self.main_window and self.record and "id" in self.record:
                dialog = SecurityDialog(self, "安全验证", "查看密码需要验证您的主密码")
                if dialog.exec_() == QDialog.Accepted:
                    if self.main_window.pm.verify_master_password(dialog.get_password()):
                        self.password_input.setEchoMode(QLineEdit.Normal)
                        self.toggle_password_btn.setText("隐藏")
                        self.password_visible = True
                    else:
                        QMessageBox.warning(self, "验证失败", "主密码错误，无法查看密码")
                else:
                    return
            else:
                self.password_input.setEchoMode(QLineEdit.Normal)
                self.toggle_password_btn.setText("隐藏")
                self.password_visible = True
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_password_btn.setText("显示")
            self.password_visible = False

    def open_generator(self):
        """打开密码生成器并把结果填入密码框"""
        dialog = PasswordGeneratorDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            pwd = dialog.get_password()
            if pwd:
                self.password_input.setText(pwd)
                self.password_input.setEchoMode(QLineEdit.Normal)
                self.toggle_password_btn.setText("隐藏")
                self.password_visible = True

    def accept(self):
        site_name = self.site_name_input.text().strip()
        if not site_name:
            QMessageBox.warning(self, "输入错误", "请输入网站名称")
            return

        self.result_data = {
            "网站名称": site_name,
            "网址": self.url_input.text().strip(),
            "账号": self.username_input.text().strip(),
            "密码": self.password_input.text(),
            "备注": self.notes_input.toPlainText().strip(),
            "网络类型": self.ntype_combo.currentText().strip()
        }
        super().accept()


class ExcelImportDialog(QDialog):
    """Excel/CSV 导入对话框"""

    import_completed = pyqtSignal(bool, str)

    def __init__(self, parent=None, password_manager=None):
        super().__init__(parent)
        self.pm = password_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Excel/CSV 数据导入")
        self.setFixedSize(500, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        ChineseStyle.add_dialog_accent(self)

        title_label = QLabel("Excel/CSV 数据导入")
        ChineseStyle.set_dialog_title(title_label)
        layout.addWidget(title_label)
        layout.addWidget(ChineseStyle.make_subtitle("选择文件并指定导入的目标数据表"))
        layout.addWidget(ChineseStyle.make_hint_bar("请确认列映射后开始导入"))

        file_group = QGroupBox("选择文件")
        file_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #D9C7A7;
                border-radius: 8px;
                padding: 10px;
                background: rgba(255, 255, 255, 0.7);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #8C7853;
            }
        """)

        file_layout = QVBoxLayout(file_group)

        file_path_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("请选择Excel或CSV文件...")
        self.file_path_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
            }
        """)
        browse_btn = ChineseStyle.tool_button("浏览", 70, 30)
        browse_btn.clicked.connect(self.browse_file)
        file_path_layout.addWidget(self.file_path_input)
        file_path_layout.addWidget(browse_btn)
        file_layout.addLayout(file_path_layout)

        sheet_layout = QHBoxLayout()
        sheet_label = QLabel("工作表:")
        sheet_label.setFixedWidth(80)
        sheet_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.sheet_combo = QComboBox()
        self.sheet_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
                min-width: 120px;
            }
        """)
        self.sheet_combo.addItem("自动选择（第一个工作表）")
        sheet_layout.addWidget(sheet_label)
        sheet_layout.addWidget(self.sheet_combo)
        sheet_layout.addStretch()
        file_layout.addLayout(sheet_layout)

        file_layout.addStretch()
        layout.addWidget(file_group)

        target_group = QGroupBox("选择目标数据表")
        target_group.setStyleSheet(file_group.styleSheet())

        target_layout = QVBoxLayout(target_group)

        self.target_radio_group = QButtonGroup()

        # 动态生成目标表选项（单位表/个人表 + 自定义表）
        table_names = self.pm.get_table_names() if self.pm else ["单位表", "个人表"]
        self.target_radios = []
        for i, tname in enumerate(table_names):
            rb = QRadioButton(tname)
            if i == 0:
                rb.setChecked(True)
            self.target_radio_group.addButton(rb)
            target_layout.addWidget(rb)
            self.target_radios.append(rb)
        target_layout.addStretch()

        layout.addWidget(target_group)

        options_group = QGroupBox("导入选项")
        options_group.setStyleSheet(file_group.styleSheet())

        options_layout = QVBoxLayout(options_group)

        mapping_label = QLabel("字段映射说明：")
        mapping_label.setStyleSheet(
            "font-family: 'Microsoft YaHei'; color: #654321; font-weight: bold; font-size: 12px;")
        options_layout.addWidget(mapping_label)

        mapping_text = QLabel("""
        • 系统会自动匹配常见的Excel/CSV列名，如：网站名称、网站名、网址、URL、账号、账户、密码等
        • 如果列名不匹配，系统会按照顺序尝试匹配
        • 必填字段：网站名称或账号至少填写一项
        • 支持.xlsx、.xls 格式的Excel文件，以及 .csv 文件（UTF-8编码）
        """)
        mapping_text.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853; font-size: 11px;")
        mapping_text.setWordWrap(True)
        options_layout.addWidget(mapping_text)

        options_layout.addStretch()
        layout.addWidget(options_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                text-align: center;
                font-family: "Microsoft YaHei";
                color: #654321;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #A64D37, stop:1 #C46C4E);
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.import_btn = ChineseStyle.primary_button("开始导入", 100, 34)
        self.import_btn.clicked.connect(self.start_import)
        button_layout.addWidget(self.import_btn)

        self.cancel_btn = ChineseStyle.secondary_button("取消", 100, 34)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def browse_file(self):
        """浏览选择Excel或CSV文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Excel/CSV文件",
            "",
            "Excel/CSV文件 (*.xlsx *.xls *.csv);;所有文件 (*)"
        )
        if file_path:
            self.file_path_input.setText(file_path)
            self.load_sheet_info(file_path)

    def load_sheet_info(self, file_path):
        """加载Excel文件的工作表信息；CSV文件无工作表"""
        self.sheet_combo.clear()
        if file_path.lower().endswith('.csv'):
            self.sheet_combo.addItem("CSV文件（无工作表）")
            self.sheet_combo.setEnabled(False)
            return

        self.sheet_combo.setEnabled(True)
        self.sheet_combo.addItem("自动选择（第一个工作表）")
        try:
            xls = pd.ExcelFile(file_path)
            sheets = xls.sheet_names
            for sheet in sheets:
                self.sheet_combo.addItem(sheet)
        except Exception as e:
            QMessageBox.warning(self, "文件错误", f"无法读取Excel文件: {str(e)}")

    def start_import(self):
        """开始导入过程"""
        file_path = self.file_path_input.text().strip()
        if not file_path:
            QMessageBox.warning(self, "选择文件", "请先选择Excel文件")
            return

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "文件不存在", "所选的Excel文件不存在")
            return

        if not (file_path.lower().endswith('.xlsx') or file_path.lower().endswith('.xls') or file_path.lower().endswith('.csv')):
            QMessageBox.warning(self, "文件格式", "请选择.xlsx、.xls或.csv格式的文件")
            return

        checked_rb = self.target_radio_group.checkedButton()
        if checked_rb is None:
            QMessageBox.warning(self, "目标表", "请选择一个目标数据表")
            return
        target_table = checked_rb.text()

        sheet_selection = self.sheet_combo.currentText()
        sheet_name = None
        if sheet_selection not in ("自动选择（第一个工作表）", "CSV文件（无工作表）"):
            sheet_name = sheet_selection

        # 验证主密码
        dialog = SecurityDialog(self, "安全验证", "导入数据需要验证您的主密码")
        if dialog.exec_() == QDialog.Accepted:
            if self.pm.verify_master_password(dialog.get_password()):
                self.set_interaction_enabled(False)
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)

                # 在线程中执行导入
                self.import_thread = ImportThread(file_path, target_table, sheet_name, self.pm)
                self.import_thread.progress_updated.connect(self.update_progress)
                self.import_thread.import_completed.connect(self.on_import_completed)
                self.import_thread.start()
            else:
                QMessageBox.warning(self, "验证失败", "主密码错误，无法导入数据")

    def set_interaction_enabled(self, enabled):
        """设置界面元素交互状态"""
        self.file_path_input.setEnabled(enabled)
        self.sheet_combo.setEnabled(enabled)
        self.unit_radio.setEnabled(enabled)
        self.personal_radio.setEnabled(enabled)
        self.import_btn.setEnabled(enabled)
        self.cancel_btn.setEnabled(enabled)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def on_import_completed(self, success, message):
        """导入完成回调"""
        self.set_interaction_enabled(True)
        self.progress_bar.setVisible(False)

        if success:
            QMessageBox.information(self, "导入成功", message)
            self.import_completed.emit(True, message)
            self.accept()
        else:
            QMessageBox.critical(self, "导入失败", message)
            self.import_completed.emit(False, message)


class ImportThread(QThread):
    """导入数据的后台线程"""

    progress_updated = pyqtSignal(int)
    import_completed = pyqtSignal(bool, str)

    def __init__(self, file_path, target_table, sheet_name, password_manager):
        super().__init__()
        self.file_path = file_path
        self.target_table = target_table
        self.sheet_name = sheet_name
        self.pm = password_manager

    def run(self):
        """线程运行函数"""
        try:
            df = _read_import_dataframe(self.file_path, self.sheet_name)

            if df.empty:
                self.import_completed.emit(False, "文件为空或没有数据")
                return

            field_mapping = {
                '网站名称': ['网站名称', '网站名', '网站', '名称', '站点名称', '平台名称'],
                '网址': ['网址', '网站地址', 'URL', '链接', '地址', '网站链接'],
                '账号': ['账号', '账户', '用户名', '用户', '登录名', '用户账号'],
                '密码': ['密码', '登陆密码', '登录密码', 'pass', 'passwd'],
                '备注': ['备注', '说明', '注释', '描述', 'note', 'description'],
                '网络类型': ['网络类型', '类型', '网络']
            }

            actual_mapping = {}
            for target_field, possible_names in field_mapping.items():
                for col in df.columns:
                    if any(name in str(col) for name in possible_names):
                        actual_mapping[target_field] = col
                        break
                else:
                    actual_mapping[target_field] = None

            total_rows = len(df)
            imported_count = 0
            skipped_count = 0
            error_count = 0

            for index, row in df.iterrows():
                try:
                    # 更新进度
                    progress = int((index + 1) / total_rows * 100)
                    self.progress_updated.emit(progress)

                    website_name = row[actual_mapping['网站名称']] if actual_mapping['网站名称'] is not None else ""
                    website_url = row[actual_mapping['网址']] if actual_mapping['网址'] is not None else ""
                    account = row[actual_mapping['账号']] if actual_mapping['账号'] is not None else ""
                    password = row[actual_mapping['密码']] if actual_mapping['密码'] is not None else ""
                    notes = row[actual_mapping['备注']] if actual_mapping['备注'] is not None else ""
                    network_type = row[actual_mapping['网络类型']] if actual_mapping['网络类型'] is not None else ""

                    website_name = str(website_name).strip() if pd.notna(website_name) else ""
                    website_url = str(website_url).strip() if pd.notna(website_url) else ""
                    account = str(account).strip() if pd.notna(account) else ""
                    password = str(password).strip() if pd.notna(password) else ""
                    notes = str(notes).strip() if pd.notna(notes) else ""
                    network_type = str(network_type).strip() if pd.notna(network_type) else ""

                    if not website_name and not account:
                        skipped_count += 1
                        continue

                    record_data = {
                        "网站名称": website_name,
                        "网址": website_url,
                        "账号": account,
                        "密码": password,
                        "备注": notes,
                        "网络类型": network_type
                    }

                    if self.pm.add_record(self.target_table, record_data):
                        imported_count += 1
                    else:
                        error_count += 1
                        skipped_count += 1

                except Exception as e:
                    error_count += 1
                    skipped_count += 1
                    continue

            self.progress_updated.emit(100)
            self.import_completed.emit(True,
                                       f"导入完成：成功导入 {imported_count} 条记录，跳过 {skipped_count} 条记录，错误 {error_count} 条记录")

        except Exception as e:
            self.import_completed.emit(False, f"导入过程中发生错误: {str(e)}")


class ExportDialog(QDialog):
    """数据导出选项对话框（功能6，支持勾选记录）"""

    def __init__(self, parent=None, current_table="单位表", data=None):
        super().__init__(parent)
        self.current_table = current_table
        self.data = data or {}  # {表名: [记录dict, ...]}
        self.setWindowTitle("导出数据")
        self.setFixedSize(460, 520)
        self.setWindowIcon(get_app_icon())
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        ChineseStyle.add_dialog_accent(self)
        _export_title = QLabel("导出数据")
        ChineseStyle.set_dialog_title(_export_title)
        layout.addWidget(_export_title)
        layout.addWidget(ChineseStyle.make_subtitle("选择格式、范围及要导出的记录"))

        fmt_label = QLabel("导出格式:")
        fmt_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321; font-weight: bold;")
        layout.addWidget(fmt_label)
        self.excel_rb = QRadioButton("Excel 文件 (.xlsx)")
        self.csv_rb = QRadioButton("CSV 文件 (.csv)")
        self.excel_rb.setChecked(True)
        for rb in (self.excel_rb, self.csv_rb):
            rb.setStyleSheet("font-family: 'Microsoft YaHei';")
            layout.addWidget(rb)

        scope_label = QLabel("导出范围:")
        scope_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321; font-weight: bold;")
        layout.addWidget(scope_label)
        self.current_rb = QRadioButton(f"仅当前表（{current_table}）")
        self.all_rb = QRadioButton("全部（所有工作表）")
        self.all_tables = list(self.data.keys()) or ["单位表", "个人表"]
        self.current_rb.setChecked(True)
        for rb in (self.current_rb, self.all_rb):
            rb.setStyleSheet("font-family: 'Microsoft YaHei';")
            layout.addWidget(rb)
            rb.toggled.connect(self._load_records)
        # 显式按钮组，保证格式/范围各自互斥
        self.fmt_group = QButtonGroup(self)
        self.fmt_group.addButton(self.excel_rb)
        self.fmt_group.addButton(self.csv_rb)
        self.scope_group = QButtonGroup(self)
        self.scope_group.addButton(self.current_rb)
        self.scope_group.addButton(self.all_rb)

        # 记录勾选列表
        list_tip = QLabel("选择要导出的记录（可勾选 / 全选）：")
        list_tip.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321; font-weight: bold;")
        layout.addWidget(list_tip)
        self.record_list = QListWidget()
        self.record_list.setStyleSheet(
            "font-family: 'Microsoft YaHei'; border: 1px solid #D9C7A7; "
            "border-radius: 6px; background: #FFFEF9;")
        layout.addWidget(self.record_list, 1)

        sel_layout = QHBoxLayout()
        self.select_all_btn = ChineseStyle.tool_button("全选", 70, 30)
        self.select_all_btn.clicked.connect(self._select_all)
        self.select_none_btn = ChineseStyle.tool_button("全不选", 80, 30)
        self.select_none_btn.clicked.connect(self._select_none)
        sel_layout.addStretch()
        sel_layout.addWidget(self.select_all_btn)
        sel_layout.addWidget(self.select_none_btn)
        layout.addLayout(sel_layout)

        self._load_records()

        mp_label = QLabel("主密码（导出须验证，导出内容为明文）:")
        mp_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321; font-weight: bold;")
        layout.addWidget(mp_label)
        self.mp_input = QLineEdit()
        self.mp_input.setEchoMode(QLineEdit.Password)
        self.mp_input.setPlaceholderText("请输入主密码以授权导出")
        self.mp_input.setStyleSheet(
            "font-family: 'Microsoft YaHei'; padding: 6px; "
            "border: 1px solid #D9C7A7; border-radius: 6px;")
        layout.addWidget(self.mp_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = ChineseStyle.primary_button("确定", 100, 34)
        ok_btn.clicked.connect(self.accept)
        cancel_btn = ChineseStyle.secondary_button("取消", 100, 34)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_records(self):
        """根据范围把记录加载到列表（每项带勾选框，默认全选）"""
        self.record_list.clear()
        tables = [self.current_table] if self.scope_group.checkedButton() is self.current_rb else self.all_tables
        multi = len(tables) > 1
        for t in tables:
            for rec in self.data.get(t, []):
                name = rec.get("网站名称", "")
                account = rec.get("账号", "")
                tag = f"[{t}] " if multi else ""
                item = QListWidgetItem(f"{tag}{name}  |  {account}")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                item.setData(Qt.UserRole, {"table": t, "record": rec})
                self.record_list.addItem(item)

    def _select_all(self):
        for i in range(self.record_list.count()):
            self.record_list.item(i).setCheckState(Qt.Checked)

    def _select_none(self):
        for i in range(self.record_list.count()):
            self.record_list.item(i).setCheckState(Qt.Unchecked)

    def get_selected(self):
        """返回勾选记录列表：[{'table':.., 'record':..}, ...]"""
        result = []
        for i in range(self.record_list.count()):
            item = self.record_list.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.data(Qt.UserRole))
        return result

    def get_choice(self):
        return "excel" if self.excel_rb.isChecked() else "csv"

    def get_scope(self):
        return "current" if self.current_rb.isChecked() else "all"

    def get_master_password(self):
        return self.mp_input.text().strip()


class NetworkTypeManagerDialog(QDialog):
    """网络类型管理：查看各类型记录数，新增/删除类型（所有类型均可删，
    删除后使用该类型的记录自动回落到「内网」或列表第一个类型）。"""

    def __init__(self, parent=None, password_manager=None):
        super().__init__(parent)
        self.pm = password_manager
        self.types_changed = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("网络类型管理")
        self.setFixedSize(380, 430)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 统一视觉：顶部色条 + 标题区 + 副标题 + 提示条
        ChineseStyle.add_dialog_accent(self, ChineseStyle.ACCENT_BROWN)
        title_label = QLabel("网络类型管理")
        ChineseStyle.set_dialog_title(title_label)
        layout.addWidget(title_label)
        layout.addWidget(ChineseStyle.make_subtitle("管理类型及其记录归属"))
        layout.addWidget(ChineseStyle.make_hint_bar("名称含「内网」的类型不参与网站核实"))

        self.type_list = QListWidget()
        self.type_list.setStyleSheet(ChineseStyle.card_list_stylesheet())
        self.type_list.setItemDelegate(CardItemDelegate(ChineseStyle.ACCENT_BROWN, self.type_list))
        self.type_list.setMinimumHeight(200)
        layout.addWidget(self.type_list)

        btn_row = QHBoxLayout()
        add_btn = ChineseStyle.primary_button("新增类型", 100, 34)
        del_btn = ChineseStyle.danger_button("删除选中", 100, 34)
        close_btn = ChineseStyle.secondary_button("关闭", 80, 34)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        add_btn.clicked.connect(self.add_type)
        del_btn.clicked.connect(self.delete_type)
        close_btn.clicked.connect(self.accept)

        self.reload_list()

    def reload_list(self):
        """按当前字典刷新列表，并统计每种类型的记录数"""
        self.type_list.clear()
        counts = {}
        if self.pm and self.pm.current_user_id:
            for recs in self.pm.current_data["tables"].values():
                for r in recs:
                    t = r.get("网络类型", "") or "（未设置）"
                    counts[t] = counts.get(t, 0) + 1
        # 显示交给 CardItemDelegate：彩色圆点 + 类型名 + 计数胶囊；UserRole 存完整配置
        dot_colors = {"互联网": "#3B6D11", "内网": "#888780",
                      "政务外网": "#BA7517", "家用网络": "#A64D37", "家用内网": "#A64D37"}
        for t in load_network_types():
            n = counts.get(t, 0)
            cfg = {"dot": dot_colors.get(t, "#A64D37"),
                   "text": t, "count": f"{n} 条", "name": t}
            item = QListWidgetItem(t)
            item.setData(Qt.UserRole, cfg)
            item.setToolTip(f"{t}：{n} 条记录")
            self.type_list.addItem(item)

    def add_type(self):
        name, ok = QInputDialog.getText(self, "新增类型", "请输入网络类型名称：")
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "输入错误", "类型名称不能为空")
            return
        if len(name) > 12:
            QMessageBox.warning(self, "输入错误", "类型名称请控制在 12 字以内")
            return
        types = load_network_types()
        if name in types:
            QMessageBox.warning(self, "已存在", f"类型「{name}」已经在列表中")
            return
        types.append(name)
        save_network_types(types)
        self.types_changed = True
        self.reload_list()

    def delete_type(self):
        item = self.type_list.currentItem()
        if item is None:
            QMessageBox.warning(self, "未选择", "请先在列表中选中要删除的类型")
            return
        cfg = item.data(Qt.UserRole) or {}
        name = (cfg.get("name") or item.text()).strip()
        types = load_network_types()
        if name not in types:
            self.reload_list()
            return
        affected = 0
        if self.pm and self.pm.current_user_id:
            for recs in self.pm.current_data["tables"].values():
                affected += sum(1 for r in recs if r.get("网络类型") == name)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除类型「{name}」吗？\n\n"
            + (f"当前有 {affected} 条记录使用该类型，删除后将自动回落为"
               f"「{fallback_network_type([t for t in types if t != name]) or '（空）'}」。" if affected else "没有记录使用该类型。"))
        if reply != QMessageBox.Yes:
            return
        new_types = [t for t in types if t != name]
        save_network_types(new_types)
        if affected:
            self.pm.reassign_network_type(name, fallback_network_type(new_types))
        self.types_changed = True
        self.reload_list()


class IdleSettingsDialog(QDialog):
    """空闲自动锁定时间设置（功能3 可配置，从欢迎菜单进入）"""

    def __init__(self, parent=None, current_minutes=DEFAULT_IDLE_MINUTES):
        super().__init__(parent)
        self.setWindowTitle("空闲自动锁定设置")
        self.setFixedSize(360, 180)
        self.setWindowIcon(get_app_icon())
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        ChineseStyle.add_dialog_accent(self)
        _idle_title = QLabel("空闲自动锁定设置")
        ChineseStyle.set_dialog_title(_idle_title)
        layout.addWidget(_idle_title)
        layout.addWidget(ChineseStyle.make_hint_bar("无操作达到设定时间后自动锁定，需重新输入主密码解锁"))

        row = QHBoxLayout()
        row.addStretch()
        self.spin = QSpinBox()
        self.spin.setRange(1, 120)
        self.spin.setValue(current_minutes)
        self.spin.setSuffix(" 分钟")
        self.spin.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 16px;")
        row.addWidget(self.spin)
        row.addStretch()
        layout.addLayout(row)

        layout.addStretch()
        btn = QHBoxLayout()
        btn.addStretch()
        ok = ChineseStyle.primary_button("确定", 100, 34)
        ok.clicked.connect(self.accept)
        cancel = ChineseStyle.secondary_button("取消", 100, 34)
        cancel.clicked.connect(self.reject)
        btn.addWidget(ok)
        btn.addWidget(cancel)
        layout.addLayout(btn)

    def get_minutes(self):
        return self.spin.value()


class ShareDialog(QDialog):
    """分享记录对话框"""

    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self.record = record or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("分享账号信息")
        self.setFixedSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        ChineseStyle.add_dialog_accent(self)

        # 标题
        title_label = QLabel("分享账号信息")
        ChineseStyle.set_dialog_title(title_label)
        layout.addWidget(title_label)
        layout.addWidget(ChineseStyle.make_subtitle("当前记录的信息摘要"))

        # 分享格式说明
        layout.addWidget(ChineseStyle.make_hint_bar("已按标准格式生成，可直接复制使用"))

        # 分享内容文本框
        self.share_text = QTextEdit()
        self.share_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D9C7A7;
                border-radius: 8px;
                padding: 10px;
                font-family: "Microsoft YaHei";
                font-size: 14px;
                background-color: #FFFEF9;
                selection-background-color: #E8D0B0;
            }
        """)
        self.share_text.setReadOnly(True)
        layout.addWidget(self.share_text)

        # 生成分享内容
        self.generate_share_content()

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        copy_btn = ChineseStyle.primary_button("复制内容", 100, 34)
        copy_btn.clicked.connect(self.copy_to_clipboard)

        close_btn = ChineseStyle.secondary_button("关闭", 100, 34)
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(copy_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def generate_share_content(self):
        """生成分享内容"""
        website_name = self.record.get("网站名称", "未知网站")
        website_url = self.record.get("网址", "")
        account = self.record.get("账号", "")
        password = self.record.get("密码", "")
        description = self.record.get("备注", "")

        # 创建一个列表，用于存储非空的字段信息
        fields = []

        # 检查每个字段是否为空，非空则添加到列表中
        if website_name and website_name != "未知网站":
            fields.append(f"网站名称：{website_name}")

        if website_url:
            fields.append(f"网址：{website_url}")

        if account:
            fields.append(f"账号：{account}")

        if password:
            fields.append(f"密码：{password}")

        if description:
            fields.append(f"备注：{description}")

        # 将列表中的字段用换行符连接起来
        share_content = "\n".join(fields)

        self.share_text.setPlainText(share_content)

    def copy_to_clipboard(self):
        """复制内容到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.share_text.toPlainText())

        # 显示复制成功提示
        QMessageBox.information(self, "复制成功", "分享内容已复制到剪贴板！")
