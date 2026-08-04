# -*- coding: utf-8 -*-
"""
墨香密码管理器 v2.0 - 程序入口
作者: xujc
日期: 2026.1.22

项目结构:
    main.py                 → 入口
    config.py               → 全局配置
    core/                   → 核心业务逻辑
    ui/                     → 界面层
    system/                 → 系统级功能
"""

import sys

# ==================== 初始化配置 ====================
import config
config.ensure_dirs()

# ==================== 启动应用 ====================
from system.single_app import SingleApplication
from system.app_controller import (
    ApplicationController, check_dependencies,
    create_app, show_single_instance_warning
)
from ui.style import setup_app_style, get_icon

def main():
    # 1. 创建单实例应用
    app = create_app(sys.argv)

    # 2. 检查是否已有实例运行
    if app.is_running():
        show_single_instance_warning()
        return

    # 3. 设置全局样式
    setup_app_style(app)

    # 4. 检查依赖
    check_dependencies()

    # 5. 启动控制器
    controller = ApplicationController()
    controller.start()

    # 6. 进入事件循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
