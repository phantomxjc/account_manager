# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 中国风样式
集中管理配色、字体、渐变按钮等 UI 风格
"""

from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
from PyQt5.QtCore import Qt

import config


# ==================== 配色常量 ====================

COLOR_BG_WINDOW      = QColor(250, 245, 235)   # 米白背景
COLOR_BG_BASE        = QColor(255, 253, 248)   # 浅米色基础
COLOR_BG_ALT         = QColor(245, 240, 230)   # 交替行
COLOR_TEXT_PRIMARY    = QColor(101, 67, 33)     # 深棕文字
COLOR_TEXT_SECONDARY  = QColor(140, 120, 83)    # 次要文字
COLOR_BORDER         = QColor(217, 199, 167)    # 边框
COLOR_ACCENT_RED     = QColor(166, 77, 55)     # 朱红强调
COLOR_BTN_BRONZE     = QColor(180, 150, 100)   # 古铜按钮
COLOR_BTN_HOVER      = QColor(180, 93, 71)     # 按钮悬停
COLOR_BTN_PRESSED    = QColor(149, 69, 47)      # 按钮按下
COLOR_BTN_GRAY       = QColor(140, 120, 83)     # 灰色按钮
COLOR_BTN_GRAY_HOVER = QColor(168, 150, 122)   # 灰色按钮悬停

GRADIENT_START = "#A64D37"
GRADIENT_END   = "#C46C4E"


# ==================== 应用程序级样式 ====================

def setup_app_style(app):
    """设置全局字体 + Fusion 调色板"""
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.Window,         COLOR_BG_WINDOW)
    pal.setColor(QPalette.WindowText,     COLOR_TEXT_PRIMARY)
    pal.setColor(QPalette.Base,          COLOR_BG_BASE)
    pal.setColor(QPalette.AlternateBase, COLOR_BG_ALT)
    pal.setColor(QPalette.ToolTipBase,   COLOR_BG_BASE)
    pal.setColor(QPalette.ToolTipText,   COLOR_TEXT_PRIMARY)
    pal.setColor(QPalette.Text,          COLOR_TEXT_PRIMARY)
    pal.setColor(QPalette.Button,        COLOR_BTN_BRONZE)
    pal.setColor(QPalette.ButtonText,    COLOR_BG_WINDOW)
    pal.setColor(QPalette.BrightText,    Qt.red)
    pal.setColor(QPalette.Link,          COLOR_ACCENT_RED)
    pal.setColor(QPalette.Highlight,     COLOR_ACCENT_RED)
    pal.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(pal)


# ==================== 渐变按钮 ====================

def create_gradient_button(text: str, width: int = 120, height: int = 40,
                           color1: str = GRADIENT_START,
                           color2: str = GRADIENT_END) -> 'QPushButton':
    """创建中国风渐变圆角按钮"""
    from PyQt5.QtWidgets import QPushButton

    btn = QPushButton(text)
    btn.setFixedSize(width, height)
    btn.setProperty("chineseStyle", True)
    btn.setStyleSheet(f"""
        QPushButton[chineseStyle="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 {color1}, stop:1 {color2});
            color: white;
            border-radius: {height // 2}px;
            font-weight: bold;
            font-family: "Microsoft YaHei";
            font-size: 14px;
        }}
        QPushButton[chineseStyle="true"]:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #B45D47, stop:1 #D47C5E);
        }}
        QPushButton[chineseStyle="true"]:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #95452F, stop:1 #B45D47);
        }}
    """)
    return btn


# ==================== 通用样式片段（供其他模块引用） ====================

STYLE_GROUP_BOX = f"""
    QGroupBox {{
        border: 1px solid {COLOR_BORDER.name()};
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 10px;
        font-family: "Microsoft YaHei";
        color: {COLOR_TEXT_PRIMARY.name()};
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
    }}
"""

STYLE_LINE_EDIT = f"""
    QLineEdit {{
        border: 1px solid {COLOR_BORDER.name()};
        border-radius: 5px;
        padding: 5px;
        font-family: "Microsoft YaHei";
        background-color: {COLOR_BG_BASE.name()};
        color: {COLOR_TEXT_PRIMARY.name()};
    }}
    QLineEdit:focus {{
        border: 1px solid {COLOR_ACCENT_RED.name()};
    }}
"""

STYLE_COMBO_BOX = f"""
    QComboBox {{
        border: 1px solid {COLOR_BORDER.name()};
        border-radius: 5px;
        padding: 5px;
        font-family: "Microsoft YaHei";
        min-width: 100px;
        background-color: {COLOR_BG_BASE.name()};
        color: {COLOR_TEXT_PRIMARY.name()};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
"""

STYLE_TABLE_WIDGET = f"""
    QTableWidget {{
        border: 1px solid {COLOR_BORDER.name()};
        border-radius: 5px;
        background-color: {COLOR_BG_BASE.name()};
        alternate-background-color: {COLOR_BG_ALT.name()};
        font-family: "Microsoft YaHei";
        gridline-color: {COLOR_BORDER.name()};
    }}
    QTableWidget::item {{
        padding: 5px;
        border-bottom: 1px solid #E8E0D0;
    }}
    QTableWidget::item:selected {{
        background-color: #E8D0B0;
        color: {COLOR_TEXT_PRIMARY.name()};
    }}
    QHeaderView::section {{
        background-color: {COLOR_BORDER.name()};
        color: {COLOR_TEXT_PRIMARY.name()};
        font-weight: bold;
        padding: 5px;
        border: none;
        font-family: "Microsoft YaHei";
    }}
"""

STYLE_TEXT_EDIT = f"""
    QTextEdit {{
        border: 1px solid {COLOR_BORDER.name()};
        border-radius: 5px;
        padding: 5px;
        font-family: "Microsoft YaHei";
        background-color: {COLOR_BG_BASE.name()};
        color: {COLOR_TEXT_PRIMARY.name()};
    }}
"""

STYLE_PROGRESS_BAR = f"""
    QProgressBar {{
        border: 1px solid {COLOR_BORDER.name()};
        border-radius: 5px;
        text-align: center;
        font-family: "Microsoft YaHei";
        color: {COLOR_TEXT_PRIMARY.name()};
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {GRADIENT_START}, stop:1 {GRADIENT_END});
        border-radius: 3px;
    }}
"""

STYLE_SECONDARY_BUTTON = f"""
    QPushButton {{
        background: {COLOR_BTN_GRAY.name()};
        color: white;
        border-radius: 5px;
        font-family: "Microsoft YaHei";
        font-size: 12px;
    }}
    QPushButton:hover {{
        background: {COLOR_BTN_GRAY_HOVER.name()};
    }}
"""

STYLE_LABEL_TITLE = f"""
    QLabel {{
        font-size: 18px;
        font-weight: bold;
        color: {COLOR_TEXT_PRIMARY.name()};
        font-family: "Microsoft YaHei";
        padding: 10px;
    }}
"""

STYLE_LABEL_SUBTITLE = f"""
    QLabel {{
        font-size: 14px;
        color: {COLOR_TEXT_SECONDARY.name()};
        font-family: "Microsoft YaHei";
    }}
"""

STYLE_LOGIN_WIDGET = f"""
    #main_widget {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #F8F4E9, stop:1 #F0E9D9);
        border-radius: 15px;
        border: 1px solid {COLOR_BORDER.name()};
    }}
"""


def get_icon() -> QIcon:
    """获取程序图标"""
    icon_path = config.get_icon_path()
    if icon_path:
        return QIcon(icon_path)
    return QIcon()
