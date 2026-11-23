# -*- coding: utf-8 -*-
"""应用图标加载（优先 枫叶.ico，兼容打包环境）。"""
import os
import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyle

from .config import BASE_DIR


def get_app_icon():
    """返回应用图标，缺失时回退内置图标"""
    candidates = []
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, '枫叶.ico'))
    candidates.append(os.path.join(BASE_DIR, '枫叶.ico'))
    candidates.append(os.path.join(BASE_DIR, '枫叶.png'))
    for path in candidates:
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    return QApplication.style().standardIcon(QStyle.SP_DriveHDIcon)
