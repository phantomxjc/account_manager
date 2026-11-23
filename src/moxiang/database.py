# -*- coding: utf-8 -*-
"""数据访问层：DatabaseManager（数据库管理）与 PasswordManager（业务逻辑）。"""
import os
import sqlite3
import hashlib
import base64
import pandas as pd
from datetime import datetime
from Crypto.Random import get_random_bytes

from .config import BASE_DIR, fallback_network_type
from .crypto import DatabaseEncryption


def _read_import_dataframe(file_path, sheet_name=None):
    """根据扩展名读取 Excel 或 CSV 为 DataFrame（供导入复用）"""
    ext = file_path.lower()
    if ext.endswith('.csv'):
        return pd.read_csv(file_path, encoding="utf-8-sig")
    if sheet_name:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    return pd.read_excel(file_path)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, master_password=None):
        self.db_file = os.path.join(BASE_DIR, "password_manager.db")
        self.master_password = master_password
        self.encryption_key = None
        self.salt = None
        self.init_database()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_file, timeout=10)
        return conn

    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 创建加密配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encryption_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salt TEXT NOT NULL,
                created_date TEXT NOT NULL
            )
        ''')

        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                master_password TEXT NOT NULL,
                created_date TEXT NOT NULL,
                last_login TEXT
            )
        ''')

        # 创建单位表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unit_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                website_name TEXT NOT NULL,
                website_url TEXT,
                account TEXT NOT NULL,
                password TEXT NOT NULL,
                notes TEXT,
                network_type TEXT DEFAULT '',
                verify_status TEXT DEFAULT '',
                verify_time TEXT DEFAULT '',
                created_time TEXT NOT NULL,
                updated_time TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 创建个人表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personal_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                website_name TEXT NOT NULL,
                website_url TEXT,
                account TEXT NOT NULL,
                password TEXT NOT NULL,
                notes TEXT,
                network_type TEXT DEFAULT '',
                verify_status TEXT DEFAULT '',
                verify_time TEXT DEFAULT '',
                created_time TEXT NOT NULL,
                updated_time TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 旧库升级（v2.2/v2.3）：自动补 network_type / verify 列，老数据零操作迁移
        for tbl in ("unit_table", "personal_table"):
            cursor.execute(f"PRAGMA table_info({tbl})")
            cols = [row[1] for row in cursor.fetchall()]
            if "network_type" not in cols:
                cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN network_type TEXT DEFAULT ''")
            if "verify_status" not in cols:
                cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN verify_status TEXT DEFAULT ''")
            if "verify_time" not in cols:
                cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN verify_time TEXT DEFAULT ''")

        # 用户自定义工作表注册表（v2.4）：默认只有单位表/个人表，可右键新增
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_time TEXT NOT NULL
            )
        ''')

        # 确保已注册的自定义表物理存在（老库升级/异常恢复）
        cursor.execute("SELECT id FROM custom_tables ORDER BY id")
        for row in cursor.fetchall():
            self._ensure_physical_table(cursor, f"custom_{row[0]}")

        conn.commit()

        # 创建备份记录表
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
        # 检查是否已存在加密配置
        cursor.execute('SELECT salt FROM encryption_config LIMIT 1')
        result = cursor.fetchone()

        if not result and self.master_password:
            # 初始化加密配置
            salt = get_random_bytes(16)
            key, _ = DatabaseEncryption.derive_key(self.master_password, salt)
            self.encryption_key = key
            self.salt = salt

            cursor.execute('''
                INSERT INTO encryption_config (salt, created_date)
                VALUES (?, ?)
            ''', (base64.b64encode(salt).decode('utf-8'),
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        elif result and self.master_password:
            # 加载现有加密配置
            salt = base64.b64decode(result[0])
            key, _ = DatabaseEncryption.derive_key(self.master_password, salt)
            self.encryption_key = key
            self.salt = salt

        conn.commit()
        conn.close()

    @staticmethod
    def _ensure_physical_table(cursor, physical_name):
        """确保某个数据表物理存在（自定义表用，结构与单位/个人表一致）"""
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {physical_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                website_name TEXT NOT NULL,
                website_url TEXT,
                account TEXT NOT NULL,
                password TEXT NOT NULL,
                notes TEXT,
                network_type TEXT DEFAULT '',
                verify_status TEXT DEFAULT '',
                verify_time TEXT DEFAULT '',
                created_time TEXT NOT NULL,
                updated_time TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

    def encrypt_password(self, password: str) -> str:
        """加密密码"""
        if self.encryption_key:
            return DatabaseEncryption.encrypt_data(password, self.encryption_key)
        return password

    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        if self.encryption_key:
            try:
                return DatabaseEncryption.decrypt_data(encrypted_password, self.encryption_key)
            except ValueError:
                # 如果解密失败，返回原始数据（可能是未加密的旧数据）
                return encrypted_password
        return encrypted_password


class PasswordManager:
    """密码管理器核心逻辑"""

    def __init__(self):
        self.db_manager = None
        self.backup_dir = os.path.join(BASE_DIR, "backups")
        self.current_user = None
        self.current_user_id = None
        self.current_data = {
            "tables": {
                "单位表": [],
                "个人表": []
            },
            "next_id": 1
        }

        # 创建备份目录
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def get_connection(self):
        """获取数据库连接"""
        return self.db_manager.get_connection() if self.db_manager else None

    # ===== 动态工作表（v2.4）：默认单位表/个人表，可右键新增自定义表 =====

    DEFAULT_TABLES = ("单位表", "个人表")

    def get_table_map(self):
        """逻辑表名 -> 物理表名 的完整映射（含自定义表）"""
        mapping = {"单位表": "unit_table", "个人表": "personal_table"}
        if not self.db_manager or not self.current_user_id:
            return mapping
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM custom_tables ORDER BY id")
            for row in cursor.fetchall():
                mapping[row[1]] = f"custom_{row[0]}"
            conn.close()
        except Exception as e:
            print(f"读取自定义表注册失败: {str(e)}")
        return mapping

    def get_table_names(self):
        """所有逻辑表名列表（单位表、个人表 + 自定义表）"""
        return list(self.get_table_map().keys())

    def create_table(self, name):
        """新建自定义工作表（返回 (ok, msg)）"""
        if not self.db_manager or not self.current_user_id:
            return False, "用户未登录"
        name = (name or "").strip()
        if not name:
            return False, "表名不能为空"
        if len(name) > 20:
            return False, "表名不能超过20个字"
        mapping = self.get_table_map()
        if name in mapping:
            return False, f"表「{name}」已存在"
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO custom_tables (name, created_time) VALUES (?, ?)",
                (name, current_time))
            new_id = cursor.lastrowid
            self.db_manager._ensure_physical_table(cursor, f"custom_{new_id}")
            conn.commit()
            conn.close()
            self.current_data["tables"][name] = []
            return True, f"工作表「{name}」创建成功"
        except Exception as e:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
            return False, f"创建失败: {str(e)}"

    def delete_table(self, name):
        """删除自定义工作表（默认两张表不允许删；返回 (ok, msg)）"""
        if not self.db_manager or not self.current_user_id:
            return False, "用户未登录"
        if name in self.DEFAULT_TABLES:
            return False, "默认表（单位表/个人表）不允许删除"
        mapping = self.get_table_map()
        if name not in mapping:
            return False, f"表「{name}」不存在"
        physical = mapping[name]
        count = len(self.current_data["tables"].get(name, []))
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_tables WHERE name = ?", (name,))
            cursor.execute(f"DROP TABLE IF EXISTS {physical}")
            conn.commit()
            conn.close()
            self.current_data["tables"].pop(name, None)
            return True, f"工作表「{name}」已删除（含 {count} 条记录）"
        except Exception as e:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
            return False, f"删除失败: {str(e)}"

    def hash_password(self, password):
        """对密码进行哈希处理"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        """注册新用户"""
        if len(password) < 6:
            return False, "密码长度至少6位"

        hashed_password = self.hash_password(password)
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = None
        try:
            # 初始化数据库管理器（首次注册时创建加密配置）
            self.db_manager = DatabaseManager(password)
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO users (username, master_password, created_date, last_login)
                VALUES (?, ?, ?, ?)
            ''', (username, hashed_password, created_date, created_date))

            conn.commit()
            return True, "注册成功"
        except sqlite3.IntegrityError:
            return False, "用户名已存在"
        except Exception as e:
            return False, f"注册失败: {str(e)}"
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def login(self, username, password):
        """用户登录"""
        try:
            # 先尝试不加密连接获取用户信息
            temp_db = DatabaseManager()
            conn = temp_db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, master_password FROM users WHERE username = ?
            ''', (username,))

            result = cursor.fetchone()
            conn.close()

            if not result:
                return False, "用户不存在"

            user_id, stored_password = result

            if stored_password == self.hash_password(password):
                # 密码验证成功，使用主密码初始化数据库管理器
                self.db_manager = DatabaseManager(password)
                self.current_user = username
                self.current_user_id = user_id

                # 更新最后登录时间
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_login = ? WHERE id = ?
                ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
                conn.commit()
                conn.close()

                # 加载用户数据到内存
                self.load_user_data()
                return True, "登录成功"
            else:
                return False, "密码错误"

        except Exception as e:
            return False, f"登录失败: {str(e)}"

    def load_user_data(self):
        """加载用户数据到内存"""
        if not self.current_user_id:
            return

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            table_map = self.get_table_map()
            all_records = []
            loaded = {}

            for logical_name, physical in table_map.items():
                cursor.execute(f'''
                    SELECT id, website_name, website_url, account, password, notes,
                           network_type, verify_status, verify_time
                    FROM {physical} WHERE user_id = ? ORDER BY id
                ''', (self.current_user_id,))

                records = []
                for row in cursor.fetchall():
                    decrypted_password = self.db_manager.decrypt_password(row[4])
                    records.append({
                        "id": row[0],
                        "网站名称": row[1],
                        "网址": row[2] or "",
                        "账号": row[3],
                        "密码": decrypted_password,
                        "备注": row[5] or "",
                        "网络类型": row[6] or fallback_network_type(),
                        "网络状态": self.normalize_verify_status(row[7]),
                        "核实时间": row[8] or ""
                    })
                loaded[logical_name] = records
                all_records.extend(records)

            conn.close()

            # 更新内存中的数据（先重置，避免残留上一个账号的同名自定义表）
            self.current_data["tables"] = loaded

            # 计算下一个ID
            if all_records:
                max_id = max(record["id"] for record in all_records)
                self.current_data["next_id"] = max_id + 1
            else:
                self.current_data["next_id"] = 1

        except Exception as e:
            print(f"加载用户数据失败: {str(e)}")

    def logout(self):
        """用户注销"""
        if self.current_user:
            self.current_user = None
            self.current_user_id = None
            self.db_manager = None
            self.current_data = {
                "tables": {
                    "单位表": [],
                    "个人表": []
                },
                "next_id": 1
            }
            return True
        return False

    def change_password(self, current_password, new_password):
        """修改用户密码（完整优化版）"""
        if not self.current_user_id:
            return False, "用户未登录"

        # 验证密码强度
        strength_valid, strength_msg = self.validate_password_strength(new_password)
        if not strength_valid:
            return False, strength_msg

        # 检查新密码是否与当前密码相同
        if current_password == new_password:
            return False, "新密码不能与当前密码相同"

        try:
            # 获取数据库连接
            conn = self.get_connection()
            cursor = conn.cursor()

            # 验证当前密码
            cursor.execute('SELECT master_password FROM users WHERE id = ?', (self.current_user_id,))
            result = cursor.fetchone()

            if not result or result[0] != self.hash_password(current_password):
                conn.close()
                return False, "当前密码错误"

            # 创建新的数据库管理器实例
            new_db_manager = DatabaseManager(new_password)

            # 备份当前数据库管理器
            old_db_manager = self.db_manager

            try:
                # 开始事务
                conn.execute('BEGIN TRANSACTION')

                # 重新加密所有密码记录
                self._reencrypt_all_passwords_in_transaction(old_db_manager, new_db_manager, cursor)

                # 更新用户主密码哈希
                cursor.execute('UPDATE users SET master_password = ? WHERE id = ?',
                               (self.hash_password(new_password), self.current_user_id))

                # 提交事务
                conn.commit()

                # 更新当前数据库管理器
                self.db_manager = new_db_manager

                # 重新加载用户数据以确保一致性
                self.load_user_data()

                return True, "密码修改成功"

            except Exception as e:
                # 回滚事务
                conn.rollback()
                # 恢复原来的数据库管理器
                self.db_manager = old_db_manager
                return False, f"密码修改失败: {str(e)}"
            finally:
                conn.close()

        except Exception as e:
            return False, f"密码修改失败: {str(e)}"

    def _reencrypt_all_passwords_in_transaction(self, old_db_manager, new_db_manager, cursor):
        """在事务中重新加密所有工作表的密码记录"""
        for logical_name, physical in self.get_table_map().items():
            cursor.execute(f'SELECT id, password FROM {physical} WHERE user_id = ?',
                           (self.current_user_id,))
            rows = cursor.fetchall()

            for record_id, old_encrypted_password in rows:
                try:
                    # 使用旧密钥解密
                    decrypted_password = old_db_manager.decrypt_password(old_encrypted_password)
                    # 使用新密钥加密
                    new_encrypted_password = new_db_manager.encrypt_password(decrypted_password)

                    # 更新数据库记录
                    cursor.execute(f'UPDATE {physical} SET password = ? WHERE id = ?',
                                   (new_encrypted_password, record_id))

                except Exception as e:
                    raise Exception(f"重新加密{logical_name}记录 {record_id} 失败: {str(e)}")

    def validate_password_strength(self, password):
        """验证密码强度"""
        if len(password) < 8:
            return False, "密码长度至少8位"

        if len(password) > 128:
            return False, "密码长度不能超过128位"

        # 检查字符类型
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "密码必须包含大写字母、小写字母和数字"

        # 检查常见弱密码
        weak_passwords = [
            'password', '123456', 'qwerty', 'admin', 'welcome',
            'password123', '12345678', '123456789', '123123',
            str(self.current_user) if self.current_user else ''
        ]

        if password.lower() in weak_passwords:
            return False, "密码过于简单，请使用更复杂的密码"

        return True, "密码强度符合要求"

    def backup_data(self, backup_type="manual"):
        """备份数据到SQLite数据库"""
        if not self.current_user_id:
            return False, "用户未登录"

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if backup_type == "auto":
                backup_file = os.path.join(self.backup_dir, f"{self.current_user}_auto_{timestamp}.db")
            else:
                backup_file = os.path.join(self.backup_dir, f"{self.current_user}_manual_{timestamp}.db")

            # 创建备份数据库
            backup_conn = sqlite3.connect(backup_file)
            backup_cursor = backup_conn.cursor()

            # 复制数据（按主库实际列结构动态建备份表，兼容自定义表与新增列）
            conn = self.get_connection()
            cursor = conn.cursor()

            table_map = self.get_table_map()
            total_rows = 0
            for logical_name, physical in table_map.items():
                cursor.execute(f'SELECT * FROM {physical} WHERE user_id = ?',
                               (self.current_user_id,))
                rows = cursor.fetchall()
                cursor.execute(f'PRAGMA table_info({physical})')
                col_names = [c[1] for c in cursor.fetchall()]
                if not col_names:
                    continue

                backup_tbl = f"{physical}_backup"
                col_defs = ", ".join(f"{c} TEXT" for c in col_names)
                backup_cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS {backup_tbl} ({col_defs})")
                placeholders = ", ".join("?" for _ in col_names)
                for row in rows:
                    backup_cursor.execute(
                        f"INSERT INTO {backup_tbl} VALUES ({placeholders})", row)
                total_rows += len(rows)

            conn.close()

            # 记录备份信息
            record_count = total_rows
            backup_cursor.execute('''
                CREATE TABLE IF NOT EXISTS backup_info (
                    backup_time TEXT,
                    user_name TEXT,
                    record_count INTEGER,
                    backup_type TEXT
                )
            ''')
            backup_cursor.execute('''
                INSERT INTO backup_info VALUES (?, ?, ?, ?)
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.current_user, record_count, backup_type))

            backup_conn.commit()
            backup_conn.close()

            return True, f"备份成功: {os.path.basename(backup_file)}"
        except Exception as e:
            return False, f"备份失败: {str(e)}"

    # 其他方法保持不变...
    def verify_master_password(self, password):
        """验证主密码是否正确"""
        if not self.current_user_id:
            return False

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT master_password FROM users WHERE id = ?
            ''', (self.current_user_id,))

            result = cursor.fetchone()
            conn.close()

            return result and result[0] == self.hash_password(password)
        except Exception as e:
            return False

    def add_record(self, table_name, record_data):
        """添加新记录"""
        if not self.current_user_id:
            return False

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 加密密码
            encrypted_password = self.db_manager.encrypt_password(record_data["密码"])
            network_type = record_data.get("网络类型", "")
            tbl = self.get_table_map().get(table_name)
            if tbl is None:
                print(f"添加记录失败: 表「{table_name}」不存在")
                return False

            cursor.execute(f'''
                INSERT INTO {tbl}
                (user_id, website_name, website_url, account, password, notes, network_type, created_time, updated_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.current_user_id,
                record_data["网站名称"],
                record_data["网址"],
                record_data["账号"],
                encrypted_password,
                record_data["备注"],
                network_type,
                current_time,
                current_time
            ))

            conn.commit()
            record_id = cursor.lastrowid
            conn.close()

            # 更新内存数据
            record_data["id"] = record_id
            self.current_data["tables"][table_name].append(record_data)
            self.current_data["next_id"] = max(self.current_data["next_id"], record_id + 1)

            return True
        except Exception as e:
            print(f"添加记录失败: {str(e)}")
            return False

    def update_record(self, table_name, record_id, new_data):
        """更新记录"""
        if not self.current_user_id:
            return False

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 加密密码
            encrypted_password = self.db_manager.encrypt_password(new_data["密码"])
            network_type = new_data.get("网络类型", "")
            tbl = self.get_table_map().get(table_name)
            if tbl is None:
                print(f"更新记录失败: 表「{table_name}」不存在")
                return False

            cursor.execute(f'''
                UPDATE {tbl} SET
                website_name = ?, website_url = ?, account = ?, password = ?, notes = ?, network_type = ?, updated_time = ?
                WHERE id = ? AND user_id = ?
            ''', (
                new_data["网站名称"],
                new_data["网址"],
                new_data["账号"],
                encrypted_password,
                new_data["备注"],
                network_type,
                current_time,
                record_id,
                self.current_user_id
            ))

            conn.commit()
            conn.close()

            # 更新内存数据
            for record in self.current_data["tables"][table_name]:
                if record["id"] == record_id:
                    record.update(new_data)
                    break

            return True
        except Exception as e:
            print(f"更新记录失败: {str(e)}")
            return False

    def update_network_type(self, table_name, record_id, new_type):
        """只更新单条记录的网络类型（不触碰密码及其他任何字段）。
        返回 (ok, old_type)：old_type 供界面弹出「从X改为Y」确认提示。"""
        if not self.current_user_id:
            return False, ""
        tbl = self.get_table_map().get(table_name)
        if tbl is None:
            return False, ""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            # 只读取 network_type 这一列
            cursor.execute(
                f"SELECT network_type FROM {tbl} WHERE id = ? AND user_id = ?",
                (record_id, self.current_user_id))
            row = cursor.fetchone()
            if not row:
                return False, ""
            old_type = row[0] or ""
            if old_type == new_type:
                return True, old_type  # 无变化，不写库
            # 只更新 network_type 这一列
            cursor.execute(
                f"UPDATE {tbl} SET network_type = ? WHERE id = ? AND user_id = ?",
                (new_type, record_id, self.current_user_id))
            conn.commit()
            # 同步内存
            for record in self.current_data["tables"].get(table_name, []):
                if record["id"] == record_id:
                    record["网络类型"] = new_type
                    break
            return True, old_type
        except Exception as e:
            print(f"更新网络类型失败: {str(e)}")
            return False, ""
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def delete_record(self, table_name, record_id):
        """删除记录"""
        if not self.current_user_id:
            return False

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            tbl = self.get_table_map().get(table_name)
            if tbl is None:
                print(f"删除记录失败: 表「{table_name}」不存在")
                return False
            cursor.execute(f'''
                DELETE FROM {tbl} WHERE id = ? AND user_id = ?
            ''', (record_id, self.current_user_id))

            conn.commit()
            conn.close()

            # 更新内存数据
            self.current_data["tables"][table_name] = [
                record for record in self.current_data["tables"][table_name]
                if record["id"] != record_id
            ]

            return True
        except Exception as e:
            print(f"删除记录失败: {str(e)}")
            return False

    def move_record(self, from_table, record_id, to_table):
        """在任意两个工作表之间迁移记录（原子操作：先插入目标表再删源表，失败自动回滚）"""
        if not self.current_user_id:
            return False, "用户未登录"
        table_map = self.get_table_map()
        if from_table not in table_map or to_table not in table_map:
            return False, "表名不合法"
        if from_table == to_table:
            return False, "源表与目标表相同"

        src = table_map[from_table]
        dst = table_map[to_table]

        record = next((r for r in self.current_data["tables"][from_table]
                       if r["id"] == record_id), None)
        if record is None:
            return False, "未找到要迁移的记录"

        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            encrypted_password = self.db_manager.encrypt_password(record["密码"])

            cursor.execute(f'''
                INSERT INTO {dst}
                (user_id, website_name, website_url, account, password, notes, network_type, created_time, updated_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.current_user_id,
                record["网站名称"],
                record["网址"],
                record["账号"],
                encrypted_password,
                record["备注"],
                record.get("网络类型", ""),
                current_time,
                current_time
            ))
            new_id = cursor.lastrowid
            cursor.execute(f'DELETE FROM {src} WHERE id = ? AND user_id = ?',
                           (record_id, self.current_user_id))
            conn.commit()

            # 更新内存数据
            moved = dict(record)
            moved["id"] = new_id
            self.current_data["tables"][from_table] = [
                r for r in self.current_data["tables"][from_table] if r["id"] != record_id
            ]
            self.current_data["tables"][to_table].append(moved)

            return True, f"已迁移「{record['网站名称']}」: {from_table} → {to_table}"
        except Exception as e:
            # 未 commit 的变更会在连接关闭时自动回滚，源表数据不受影响
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False, f"迁移失败: {str(e)}"
        finally:
            if conn is not None:
                conn.close()

    def reassign_network_type(self, old_type, new_type):
        """删除某网络类型后，把所有使用 old_type 的记录改挂到 new_type（库+内存同步）"""
        if not self.current_user_id:
            return 0
        changed = 0
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            table_map = self.get_table_map()
            for table_name, tbl in table_map.items():
                for record in self.current_data["tables"][table_name]:
                    if record.get("网络类型") == old_type:
                        record["网络类型"] = new_type
                        cursor.execute(f'''
                            UPDATE {tbl} SET network_type = ?, updated_time = ?
                            WHERE id = ? AND user_id = ?
                        ''', (new_type, current_time, record["id"], self.current_user_id))
                        changed += 1
            if changed:
                conn.commit()
        except Exception as e:
            print(f"回落网络类型失败: {str(e)}")
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn is not None:
                conn.close()
        return changed

    @staticmethod
    def normalize_verify_status(status):
        """把任意核实结果归一为两态：可访问 / 不可访问。
        空值（未核实/不核实）保持空，界面显示为「—」。
        注意：必须先判「不可访问」，因为其中包含「可访问」三字。"""
        s = (status or "").strip()
        if not s or s in ("—", "-", "未核实", "不核实"):
            return ""
        if "不可访问" in s or "不访问" in s:
            return "不可访问"
        if "可访问" in s:
            return "可访问"
        # 其余任何文字（超时/无法解析/SSL错误/WinError 等）一律算不可访问
        return "不可访问"

    def update_verify_status(self, table_name, record_id, status, verify_time):
        """写入单条记录的核实结果（库+内存同步）。
        状态会归一为两态：可访问 / 不可访问（空=未核实）。
        verify_time: "MM-dd HH:mm" 格式字符串，传空则不更新时间
        """
        if not self.current_user_id:
            return False
        tbl = self.get_table_map().get(table_name)
        if tbl is None:
            return False
        status = self.normalize_verify_status(status)
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE {tbl} SET verify_status = ?, verify_time = ?
                WHERE id = ? AND user_id = ?
            ''', (status, verify_time, record_id, self.current_user_id))
            conn.commit()

            # 同步内存
            for record in self.current_data["tables"].get(table_name, []):
                if record["id"] == record_id:
                    record["网络状态"] = status
                    if verify_time:
                        record["核实时间"] = verify_time
                    break
            return True
        except Exception as e:
            print(f"写入核实状态失败: {str(e)}")
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            if conn is not None:
                conn.close()

    def search_records(self, table_name, search_term, search_field="所有字段"):
        """搜索记录"""
        if not search_term:
            return self.current_data["tables"][table_name]

        results = []
        for record in self.current_data["tables"][table_name]:
            if search_field != "所有字段":
                field_value = record.get(search_field, "")
                if search_term.lower() in str(field_value).lower():
                    results.append(record)
            else:
                for value in record.values():
                    if search_term.lower() in str(value).lower():
                        results.append(record)
                        break
        return results

    def import_from_excel(self, file_path, target_table, sheet_name=None):
        """从Excel/CSV文件导入数据到指定表"""
        if not self.current_user_id:
            return False, "用户未登录"

        if target_table not in self.get_table_map():
            return False, f"目标表「{target_table}」不存在"

        try:
            df = _read_import_dataframe(file_path, sheet_name)

            if df.empty:
                return False, "文件为空或没有数据"

            field_mapping = {
                '网站名称': ['网站名称', '网站名', '网站', '名称', '站点名称', '平台名称'],
                '网址': ['网址', '网站地址', 'URL', '链接', '地址', '网站链接'],
                '账号': ['账号', '账户', '用户名', '用户', '登录名', '用户账号'],
                '密码': ['密码', '登陆密码', '登录密码', 'pass', 'passwd'],
                '备注': ['备注', '说明', '注释', '描述', 'note', 'description'],
                '网络类型': ['网络类型', '类型', '网络']
            }

            actual_mapping = {}
            for target_field, possible_names in field_mapping.items():
                for col in df.columns:
                    if any(name in str(col) for name in possible_names):
                        actual_mapping[target_field] = col
                        break
                else:
                    actual_mapping[target_field] = None

            imported_count = 0
            skipped_count = 0
            error_count = 0

            for index, row in df.iterrows():
                try:
                    website_name = row[actual_mapping['网站名称']] if actual_mapping['网站名称'] is not None else ""
                    website_url = row[actual_mapping['网址']] if actual_mapping['网址'] is not None else ""
                    account = row[actual_mapping['账号']] if actual_mapping['账号'] is not None else ""
                    password = row[actual_mapping['密码']] if actual_mapping['密码'] is not None else ""
                    notes = row[actual_mapping['备注']] if actual_mapping['备注'] is not None else ""
                    network_type = row[actual_mapping['网络类型']] if actual_mapping['网络类型'] is not None else ""

                    website_name = str(website_name).strip() if pd.notna(website_name) else ""
                    website_url = str(website_url).strip() if pd.notna(website_url) else ""
                    account = str(account).strip() if pd.notna(account) else ""
                    password = str(password).strip() if pd.notna(password) else ""
                    notes = str(notes).strip() if pd.notna(notes) else ""
                    network_type = str(network_type).strip() if pd.notna(network_type) else ""

                    if not website_name and not account:
                        skipped_count += 1
                        continue

                    record_data = {
                        "网站名称": website_name,
                        "网址": website_url,
                        "账号": account,
                        "密码": password,
                        "备注": notes,
                        "网络类型": network_type
                    }

                    if self.add_record(target_table, record_data):
                        imported_count += 1
                    else:
                        error_count += 1
                        skipped_count += 1

                except Exception as e:
                    error_count += 1
                    skipped_count += 1
                    continue

            return True, f"导入完成：成功导入 {imported_count} 条记录，跳过 {skipped_count} 条记录，错误 {error_count} 条记录"

        except Exception as e:
            return False, f"导入失败: {str(e)}"
