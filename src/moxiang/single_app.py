# -*- coding: utf-8 -*-
"""单实例应用程序类。"""
import sys
import hashlib
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSharedMemory


class SingleApplication(QApplication):
    """单实例应用程序类"""

    def __init__(self, argv):
        super().__init__(argv)
        # 创建一个唯一的共享内存键（包含可执行文件路径避免冲突）
        app_key = f"墨香密码管理器_{hashlib.md5(sys.executable.encode()).hexdigest()[:8]}"
        self._shared_memory = QSharedMemory(app_key)

        # 尝试附加到共享内存，如果成功说明已有实例运行
        if self._shared_memory.attach():
            self._is_running = True
        else:
            # 创建共享内存
            self._is_running = False
            if not self._shared_memory.create(1):
                self._is_running = True

    def is_running(self):
        return self._is_running
