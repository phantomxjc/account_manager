# -*- coding: utf-8 -*-
"""主窗口：数据表浏览 / 增删改查 / 搜索 / 导入导出 / 空闲自动锁定。"""
import os
import time
import webbrowser
import zipfile
import io
import pandas as pd

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QGroupBox, QComboBox, QMessageBox,
                             QMenu, QAction, QFileDialog, QApplication, QSystemTrayIcon,
                             QDialog, QHeaderView, QListWidget, QListWidgetItem,
                             QAbstractItemView)
from PyQt5.QtCore import Qt, QEvent, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor

from ..config import (BASE_DIR, DEFAULT_IDLE_MINUTES, load_config, save_config,
                      load_network_types, load_toolbar_order, save_toolbar_order,
                      DEFAULT_TOOLBAR_ORDER)
from ..style import ChineseStyle
from ..icon import get_app_icon
from ..netcheck import verify_website, detect_network_type
from ..ui.dialogs import (SecurityDialog, ChangePasswordDialog, RecordDialog,
                          ExcelImportDialog, ShareDialog, ExportDialog,
                          IdleSettingsDialog, NetworkTypeManagerDialog, CardItemDelegate)


# 功能栏按钮元数据：key -> (显示名, 点击槽函数名, 渐变色1, 渐变色2)
# 顺序由 config.DEFAULT_TOOLBAR_ORDER / mx_config.json 决定，与此表顺序无关
TOOLBAR_ACTIONS = {
    "add":           ("新增记录",  "add_record",           "#A64D37", "#C46C4E"),
    "edit":          ("编辑记录",  "edit_record",          "#A64D37", "#C46C4E"),
    "delete":        ("删除记录",  "delete_record",        "#A64D37", "#C46C4E"),
    "view_password": ("查看密码",  "view_password",        "#A64D37", "#C46C4E"),
    "refresh":       ("刷新数据",  "refresh_table",        "#A64D37", "#C46C4E"),
    "import":        ("Excel导入", "excel_import",         "#A64D37", "#C46C4E"),
    "share":         ("分享记录",  "share_record",         "#A64D37", "#C46C4E"),
    "export":        ("导出数据",  "export_data",          "#8C7853", "#A8967A"),
    "move":          ("迁移记录",  "move_record_ui",       "#A64D37", "#C0603F"),
    "verify":        ("核实网站",  "verify_website",       "#A64D37", "#C0603F"),
    "verify_all":    ("全部核实",  "verify_all_websites",  "#A64D37", "#C0603F"),
}


class ToolbarOrderDialog(QDialog):
    """功能栏排序对话框：上移/下移调整顺序，支持恢复默认。"""
    def __init__(self, current_order, parent=None):
        super().__init__(parent)
        self.setWindowTitle("功能栏排序")
        self.setMinimumWidth(340)
        self.setStyleSheet("QDialog { background: #FBF7F0; font-family: 'Microsoft YaHei'; }")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        # 统一视觉：顶部色条 + 标题区 + 副标题 + 提示条
        ChineseStyle.add_dialog_accent(self, ChineseStyle.ACCENT)
        title_label = QLabel("功能栏排序")
        ChineseStyle.set_dialog_title(title_label)
        layout.addWidget(title_label)
        layout.addWidget(ChineseStyle.make_subtitle("调整按钮在工具栏中的显示顺序"))
        layout.addWidget(ChineseStyle.make_hint_bar("选中后点上移 / 下移调整，确定后立即生效"))

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(ChineseStyle.card_list_stylesheet())
        self.list_widget.setItemDelegate(CardItemDelegate(ChineseStyle.ACCENT, self.list_widget))
        self._fill_list(current_order)
        self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        up_btn = ChineseStyle.secondary_button("↑ 上移", 80, 34)
        down_btn = ChineseStyle.secondary_button("↓ 下移", 80, 34)
        reset_btn = ChineseStyle.secondary_button("恢复默认", 100, 34)
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        btn_row.addStretch()
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

        ok_row = QHBoxLayout()
        ok_btn = ChineseStyle.primary_button("确定", 90, 34)
        cancel_btn = ChineseStyle.secondary_button("取消", 90, 34)
        ok_row.addStretch()
        ok_row.addWidget(cancel_btn)
        ok_row.addWidget(ok_btn)
        layout.addLayout(ok_row)

        up_btn.clicked.connect(self._move_up)
        down_btn.clicked.connect(self._move_down)
        reset_btn.clicked.connect(self._reset_default)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def _fill_list(self, order):
        """按 order 填充列表：UserRole 存 key，delegate 用 cfg 画序号徽章"""
        self.list_widget.clear()
        for idx, key in enumerate(order, 1):
            label = TOOLBAR_ACTIONS[key][0]
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {"key": key, "badge": idx, "text": label})
            self.list_widget.addItem(item)

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)

    def _reset_default(self):
        self._fill_list(DEFAULT_TOOLBAR_ORDER)
        self.list_widget.setCurrentRow(0)

    def get_order(self):
        """返回当前列表顺序对应的 key 列表"""
        order = []
        for i in range(self.list_widget.count()):
            data = self.list_widget.item(i).data(Qt.UserRole)
            if isinstance(data, dict):
                order.append(data["key"])
            else:  # 兼容旧格式
                order.append(data)
        return order


