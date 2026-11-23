# -*- coding: utf-8 -*-
"""全局配置与本地存储：路径、配置读写、记住账号密码。"""
import os
import sys
import json
import base64
from Crypto.Cipher import AES

from .crypto import DatabaseEncryption

# 基础目录：
#   打包后（frozen）指向 exe 所在目录；
#   开发时指向项目根目录（src 的父目录），使 resources / 数据库 / 配置文件
#   统一落在项目根，便于开发与发布保持一致。
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ===== 空闲自动锁定配置 =====
CONFIG_FILE = os.path.join(BASE_DIR, "mx_config.json")
DEFAULT_IDLE_MINUTES = 5


def load_config():
    """读取本地配置，缺失或异常时返回空字典"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    """写入本地配置"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ===== 网络类型字典（默认预置「互联网 / 内网」，用户可在界面里增删）=====
DEFAULT_NETWORK_TYPES = ["互联网", "内网"]


def load_network_types():
    """读取网络类型列表；旧配置缺失或为空时自动补默认两项并写回"""
    cfg = load_config()
    types = cfg.get("network_types")
    cleaned = []
    if isinstance(types, list):
        for t in types:
            if isinstance(t, str) and t.strip() and t.strip() not in cleaned:
                cleaned.append(t.strip())
    if not cleaned:
        cleaned = list(DEFAULT_NETWORK_TYPES)
        save_network_types(cleaned)
    return cleaned


def save_network_types(types):
    """保存网络类型列表到配置"""
    cfg = load_config()
    cfg["network_types"] = [t for t in types if isinstance(t, str) and t.strip()]
    save_config(cfg)


# ===== 功能栏排序（默认方案：高频CRUD → 核实 → 数据流转 → 分享）=====
DEFAULT_TOOLBAR_ORDER = [
    "add", "view_password", "edit", "delete", "refresh",
    "verify", "verify_all",
    "import", "export", "move",
    "share",
]


def load_toolbar_order():
    """读取功能栏顺序；去重、过滤非法 key，并补齐新增按钮（兼容旧配置）"""
    cfg = load_config()
    saved = cfg.get("toolbar_order")
    cleaned = []
    if isinstance(saved, list):
        for k in saved:
            if k in DEFAULT_TOOLBAR_ORDER and k not in cleaned:
                cleaned.append(k)
    # 旧配置没存过 / 后续新增按钮：用默认顺序补齐
    for k in DEFAULT_TOOLBAR_ORDER:
        if k not in cleaned:
            cleaned.append(k)
    return cleaned


def save_toolbar_order(order):
    """保存功能栏顺序到配置"""
    cfg = load_config()
    cfg["toolbar_order"] = [k for k in order if k in DEFAULT_TOOLBAR_ORDER]
    save_config(cfg)


def fallback_network_type(types=None):
    """删除某类型后记录的回落类型：优先「内网」，其次列表第一个，全空则留空"""
    types = types if types is not None else load_network_types()
    if "内网" in types:
        return "内网"
    return types[0] if types else ""


# ===== 记住账号密码（本地 AES-GCM 加密存储，非明文）=====
REMEMBER_FILE = os.path.join(BASE_DIR, "remember.json")
_REMEMBER_PASSPHRASE = "MoxiangLocalRemember_v1"
_REMEMBER_SALT = b"moxiang_remember_salt_2026"


def _remember_key():
    key, _ = DatabaseEncryption.derive_key(_REMEMBER_PASSPHRASE, _REMEMBER_SALT)
    return key


def save_remembered(username, remember_pwd=False, master_password=None):
    """保存记住的账号；remember_pwd=True 且提供密码时才连带加密保存密码。
    只记账号时密码字段留空（has_pwd=False），下次登录密码框为空。"""
    try:
        data = {"username": username, "has_pwd": False, "nonce": "", "cipher": ""}
        if remember_pwd and master_password:
            key = _remember_key()
            cipher = AES.new(key, AES.MODE_GCM)
            token = cipher.encrypt(master_password.encode("utf-8"))
            data["has_pwd"] = True
            data["nonce"] = base64.b64encode(cipher.nonce).decode()
            data["cipher"] = base64.b64encode(token).decode()
        with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def load_remembered():
    """返回 (username, password_or_None)。
    - 无记录 -> (None, None)
    - 只记账号 -> (username, None)
    - 同时记密码 -> (username, password)
    """
    try:
        if not os.path.exists(REMEMBER_FILE):
            return None, None
        with open(REMEMBER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        uname = data.get("username") or None
        if not data.get("has_pwd"):
            return uname, None
        key = _remember_key()
        nonce = base64.b64decode(data["nonce"])
        token = base64.b64decode(data["cipher"])
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        pwd = cipher.decrypt(token).decode("utf-8")
        return uname, pwd
    except Exception:
        return None, None


def clear_remembered():
    """清除记住的账号密码"""
    try:
        if os.path.exists(REMEMBER_FILE):
            os.remove(REMEMBER_FILE)
    except Exception:
        pass
