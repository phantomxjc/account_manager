# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 单实例控制
基于 QSharedMemory，防止程序重复启动
"""

import hashlib
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSharedMemory

import config


class SingleApplication(QApplication):
    """单实例应用程序类"""

    def __init__(self, argv):
        super().__init__(argv)

        # 生成唯一共享内存键
        exec_hash = hashlib.md5(sys.executable.encode()).hexdigest()[:8]
        app_key = f"{config.APP_KEY_PREFIX}{exec_hash}"
        self._shared_memory = QSharedMemory(app_key)

        # 尝试附加 → 已有实例在运行
        if self._shared_memory.attach():
            self._is_running = True
        else:
            # 创建新的共享内存段
            if self._shared_memory.create(1):
                self._is_running = False
            else:
                # 创建失败（可能上次异常退出残留）
                self._is_running = True

    def is_running(self) -> bool:
        return self._is_running
