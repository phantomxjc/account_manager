# -*- coding: utf-8 -*-
"""中国风界面样式配置。"""
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget, QFrame, QLabel, QListWidget
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QBrush
from PyQt5.QtCore import Qt, QPoint


class DiamondDivider(QWidget):
    """菱形节点装饰线：左右浅棕细线 + 中央朱红菱形（中国风），替代原顶部实心色条。"""
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self.node_color = QColor(color or "#A64D37")
        self.setFixedHeight(14)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cy = h / 2.0
        cx = w / 2.0
        r = 4.2                      # 菱形半对角
        gap = 6                      # 菱形与线的间隙
        # 左右两段浅棕细线
        pen = QPen(QColor("#D9C7A7"))
        pen.setWidth(1)
        p.setPen(pen)
        p.drawLine(2, int(cy), int(cx - r - gap), int(cy))
        p.drawLine(int(cx + r + gap), int(cy), w - 2, int(cy))
        # 中央朱红菱形
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self.node_color))
        diamond = [QPoint(int(cx), int(cy - r)), QPoint(int(cx + r), int(cy)),
                   QPoint(int(cx), int(cy + r)), QPoint(int(cx - r), int(cy))]
        p.drawPolygon(diamond)
        p.end()


class ChineseStyle:
    """中国风样式配置"""

    @staticmethod
    def setup_style(app):
        """设置应用程序的中国风样式"""
        # 设置中文字体
        font = QFont("Microsoft YaHei", 10)
        app.setFont(font)

        # 设置中国风颜色方案
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(250, 245, 235))  # 米白色背景
        palette.setColor(QPalette.WindowText, QColor(101, 67, 33))  # 深棕色文字
        palette.setColor(QPalette.Base, QColor(255, 253, 248))  # 浅米色基础
        palette.setColor(QPalette.AlternateBase, QColor(245, 240, 230))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 253, 248))
        palette.setColor(QPalette.ToolTipText, QColor(101, 67, 33))
        palette.setColor(QPalette.Text, QColor(101, 67, 33))
        palette.setColor(QPalette.Button, QColor(180, 150, 100))  # 古铜色按钮
        palette.setColor(QPalette.ButtonText, QColor(250, 245, 235))
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(166, 77, 55))  # 朱红色链接
        palette.setColor(QPalette.Highlight, QColor(166, 77, 55))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        app.setPalette(palette)

    @staticmethod
    def create_gradient_button(text, width=120, height=40, color1="#A64D37", color2="#C46C4E", radius=6):
        """创建中国风渐变按钮（默认 6px 圆角，全局统一；工具栏/弹窗一致）"""
        button = QPushButton(text)
        button.setFixedSize(width, height)
        button.setProperty("chineseStyle", True)
        button.setStyleSheet(f"""
            QPushButton[chineseStyle="true"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 {color1}, stop:1 {color2});
                color: white;
                border-radius: {radius}px;
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
        return button

    # ===== 对话框统一视觉语言（暖米+朱红中国风）=====
    ACCENT = "#A64D37"       # 朱红：主色 / 选中强调
    ACCENT_BROWN = "#8C7853" # 深棕：次级
    TITLE_COLOR = "#654321"  # 标题棕

    @staticmethod
    def add_dialog_accent(dialog, color=None):
        """对话框顶部菱形节点装饰线（浅棕细线+中央朱红菱形），在布局最前面插入。"""
        layout = dialog.layout()
        if layout is None or getattr(dialog, "_accent_added", False):
            return
        divider = DiamondDivider(color=color, parent=dialog)
        layout.insertWidget(0, divider)
        dialog._accent_added = True
        return divider

    @staticmethod
    def set_dialog_title(label, subtitle=None, color=None):
        """把标题标签设成统一风格：左侧朱红竖线 + 16px 粗体。
        文字起点 = 4px 竖线 + 12px padding = 16px，与副标题严格对齐。"""
        color = color or ChineseStyle.ACCENT
        label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px; font-weight: bold; color: {ChineseStyle.TITLE_COLOR};
                font-family: "Microsoft YaHei"; padding: 2px 0 2px 12px;
                border-left: 4px solid {color};
            }}
        """)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    @staticmethod
    def make_subtitle(text):
        """统一副标题（灰色小字），左边距 16px 与标题文字对齐"""
        sub = QLabel(text)
        sub.setStyleSheet("font-size: 11px; color: #9A8B77; font-family: 'Microsoft YaHei'; padding: 0 0 0 16px;")
        return sub

    @staticmethod
    def make_hint_bar(text, color=None):
        """统一提示条：浅米底 + 左侧竖线"""
        color = color or "#C9A47A"
        hint = QLabel(text)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"""
            QLabel {{
                background: #F3E8DA; border-left: 3px solid {color}; border-radius: 4px;
                padding: 7px 10px; font-size: 11px; color: #8C6A47;
                font-family: "Microsoft YaHei";
            }}
        """)
        return hint

    @staticmethod
    def card_list_stylesheet(accent=None):
        """统一卡片化 QListWidget 样式（选中态左侧朱红竖线）"""
        accent = accent or ChineseStyle.ACCENT
        return """
            QListWidget {
                background: #FFFDF8; border: 1px solid #E4D6C2; border-radius: 7px;
                padding: 5px; font-family: "Microsoft YaHei";
                font-size: 12px; color: #5A4632;
            }
            QListWidget::item { padding: 7px 8px; border-radius: 5px; }
            QListWidget::item:selected { background: #F0DBCB; color: #6B4423;
                border-left: 3px solid __ACCENT__; }
            QListWidget::item:hover:!selected { background: #F7F1E6; }
        """.replace("__ACCENT__", accent)

    @staticmethod
    def primary_button(text, width=90, height=34):
        """主操作按钮：实心朱红"""
        return ChineseStyle.create_gradient_button(text, width, height,
                                                   "#A64D37", "#C0603F", radius=6)

    @staticmethod
    def secondary_button(text, width=90, height=34):
        """次要按钮：灰棕描边"""
        b = QPushButton(text)
        b.setFixedSize(width, height)
        b.setStyleSheet("""
            QPushButton {
                background: #FBF7F0; color: #7A5C3A; border: 1px solid #D9C7A7;
                border-radius: 6px; font-family: "Microsoft YaHei"; font-size: 12px;
            }
            QPushButton:hover { background: #F0E4D4; }
        """)
        return b

    @staticmethod
    def danger_button(text, width=100, height=34):
        """危险操作按钮：红色系描边（删除类）"""
        b = QPushButton(text)
        b.setFixedSize(width, height)
        b.setStyleSheet("""
            QPushButton {
                background: #FAECE7; color: #A32D2D; border: 1px solid #E8B4A8;
                border-radius: 6px; font-family: "Microsoft YaHei"; font-size: 12px;
            }
            QPushButton:hover { background: #F5D9CF; }
        """)
        return b

    @staticmethod
    def tool_button(text, width=None, height=30):
        """工具按钮：浅底细描边（重新生成/复制/浏览/全选等轻量操作）。
        宽度不传时按字数自适应，保证同类按钮宽窄一致。"""
        if width is None:
            width = max(62, len(text) * 14 + 30)
        b = QPushButton(text)
        b.setFixedSize(width, height)
        b.setStyleSheet("""
            QPushButton {
                background: #FFFDF8; color: #7A5C3A; border: 1px solid #D9C7A7;
                border-radius: 6px; font-family: "Microsoft YaHei"; font-size: 12px;
            }
            QPushButton:hover { background: #F3E6D4; border-color: #C9A47A; }
            QPushButton:pressed { background: #EAD9C2; }
        """)
        return b
