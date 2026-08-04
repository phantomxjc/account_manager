# 墨香密码管理器 v2.0

一款基于 PyQt5 开发的本地桌面密码管理器，采用中国风 UI 设计，AES-GCM 加密存储。

## 项目结构

```
墨香密码管理器/
├── main.py                  # 程序入口
├── config.py                # 全局配置（路径、常量、版本号）
├── core/                    # 核心业务逻辑
│   ├── __init__.py
│   ├── encryption.py        # 加密/解密（AES-GCM + PBKDF2）
│   ├── database.py          # 数据库管理（SQLite + 表初始化）
│   ├── password_manager.py  # 密码管理核心逻辑（CRUD/导入/备份/改密）
│   └── excel_import.py      # Excel 导入线程与字段映射
├── ui/                      # 界面层
│   ├── __init__.py
│   ├── style.py             # 中国风样式（配色/字体/渐变按钮）
│   ├── login_window.py      # 登录/注册窗口
│   ├── main_window.py       # 主窗口（表格/搜索/右键菜单）
│   ├── dialogs.py           # 所有对话框（新增/编辑/查看/分享/导入）
│   └── change_password_dialog.py  # 修改密码对话框
├── system/                  # 系统级功能
│   ├── __init__.py
│   ├── single_app.py        # 单实例控制（QSharedMemory）
│   ├── tray_icon.py         # 系统托盘管理
│   └── security_dialog.py   # 安全验证对话框（复用）
├── assets/                  # 静态资源
│   └── 枫叶.png            # 程序图标
├── backups/                 # 自动创建的备份目录
└── requirements.txt         # Python 依赖
```

## 快速启动

```bash
pip install -r requirements.txt
python main.py
```

## 功能一览

- 🔐 主密码 + AES-GCM 加密存储
- 📂 单位表 / 个人表分类管理
- 📥 Excel 批量导入（智能字段映射）
- 💾 本地数据库备份
- 🖱️ 双击网址自动打开浏览器
- 📋 一键分享/复制账号信息
- 🔒 敏感操作需二次验证主密码
- 🔄 单实例运行 + 系统托盘最小化
- 🔑 修改主密码自动重加密全部数据

## 技术栈

- Python 3.8+
- PyQt5（GUI）
- SQLite（本地存储）
- pycryptodome（AES-GCM 加密）
- pandas + openpyxl（Excel 导入）
