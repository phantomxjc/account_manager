# -*- coding: utf-8 -*-
"""
墨香密码管理器 - 分享记录对话框
将账号信息按标准格式展示并支持一键复制
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox

from ui.style import create_gradient_button, STYLE_LABEL_TITLE


class ShareDialog(QDialog):
    """分享账号信息对话框"""

    def __init__(self, parent=None, record: dict = None):
        super().__init__(parent)
        self.record = record or {}
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("分享账号信息")
        self.setFixedSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 标题
        t = QLabel("分享账号信息")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(STYLE_LABEL_TITLE)
        layout.addWidget(t)

        # 说明
        info = QLabel("以下信息已按标准格式生成，可直接复制使用：")
        info.setStyleSheet("font-family: 'Microsoft YaHei'; color: #8C7853;")
        layout.addWidget(info)

        # 内容
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D9C7A7;
                border-radius: 8px;
                padding: 10px;
                font-family: "Microsoft YaHei";
                font-size: 14px;
                background-color: #FFFEF9;
                selection-background-color: #E8D0B0;
            }
        """)
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        # 生成内容
        self._generate_content()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        copy_btn = create_gradient_button("复制内容", 100, 35)
        copy_btn.clicked.connect(self._copy)

        close_btn = create_gradient_button("关闭", 100, 35, "#8C7853", "#A8967A")
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _generate_content(self):
        fields = []
        name = self.record.get("网站名称", "")
        url  = self.record.get("网址", "")
        acc  = self.record.get("账号", "")
        pwd  = self.record.get("密码", "")
        desc = self.record.get("备注", "")

        if name and name != "未知网站":
            fields.append(f"网站名称：{name}")
        if url:
            fields.append(f"网址：{url}")
        if acc:
            fields.append(f"账号：{acc}")
        if pwd:
            fields.append(f"密码：{pwd}")
        if desc:
            fields.append(f"备注：{desc}")

        self.text_edit.setPlainText("\n".join(fields))

    def _copy(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.text_edit.toPlainText())
        QMessageBox.information(self, "复制成功", "分享内容已复制到剪贴板！")
