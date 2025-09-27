"""
HILSシステム用基底ログクラスモジュール

このモジュールは、HILSシステムにおけるシミュレータ・ハードウェア両側の
ログ記録機能を提供する基底クラスを定義します。通信ログ（RTT、タイムアウト等）と
カスタムログ（アプリケーション固有データ）の両方をCSV形式で出力できます。

主な機能:
- 通信パフォーマンス測定（RTT、処理時間等）
- アプリケーション固有データの記録
- ファイル管理（自動ディレクトリ作成、フラッシュ等）
- シミュレータ・ハードウェア別のログ形式対応
"""

import csv
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# TODO: アプリケーションパス設定を環境変数化
sys.path.append("/app")
from common.logging_utils import get_log_directory


class BaseLogger(ABC):
    """シミュレータ用基底ログクラス

    HILSシステムのシミュレータ側でのログ記録を担当します。
    通信ログ（RTT、タイムアウト）とカスタムログ（アプリケーション固有）を
    別々のCSVファイルに記録し、リアルタイム解析を可能にします。

    ログファイル構成:
    - {filename}_comm.csv: 通信パフォーマンスデータ
    - {filename}_custom.csv: アプリケーション固有データ
    """

    def __init__(self, log_filename: str, custom_headers: List[str] = None):
        """
        ログファイルを初期化し、ヘッダーを書き込む

        Args:
            log_filename: ログファイル名（拡張子なし）
                         例: "vehicle_sim" → "vehicle_sim_comm.csv", "vehicle_sim_custom.csv"
            custom_headers: カスタムログのヘッダーリスト
                          例: ["step_id", "velocity", "position"]

        Note:
            ログディレクトリは logging_utils.get_log_directory() で決定されます
        """
        log_dir = get_log_directory()

        # 通信ログ（共通フォーマット）
        # RTT解析やタイムアウト検出に使用される標準的な通信メトリクス
        self.comm_log_file = (log_dir / f"{log_filename}_comm.csv").open("w", newline="")
        self.comm_log = csv.writer(self.comm_log_file)
        self.comm_log.writerow([
            "step_id",           # シミュレーションステップID
            "t_sim_send_ns",     # シミュレータ送信時刻（ns）
            "t_sim_recv_ns",     # シミュレータ受信時刻（ns）
            "t_act_recv_ns",     # ハードウェア受信時刻（ns）
            "t_act_send_ns",     # ハードウェア送信時刻（ns）
            "timeout",           # タイムアウト発生フラグ
            "deadline_miss_ms",  # デッドライン超過時間（ms）
            "rtt_us"            # ラウンドトリップ時間（μs）
        ])

        # カスタムログ（アプリケーション固有データ）
        # シミュレーション種別に応じた独自データを記録
        if custom_headers:
            self.custom_log_file = (log_dir / f"{log_filename}_custom.csv").open("w", newline="")
            self.custom_log = csv.writer(self.custom_log_file)
            self.custom_log.writerow(custom_headers)
        else:
            # カスタムログが不要な場合
            self.custom_log_file = None
            self.custom_log = None

    def log_communication(self, step_id: int, t_sim_send: Optional[int],
                         t_sim_recv: Optional[int], t_act_recv: Optional[int],
                         t_act_send: Optional[int], timeout: bool, deadline_miss_ms: float):
        """
        通信パフォーマンスログを記録

        Args:
            step_id: シミュレーションステップID
            t_sim_send: シミュレータがコマンドを送信した時刻（ns）
            t_sim_recv: シミュレータが応答を受信した時刻（ns）
            t_act_recv: ハードウェアがコマンドを受信した時刻（ns）
            t_act_send: ハードウェアが応答を送信した時刻（ns）
            timeout: タイムアウトが発生したかどうか
            deadline_miss_ms: リアルタイム制約に対する遅延時間（ms）

        Note:
            RTT（ラウンドトリップ時間）は自動計算され、μs単位で記録されます
            Noneの時刻値は0として記録されます
        """
        # RTT計算（シミュレータ送信→受信の時間差）
        rtt_us = 0.0
        if t_sim_send and t_sim_recv:
            rtt_us = (t_sim_recv - t_sim_send) / 1000.0  # ns → μs変換

        # 通信ログエントリを記録
        self.comm_log.writerow([
            step_id,
            t_sim_send or 0,     # Noneの場合は0
            t_sim_recv or 0,
            t_act_recv or 0,
            t_act_send or 0,
            timeout,
            f"{deadline_miss_ms:.3f}",  # 小数点以下3桁
            f"{rtt_us:.1f}"            # 小数点以下1桁
        ])
        # リアルタイム解析のために即座にフラッシュ
        self.comm_log_file.flush()

    def log_custom(self, data: List[Any]):
        """
        カスタムログエントリを記録

        Args:
            data: ログデータのリスト（ヘッダーと同じ順序）
                 例: [step_id, velocity, position, force]

        Note:
            カスタムログが設定されていない場合は何も行いません
            データは即座にフラッシュされ、リアルタイム監視が可能です
        """
        if self.custom_log:
            self.custom_log.writerow(data)
            # リアルタイム解析のために即座にフラッシュ
            self.custom_log_file.flush()

    @abstractmethod
    def log_step(self, step_id: int, t_sim_send: Optional[int], t_sim_recv: Optional[int],
                 t_act_recv: Optional[int], t_act_send: Optional[int], timeout: bool,
                 deadline_miss_ms: float, sent_cmd: Dict[str, Any], received_result: Any):
        """
        1ステップ分のログを記録（サブクラスで実装必須）

        Args:
            step_id: シミュレーションステップID
            t_sim_send: シミュレータ送信時刻（ns）
            t_sim_recv: シミュレータ受信時刻（ns）
            t_act_recv: ハードウェア受信時刻（ns）
            t_act_send: ハードウェア送信時刻（ns）
            timeout: タイムアウト発生フラグ
            deadline_miss_ms: デッドライン超過時間（ms）
            sent_cmd: 送信したコマンド辞書
            received_result: 受信した結果データ

        Note:
            このメソッドは通常、通信ログとカスタムログの両方を記録します
            サブクラスで log_communication() と log_custom_data() を適切に呼び出してください
        """
        pass

    def close(self):
        """
        ログファイルを閉じてリソースを解放

        Note:
            プログラム終了時や長時間実行での定期的なファイル切り替え時に使用
            with文での自動クローズには対応していません
        """
        self.comm_log_file.close()
        if self.custom_log_file:
            self.custom_log_file.close()


