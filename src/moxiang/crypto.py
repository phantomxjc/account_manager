# -*- coding: utf-8 -*-
"""数据库加密管理器（AES-GCM）。"""
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2


class DatabaseEncryption:
    """数据库加密管理器（优化版）"""

    @staticmethod
    def derive_key(master_password: str, salt: bytes = None) -> tuple:
        """从主密码派生加密密钥"""
        if salt is None:
            salt = get_random_bytes(16)

        # 使用PBKDF2派生密钥，增加迭代次数提高安全性
        key = PBKDF2(master_password, salt, 32, count=1000000)  # 增加到100万次迭代
        return key, salt

    @staticmethod
    def encrypt_data(data: str, key: bytes) -> str:
        """加密数据"""
        # 对数据进行UTF-8编码前的验证
        try:
            data.encode('utf-8')
        except UnicodeEncodeError:
            raise ValueError("数据包含无效的UTF-8字符")

        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(data.encode('utf-8'))
        encrypted_data = base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')
        return encrypted_data

    @staticmethod
    def decrypt_data(encrypted_data: str, key: bytes) -> str:
        """解密数据"""
        try:
            data = base64.b64decode(encrypted_data.encode('utf-8'))
            if len(data) < 32:  # nonce(16) + tag(16) 至少需要32字节
                raise ValueError("加密数据长度不足")

            nonce = data[:16]
            tag = data[16:32]
            ciphertext = data[32:]

            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")
