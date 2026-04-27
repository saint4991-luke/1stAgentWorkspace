#!/usr/bin/env python3
"""
Log Redirector - 攔截 print() 輸出並寫入 log 檔案
使用方法：在 .py 檔案開頭 import 這個模組即可
"""

import sys
import os
from datetime import datetime
from pathlib import Path

class LogRedirector:
    def __init__(self, app_name="default", log_dir="/app/shared/logs"):
        self.app_name = app_name
        # 確保轉為絕對路徑 (Absolute Path)
        # 如果傳入的是相對路徑，它會根據當前執行目錄轉為絕對路徑
        self.log_dir = Path(log_dir).resolve()
        self.original_stdout = sys.stdout
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            # 在終端機印出錯誤，因為此時 stdout 可能還沒導向
            print(f"Critcal Error: Cannot create log directory {self.log_dir}. {e}", file=sys.stderr)
            raise
        

        # 記錄目前日期
        self.current_date = self._get_today_str()
        self.log_file = self._get_log_file(self.current_date)

        self._write_log(f"=== Log redirector started at {datetime.now().isoformat()} ===")

    def _get_today_str(self):
        return datetime.now().strftime("%Y%m%d")

    def _get_log_file(self, date_str):
        return self.log_dir / f"{self.app_name}_{date_str}.log"

    def _rotate_if_needed(self):
        """如果跨日，自動切換 log 檔"""
        today = self._get_today_str()
        if today != self.current_date:
            self.current_date = today
            self.log_file = self._get_log_file(today)
            self._write_log(f"=== Log rotated at {datetime.now().isoformat()} ===")

    def _write_log(self, message):
        self._rotate_if_needed()  # 👈 每次寫之前檢查

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} {message}\n"

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def write(self, text):
        if text.strip():
            self._write_log(text.strip())

        self.original_stdout.write(text)

    def flush(self):
        self.original_stdout.flush()

    def restore(self):
        sys.stdout = self.original_stdout
        self._write_log(f"=== Log redirector stopped at {datetime.now().isoformat()} ===")

    def isatty(self):
        return False

def setup_logging(app_name="default", log_dir=None):
    """
    快速設置函數 - 在 .py 開頭呼叫這個函數即可
    """
    if log_dir is None:
        log_dir = os.getenv("LOG_PATH", "logs") 

    redirector = LogRedirector(app_name, log_dir)
    sys.stdout = redirector
    sys.stderr = redirector
    
    # 註冊清理函數（程式結束時自動恢復）
    import atexit
    atexit.register(redirector.restore)
    
    return redirector