class BaseHwLogger(ABC):
    """ハードウェア用基底ログクラス

    HILSシステムのハードウェア側でのログ記録を担当します。
    シミュレータ用のBaseLoggerとは異なり、ハードウェア側の特性に特化した
    ログ形式（処理時間、コマンド欠落等）を提供します。

    ログファイル構成:
    - {filename}_comm.csv: ハードウェア通信・処理パフォーマンス
    - {filename}_custom.csv: ハードウェア固有データ（制御結果等）
    """

    def __init__(self, log_filename: str, custom_headers: List[str] = None):
        """
        ハードウェア用ログファイルを初期化

        Args:
            log_filename: ログファイル名（拡張子なし）
            custom_headers: カスタムログのヘッダーリスト

        Note:
            ハードウェア側では主に応答性と処理時間に焦点を当てたログを記録
        """
        log_dir = get_log_directory()

        # ハードウェア通信ログ（処理時間重視）
        self.comm_log_file = (log_dir / f"{log_filename}_comm.csv").open("w", newline="")
        self.comm_log = csv.writer(self.comm_log_file)
        self.comm_log.writerow([
            "step_id",            # シミュレーションステップID
            "t_act_recv_ns",      # ハードウェア受信時刻（ns）
            "t_act_send_ns",      # ハードウェア送信時刻（ns）
            "processing_time_us", # 処理時間（μs）
            "missing_cmd",        # コマンド欠落フラグ
            "note"               # 追加情報・エラーメッセージ
        ])

        # カスタムログ（ハードウェア固有データ）
        if custom_headers:
            self.custom_log_file = (log_dir / f"{log_filename}_custom.csv").open("w", newline="")
            self.custom_log = csv.writer(self.custom_log_file)
            self.custom_log.writerow(custom_headers)
        else:
            self.custom_log_file = None
            self.custom_log = None

    def log_communication(self, step_id: int, t_recv: int, t_send: int,
                         missing_cmd: bool, note: str):
        """
        ハードウェア通信ログを記録

        Args:
            step_id: シミュレーションステップID
            t_recv: ハードウェアがコマンドを受信した時刻（ns）
            t_send: ハードウェアが応答を送信した時刻（ns）
            missing_cmd: コマンドが欠落・遅延したかどうか
            note: エラー情報や追加メモ

        Note:
            処理時間は自動計算され、μs単位で記録されます
            ハードウェアの応答性能評価に使用されます
        """
        # 処理時間計算（受信→送信の時間差）
        processing_time_us = (t_send - t_recv) / 1000.0  # ns → μs変換

        self.comm_log.writerow([
            step_id,
            t_recv,
            t_send,
            f"{processing_time_us:.1f}",  # 小数点以下1桁
            missing_cmd,
            note
        ])
        # リアルタイム監視のために即座にフラッシュ
        self.comm_log_file.flush()

    def log_custom(self, data: List[Any]):
        """
        ハードウェアカスタムログを記録

        Args:
            data: ログデータのリスト（ヘッダーと同じ順序）

        Note:
            ハードウェア固有の状態や制御結果を記録
            例: モータ回転数、センサ値、制御出力等
        """
        if self.custom_log:
            self.custom_log.writerow(data)
            self.custom_log_file.flush()

    @abstractmethod
    def log_step(self, step_id: int, t_recv: int, t_send: int, missing_cmd: bool,
                 note: str, result: Any):
        """
        ハードウェア1ステップ分のログを記録（サブクラスで実装必須）

        Args:
            step_id: シミュレーションステップID
            t_recv: 受信時刻（ns）
            t_send: 送信時刻（ns）
            missing_cmd: コマンド欠落フラグ
            note: エラー情報や状態メモ
            result: ハードウェア処理結果

        Note:
            通信ログとカスタムログの両方を適切に記録してください
        """
        pass

    def close(self):
        """
        ハードウェアログファイルを閉じる

        Note:
            ハードウェア側でのリソース解放時に使用
        """
        self.comm_log_file.close()
        if self.custom_log_file:
            self.custom_log_file.close()