class VerifyWebsiteThread(QThread):
    """后台核实网站有效性（基于 netcheck.verify_website）"""
    verify_done = pyqtSignal(bool, str, str, str)   # (可达与否, 网站名称, 结果描述, 状态短语)

    def __init__(self, url, site_name, parent=None):
        super().__init__(parent)
        self.url = url
        self.site_name = site_name

    def run(self):
        ok, detail, cost = verify_website(self.url, timeout=5)
        # 状态栏保留详细原因供诊断；持久化的 status 只取两态
        status_text = f"可访问 ({detail} · {cost}ms)" if ok else f"不可访问 · {detail} ({cost}ms)"
        short_status = "可访问" if ok else "不可访问"
        self.verify_done.emit(ok, self.site_name, status_text, short_status)


class BatchVerifyThread(QThread):
    """批量核实所有工作表网站：逐条信号回报进度，含「内网/家用」的类型跳过"""
    one_done = pyqtSignal(str, int, bool, str, str)   # (表名, 记录id, 可达, 状态短语, 状态短语2)
    progress = pyqtSignal(int, int, int, int, int)    # (当前序号, 总数, 可访问数, 失败数, 跳过数)
    batch_done = pyqtSignal(int, int, int, int)       # (总数, 可访问, 失败, 跳过)

    def __init__(self, password_manager, parent=None):
        super().__init__(parent)
        self.pm = password_manager
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        table_map = self.pm.get_table_map()
        # 收集所有要核实的记录（跳过内网/家用与空网址）
        jobs = []
        skipped = 0
        for logical, physical in table_map.items():
            for rec in self.pm.current_data["tables"].get(logical, []):
                ntype = (rec.get("网络类型") or "").strip()
                url = (rec.get("网址") or "").strip()
                if "内网" in ntype or "家用" in ntype or not url:
                    skipped += 1
                    continue
                jobs.append((logical, rec["id"], rec.get("网站名称") or url, url))

        ok_cnt = fail_cnt = 0
        total = len(jobs)
        for idx, (logical, rid, name, url) in enumerate(jobs, 1):
            if self._stop:
                break
            ok, detail, cost = verify_website(url, timeout=5)
            if ok:
                ok_cnt += 1
            else:
                fail_cnt += 1
            # 持久化只用两态；phrase 供状态栏/汇总显示详细原因
            status = "可访问" if ok else "不可访问"
            phrase = f"可访问 ({detail} · {cost}ms)" if ok else f"不可访问 · {detail} ({cost}ms)"
            self.one_done.emit(logical, rid, ok, status, phrase)
            self.progress.emit(idx, total, ok_cnt, fail_cnt, skipped)

        self.batch_done.emit(total, ok_cnt, fail_cnt, skipped)


