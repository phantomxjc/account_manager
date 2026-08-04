# -*- coding: utf-8 -*-
"""
墨香密码管理器 - Excel 导入模块
后台线程执行，支持字段模糊映射
"""

import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal

import config
from core.password_manager import PasswordManager


class ExcelImportWorker(QThread):
    """Excel 导入后台线程"""

    progress_updated = pyqtSignal(int)
    import_completed = pyqtSignal(bool, str)

    def __init__(self, file_path: str, target_table: str,
                 sheet_name=None, password_manager: PasswordManager = None):
        super().__init__()
        self.file_path = file_path
        self.target_table = target_table  # "单位表" / "个人表"
        self.sheet_name = sheet_name
        self.pm = password_manager

    # ==================== 字段映射 ====================

    def _build_field_mapping(self, columns) -> dict:
        """根据 Excel 列名自动匹配目标字段"""
        mapping = {}
        for target_field, candidates in config.EXCEL_FIELD_MAPPING.items():
            for col in columns:
                if any(name in str(col) for name in candidates):
                    mapping[target_field] = col
                    break
            else:
                mapping[target_field] = None
        return mapping

    def _cell_to_str(self, value) -> str:
        """安全地把单元格转成字符串"""
        if value is None:
            return ""
        try:
            return str(value).strip()
        except Exception:
            return ""

    # ==================== 线程主逻辑 ====================

    def run(self):
        try:
            # 读取 Excel
            if self.sheet_name:
                df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)
            else:
                df = pd.read_excel(self.file_path)

            if df.empty:
                self.import_completed.emit(False, "Excel 文件为空或没有数据")
                return

            mapping = self._build_field_mapping(df.columns)
            total = len(df)
            imported = skipped = errors = 0

            for idx, row in df.iterrows():
                progress = int((idx + 1) / total * 100)
                self.progress_updated.emit(progress)

                record = {
                    "网站名称": self._cell_to_str(row[mapping['网站名称']]) if mapping['网站名称'] else "",
                    "网址":     self._cell_to_str(row[mapping['网址']])     if mapping['网址']     else "",
                    "账号":     self._cell_to_str(row[mapping['账号']])     if mapping['账号']     else "",
                    "密码":     self._cell_to_str(row[mapping['密码']])     if mapping['密码']     else "",
                    "备注":     self._cell_to_str(row[mapping['备注']])     if mapping['备注']     else "",
                }

                if not record["网站名称"] and not record["账号"]:
                    skipped += 1
                    continue

                if self.pm.add_record(self.target_table, record):
                    imported += 1
                else:
                    errors += 1
                    skipped += 1

            self.progress_updated.emit(100)
            msg = f"导入完成：成功 {imported} 条，跳过 {skipped} 条，错误 {errors} 条"
            self.import_completed.emit(True, msg)

        except Exception as e:
            self.import_completed.emit(False, f"导入失败: {e}")
