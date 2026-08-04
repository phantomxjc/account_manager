# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 系统托盘管理
"""

import sys
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QStyle, QMessageBox
from PyQt5.QtGui import QIcon

import config
from ui.style import get_icon


class TrayIconManager:
    """系统托盘图标管理器"""

    def __init__(self, parent_window=None):
        self.parent = parent_window
        self.tray = None
        self._init_tray()

    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("系统不支持托盘功能")
            return

        self.tray = QSystemTrayIcon(self.parent)

        # 设置图标
        icon = get_icon()
        if icon.isNull():
            icon = self.parent.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray.setIcon(icon)
        self.tray.setToolTip("墨香密码管理器")

        # 菜单
        menu = QMenu()

        show_action = QAction("显示主窗口", self.parent)
        show_action.triggered.connect(self._on_show)
        menu.addAction(show_action)

        menu.addSeparator()

        exit_action = QAction("退出", self.parent)
        exit_action.triggered.connect(self._on_quit)
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()
        print("系统托盘图标已初始化")

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._on_show()
        elif reason == QSystemTrayIcon.Trigger:
            pass  # 单击显示菜单（默认行为）

    def _on_show(self):
        if self.parent:
            self.parent.show()
            self.parent.raise_()
            self.parent.activateWindow()

    def _on_quit(self):
        if self.parent:
            self.parent.close()
        QApplication_quit_helper()

    def show_message(self, title: str, msg: str, timeout: int = 2000):
        if self.tray:
            self.tray.showMessage(title, msg, QSystemTrayIcon.Information, timeout)

    def hide(self):
        if self.tray:
            self.tray.hide()


def QApplication_quit_helper():
    from PyQt5.QtWidgets import QApplication
    QApplication.quit()
