# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 应用程序控制器
管理窗口生命周期、系统托盘、全局退出
"""

import sys
from PyQt5.QtWidgets import QMessageBox, QApplication, QStyle

import config
from core.password_manager import PasswordManager
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from ui.style import get_icon
from system.single_app import SingleApplication
from system.tray_icon import TrayIconManager


class ApplicationController:
    """应用程序控制器"""

    def __init__(self):
        self.pm = PasswordManager()
        self.login_window = None
        self.main_window = None
        self.tray_icon = None
        self.is_hidden_to_tray = False

        self._init_windows()
        self._init_tray()

    # ==================== 初始化 ====================

    def _init_windows(self):
        self.login_window = LoginWindow(self.pm)
        self.login_window.login_success.connect(self._on_login_success)

    def _init_tray(self):
        self.tray_icon = TrayIconManager(self.login_window)

    # ==================== 窗口切换 ====================

    def _on_login_success(self, username: str):
        if self.main_window:
            self.main_window.close()
        self.main_window = MainWindow(self.pm, self.login_window, self)
        self.main_window.show()
        self.is_hidden_to_tray = False

    def show_main_window_from_tray(self):
        if self.main_window:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
            self.is_hidden_to_tray = False

    def hide_to_tray(self):
        if self.main_window:
            self.main_window.hide()
            self.is_hidden_to_tray = True
            if self.tray_icon:
                self.tray_icon.show_message("墨香密码管理器", "程序已最小化到系统托盘")

    def quit_application(self):
        print("正在退出应用程序...")
        if self.tray_icon:
            self.tray_icon.hide()
        if self.main_window:
            self.main_window.close()
        if self.login_window:
            self.login_window.close()
        QApplication.quit()

    # ==================== 启动 ====================

    def start(self):
        self.login_window.show_login()


# ==================== 依赖检查 ====================

def check_dependencies() -> bool:
    """检查并提示安装缺失的依赖"""
    missing = []
    try:
        from Crypto.Cipher import AES  # noqa
    except ImportError:
        missing.append("pycryptodome")

    if missing:
        reply = QMessageBox.question(
            None, "缺少依赖库",
            f"系统需要以下库进行数据加密：\n{', '.join(missing)}\n\n是否要安装？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            import subprocess
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "pycryptodome"]
                )
                QMessageBox.information(None, "安装成功", "依赖库安装成功，请重新启动程序")
            except Exception as e:
                QMessageBox.critical(None, "安装失败", f"安装依赖库失败: {e}")
            sys.exit(0)
        else:
            QMessageBox.warning(None, "警告", "未安装加密库，数据将不会加密存储")
            return False
    return True


# ==================== 程序入口 ====================

def create_app(argv) -> SingleApplication:
    """创建单实例应用对象"""
    return SingleApplication(argv)


def show_single_instance_warning():
    """已有实例在运行时弹出提示"""
    QMessageBox.information(
        None, "程序已运行",
        "墨香密码管理器已经在运行中！\n\n请检查系统托盘或任务栏。"
    )
    sys.exit(0)
