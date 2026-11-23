# -*- coding: utf-8 -*-
"""应用程序控制器与启动入口：窗口切换、系统托盘、单实例、主流程。"""
import os
import sys

# 在导入 pandas/numpy(OpenBLAS) 之前设定，避免某些受限环境下 OpenBLAS
# 多线程初始化时内存分配失败导致程序崩溃；密码管理器无重计算需求，单线程足够。
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction,
                             QMessageBox)
from PyQt5.QtCore import Qt

from .database import PasswordManager
from .single_app import SingleApplication
from .style import ChineseStyle
from .icon import get_app_icon
from .ui.login_window import LoginWindow
from .ui.main_window import MainWindow


class ApplicationController:
    """应用程序控制器，管理窗口切换"""

    def __init__(self):
        self.pm = PasswordManager()
        self.login_window = LoginWindow(self.pm)
        self.main_window = None
        self.tray_icon = None
        self.is_hidden_to_tray = False

        # 连接信号
        self.login_window.login_success.connect(self.show_main_window)

        # 初始化系统托盘
        self.init_tray_icon()

    def create_tray_icon(self):
        """创建托盘图标（统一使用 get_app_icon）"""
        return get_app_icon()

    def init_tray_icon(self):
        """初始化系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("系统不支持托盘功能")
            return

        self.tray_icon = QSystemTrayIcon(self.login_window)

        # 设置托盘图标
        icon = self.create_tray_icon()
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("墨香密码管理器")

        # 创建托盘菜单
        tray_menu = QMenu()

        show_action = QAction("显示主窗口", self.login_window)
        show_action.triggered.connect(self.show_main_window_from_tray)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        exit_action = QAction("退出", self.login_window)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # 显示托盘图标
        self.tray_icon.show()
        print("系统托盘图标已初始化")

    def on_tray_icon_activated(self, reason):
        """托盘图标激活事件：双击恢复/解锁"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_main_window_from_tray()

    def show_main_window_from_tray(self):
        """从托盘恢复：若处于空闲锁屏状态则弹出登录界面重新验证主密码，
        否则直接显示主窗口（常规最小化到托盘的恢复）。"""
        if self.main_window and getattr(self.main_window, 'is_locked', False):
            # 锁屏状态：显示登录界面，由用户重新输入主密码解锁
            self.login_window.show_login()
            return
        if self.main_window:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
            self.is_hidden_to_tray = False
            print("从托盘恢复主窗口")

    def show_main_window(self, username):
        """显示主窗口"""
        if self.main_window:
            self.main_window.close()

        self.main_window = MainWindow(self.pm, self.login_window, self)
        self.main_window.show()
        self.is_hidden_to_tray = False
        print("主窗口已显示")

    def hide_to_tray(self):
        """隐藏到系统托盘"""
        if self.main_window:
            self.main_window.hide()
            self.is_hidden_to_tray = True
            if self.tray_icon:
                self.tray_icon.showMessage(
                    "墨香密码管理器",
                    "程序已最小化到系统托盘",
                    QSystemTrayIcon.Information,
                    2000
                )
            print("已隐藏到系统托盘")

    def quit_application(self):
        """退出应用程序"""
        print("正在退出应用程序...")
        if self.tray_icon:
            self.tray_icon.hide()
        if self.main_window:
            self.main_window.close()
        if self.login_window:
            self.login_window.close()
        QApplication.quit()

    def start(self):
        """启动应用程序"""
        self.login_window.show_login()


def main():
    # 高 DPI 适配：必须在创建 QApplication 之前设置，避免 4K 屏模糊
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 修改：创建单实例应用程序
    app = SingleApplication(sys.argv)  # 使用 SingleApplication 替代 QApplication

    # 关键：托盘程序必须关闭「最后一个窗口关闭即退出」的默认行为。
    # 空闲锁定后主窗口 hide()、登录窗口也是隐藏状态，若保持默认 True，
    # Qt 会认为所有窗口都关闭了（系统托盘图标不算窗口），直接退出整个进程，
    # 表现为「自动锁定后软件就没了」。退出只应由用户显式操作触发（托盘菜单/关闭确认）。
    app.setQuitOnLastWindowClosed(False)

    # 新增：检查是否已有实例运行
    if app.is_running():
        QMessageBox.information(
            None,
            "程序已运行",
            "墨香密码管理器已经在运行中！\n\n请检查系统托盘或任务栏。"
        )
        sys.exit(0)

    # 设置中国风样式
    ChineseStyle.setup_style(app)

    # 检查并安装必要的加密库
    try:
        from Crypto.Cipher import AES
    except ImportError:
        reply = QMessageBox.question(
            None, "缺少依赖库",
            "系统需要pycryptodome库进行数据加密。是否要安装？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome"])
                QMessageBox.information(None, "安装成功", "依赖库安装成功，请重新启动程序")
            except Exception as e:
                QMessageBox.critical(None, "安装失败", f"安装依赖库失败: {str(e)}")
            sys.exit(0)
        else:
            QMessageBox.warning(None, "警告", "未安装加密库，数据将不会加密存储")

    controller = ApplicationController()
    controller.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
