# -*- coding: utf-8 -*-
"""
墨香密码管理器 - Excel 导入对话框
支持选择文件、工作表、目标表，后台线程执行导入
"""

import os
import pandas as pd
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QComboBox, QRadioButton,
                             QButtonGroup, QGroupBox, QProgressBar, QFileDialog,
                             QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal

from ui.style import (create_gradient_button, STYLE_LINE_EDIT,
                        STYLE_COMBO_BOX, STYLE_GROUP_BOX, STYLE_PROGRESS_BAR)
from core.excel_import import ExcelImportWorker
from core.password_manager import PasswordManager


class ExcelImportDialog(QDialog):
    """Excel 数据导入对话框"""

    import_completed = pyqtSignal(bool, str)

    def __init__(self, parent=None, password_manager: PasswordManager = None):
        super().__init__(parent)
        self.pm = password_manager
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("Excel 数据导入")
        self.setFixedSize(500, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 标题
        t = QLabel("Excel 数据导入")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("""
            QLabel {
                font-size: 20px; font-weight: bold; color: #654321;
                font-family: "Microsoft YaHei"; padding: 10px;
            }
        """)
        layout.addWidget(t)

        info = QLabel("请选择 Excel 文件，并指定要导入的目标数据表（单位表或个人表）")
        info.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853; font-size: 12px;")
        layout.addWidget(info)

        # ===== 文件选择 =====
        file_group = QGroupBox("选择 Excel 文件")
        file_group.setStyleSheet(STYLE_GROUP_BOX)
        file_layout = QVBoxLayout(file_group)

        path_row = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("请选择 Excel 文件...")
        self.file_path_input.setStyleSheet(STYLE_LINE_EDIT)
        browse_btn = create_gradient_button("浏览", 80, 30)
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self.file_path_input)
        path_row.addWidget(browse_btn)
        file_layout.addLayout(path_row)

        sheet_row = QHBoxLayout()
        sheet_lbl = QLabel("工作表:")
        sheet_lbl.setFixedWidth(80)
        sheet_lbl.setStyleSheet("font-family: 'Microsoft YaHei'; color: #654321;")
        self.sheet_combo = QComboBox()
        self.sheet_combo.setStyleSheet(STYLE_COMBO_BOX)
        self.sheet_combo.addItem("自动选择（第一个工作表）")
        sheet_row.addWidget(sheet_lbl)
        sheet_row.addWidget(self.sheet_combo)
        sheet_row.addStretch()
        file_layout.addLayout(sheet_row)

        layout.addWidget(file_group)

        # ===== 目标表选择 =====
        target_group = QGroupBox("选择目标数据表")
        target_group.setStyleSheet(STYLE_GROUP_BOX)
        target_layout = QVBoxLayout(target_group)

        self.target_group = QButtonGroup()
        self.unit_radio = QRadioButton("单位表")
        self.unit_radio.setChecked(True)
        self.personal_radio = QRadioButton("个人表")
        self.target_group.addButton(self.unit_radio)
        self.target_group.addButton(self.personal_radio)
        target_layout.addWidget(self.unit_radio)
        target_layout.addWidget(self.personal_radio)
        layout.addWidget(target_group)

        # ===== 说明 =====
        opt_group = QGroupBox("导入说明")
        opt_group.setStyleSheet(STYLE_GROUP_BOX)
        opt_layout = QVBoxLayout(opt_group)
        mapping_lbl = QLabel("""
        • 系统自动匹配常见列名：网站名称、网址、账号、密码、备注等
        • 必填字段：网站名称或账号至少填写一项
        • 支持 .xlsx 和 .xls 格式
        """)
        mapping_lbl.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853; font-size: 11px;")
        mapping_lbl.setWordWrap(True)
        opt_layout.addWidget(mapping_lbl)
        layout.addWidget(opt_group)

        # ===== 进度条 =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(STYLE_PROGRESS_BAR)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # ===== 按钮 =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.import_btn = create_gradient_button("开始导入", 100, 35)
        self.import_btn.clicked.connect(self._start_import)

        self.cancel_btn = create_gradient_button("取消", 100, 35, "#8C7853", "#A8967A")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    # ==================== 逻辑 ====================

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
        )
        if path:
            self.file_path_input.setText(path)
            self._load_sheets(path)

    def _load_sheets(self, path: str):
        try:
            xls = pd.ExcelFile(path)
            self.sheet_combo.clear()
            self.sheet_combo.addItem("自动选择（第一个工作表）")
            for s in xls.sheet_names:
                self.sheet_combo.addItem(s)
        except Exception as e:
            QMessageBox.warning(self, "文件错误", f"无法读取 Excel 文件: {e}")

    def _start_import(self):
        path = self.file_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "选择文件", "请先选择 Excel 文件")
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "文件不存在", "所选的 Excel 文件不存在")
            return
        if not (path.lower().endswith('.xlsx') or path.lower().endswith('.xls')):
            QMessageBox.warning(self, "格式错误", "请选择 .xlsx 或 .xls 格式")
            return

        target = "单位表" if self.unit_radio.isChecked() else "个人表"
        sel = self.sheet_combo.currentText()
        sheet = None if sel == "自动选择（第一个工作表）" else sel

        # 验证主密码
        from ui.security_dialog import SecurityDialog
        dlg = SecurityDialog(self, "安全验证", "导入数据需要验证您的主密码")
        if dlg.exec_() != QDialog.Accepted:
            return
        if not self.pm.verify_master_password(dlg.get_password()):
            QMessageBox.warning(self, "验证失败", "主密码错误，无法导入数据")
            return

        # 启动线程
        self._set_interaction(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = ExcelImportWorker(path, target, sheet, self.pm)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.import_completed.connect(self._on_completed)
        self.worker.start()

    def _set_interaction(self, enabled: bool):
        self.file_path_input.setEnabled(enabled)
        self.sheet_combo.setEnabled(enabled)
        self.unit_radio.setEnabled(enabled)
        self.personal_radio.setEnabled(enabled)
        self.import_btn.setEnabled(enabled)
        self.cancel_btn.setEnabled(enabled)

    def _on_completed(self, success: bool, message: str):
        self._set_interaction(True)
        self.progress_bar.setVisible(False)

        if success:
            QMessageBox.information(self, "导入成功", message)
            self.import_completed.emit(True, message)
            self.accept()
        else:
            QMessageBox.critical(self, "导入失败", message)
            self.import_completed.emit(False, message)
