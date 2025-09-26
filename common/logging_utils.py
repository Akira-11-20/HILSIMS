import os
import pathlib
from datetime import datetime


def get_log_directory():
    """実行時の日時でログディレクトリを取得"""
    # 環境変数から共有タイムスタンプを取得（未設定なら現在時刻）
    timestamp_str = os.environ.get("LOG_TIMESTAMP")
    if not timestamp_str:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_base = pathlib.Path("/app/logs")
    log_dir = log_base / timestamp_str
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