class MainWindow(QMainWindow):
    """主窗口 - 添加右键菜单功能"""

    def __init__(self, password_manager, login_window, app_controller):  # 修改：添加 app_controller 参数
        super().__init__()
        self.pm = password_manager
        self.login_window = login_window
        self.app_controller = app_controller  # 新增：保存应用程序控制器引用
        self.current_table = "单位表"
        self.current_records = []
        self.toolbar_buttons = {}
        self.init_ui()

    def _build_toolbar(self):
        """按配置顺序重建功能栏按钮（排序后调用）"""
        # 清空旧按钮
        while self.toolbar_layout.count():
            item = self.toolbar_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.toolbar_buttons.clear()

        for key in load_toolbar_order():
            meta = TOOLBAR_ACTIONS.get(key)
            if not meta:
                continue
            label, slot_name, c1, c2 = meta
            btn = ChineseStyle.create_gradient_button(label, 100, 30, c1, c2, radius=6)
            slot = getattr(self, slot_name, None)
            if slot:
                btn.clicked.connect(slot)
            self.toolbar_layout.addWidget(btn)
            self.toolbar_buttons[key] = btn
            # 保留原有属性名兼容其它代码引用
            setattr(self, self._toolbar_attr(key), btn)

    @staticmethod
    def _toolbar_attr(key):
        return {
            "add": "add_btn", "edit": "edit_btn", "delete": "delete_btn",
            "view_password": "view_password_btn", "refresh": "refresh_btn",
            "import": "import_btn", "share": "share_btn", "export": "export_btn",
            "move": "move_btn", "verify": "verify_btn", "verify_all": "verify_all_btn",
        }.get(key, key + "_btn")

    def open_toolbar_order(self):
        """打开功能栏排序对话框"""
        dlg = ToolbarOrderDialog(load_toolbar_order(), self)
        if dlg.exec_() == QDialog.Accepted:
            new_order = dlg.get_order()
            save_toolbar_order(new_order)
            self._build_toolbar()
            self.update_status("功能栏顺序已更新")

    def init_ui(self):
        self.setWindowTitle(f"墨香 - {self.pm.current_user}")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(get_app_icon())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 标题栏
        title_layout = QHBoxLayout()

        title_label = QLabel("墨香")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #654321;
                font-family: "Microsoft YaHei";
                padding: 5px;
            }
        """)
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 用户信息标签 - 设置为支持右键菜单
        self.user_info_label = QLabel(f"欢迎，{self.pm.current_user}")
        self.user_info_label.setStyleSheet("""
            QLabel {
                font-family: 'Microsoft YaHei'; 
                color: #8C7853;
                padding: 5px;
                border: 1px solid transparent;
                border-radius: 5px;
            }
            QLabel:hover {
                background-color: rgba(217, 199, 167, 0.2);
                border: 1px solid #D9C7A7;
            }
        """)
        self.user_info_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.user_info_label.customContextMenuRequested.connect(self.show_account_menu)
        title_layout.addWidget(self.user_info_label)

        main_layout.addLayout(title_layout)

        # 控制面板
        control_frame = QGroupBox("控制面板")
        control_frame.setStyleSheet("""
            QGroupBox {
                border: 1px solid #D9C7A7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-family: "Microsoft YaHei";
                color: #654321;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        control_layout = QVBoxLayout(control_frame)

        # 第一行：功能栏按钮独占（数据驱动，顺序由配置决定，右键「欢迎」菜单可排序）
        control_row1 = QHBoxLayout()
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar_layout.setSpacing(7)          # 按钮之间留缝，不再连成色带
        control_row1.addLayout(self.toolbar_layout)
        self._build_toolbar()
        control_row1.addStretch()
        control_layout.addLayout(control_row1)

        # 第二行：数据表选择 + 搜索功能
        control_row2 = QHBoxLayout()

        table_label = QLabel("数据表:")
        table_label.setStyleSheet("font-family: 'Microsoft YaHei';")
        control_row2.addWidget(table_label)

        self.table_combo = QComboBox()
        self.table_combo.addItems(self.pm.get_table_names())
        self.table_combo.setCurrentText(self.current_table)
        self.table_combo.currentTextChanged.connect(self.on_table_changed)
        self.table_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
                min-width: 100px;
            }
        """)
        control_row2.addWidget(self.table_combo)

        control_row2.addSpacing(20)

        search_label = QLabel("搜   索:")
        search_label.setStyleSheet("font-family: 'Microsoft YaHei';")
        control_row2.addWidget(search_label)

        self.search_field_combo = QComboBox()
        self.search_field_combo.addItems(["所有字段", "网站名称", "网址", "账号", "网络类型", "备注"])
        self.search_field_combo.setStyleSheet(self.table_combo.styleSheet())
        control_row2.addWidget(self.search_field_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键词...")
        self.search_input.textChanged.connect(self.on_search)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                padding: 5px;
                font-family: "Microsoft YaHei";
            }
        """)
        control_row2.addWidget(self.search_input)

        self.clear_search_btn = ChineseStyle.create_gradient_button("清空搜索", 80, 30, "#8C7853", "#A8967A")
        self.clear_search_btn.clicked.connect(self.clear_search)
        control_row2.addWidget(self.clear_search_btn)

        control_row2.addStretch()
        control_layout.addLayout(control_row2)

        main_layout.addWidget(control_frame)

        # 数据表格
        table_frame = QGroupBox("数据记录")
        table_frame.setStyleSheet(control_frame.styleSheet())

        table_layout = QVBoxLayout(table_frame)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(8)
        self.table_widget.setHorizontalHeaderLabels(
            ["ID", "网站名称", "网址", "账号", "密码", "网络类型", "状态", "备注"])

        self.table_widget.setStyleSheet("""
            QTableWidget {
                border: 1px solid #D9C7A7;
                border-radius: 5px;
                background-color: #FFFEF9;
                alternate-background-color: #F8F4E9;
                font-family: "Microsoft YaHei";
                gridline-color: #D9C7A7;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #E8E0D0;
            }
            QTableWidget::item:selected {
                background-color: #E8D0B0;
                color: #654321;
            }
            QHeaderView::section {
                background-color: #D9C7A7;
                color: #654321;
                font-weight: bold;
                padding: 5px;
                border: none;
                font-family: "Microsoft YaHei";
            }
        """)

        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)       # 状态：固定窄列，只显示圆点
        self.table_widget.setColumnWidth(6, 56)
        header.setSectionResizeMode(7, QHeaderView.Stretch)

        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        table_layout.addWidget(self.table_widget)
        main_layout.addWidget(table_frame)

        # 状态栏
        status_bar = QHBoxLayout()

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853;")
        status_bar.addWidget(self.status_label)

        status_bar.addStretch()

        self.record_count_label = QLabel("")
        self.record_count_label.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853;")
        status_bar.addWidget(self.record_count_label)

        main_layout.addLayout(status_bar)

        self.refresh_table()
        self.update_status("系统就绪")

        # ===== 空闲自动锁定（功能3，空闲时长可配置）=====
        self.idle_timeout = load_config().get("idle_minutes", DEFAULT_IDLE_MINUTES) * 60
        self.last_activity = time.time()
        self.is_locked = False
        self._relocking = False
        self.installEventFilter(self)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.check_idle)
        self.idle_timer.start(1000)      # 每秒检测一次空闲

    def eventFilter(self, obj, event):
        """监听用户鼠标/键盘活动，重置空闲计时"""
        if event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress,
                            QEvent.MouseButtonRelease, QEvent.KeyPress,
                            QEvent.KeyRelease, QEvent.Wheel):
            self.last_activity = time.time()
        return super().eventFilter(obj, event)

    def check_idle(self):
        """空闲超时则自动锁定"""
        if self.is_locked:
            return
        # 有模态对话框打开时视为活动中，避免误锁
        if QApplication.activeModalWidget() is not None:
            self.last_activity = time.time()
            return
        if time.time() - self.last_activity >= self.idle_timeout:
            self.auto_lock()

    def auto_lock(self):
        """空闲自动锁定：隐藏主窗口并退回系统托盘，需双击托盘图标并重新验证主密码才能进入。
        
        设计：锁屏后不直接弹出登录框，而是隐藏到托盘静默等待；
        用户双击托盘图标时再由 app 控制器弹出登录界面（见 ApplicationController.show_main_window_from_tray）。
        """
        self.is_locked = True
        self.idle_timer.stop()
        self._relocking = True

        # 隐藏主窗口，静默退回系统托盘（关键改动：不再直接弹出登录框）
        self.hide()
        self.app_controller.is_hidden_to_tray = True

        if self.app_controller.tray_icon:
            self.app_controller.tray_icon.showMessage(
                "墨香密码管理器",
                "已因长时间无操作自动锁定\n请双击托盘图标重新解锁",
                QSystemTrayIcon.Information, 3000)
        else:
            # 无系统托盘的极端环境下，退化为直接显示登录框，保证仍可解锁
            self.login_window.show_login()

    def show_account_menu(self, pos):
        """显示账号右键菜单（含空闲锁定设置入口）"""
        menu = QMenu(self)

        backup_action = QAction("📊 手动备份", self)
        change_pwd_action = QAction("🔑 修改密码", self)
        idle_action = QAction("⏲ 空闲锁定设置", self)
        ntype_action = QAction("🏷 网络类型管理", self)
        toolbar_order_action = QAction("🔀 功能栏排序", self)
        new_table_action = QAction("🗂 新建工作表", self)
        del_table_action = QAction("🗑 删除工作表（仅自定义表）", self)
        logout_action = QAction("🚪 注销账号", self)

        menu.addAction(backup_action)
        menu.addAction(change_pwd_action)
        menu.addAction(idle_action)
        menu.addAction(ntype_action)
        menu.addSeparator()
        menu.addAction(toolbar_order_action)
        menu.addSeparator()
        menu.addAction(new_table_action)
        menu.addAction(del_table_action)
        menu.addSeparator()
        menu.addAction(logout_action)

        backup_action.triggered.connect(self.manual_backup)
        change_pwd_action.triggered.connect(self.change_password)
        idle_action.triggered.connect(self.open_idle_settings)
        ntype_action.triggered.connect(self.open_type_manager)
        toolbar_order_action.triggered.connect(self.open_toolbar_order)
        new_table_action.triggered.connect(self.create_table_ui)
        del_table_action.triggered.connect(self.delete_table_ui)
        logout_action.triggered.connect(self.logout)

        menu.exec_(self.user_info_label.mapToGlobal(pos))

    def create_table_ui(self):
        """新建自定义工作表"""
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "新建工作表", "请输入新工作表名称（不超过20个字）:", text="")
        if not ok:
            return
        ok2, msg = self.pm.create_table(name)
        if ok2:
            self.refresh_table_combo(select=name)
            self.update_status(msg)
            QMessageBox.information(self, "创建成功", msg)
        else:
            QMessageBox.warning(self, "创建失败", msg)

    def delete_table_ui(self):
        """删除自定义工作表（默认表不允许）"""
        custom_names = [t for t in self.pm.get_table_names()
                        if t not in self.pm.DEFAULT_TABLES]
        if not custom_names:
            QMessageBox.information(self, "没有可删除的表",
                                    "当前没有自定义工作表。\n默认表（单位表/个人表）不允许删除。")
            return
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(
            self, "删除工作表", "选择要删除的自定义工作表（数据将一并删除）:",
            custom_names, 0, False)
        if not ok:
            return
        confirm = QMessageBox.question(
            self, "确认删除",
            f"确定删除工作表「{name}」吗？\n其中所有记录将被永久删除！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        ok2, msg = self.pm.delete_table(name)
        if ok2:
            if self.current_table == name:
                self.current_table = "单位表"
            self.refresh_table_combo(select=self.current_table)
            self.refresh_table()
            self.update_status(msg)
        else:
            QMessageBox.warning(self, "删除失败", msg)

    def refresh_table_combo(self, select=None):
        """工作表下拉框按当前表清单重建（新建/删除表后调用）"""
        self.table_combo.blockSignals(True)
        self.table_combo.clear()
        self.table_combo.addItems(self.pm.get_table_names())
        if select:
            self.table_combo.setCurrentText(select)
        self.table_combo.blockSignals(False)

    def open_idle_settings(self):
        """打开空闲自动锁定时间设置，并持久化到配置"""
        minutes = int(self.idle_timeout // 60)
        dlg = IdleSettingsDialog(self, minutes)
        if dlg.exec_() == QDialog.Accepted:
            new_min = dlg.get_minutes()
            self.idle_timeout = new_min * 60
            cfg = load_config()
            cfg["idle_minutes"] = new_min
            save_config(cfg)
            self.update_status(f"空闲自动锁定已设为 {new_min} 分钟")
            QMessageBox.information(self, "设置已保存",
                                    f"空闲自动锁定时间已设为 {new_min} 分钟。\n下次登录生效（当前会话立即生效）。")

    def on_item_double_clicked(self, item):
        """处理表格项双击事件"""
        row = item.row()
        column = item.column()

        if column == 2:  # 网址列
            url_item = self.table_widget.item(row, 2)
            if url_item and url_item.text():
                self.open_url_in_browser(url_item.text())
        elif column == 4:  # 密码列
            self.view_password()
        elif column == 5:  # 网络类型列：下拉选择 + 确认后写入
            self.change_network_type(row)
        else:  # 其他列
            self.edit_record()

    def change_network_type(self, row):
        """在表格里直接改单条记录的网络类型：下拉选 -> 确认 -> 才写库。

        只调用 pm.update_network_type（仅 UPDATE network_type 列），
        不读取、不修改密码及其他字段。
        """
        id_item = self.table_widget.item(row, 0)
        if not id_item:
            return
        record_id = int(id_item.text())

        # 当前值
        cur_item = self.table_widget.item(row, 5)
        old_type = (cur_item.text() if cur_item else "").strip()

        # 网络类型字典（当前配置的类型列表）
        types = [t for t in load_network_types() if t]
        if old_type and old_type not in types:
            types.insert(0, old_type)
        types.append("(清空)")  # 允许清空为未设置
        if not types:
            QMessageBox.warning(self, "无可用类型", "请先在「网络类型管理」中添加类型。")
            return

        # 名称用于确认提示（不碰密码）
        name_item = self.table_widget.item(row, 1)
        site_name = name_item.text() if name_item else ""

        dialog = QDialog(self)
        dialog.setWindowTitle("修改网络类型")
        dialog.setFixedSize(280, 120)
        dialog.setWindowIcon(get_app_icon())
        lay = QVBoxLayout(dialog)
        lay.addWidget(QLabel(f"为「{site_name[:16]}」选择网络类型："))
        combo = QComboBox()
        combo.addItems(types)
        if old_type in types:
            combo.setCurrentText(old_type)
        lay.addWidget(combo)
        btn_row = QHBoxLayout()
        ok = ChineseStyle.primary_button("确定", 80, 34)
        cancel = ChineseStyle.secondary_button("取消", 80, 34)
        ok.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(ok)
        btn_row.addWidget(cancel)
        lay.addLayout(btn_row)

        if dialog.exec_() != QDialog.Accepted:
            return

        new_type = combo.currentText()
        if new_type == "(清空)":
            new_type = ""
        if new_type == old_type:
            return  # 无变化，连确认窗都不弹

        # 确认窗：是否将该条记录网络类型从 X 改为 Y
        old_show = old_type or "未设置"
        new_show = new_type or "未设置"
        reply = QMessageBox.question(
            self, "确认修改",
            f"是否将该条记录的网络类型从「{old_show}」修改为「{new_show}」？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        success, actual_old = self.pm.update_network_type(
            self.current_table, record_id, new_type)
        if success:
            self.update_table()  # 刷新以更新颜色/文字
            self.update_status(f"网络类型已修改：{old_show} → {new_show}")
        else:
            QMessageBox.warning(self, "修改失败", "网络类型更新失败，请重试。")

    def open_url_in_browser(self, url):
        """在默认浏览器中打开网址"""
        if not url:
            QMessageBox.warning(self, "网址为空", "该记录的网址为空，无法打开。")
            return

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        try:
            webbrowser.open(url)
            self.update_status(f"正在打开网址: {url}")
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"无法打开网址: {str(e)}")

    def on_table_changed(self, table_name):
        self.current_table = table_name
        self.refresh_table()
        self.update_status(f"已切换到 {self.current_table}")

    def on_search(self):
        search_term = self.search_input.text()
        search_field = self.search_field_combo.currentText()
        self.current_records = self.pm.search_records(self.current_table, search_term, search_field)
        self.update_table()
        self.update_status(f"搜索完成，找到 {len(self.current_records)} 条记录")

    def clear_search(self):
        self.search_input.clear()
        self.refresh_table()

    def refresh_table(self):
        self.current_records = self.pm.current_data["tables"][self.current_table]
        self.update_table()
        self.update_status("数据已刷新")

    def _ntype_color(self, ntype):
        """网络类型标签颜色：内网灰 / 互联网绿 / 外网与政务橙黄 / 其他棕"""
        t = ntype or ""
        if "内网" in t:
            return QColor(136, 135, 128)
        if "互联网" in t:
            return QColor(59, 109, 17)
        if "外网" in t or "政务" in t:
            return QColor(133, 79, 11)
        return QColor(101, 67, 33)

    def update_table(self):
        """更新表格显示"""
        self.table_widget.setRowCount(0)

        for record in self.current_records:
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)

            # 密码显示为星号
            display_pwd = "•" * 8 if record.get("密码") else ""

            ntype = (record.get("网络类型") or "").strip()
            ntype_item = QTableWidgetItem(ntype)
            ntype_item.setForeground(self._ntype_color(ntype))
            ntype_item.setToolTip("在新增/编辑记录中设置；右键「欢迎」菜单可管理类型")

            vstatus = (record.get("网络状态") or "").strip()
            vtime = (record.get("核实时间") or "").strip()
            # 只显示圆点，不显示文字；颜色区分状态，tooltip 保留详情
            vitem = QTableWidgetItem("●")
            if vstatus == "可访问":
                dot_color = QColor(46, 139, 87)      # 绿
                tip = f"可访问 · 核实时间: {vtime or '未核实'}"
            elif vstatus == "不可访问":
                dot_color = QColor(200, 52, 52)      # 红
                tip = f"不可访问 · 核实时间: {vtime or '未核实'}"
            else:
                dot_color = QColor(205, 200, 190)    # 浅灰（未核实）
                tip = "未核实"
            vitem.setForeground(dot_color)
            vitem.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            dot_font = vitem.font()
            dot_font.setPointSize(13)
            vitem.setFont(dot_font)
            vitem.setToolTip(tip)

            self.table_widget.setItem(row, 0, QTableWidgetItem(str(record["id"])))
            self.table_widget.setItem(row, 1, QTableWidgetItem(record.get("网站名称", "")))

            # 网址列特殊处理：添加超链接样式
            url_item = QTableWidgetItem(record.get("网址", ""))
            url_item.setForeground(QColor(166, 77, 55))  # 朱红色
            url_item.setToolTip("双击打开此网址")
            self.table_widget.setItem(row, 2, url_item)

            self.table_widget.setItem(row, 3, QTableWidgetItem(record.get("账号", "")))
            self.table_widget.setItem(row, 4, QTableWidgetItem(display_pwd))
            self.table_widget.setItem(row, 5, ntype_item)
            self.table_widget.setItem(row, 6, vitem)
            self.table_widget.setItem(row, 7, QTableWidgetItem(record.get("备注", "")))

        # 更新记录计数
        total_records = sum(len(recs) for recs in self.pm.current_data["tables"].values())
        self.record_count_label.setText(f"总记录数: {total_records}")

    def add_record(self):
        """添加新记录"""
        dialog = RecordDialog(self, "新增记录", main_window=self)
        if dialog.exec_() == QDialog.Accepted and dialog.result_data:
            try:
                if self.pm.add_record(self.current_table, dialog.result_data):
                    self.refresh_table()
                    QMessageBox.information(self, "成功", "记录添加成功")
                    self.update_status("记录添加成功")
                else:
                    QMessageBox.critical(self, "错误", "添加记录失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加记录时出错: {str(e)}")

    def edit_record(self):
        """编辑记录"""
        selected = self.table_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请选择要编辑的记录")
            return

        row = self.table_widget.currentRow()
        record_id = int(self.table_widget.item(row, 0).text())

        # 查找原始记录
        original_record = None
        for record in self.pm.current_data["tables"][self.current_table]:
            if record["id"] == record_id:
                original_record = record
                break

        if not original_record:
            QMessageBox.critical(self, "错误", "未找到记录")
            return

        # 验证主密码
        dialog = SecurityDialog(self, "安全验证", "编辑记录需要验证您的主密码")
        if dialog.exec_() == QDialog.Accepted:
            if self.pm.verify_master_password(dialog.get_password()):
                dialog = RecordDialog(self, "编辑记录", original_record, main_window=self)
                if dialog.exec_() == QDialog.Accepted and dialog.result_data:
                    if self.pm.update_record(self.current_table, record_id, dialog.result_data):
                        self.refresh_table()
                        QMessageBox.information(self, "成功", "记录更新成功")
                        self.update_status("记录更新成功")
                    else:
                        QMessageBox.critical(self, "错误", "更新记录失败")
            else:
                QMessageBox.warning(self, "验证失败", "主密码错误，无法编辑记录")

    def view_password(self):
        """查看密码功能"""
        selected = self.table_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请选择要查看密码的记录")
            return

        row = self.table_widget.currentRow()
        record_id = int(self.table_widget.item(row, 0).text())

        # 查找原始记录
        original_record = None
        for record in self.pm.current_data["tables"][self.current_table]:
            if record["id"] == record_id:
                original_record = record
                break

        if not original_record:
            QMessageBox.critical(self, "错误", "未找到记录")
            return

        # 验证主密码
        dialog = SecurityDialog(self, "安全验证", "查看密码需要验证您的主密码")
        if dialog.exec_() == QDialog.Accepted:
            if self.pm.verify_master_password(dialog.get_password()):
                site_name = original_record.get("网站名称", "")
                username = original_record.get("账号", "")
                password = original_record.get("密码", "")

                # 显示密码信息
                msg = QMessageBox(self)
                msg.setWindowTitle("密码详情")
                msg.setText(f"""
                <div style="font-family: 'Microsoft YaHei'; color: #654321;">
                    <h3>密码详情</h3>
                    <p><b>网站名称:</b> {site_name}</p>
                    <p><b>账号:</b> {username}</p>
                    <p><b>密码:</b> <span style="color: #A64D37; font-weight: bold;">{password}</span></p>
                </div>
                """)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
            else:
                QMessageBox.warning(self, "验证失败", "主密码错误，无法查看密码")

    def delete_record(self):
        """删除记录"""
        selected = self.table_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请选择要删除的记录")
            return

        row = self.table_widget.currentRow()
        record_id = int(self.table_widget.item(row, 0).text())

        reply = QMessageBox.question(self, "确认删除",
                                     "确定要删除选中的记录吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.pm.delete_record(self.current_table, record_id):
                self.refresh_table()
                QMessageBox.information(self, "成功", "记录删除成功")
                self.update_status("记录删除成功")
            else:
                QMessageBox.critical(self, "错误", "删除记录失败")

    def _find_record_by_id(self, record_id):
        """在当前表中按 id 查找记录"""
        return next((r for r in self.pm.current_data["tables"][self.current_table]
                     if r["id"] == record_id), None)

    def move_record_ui(self):
        """迁移记录：把选中记录移到其他工作表"""
        selected = self.table_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请选择要迁移的记录")
            return
        row = self.table_widget.currentRow()
        record_id = int(self.table_widget.item(row, 0).text())
        record = self._find_record_by_id(record_id)
        if not record:
            QMessageBox.critical(self, "错误", "未找到记录")
            return

        other_tables = [t for t in self.pm.get_table_names() if t != self.current_table]
        if not other_tables:
            QMessageBox.information(self, "无法迁移", "只有当前一个工作表，无目标表可迁移。")
            return
        from PyQt5.QtWidgets import QInputDialog
        target, ok = QInputDialog.getItem(
            self, "迁移记录", f"把「{record.get('网站名称') or record.get('账号')}」迁移到:",
            other_tables, 0, False)
        if not ok:
            return
        name = record.get("网站名称") or record.get("账号") or str(record_id)
        reply = QMessageBox.question(
            self, "确认迁移",
            f"确定将「{name}」从 {self.current_table} 迁移到 {target} 吗？")
        if reply != QMessageBox.Yes:
            return

        ok, msg = self.pm.move_record(self.current_table, record_id, target)
        if ok:
            self.refresh_table()
            self.update_status(msg)
        else:
            QMessageBox.critical(self, "迁移失败", msg)

    def verify_website(self):
        """一键核实选中记录网站的有效性（含「内网/家用」的类型不核实）"""
        selected = self.table_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请选择要核实的记录")
            return
        row = self.table_widget.currentRow()
        record_id = int(self.table_widget.item(row, 0).text())
        record = self._find_record_by_id(record_id)
        if not record:
            QMessageBox.critical(self, "错误", "未找到记录")
            return

        ntype = (record.get("网络类型") or "").strip()
        if "内网" in ntype or "家用" in ntype:
            QMessageBox.information(
                self, "无需核实",
                f"该记录网络类型为「{ntype or '未设置'}」。\n内网/家用地址无法从公网核实，请为互联网/政务外网站点使用此功能。")
            return

        url = (record.get("网址") or "").strip()
        if not url:
            QMessageBox.warning(self, "网址为空", "该记录没有填写网址，无法核实。")
            return

        if getattr(self, "_verify_thread", None) and self._verify_thread.isRunning():
            QMessageBox.information(self, "正在核实", "上一次核实还在进行中，请稍候。")
            return

        name = record.get("网站名称") or url
        self.update_status(f"正在核实: {name} {url} ...")
        self._verify_thread = VerifyWebsiteThread(url, name, self)
        self._verify_thread.verify_done.connect(self._on_verify_done)
        self._verify_thread.start()

    def _on_verify_done(self, ok, site_name, status_text, short_status):
        """单条核实完成：结果写入状态栏 + 数据库 + 刷新行。
        short_status 已是两态（可访问/不可访问），详细原因只在状态栏显示。"""
        mark = "✓" if ok else "✗"
        self.update_status(f"{mark} 核实完成: {site_name} → {status_text}")

        # 写入数据库与内存
        row = self.table_widget.currentRow()
        if row >= 0:
            try:
                record_id = int(self.table_widget.item(row, 0).text())
                now = time.strftime("%m-%d %H:%M")
                if self.pm.update_verify_status(self.current_table, record_id,
                                                short_status, now):
                    self.refresh_table()
            except Exception:
                pass

    def verify_all_websites(self):
        """批量核实所有工作表的可核实站点（内网/家用/空网址跳过）"""
        if getattr(self, "_batch_thread", None) and self._batch_thread.isRunning():
            QMessageBox.information(self, "正在核实", "批量核实正在进行中，请稍候。")
            return
        total = sum(
            1 for recs in self.pm.current_data["tables"].values()
            for rec in recs
            if "内网" not in (rec.get("网络类型") or "")
            and "家用" not in (rec.get("网络类型") or "")
            and (rec.get("网址") or "").strip())
        if total == 0:
            QMessageBox.information(self, "无需核实", "没有可核实的站点（内网/家用/空网址已跳过）。")
            return

        self._batch_start_time = time.strftime("%m-%d %H:%M")
        self.update_status(f"开始批量核实：共 {total} 个站点（内网/家用已跳过）…")
        self._batch_thread = BatchVerifyThread(self.pm, self)
        self._batch_thread.one_done.connect(self._on_batch_one)
        self._batch_thread.progress.connect(self._on_batch_progress)
        self._batch_thread.batch_done.connect(self._on_batch_done)
        self._batch_thread.start()

    def _on_batch_one(self, table_name, record_id, ok, short_status, phrase):
        """批量核实：单条结果落库（注意：其他表的记录也直接落库）"""
        self.pm.update_verify_status(table_name, record_id, short_status,
                                     self._batch_start_time)

    def _on_batch_progress(self, idx, total, ok_cnt, fail_cnt, skipped):
        """批量核实：状态栏滚动进度"""
        self.update_status(
            f"⏳ 批量核实中：{idx}/{total} · 可访问 {ok_cnt} · 失败 {fail_cnt} · 跳过 {skipped}")

    def _on_batch_done(self, total, ok_cnt, fail_cnt, skipped):
        """批量核实完成：刷新表格并汇总"""
        self.refresh_table()
        self.update_status(
            f"✓ 批量核实完成：共 {total} 个 · 可访问 {ok_cnt} · 失败 {fail_cnt} · 跳过 {skipped}（结果已保存）")
        QMessageBox.information(
            self, "批量核实完成",
            f"共核实 {total} 个站点：\n可访问 {ok_cnt} 个\n无法访问 {fail_cnt} 个\n跳过 {skipped} 个\n\n每条状态已保存到「网络状态」列。")

    def open_type_manager(self):
        """打开网络类型管理对话框"""
        dlg = NetworkTypeManagerDialog(self, self.pm)
        dlg.exec_()
        if dlg.types_changed:
            self.refresh_table()
            self.update_status("网络类型字典已更新，相关记录已同步")

    def share_record(self):
        """分享选中的记录"""
        selected = self.table_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请选择要分享的记录")
            return

        row = self.table_widget.currentRow()
        record_id = int(self.table_widget.item(row, 0).text())

        # 查找原始记录
        original_record = None
        for record in self.pm.current_data["tables"][self.current_table]:
            if record["id"] == record_id:
                original_record = record
                break

        if not original_record:
            QMessageBox.critical(self, "错误", "未找到记录")
            return

        # 验证主密码
        dialog = SecurityDialog(self, "安全验证", "分享记录需要验证您的主密码")
        if dialog.exec_() == QDialog.Accepted:
            if self.pm.verify_master_password(dialog.get_password()):
                self.show_share_dialog(original_record)
            else:
                QMessageBox.warning(self, "验证失败", "主密码错误，无法分享记录")

    def show_share_dialog(self, record):
        """显示分享对话框"""
        dialog = ShareDialog(self, record)
        dialog.exec_()

    def manual_backup(self):
        """手动备份数据"""
        success, message = self.pm.backup_data("manual")
        if success:
            QMessageBox.information(self, "备份成功", message)
            self.update_status("数据备份完成")
        else:
            QMessageBox.critical(self, "备份失败", message)

    def change_password(self):
        """打开修改密码对话框"""
        dialog = ChangePasswordDialog(self, self.pm)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            # 密码修改成功，可以执行一些后续操作
            self.update_status("密码修改成功")

            # 可选：询问用户是否重新登录
            reply = QMessageBox.question(self, "修改成功",
                                         "密码修改成功，建议重新登录以确保安全。\n是否立即重新登录？",
                                         QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.logout()

    def logout(self):
        """注销当前账号"""
        reply = QMessageBox.question(self, "确认注销",
                                     "确定要注销当前账号吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.pm.logout()
            self.hide()
            self.login_window.show_login()

    def update_status(self, message):
        """更新状态栏"""
        self.status_label.setText(message)

    def excel_import(self):
        """打开Excel导入对话框"""
        dialog = ExcelImportDialog(self, self.pm)
        dialog.import_completed.connect(self.on_excel_import_completed)
        dialog.exec_()

    def on_excel_import_completed(self, success, message):
        """Excel导入完成回调"""
        if success:
            self.refresh_table()
            total_records = sum(len(recs) for recs in self.pm.current_data["tables"].values())
            self.record_count_label.setText(f"总记录数: {total_records}")
        self.update_status(message)

    def export_data(self):
        """导出数据（Excel / CSV，导出内容为明文，须输入主密码授权，可勾选记录）"""
        data = self.pm.current_data.get("tables", {})
        dlg = ExportDialog(self, self.current_table, data)
        if dlg.exec_() != QDialog.Accepted:
            return
        fmt = dlg.get_choice()

        # 导出涉及明文密码，必须输入并验证主密码
        master_pwd = dlg.get_master_password()
        if not master_pwd:
            QMessageBox.warning(self, "需要主密码", "导出明文密码必须先输入主密码")
            return
        if not self.pm.verify_master_password(master_pwd):
            QMessageBox.warning(self, "验证失败", "主密码错误，已取消导出")
            return

        selected = dlg.get_selected()
        if not selected:
            QMessageBox.warning(self, "未选择记录", "请至少勾选一条要导出的记录")
            return

        scope = dlg.get_scope()
        if fmt == "excel":
            file_filter = "Excel 文件 (*.xlsx)"
            default_name = "墨香密码导出.xlsx"
        else:
            if scope == "all":
                file_filter = "ZIP 文件 (*.zip)"
                default_name = "墨香密码导出.zip"
            else:
                file_filter = "CSV 文件 (*.csv)"
                default_name = "墨香密码导出.csv"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", os.path.join(BASE_DIR, default_name), file_filter)
        if not save_path:
            return

        reply = QMessageBox.warning(
            self, "安全提醒",
            "导出的文件将包含【明文密码】。\n请勿通过微信/邮件等不安全渠道发送，也不要长期存放在公共电脑上。\n\n确定导出吗？",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # 与导入格式对齐的列（去掉 id，导入时会重新分配）
        columns = ["网站名称", "网址", "账号", "密码", "网络类型", "备注"]
        try:
            # 按表分组勾选的记录
            by_table = {}
            for sel in selected:
                by_table.setdefault(sel["table"], []).append(sel["record"])

            if fmt == "excel":
                with pd.ExcelWriter(save_path, engine="openpyxl") as writer:
                    for t, rows in by_table.items():
                        df = pd.DataFrame(
                            [{c: r.get(c, "") for c in columns} for r in rows],
                            columns=columns)
                        df.to_excel(writer, sheet_name=t, index=False)
            else:
                if len(by_table) == 1:
                    # 单表：直接写 CSV，可被导入功能重新导入
                    rows = list(by_table.values())[0]
                    df = pd.DataFrame(
                        [{c: r.get(c, "") for c in columns} for r in rows],
                        columns=columns)
                    df.to_csv(save_path, index=False, encoding="utf-8-sig")
                else:
                    # 多表：打包成 zip，内含 各工作表.csv，解压后可逐表导入
                    with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
                        for t, rows in by_table.items():
                            df = pd.DataFrame(
                                [{c: r.get(c, "") for c in columns} for r in rows],
                                columns=columns)
                            buffer = io.StringIO()
                            df.to_csv(buffer, index=False, encoding="utf-8-sig")
                            zf.writestr(f"{t}.csv", buffer.getvalue())

            QMessageBox.information(self, "导出成功", f"已导出 {len(selected)} 条记录到：\n{save_path}")
            self.update_status("数据导出完成")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出数据时出错：{str(e)}")

    # 新增：重写关闭事件处理
    def closeEvent(self, event):
        """重写关闭事件，询问用户操作"""
        if getattr(self, '_relocking', False):
            event.accept()
            return
        if not self.app_controller.is_hidden_to_tray:
            reply = QMessageBox.question(
                self,
                "确认退出",
                "您确定要退出程序吗？\n\n选择'是'将退出程序，选择'否'将最小化到系统托盘。",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 退出程序
                event.accept()
                self.app_controller.quit_application()
            elif reply == QMessageBox.No:
                # 最小化到托盘
                event.ignore()
                self.app_controller.hide_to_tray()
            else:
                # 取消关闭
                event.ignore()
        else:
            event.accept()
