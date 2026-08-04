# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 全局配置
"""

import os
import sys

# ==================== 版本信息 ====================
VERSION = "2.0"
AUTHOR = "xujc"
RELEASE_DATE = "2026.1.22"

# ==================== 路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
DATABASE_FILE = os.path.join(BASE_DIR, "password_manager.db")
ICON_FILE = os.path.join(ASSETS_DIR, "枫叶.png")

# ==================== 加密配置 ====================
PBKDF2_ITERATIONS = 1000000      # PBKDF2 迭代次数
SALT_LENGTH = 16                  # 盐值长度（字节）
KEY_LENGTH = 32                   # AES-256 密钥长度
GCM_NONCE_LENGTH = 16             # GCM 模式 nonce 长度
GCM_TAG_LENGTH = 16               # GCM 认证标签长度

# ==================== 密码强度规则 ====================
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_REQUIRE_UPPER = True
PASSWORD_REQUIRE_LOWER = True
PASSWORD_REQUIRE_DIGIT = True

# 常见弱密码黑名单
WEAK_PASSWORDS = [
    'password', '123456', 'qwerty', 'admin', 'welcome',
    'password123', '12345678', '123456789', '123123',
]

# ==================== 界面配置 ====================
WINDOW_TITLE = "墨香密码管理器"
LOGIN_WINDOW_SIZE = (500, 500)
MAIN_WINDOW_SIZE = (1200, 800)
DIALOG_SIZES = {
    "record": (500, 450),
    "change_password": (500, 450),
    "excel_import": (500, 600),
    "share": (500, 400),
    "security": (350, 200),
}

# ==================== 表格列定义 ====================
TABLE_COLUMNS = ["ID", "网站名称", "网址", "账号", "密码", "备注"]
TABLE_HEADERS = {
    "单位表": TABLE_COLUMNS,
    "个人表": TABLE_COLUMNS,
}

# ==================== Excel 导入字段映射 ====================
EXCEL_FIELD_MAPPING = {
    '网站名称': ['网站名称', '网站名', '网站', '名称', '站点名称', '平台名称'],
    '网址':     ['网址', '网站地址', 'URL', '链接', '地址', '网站链接'],
    '账号':     ['账号', '账户', '用户名', '用户', '登录名', '用户账号'],
    '密码':     ['密码', '登陆密码', '登录密码', 'pass', 'passwd'],
    '备注':     ['备注', '说明', '注释', '描述', 'note', 'description'],
}

# ==================== 搜索字段选项 ====================
SEARCH_FIELDS = ["所有字段", "网站名称", "网址", "账号", "备注"]

# ==================== 单实例配置 ====================
APP_KEY_PREFIX = "墨香密码管理器_"

# ==================== 备份配置 ====================
BACKUP_TYPES = {
    "manual": "manual",
    "auto": "auto",
}


def get_icon_path():
    """获取图标路径，兼容打包环境"""
    candidates = [
        ICON_FILE,
        os.path.join(os.getcwd(), "枫叶.png"),
    ]
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, "枫叶.png"))

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def ensure_dirs():
    """确保必要的目录存在"""
    for d in [BACKUP_DIR, ASSETS_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)
