# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 数据库管理模块
负责 SQLite 连接、表结构初始化、加密配置存取
"""

import os
import base64
import sqlite3
from datetime import datetime

import config
from core.encryption import DatabaseEncryption


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, master_password=None):
        """
        master_password: 首次注册时传入，用于初始化加密配置
        """
        self.db_file = config.DATABASE_FILE
        self.master_password = master_password
        self.encryption_key = None
        self.salt = None
        self.init_database()

    # ==================== 基础连接 ====================

    def get_connection(self):
        """获取一个新的 SQLite 连接"""
        return sqlite3.connect(self.db_file)

    def init_database(self):
        """初始化所有表结构 + 加密配置"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # ---------- 加密配置表 ----------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encryption_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salt TEXT NOT NULL,
                created_date TEXT NOT NULL
            )
        ''')

        # ---------- 用户表 ----------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                master_password TEXT NOT NULL,
                created_date TEXT NOT NULL,
                last_login TEXT
            )
        ''')

        # ---------- 单位表 ----------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unit_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                website_name TEXT NOT NULL,
                website_url TEXT,
                account TEXT NOT NULL,
                password TEXT NOT NULL,
                notes TEXT,
                created_time TEXT NOT NULL,
                updated_time TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # ---------- 个人表 ----------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personal_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                website_name TEXT NOT NULL,
                website_url TEXT,
                account TEXT NOT NULL,
                password TEXT NOT NULL,
                notes TEXT,
                created_time TEXT NOT NULL,
                updated_time TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # ---------- 备份记录表 ----------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                backup_file TEXT NOT NULL,
                backup_time TEXT NOT NULL,
                backup_type TEXT NOT NULL,
                record_count INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # ---------- 初始化加密配置 ----------
        cursor.execute('SELECT salt FROM encryption_config LIMIT 1')
        result = cursor.fetchone()

        if not result and self.master_password:
            # 首次注册：生成 salt + 派生密钥
            salt = self._generate_salt()
            key, _ = DatabaseEncryption.derive_key(self.master_password, salt)
            self.encryption_key = key
            self.salt = salt

            cursor.execute(
                'INSERT INTO encryption_config (salt, created_date) VALUES (?, ?)',
                (base64.b64encode(salt).decode('utf-8'),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )

        elif result and self.master_password:
            # 已有配置：加载 salt 并派生密钥
            salt = base64.b64decode(result[0])
            key, _ = DatabaseEncryption.derive_key(self.master_password, salt)
            self.encryption_key = key
            self.salt = salt

        conn.commit()
        conn.close()

    # ==================== 加密 / 解密接口 ====================

    def encrypt_password(self, password: str) -> str:
        """加密密码字段"""
        if self.encryption_key:
            return DatabaseEncryption.encrypt_data(password, self.encryption_key)
        return password

    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码字段（失败返回原文，兼容旧数据）"""
        if not self.encryption_key:
            return encrypted_password
        try:
            return DatabaseEncryption.decrypt_data(
                encrypted_password, self.encryption_key
            )
        except ValueError:
            return encrypted_password

    # ==================== 内部工具 ====================

    def _generate_salt(self) -> bytes:
        """生成新的随机盐值"""
        from Crypto.Random import get_random_bytes
        return get_random_bytes(config.SALT_LENGTH)

    def is_initialized(self) -> bool:
        """数据库文件是否已存在"""
        return os.path.exists(self.db_file)
