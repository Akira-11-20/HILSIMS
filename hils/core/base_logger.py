import csv
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

sys.path.append("/app")
from common.logging_utils import get_log_directory


class BaseLogger(ABC):
    """共通ログ機能付きの基底ログクラス"""

    def __init__(self, log_filename: str, custom_headers: List[str] = None):
        """
        Args:
            log_filename: ログファイル名（拡張子なし）
            custom_headers: カスタムヘッダーのリスト
        """
        log_dir = get_log_directory()

        # 通信ログ（共通）
        self.comm_log_file = (log_dir / f"{log_filename}_comm.csv").open("w", newline="")
        self.comm_log = csv.writer(self.comm_log_file)
        self.comm_log.writerow([
            "step_id", "t_sim_send_ns", "t_sim_recv_ns", "t_act_recv_ns", "t_act_send_ns",
            "timeout", "deadline_miss_ms", "rtt_us"
        ])

        # カスタムログ（アプリケーション固有）
        if custom_headers:
            self.custom_log_file = (log_dir / f"{log_filename}_custom.csv").open("w", newline="")
            self.custom_log = csv.writer(self.custom_log_file)
            self.custom_log.writerow(custom_headers)
        else:
            self.custom_log_file = None
            self.custom_log = None

    def log_communication(self, step_id: int, t_sim_send: Optional[int],
                         t_sim_recv: Optional[int], t_act_recv: Optional[int],
                         t_act_send: Optional[int], timeout: bool, deadline_miss_ms: float):
        """通信ログを記録"""
        # RTT計算
        rtt_us = 0.0
        if t_sim_send and t_sim_recv:
            rtt_us = (t_sim_recv - t_sim_send) / 1000.0  # ns -> us

        self.comm_log.writerow([
            step_id, t_sim_send or 0, t_sim_recv or 0, t_act_recv or 0, t_act_send or 0,
            timeout, f"{deadline_miss_ms:.3f}", f"{rtt_us:.1f}"
        ])
        self.comm_log_file.flush()

    def log_custom(self, data: List[Any]):
        """カスタムログを記録"""
        if self.custom_log:
            self.custom_log.writerow(data)
            self.custom_log_file.flush()

    @abstractmethod
    def log_step(self, step_id: int, t_sim_send: Optional[int], t_sim_recv: Optional[int],
                 t_act_recv: Optional[int], t_act_send: Optional[int], timeout: bool,
                 deadline_miss_ms: float, sent_cmd: Dict[str, Any], received_result: Any):
        """ステップログを記録（実装必須）"""
        pass

    def close(self):
        """ログファイルを閉じる"""
        self.comm_log_file.close()
        if self.custom_log_file:
            self.custom_log_file.close()


class BaseHwLogger(ABC):
    """ハードウェア用共通ログ機能付きの基底ログクラス"""

    def __init__(self, log_filename: str, custom_headers: List[str] = None):
        log_dir = get_log_directory()

        # 通信ログ（共通）
        self.comm_log_file = (log_dir / f"{log_filename}_comm.csv").open("w", newline="")
        self.comm_log = csv.writer(self.comm_log_file)
        self.comm_log.writerow([
            "step_id", "t_act_recv_ns", "t_act_send_ns", "processing_time_us", "missing_cmd", "note"
        ])

        # カスタムログ（アプリケーション固有）
        if custom_headers:
            self.custom_log_file = (log_dir / f"{log_filename}_custom.csv").open("w", newline="")
            self.custom_log = csv.writer(self.custom_log_file)
            self.custom_log.writerow(custom_headers)
        else:
            self.custom_log_file = None
            self.custom_log = None

    def log_communication(self, step_id: int, t_recv: int, t_send: int,
                         missing_cmd: bool, note: str):
        """通信ログを記録"""
        processing_time_us = (t_send - t_recv) / 1000.0  # ns -> us

        self.comm_log.writerow([
            step_id, t_recv, t_send, f"{processing_time_us:.1f}", missing_cmd, note
        ])
        self.comm_log_file.flush()

    def log_custom(self, data: List[Any]):
        """カスタムログを記録"""
        if self.custom_log:
            self.custom_log.writerow(data)
            self.custom_log_file.flush()

    @abstractmethod
    def log_step(self, step_id: int, t_recv: int, t_send: int, missing_cmd: bool,
                 note: str, result: Any):
        """ステップログを記録（実装必須）"""
        pass

    def close(self):
        """ログファイルを閉じる"""
        self.comm_log_file.close()
        if self.custom_log_file:
            self.custom_log_file.close()