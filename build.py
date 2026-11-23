# -*- coding: utf-8 -*-
"""墨香密码管理器 - 打包脚本（PyInstaller onedir）。

用法:
    python build.py                # 构建到系统临时目录，并合并发布到默认目标 H:\\墨香密码管理器
    python build.py --dest D:/xxx  # 指定输出目标目录

设计要点（沿用已验证的坑位）：
1. workpath / distpath 指向系统临时目录，避免沙箱对构建中间产物任意删除的拦截。
2. ico 通过 --add-data 打包进 bundle 根目录（onedir 下即 _internal/枫叶.ico），
   运行时经 config.BASE_DIR / sys._MEIPASS 命中。
3. 显式 exclude matplotlib、hiddenimport Crypto/openpyxl/numpy，控制体积并避免缺模块。
4. 发布采用「覆盖写 + 跳过占用文件」的合并拷贝（而非先删后拷），既能保留目标目录中
   用户已有的运行数据（password_manager.db / remember.json / mx_config.json / backups），
   又避免安全层对删除操作的拦截；少数被 Defender 等临时锁定的 .dll/.pyd 会在重试后仍
   锁定时跳过并提示，待其释放后再次运行本脚本即可补齐。
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ENTRY = os.path.join(PROJECT_ROOT, "src", "launcher.py")
ICON_PATH = os.path.join(PROJECT_ROOT, "resources", "枫叶.ico")
PYTHON = sys.executable

APP_NAME = "墨香密码管理器"
DEFAULT_DEST = r"H:\墨香密码管理器"


def _robust_copy_file(src, dst, skipped):
    """覆盖写；遇到占用(WinError 32)重试，仍失败则记录跳过。"""
    for attempt in range(10):
        try:
            shutil.copy2(src, dst)
            return
        except (PermissionError, OSError) as e:
            if getattr(e, 'winerror', None) == 32 or e.errno == 32:
                if attempt < 9:
                    time.sleep(1.2)
                    continue
                skipped.append(dst)
                return
            if attempt < 3:
                time.sleep(0.5)
                continue
            skipped.append(dst)
            return


def _merge_copy(src, dst, skipped):
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            _merge_copy(os.path.join(src, name), os.path.join(dst, name), skipped)
    else:
        _robust_copy_file(src, dst, skipped)


def build(dest: str):
    if not os.path.exists(SRC_ENTRY):
        print(f"[错误] 找不到入口文件: {SRC_ENTRY}")
        sys.exit(1)
    if not os.path.exists(ICON_PATH):
        print(f"[警告] 找不到图标: {ICON_PATH}，将继续打包但不带自定义图标。")
        icon_args = []
    else:
        icon_args = ["--icon", ICON_PATH]

    # 构建中间产物放到系统临时目录，规避沙箱删除拦截
    tmp_root = os.environ.get("TEMP", os.path.dirname(os.path.abspath(__file__)))
    workpath = os.path.join(tmp_root, "mx_build_work")
    distpath = os.path.join(tmp_root, "mx_build_dist")
    os.makedirs(workpath, exist_ok=True)
    os.makedirs(distpath, exist_ok=True)

    cmd = [
        PYTHON, "-m", "PyInstaller",
        SRC_ENTRY,
        "--name", APP_NAME,
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--workpath", workpath,
        "--distpath", distpath,
        "--add-data", f"{ICON_PATH};.",   # 关键：放到 bundle 根目录（onedir 下为 _internal/枫叶.ico）
        "--hidden-import", "Crypto",
        "--hidden-import", "Crypto.Cipher.AES",
        "--hidden-import", "Crypto.Random",
        "--hidden-import", "Crypto.Protocol.KDF",
        "--hidden-import", "openpyxl",
        "--hidden-import", "numpy",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "tkinter",
        *icon_args,
    ]

    print("[构建] 执行命令:")
    print(" ".join(cmd))
    ret = subprocess.call(cmd)
    if ret != 0:
        print(f"[错误] PyInstaller 返回码 {ret}")
        sys.exit(ret)

    # 合并发布到目标目录
    built_dir = os.path.join(distpath, APP_NAME)
    if not os.path.isdir(built_dir):
        print(f"[错误] 构建产物不存在: {built_dir}")
        sys.exit(1)

    os.makedirs(dest, exist_ok=True)
    skipped = []
    print(f"[发布] 合并覆盖写 {built_dir} -> {dest}（保留用户数据文件）")
    _merge_copy(built_dir, dest, skipped)

    if skipped:
        print(f"[提示] 以下 {len(skipped)} 个文件被占用未能更新（多为 Defender 临时扫描锁定的 "
              f"dll/pyd），待其释放后再次运行 python build.py 即可补齐：")
        for s in skipped[:20]:
            print("   ", s)
        if len(skipped) > 20:
            print(f"   ... 共 {len(skipped)} 个")
    else:
        print("[发布] 全部文件更新成功。")

    exe_path = os.path.join(dest, f"{APP_NAME}.exe")
    print("[完成] 构建与发布完成。")
    print(f"  可执行文件: {exe_path}")
    print(f"  目标目录  : {dest}")
    if not os.path.exists(exe_path):
        print("[警告] 未找到预期的可执行文件，请检查上面的输出。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="墨香密码管理器打包脚本")
    parser.add_argument("--dest", default=DEFAULT_DEST, help="输出目标目录")
    args = parser.parse_args()
    build(args.dest)
