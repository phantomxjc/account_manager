# -*- coding: utf-8 -*-
"""墨香密码管理器 - 中国风本地密码管理工具。

项目结构（标准包布局）：
    src/moxiang/        主包
        config.py       全局配置与本地存储（路径、配置读写、记住账号密码）
        crypto.py       数据库加密（AES-GCM）
        database.py     数据访问层（DatabaseManager / PasswordManager）
        style.py        中国风界面样式
        icon.py         应用图标加载
        single_app.py   单实例应用
        app.py          应用控制器与入口
        ui/             UI 层（登录窗、主窗、对话框）
"""
__version__ = "2.4.0"
__author__ = "xujc"
