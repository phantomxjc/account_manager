# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 主窗口
含表格展示、搜索、右键菜单、备份、改密、注销等全部交互
"""

import webbrowser
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QGroupBox, QHeaderView,
                             QMenu, QAction, QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

import config
from ui.style import (create_gradient_button, STYLE_GROUP_BOX,
                        STYLE_COMBO_BOX, STYLE_LINE_EDIT, STYLE_TABLE_WIDGET)
from ui.record_dialog import RecordDialog
from ui.share_dialog import ShareDialog
from ui.change_password_dialog import ChangePasswordDialog
from ui.excel_import_dialog import ExcelImportDialog
from ui.security_dialog import SecurityDialog
from system.tray_icon import TrayIconManager
from core.password_manager import PasswordManager


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, password_manager: PasswordManager,
                 login_window, app_controller):
        super().__init__()
        self.pm = password_manager
        self.login_window = login_window
        self.app_controller = app_controller
        self.tray = None

        self.current_table = "单位表"
        self.current_records = []

        self._init_ui()
        self._init_tray()

    # ==================== UI 初始化 ====================

    def _init_ui(self):
        self.setWindowTitle(f"墨香 - {self.pm.current_user}")
        self.setGeometry(100, 100, 1200, 800)
        from ui.style import get_icon
        self.setWindowIcon(get_icon())

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ===== 标题栏 =====
        title_row = QHBoxLayout()

        title_lbl = QLabel("墨香")
        title_lbl.setStyleSheet("""
            QLabel {
                font-size: 24px; font-weight: bold; color: #654321;
                font-family: "Microsoft YaHei"; padding: 5px;
            }
        """)
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self.user_label = QLabel(f"欢迎，{self.pm.current_user}")
        self.user_label.setStyleSheet("""
            QLabel {
                font-family: 'Microsoft YaHei'; color: #8C7853;
                padding: 5px; border: 1px solid transparent; border-radius: 5px;
            }
            QLabel:hover { background-color: rgba(217,199,167,0.2); border: 1px solid #D9C7A7; }
        """)
        self.user_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.user_label.customContextMenuRequested.connect(self._show_account_menu)
        title_row.addWidget(self.user_label)

        main_layout.addLayout(title_row)

        # ===== 控制面板 =====
        ctrl_frame = QGroupBox("控制面板")
        ctrl_frame.setStyleSheet(STYLE_GROUP_BOX)
        ctrl_layout = QVBoxLayout(ctrl_frame)

        # 第一行按钮
        row1 = QHBoxLayout()

        tbl_lbl = QLabel("数据表:")
        tbl_lbl.setStyleSheet("font-family: 'Microsoft YaHei';")
        row1.addWidget(tbl_lbl)

        self.table_combo = QComboBox()
        self.table_combo.addItems(["单位表", "个人表"])
        self.table_combo.setCurrentText(self.current_table)
        self.table_combo.currentTextChanged.connect(self._on_table_changed)
        self.table_combo.setStyleSheet(STYLE_COMBO_BOX)
        row1.addWidget(self.table_combo)
        row1.addSpacing(20)

        self.btn_add = create_gradient_button("新增记录", 100, 30)
        self.btn_add.clicked.connect(self._add_record)
        row1.addWidget(self.btn_add)

        self.btn_edit = create_gradient_button("编辑记录", 100, 30)
        self.btn_edit.clicked.connect(self._edit_record)
        row1.addWidget(self.btn_edit)

        self.btn_del = create_gradient_button("删除记录", 100, 30)
        self.btn_del.clicked.connect(self._delete_record)
        row1.addWidget(self.btn_del)

        self.btn_view = create_gradient_button("查看密码", 100, 30)
        self.btn_view.clicked.connect(self._view_password)
        row1.addWidget(self.btn_view)

        self.btn_refresh = create_gradient_button("刷新数据", 100, 30)
        self.btn_refresh.clicked.connect(self._refresh)
        row1.addWidget(self.btn_refresh)

        self.btn_import = create_gradient_button("Excel导入", 100, 30)
        self.btn_import.clicked.connect(self._excel_import)
        row1.addWidget(self.btn_import)

        self.btn_share = create_gradient_button("分享记录", 100, 30)
        self.btn_share.clicked.connect(self._share_record)
        row1.addWidget(self.btn_share)

        row1.addStretch()
        ctrl_layout.addLayout(row1)

        # 第二行搜索
        row2 = QHBoxLayout()

        search_lbl = QLabel("搜   索:")
        search_lbl.setStyleSheet("font-family: 'Microsoft YaHei';")
        row2.addWidget(search_lbl)

        self.search_field = QComboBox()
        self.search_field.addItems(config.SEARCH_FIELDS)
        self.search_field.setStyleSheet(STYLE_COMBO_BOX)
        row2.addWidget(self.search_field)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键词...")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setStyleSheet(STYLE_LINE_EDIT)
        row2.addWidget(self.search_input)

        self.btn_clear = create_gradient_button("清空搜索", 80, 30, "#8C7853", "#A8967A")
        self.btn_clear.clicked.connect(self._clear_search)
        row2.addWidget(self.btn_clear)

        row2.addStretch()
        ctrl_layout.addLayout(row2)

        main_layout.addWidget(ctrl_frame)

        # ===== 数据表格 =====
        table_frame = QGroupBox("数据记录")
        table_frame.setStyleSheet(STYLE_GROUP_BOX)
        table_layout = QVBoxLayout(table_frame)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(6)
        self.table_widget.setHorizontalHeaderLabels(config.TABLE_COLUMNS)
        self.table_widget.setStyleSheet(STYLE_TABLE_WIDGET)

        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)

        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.itemDoubleClicked.connect(self._on_double_click)

        table_layout.addWidget(self.table_widget)
        main_layout.addWidget(table_frame)

        # ===== 状态栏 =====
        status_row = QHBoxLayout()
        self.status_lbl = QLabel("就绪")
        self.status_lbl.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853;")
        status_row.addWidget(self.status_lbl)

        status_row.addStretch()

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853;")
        status_row.addWidget(self.count_lbl)

        main_layout.addLayout(status_row)

        # 初始加载
        self._refresh()
        self._update_status("系统就绪")

    def _init_tray(self):
        self.tray = TrayIconManager(self)

    # ==================== 右键菜单 ====================

    def _show_account_menu(self, pos):
        menu = QMenu(self)

        act_backup = QAction("📊 手动备份", self)
        act_pwd = QAction("🔑 修改密码", self)
        act_logout = QAction("🚪 注销账号", self)

        menu.addAction(act_backup)
        menu.addAction(act_pwd)
        menu.addSeparator()
        menu.addAction(act_logout)

        act_backup.triggered.connect(self._manual_backup)
        act_pwd.triggered.connect(self._change_password)
        act_logout.triggered.connect(self._logout)

        menu.exec_(self.user_label.mapToGlobal(pos))

    # ==================== 表格操作 ====================

    def _on_table_changed(self, name: str):
        self.current_table = name
        self._refresh()
        self._update_status(f"已切换到 {name}")

    def _on_search(self):
        term = self.search_input.text()
        field = self.search_field.currentText()
        if not term:
            self._refresh()
            return
        self.current_records = self.pm.search_records(self.current_table, term, field)
        self._update_table()
        self._update_status(f"搜索完成，找到 {len(self.current_records)} 条记录")

    def _clear_search(self):
        self.search_input.clear()
        self._refresh()

    def _refresh(self):
        self.current_records = self.pm.current_data["tables"][self.current_table]
        self._update_table()
        self._update_status("数据已刷新")

    def _update_table(self):
        self.table_widget.setRowCount(0)
        for rec in self.current_records:
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)

            display_pwd = "•" * 8 if rec.get("密码") else ""

            self.table_widget.setItem(row, 0, QTableWidgetItem(str(rec.get("id", ""))))
            self.table_widget.setItem(row, 1, QTableWidgetItem(rec.get("网站名称", "")))

            url_item = QTableWidgetItem(rec.get("网址", ""))
            url_item.setForeground(QColor(166, 77, 55))
            url_item.setToolTip("双击打开此网址")
            self.table_widget.setItem(row, 2, url_item)

            self.table_widget.setItem(row, 3, QTableWidgetItem(rec.get("账号", "")))
            self.table_widget.setItem(row, 4, QTableWidgetItem(display_pwd))
            self.table_widget.setItem(row, 5, QTableWidgetItem(rec.get("备注", "")))

        total = (
            len(self.pm.current_data["tables"]["单位表"]) +
            len(self.pm.current_data["tables"]["个人表"])
        )
        self.count_lbl.setText(f"总记录数: {total}")

    # ==================== 双击行为 ====================

    def _on_double_click(self, item):
        row = item.row()
        col = item.column()

        if col == 2:
            url = self.table_widget.item(row, 2).text()
            self._open_url(url)
        elif col == 4:
            self._view_password()
        else:
            self._edit_record()

    def _open_url(self, url: str):
        if not url:
            QMessageBox.warning(self, "网址为空", "该记录的网址为空，无法打开。")
            return
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        try:
            webbrowser.open(url)
            self._update_status(f"正在打开: {url}")
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"无法打开网址: {e}")

    # ==================== CRUD 操作 ====================

    def _add_record(self):
        dlg = RecordDialog(self, "新增记录", main_window=self)
        if dlg.exec_() == dlg.Accepted and dlg.result_data:
            if self.pm.add_record(self.current_table, dlg.result_data):
                self._refresh()
                QMessageBox.information(self, "成功", "记录添加成功")
                self._update_status("记录添加成功")
            else:
                QMessageBox.critical(self, "错误", "添加记录失败")

    def _edit_record(self):
        sel = self.table_widget.selectedItems()
        if not sel:
            QMessageBox.warning(self, "警告", "请选择要编辑的记录")
            return

        row = self.table_widget.currentRow()
        rec_id = int(self.table_widget.item(row, 0).text())

        original = self._find_record(rec_id)
        if not original:
            QMessageBox.critical(self, "错误", "未找到记录")
            return

        # 验证主密码
        dlg = SecurityDialog(self, "安全验证", "编辑记录需要验证您的主密码")
        if dlg.exec_() != dlg.Accepted:
            return
        if not self.pm.verify_master_password(dlg.get_password()):
            QMessageBox.warning(self, "验证失败", "主密码错误")
            return

        edit_dlg = RecordDialog(self, "编辑记录", original, main_window=self)
        if edit_dlg.exec_() == edit_dlg.Accepted and edit_dlg.result_data:
            if self.pm.update_record(self.current_table, rec_id, edit_dlg.result_data):
                self._refresh()
                QMessageBox.information(self, "成功", "记录更新成功")
                self._update_status("记录更新成功")

    def _view_password(self):
        sel = self.table_widget.selectedItems()
        if not sel:
            QMessageBox.warning(self, "警告", "请选择要查看密码的记录")
            return

        row = self.table_widget.currentRow()
        rec_id = int(self.table_widget.item(row, 0).text())
        original = self._find_record(rec_id)
        if not original:
            return

        dlg = SecurityDialog(self, "安全验证", "查看密码需要验证您的主密码")
        if dlg.exec_() != dlg.Accepted:
            return
        if not self.pm.verify_master_password(dlg.get_password()):
            QMessageBox.warning(self, "验证失败", "主密码错误")
            return

        site = original.get("网站名称", "")
        user = original.get("账号", "")
        pwd = original.get("密码", "")

        msg = QMessageBox(self)
        msg.setWindowTitle("密码详情")
        msg.setText(f"""
        <div style="font-family: 'Microsoft YaHei'; color: #654321;">
            <h3>密码详情</h3>
            <p><b>网站名称:</b> {site}</p>
            <p><b>账号:</b> {user}</p>
            <p><b>密码:</b> <span style="color: #A64D37; font-weight: bold;">{pwd}</span></p>
        </div>
        """)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def _delete_record(self):
        sel = self.table_widget.selectedItems()
        if not sel:
            QMessageBox.warning(self, "警告", "请选择要删除的记录")
            return

        row = self.table_widget.currentRow()
        rec_id = int(self.table_widget.item(row, 0).text())

        reply = QMessageBox.question(
            self, "确认删除", "确定要删除选中的记录吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.pm.delete_record(self.current_table, rec_id):
                self._refresh()
                QMessageBox.information(self, "成功", "记录删除成功")
                self._update_status("记录删除成功")

    # ==================== 分享 ====================

    def _share_record(self):
        sel = self.table_widget.selectedItems()
        if not sel:
            QMessageBox.warning(self, "警告", "请选择要分享的记录")
            return

        row = self.table_widget.currentRow()
        rec_id = int(self.table_widget.item(row, 0).text())
        original = self._find_record(rec_id)
        if not original:
            return

        dlg = SecurityDialog(self, "安全验证", "分享记录需要验证您的主密码")
        if dlg.exec_() != dlg.Accepted:
            return
        if not self.pm.verify_master_password(dlg.get_password()):
            QMessageBox.warning(self, "验证失败", "主密码错误")
            return

        share_dlg = ShareDialog(self, original)
        share_dlg.exec_()

    # ==================== 备份 / 改密 / 注销 ====================

    def _manual_backup(self):
        ok, msg = self.pm.backup_data("manual")
        if ok:
            QMessageBox.information(self, "备份成功", msg)
            self._update_status("数据备份完成")
        else:
            QMessageBox.critical(self, "备份失败", msg)

    def _change_password(self):
        dlg = ChangePasswordDialog(self, self.pm)
        if dlg.exec_() == dlg.Accepted:
            self._update_status("密码修改成功")
            reply = QMessageBox.question(
                self, "修改成功",
                "密码修改成功，建议重新登录以确保安全。\n是否立即重新登录？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._logout()

    def _logout(self):
        reply = QMessageBox.question(
            self, "确认注销", "确定要注销当前账号吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.pm.logout()
            self.hide()
            self.login_window.show_login()

    # ==================== Excel 导入 ====================

    def _excel_import(self):
        dlg = ExcelImportDialog(self, self.pm)
        dlg.import_completed.connect(self._on_import_done)
        dlg.exec_()

    def _on_import_done(self, success: bool, msg: str):
        if success:
            self._refresh()
        self._update_status(msg)

    # ==================== 关闭事件 ====================

    def closeEvent(self, event):
        if not self.app_controller.is_hidden_to_tray:
            reply = QMessageBox.question(
                self, "确认退出",
                "您确定要退出程序吗？\n\n选择'是'将退出程序，选择'否'将最小化到系统托盘。",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
                self.app_controller.quit_application()
            elif reply == QMessageBox.No:
                event.ignore()
                self.app_controller.hide_to_tray()
            else:
                event.ignore()
        else:
            event.accept()

    # ==================== 辅助方法 ====================

    def _find_record(self, rec_id: int) -> dict:
        for rec in self.pm.current_data["tables"][self.current_table]:
            if rec["id"] == rec_id:
                return rec
        return None

    def _update_status(self, msg: str):
        self.status_lbl.setText(msg)
