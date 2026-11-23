# 墨香密码管理器（Moxiang Password Manager）

一个基于 PyQt5 的**本地**密码管理器，采用「主密码 + PBKDF2 + AES-GCM」加密存储，支持单位表 / 个人表双库管理、网络类型标注、网站可达性核实、Excel 导入导出、空闲自动锁定等功能。本项目由早期单文件脚本重构而来，采用标准项目架构。

> 数据全部保存在本地（exe 同目录或项目根目录），不上传云端、不联网传输密码。

## 功能特性

- 🔐 **加密存储**：PBKDF2（100 万次迭代）派生密钥 + AES-GCM 认证加密，主密码不落盘
- 📝 **双表管理**：单位表 / 个人表独立增删改查与搜索，支持记录互迁
- 🌐 **网络类型**：每条记录标注「互联网 / 政务外网 / 内网」等类型，类型可自定义管理，单元格双击下拉切换
  - 内置识别规则：`10.x`、`172.16~31.x`、`.gov.cn`、`zwfw` → 政务外网；`192.168.x` → 家用网络；DNS 解析失败 → 内网；其余 → 互联网
- 🔎 **网站核实**：单条 / 批量探测网址可达性，状态列以 🟢 可访问 / 🔴 不可访问 圆点呈现
- 🧰 **强密码生成器**：一键生成高强度随机密码
- ⏲ **空闲自动锁定**：锁定时间可在「欢迎，主人」右键菜单配置；锁定后隐藏主窗，双击托盘才弹登录
- 📤 **数据导出**：Excel / CSV 明文导出（需主密码授权），支持勾选记录导出
- 📥 **数据导入**：Excel / CSV 导入，字段自动映射
- 💾 **记住账号**：默认只记账号；勾选后可记密码，仍以 AES-GCM 加密保存
- 🖥 **系统托盘 + 单实例**：常驻托盘、单实例运行、高 DPI 适配
- 🎨 **中国风界面**：朱红 / 米色配色，统一弹窗样式与中式菱形装饰线，功能栏顺序可自定义

## 项目结构

```
墨香密码管理器/
├── build.py                  # PyInstaller onedir 打包脚本
├── requirements.txt          # 依赖清单
├── resources/
│   └── 枫叶.ico              # 应用图标
└── src/
    ├── launcher.py           # 冻结入口（非包脚本，避免相对导入问题）
    └── moxiang/              # 主包
        ├── __init__.py       # 版本 / 元信息
        ├── __main__.py       # `python -m moxiang` 入口
        ├── app.py            # ApplicationController + main()
        ├── config.py         # 路径 / 配置读写 / 网络类型 / 工具栏排序
        ├── crypto.py         # 密钥派生与加解密
        ├── database.py       # 数据访问层（含迁移 / 互迁 / 核实状态）
        ├── netcheck.py       # 网址 / IP 识别与可达性探测
        ├── style.py          # 中国风样式与自绘控件
        ├── icon.py           # 应用图标加载
        ├── single_app.py     # 单实例应用
        └── ui/
            ├── dialogs.py        # 所有对话框 + 导入线程
            ├── login_window.py
            └── main_window.py
```

运行时会在 exe 同级目录（或开发时项目根目录）生成 `password_manager.db`、`mx_config.json`、`remember.json`、`backups/`。**这些文件包含个人数据，已加入 `.gitignore`，不会进入版本库。**

## 开发运行

```bash
pip install -r requirements.txt
python -m moxiang
# 或
python src/launcher.py
```

## 打包为 exe

```bash
pip install -r requirements.txt
python build.py                 # 默认输出到 H:\墨香密码管理器
python build.py --dest D:\path  # 自定义输出目录
```

打包产物为 onedir（文件夹），入口 `墨香密码管理器.exe`，可直接双击运行。

## 版本

当前版本 `2.4.0`。
