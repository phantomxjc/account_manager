# -*- coding: utf-8 -*-
"""墨香密码管理器 - PyInstaller 打包启动入口。

本文件刻意放在包外（src/ 根目录），只做一件事：导入 moxiang 包并调用 main()。
原因：PyInstaller 会把本文件作为顶层脚本运行（__name__ == "__main__"，没有父包上下文），
而 moxiang 内部各模块使用的相对导入（from .xxx import ...）只有在「以包方式导入」时才能解析。
通过 `from moxiang.app import main` 进入包，所有相对导入即可正常工作。
"""
from moxiang.app import main

if __name__ == "__main__":
    main()
