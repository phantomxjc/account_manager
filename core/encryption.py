# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 加密模块
提供 AES-GCM 对称加密 / 解密 和 PBKDF2 密钥派生
"""

import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2

import config


class DatabaseEncryption:
    """数据库加密管理器（AES-GCM + PBKDF2）"""

    @staticmethod
    def derive_key(master_password: str, salt: bytes = None) -> tuple:
        """
        从主密码派生加密密钥
        返回: (key: bytes, salt: bytes)
        """
        if salt is None:
            salt = get_random_bytes(config.SALT_LENGTH)

        key = PBKDF2(
            master_password,
            salt,
            config.KEY_LENGTH,
            count=config.PBKDF2_ITERATIONS
        )
        return key, salt

    @staticmethod
    def encrypt_data(data: str, key: bytes) -> str:
        """
        使用 AES-GCM 加密字符串
        返回: base64 编码的 "nonce + tag + ciphertext"
        """
        try:
            data.encode('utf-8')
        except UnicodeEncodeError:
            raise ValueError("数据包含无效的 UTF-8 字符")

        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(data.encode('utf-8'))

        # 拼接 nonce + tag + ciphertext 后 base64 编码
        encrypted_blob = cipher.nonce + tag + ciphertext
        return base64.b64encode(encrypted_blob).decode('utf-8')

    @staticmethod
    def decrypt_data(encrypted_data: str, key: bytes) -> str:
        """
        使用 AES-GCM 解密字符串
        输入: base64 编码的 "nonce + tag + ciphertext"
        返回: 明文字符串
        """
        try:
            raw = base64.b64decode(encrypted_data.encode('utf-8'))
        except Exception:
            raise ValueError("加密数据 base64 解码失败")

        min_len = config.GCM_NONCE_LENGTH + config.GCM_TAG_LENGTH  # 32 字节
        if len(raw) < min_len:
            raise ValueError("加密数据长度不足")

        nonce = raw[:config.GCM_NONCE_LENGTH]
        tag = raw[config.GCM_NONCE_LENGTH:config.GCM_TAG_LENGTH + config.GCM_NONCE_LENGTH]
        ciphertext = raw[config.GCM_NONCE_LENGTH + config.GCM_TAG_LENGTH:]

        try:
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext.decode('utf-8')
        except ValueError as e:
            raise ValueError(f"解密验证失败（数据可能被篡改）: {e}")
        except Exception as e:
            raise ValueError(f"解密失败: {e}")
