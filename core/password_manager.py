# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 核心业务逻辑
负责：用户注册/登录、记录 CRUD、密码修改与重加密、备份、搜索、Excel 导入
"""

import os
import hashlib
import sqlite3
from datetime import datetime

import config
from core.database import DatabaseManager
from core.encryption import DatabaseEncryption


class PasswordManager:
    """密码管理器核心逻辑"""

    # ==================== 初始化 ====================

    def __init__(self):
        self.db_manager = None
        self.backup_dir = config.BACKUP_DIR
        self.current_user = None
        self.current_user_id = None

        # 内存数据缓存
        self.current_data = {
            "tables": {
                "单位表": [],
                "个人表": [],
            },
            "next_id": 1,
        }

        config.ensure_dirs()

    # ==================== 工具方法 ====================

    def get_connection(self):
        """获取数据库连接"""
        return self.db_manager.get_connection() if self.db_manager else None

    @staticmethod
    def hash_password(password: str) -> str:
        """对主密码进行 SHA-256 哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    # ==================== 用户管理 ====================

    def register_user(self, username: str, password: str) -> tuple:
        """
        注册新用户
        返回: (success: bool, message: str)
        """
        # 密码强度预检
        valid, msg = self.validate_password_strength(password)
        if not valid:
            return False, msg

        try:
            self.db_manager = DatabaseManager(password)
            conn = self.get_connection()
            cursor = conn.cursor()

            created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                'INSERT INTO users (username, master_password, created_date, last_login) '
                'VALUES (?, ?, ?, ?)',
                (username, self.hash_password(password), created_date, created_date)
            )
            conn.commit()
            conn.close()
            return True, "注册成功"
        except sqlite3.IntegrityError:
            return False, "用户名已存在"
        except Exception as e:
            return False, f"注册失败: {e}"

    def login(self, username: str, password: str) -> tuple:
        """
        用户登录
        返回: (success: bool, message: str)
        """
        try:
            # 先用临时连接验证
            temp_db = DatabaseManager()
            conn = temp_db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, master_password FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            conn.close()

            if not result:
                return False, "用户不存在"

            user_id, stored_hash = result
            if stored_hash != self.hash_password(password):
                return False, "密码错误"

            # 验证通过 → 用主密码初始化加密
            self.db_manager = DatabaseManager(password)
            self.current_user = username
            self.current_user_id = user_id

            # 更新最后登录时间
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id)
            )
            conn.commit()
            conn.close()

            self.load_user_data()
            return True, "登录成功"

        except Exception as e:
            return False, f"登录失败: {e}"

    def logout(self) -> bool:
        """注销当前用户，清空内存"""
        if not self.current_user:
            return False

        self.current_user = None
        self.current_user_id = None
        self.db_manager = None
        self.current_data = {
            "tables": {"单位表": [], "个人表": []},
            "next_id": 1,
        }
        return True

    # ==================== 数据加载 ====================

    def load_user_data(self):
        """从数据库加载当前用户的所有记录到内存"""
        if not self.current_user_id:
            return

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            for table_key, db_table in [("单位表", "unit_table"), ("个人表", "personal_table")]:
                cursor.execute(
                    f'SELECT id, website_name, website_url, account, password, notes '
                    f'FROM {db_table} WHERE user_id = ? ORDER BY id',
                    (self.current_user_id,)
                )
                records = []
                for row in cursor.fetchall():
                    records.append({
                        "id": row[0],
                        "网站名称": row[1],
                        "网址": row[2] or "",
                        "账号": row[3],
                        "密码": self.db_manager.decrypt_password(row[4]),
                        "备注": row[5] or "",
                    })
                self.current_data["tables"][table_key] = records

            conn.close()

            # 计算下一个可用 ID
            all_records = (
                self.current_data["tables"]["单位表"] +
                self.current_data["tables"]["个人表"]
            )
            self.current_data["next_id"] = (
                max(r["id"] for r in all_records) + 1 if all_records else 1
            )

        except Exception as e:
            print(f"加载用户数据失败: {e}")

    # ==================== 记录 CRUD ====================

    def add_record(self, table_name: str, record_data: dict) -> bool:
        """新增一条记录"""
        if not self.current_user_id or table_name not in self.current_data["tables"]:
            return False

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            encrypted_pwd = self.db_manager.encrypt_password(record_data["密码"])

            db_table = "unit_table" if table_name == "单位表" else "personal_table"
            cursor.execute(
                f'INSERT INTO {db_table} '
                f'(user_id, website_name, website_url, account, password, notes, created_time, updated_time) '
                f'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (self.current_user_id,
                 record_data["网站名称"],
                 record_data["网址"],
                 record_data["账号"],
                 encrypted_pwd,
                 record_data["备注"],
                 now, now)
            )
            conn.commit()
            record_id = cursor.lastrowid
            conn.close()

            record_data["id"] = record_id
            self.current_data["tables"][table_name].append(record_data)
            self.current_data["next_id"] = max(self.current_data["next_id"], record_id + 1)
            return True
        except Exception as e:
            print(f"添加记录失败: {e}")
            return False

    def update_record(self, table_name: str, record_id: int, new_data: dict) -> bool:
        """更新一条记录"""
        if not self.current_user_id:
            return False

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            encrypted_pwd = self.db_manager.encrypt_password(new_data["密码"])

            db_table = "unit_table" if table_name == "单位表" else "personal_table"
            cursor.execute(
                f'UPDATE {db_table} SET '
                f'website_name=?, website_url=?, account=?, password=?, notes=?, updated_time=? '
                f'WHERE id=? AND user_id=?',
                (new_data["网站名称"], new_data["网址"], new_data["账号"],
                 encrypted_pwd, new_data["备注"], now,
                 record_id, self.current_user_id)
            )
            conn.commit()
            conn.close()

            # 同步内存
            for rec in self.current_data["tables"][table_name]:
                if rec["id"] == record_id:
                    rec.update(new_data)
                    break
            return True
        except Exception as e:
            print(f"更新记录失败: {e}")
            return False

    def delete_record(self, table_name: str, record_id: int) -> bool:
        """删除一条记录"""
        if not self.current_user_id:
            return False

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            db_table = "unit_table" if table_name == "单位表" else "personal_table"
            cursor.execute(
                f'DELETE FROM {db_table} WHERE id=? AND user_id=?',
                (record_id, self.current_user_id)
            )
            conn.commit()
            conn.close()

            self.current_data["tables"][table_name] = [
                r for r in self.current_data["tables"][table_name]
                if r["id"] != record_id
            ]
            return True
        except Exception as e:
            print(f"删除记录失败: {e}")
            return False

    # ==================== 搜索 ====================

    def search_records(self, table_name: str, search_term: str, search_field: str = "所有字段"):
        """在指定表中搜索记录"""
        records = self.current_data["tables"].get(table_name, [])
        if not search_term:
            return records

        term = search_term.lower()
        results = []

        for rec in records:
            if search_field != "所有字段":
                val = str(rec.get(search_field, "")).lower()
                if term in val:
                    results.append(rec)
            else:
                if any(term in str(v).lower() for v in rec.values()):
                    results.append(rec)
                    continue
        return results

    # ==================== 密码修改（含全部重加密） ====================

    def change_password(self, current_password: str, new_password: str) -> tuple:
        """
        修改主密码并重新加密所有记录
        返回: (success: bool, message: str)
        """
        if not self.current_user_id:
            return False, "用户未登录"

        # 强度校验
        valid, msg = self.validate_password_strength(new_password)
        if not valid:
            return False, msg

        if current_password == new_password:
            return False, "新密码不能与当前密码相同"

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 验证当前密码
            cursor.execute('SELECT master_password FROM users WHERE id=?', (self.current_user_id,))
            row = cursor.fetchone()
            if not row or row[0] != self.hash_password(current_password):
                conn.close()
                return False, "当前密码错误"

            # 创建新密钥
            new_db = DatabaseManager(new_password)
            old_db = self.db_manager

            conn.execute('BEGIN TRANSACTION')

            # 重加密两张表
            for db_table, key in [("unit_table", "单位表"), ("personal_table", "个人表")]:
                cursor.execute(
                    f'SELECT id, password FROM {db_table} WHERE user_id=?',
                    (self.current_user_id,)
                )
                for rec_id, old_enc in cursor.fetchall():
                    plain = old_db.decrypt_password(old_enc)
                    new_enc = new_db.encrypt_password(plain)
                    cursor.execute(
                        f'UPDATE {db_table} SET password=? WHERE id=?',
                        (new_enc, rec_id)
                    )

            # 更新哈希
            cursor.execute(
                'UPDATE users SET master_password=? WHERE id=?',
                (self.hash_password(new_password), self.current_user_id)
            )

            conn.commit()

            # 切换管理器
            self.db_manager = new_db
            self.load_user_data()
            return True, "密码修改成功"

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            self.db_manager = old_db
            return False, f"密码修改失败: {e}"
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def verify_master_password(self, password: str) -> bool:
        """验证主密码是否正确"""
        if not self.current_user_id:
            return False
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT master_password FROM users WHERE id=?', (self.current_user_id,))
            row = cursor.fetchone()
            conn.close()
            return bool(row and row[0] == self.hash_password(password))
        except Exception:
            return False

    # ==================== 密码强度校验 ====================

    def validate_password_strength(self, password: str) -> tuple:
        """验证密码强度，返回 (是否通过, 提示信息)"""
        if len(password) < config.PASSWORD_MIN_LENGTH:
            return False, f"密码长度至少 {config.PASSWORD_MIN_LENGTH} 位"
        if len(password) > config.PASSWORD_MAX_LENGTH:
            return False, f"密码长度不能超过 {config.PASSWORD_MAX_LENGTH} 位"

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "密码必须包含大写字母、小写字母和数字"

        weak = [w for w in config.WEAK_PASSWORDS if w]
        weak.append(self.current_user.lower()) if self.current_user else None
        if password.lower() in weak:
            return False, "密码过于简单，请使用更复杂的密码"

        return True, "密码强度符合要求"

    # ==================== 备份 ====================

    def backup_data(self, backup_type: str = "manual") -> tuple:
        """
        备份当前用户数据到独立 SQLite 文件
        返回: (success: bool, message: str)
        """
        if not self.current_user_id:
            return False, "用户未登录"

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "auto" if backup_type == "auto" else "manual"
            backup_file = os.path.join(
                self.backup_dir, f"{self.current_user}_{prefix}_{timestamp}.db"
            )

            backup_conn = sqlite3.connect(backup_file)
            b_cursor = backup_conn.cursor()

            # 建表
            for db_table in ["unit_table", "personal_table"]:
                b_cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {db_table}_backup (
                        id INTEGER PRIMARY KEY, user_id INTEGER,
                        website_name TEXT, website_url TEXT,
                        account TEXT, password TEXT,
                        notes TEXT, created_time TEXT, updated_time TEXT
                    )
                ''')

            conn = self.get_connection()
            c_cursor = conn.cursor()

            total = 0
            for db_table in ["unit_table", "personal_table"]:
                c_cursor.execute(
                    f'SELECT * FROM {db_table} WHERE user_id=?',
                    (self.current_user_id,)
                )
                for row in c_cursor.fetchall():
                    b_cursor.execute(
                        f'INSERT INTO {db_table}_backup VALUES (?,?,?,?,?,?,?,?,?)',
                        row
                    )
                    total += 1

            conn.close()

            # 备份元信息
            b_cursor.execute('''
                CREATE TABLE IF NOT EXISTS backup_info (
                    backup_time TEXT, user_name TEXT,
                    record_count INTEGER, backup_type TEXT
                )
            ''')
            b_cursor.execute(
                'INSERT INTO backup_info VALUES (?,?,?,?)',
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 self.current_user, total, backup_type)
            )

            backup_conn.commit()
            backup_conn.close()

            return True, f"备份成功: {os.path.basename(backup_file)}"
        except Exception as e:
            return False, f"备份失败: {e}"
