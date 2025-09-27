"""
数値通信テスト用シミュレーションモジュール

このモジュールは、HILSシステムの基本的な通信機能をテストするための
シンプルな数値シミュレーションを実装します。実際の物理シミュレーションは行わず、
単調増加する数値を生成してハードウェア側に送信し、応答を受信・記録します。

主な用途:
- 通信プロトコルの動作確認
- タイミング特性の測定
- システム統合テスト
"""

import sys
from typing import Any, Dict

# TODO: アプリケーションパス設定を環境変数化
sys.path.append("/app")
from hils.core.sim.simulator_base import SimulatorState, SimulatorProcessor, SimulatorLogger


class NumericState(SimulatorState):
    """数値シミュレーション状態クラス

    単調増加するカウンター値を保持します。
    実際の物理状態ではなく、通信テスト用の単純な状態です。
    """

    def __init__(self):
        # 単調増加するカウンター値
        self.counter = 0.0

    def copy(self) -> Dict[str, Any]:
        """状態の辞書形式コピーを返す"""
        return {"counter": self.counter}

    def reset(self) -> None:
        """状態を初期値にリセット"""
        self.counter = 0.0


class NumericProcessor(SimulatorProcessor):
    """数値通信テスト用プロセッサ

    単調増加する数値を生成してハードウェア側に送信し、
    応答を受信・処理します。物理計算は行わず、純粋に
    通信機能のテストに特化しています。
    """

    def _create_state(self) -> SimulatorState:
        """NumericState インスタンスを生成"""
        return NumericState()

    def generate_command(self, step_id: int) -> Dict[str, Any]:
        """
        ハードウェア側への制御コマンドを生成

        Args:
            step_id: シミュレーションステップID

        Returns:
            送信する数値データを含む辞書

        Note:
            毎回0.1ずつ増加する値を送信します
        """
        # カウンター値を増加
        self.state.counter += 0.1
        return {"value": self.state.counter}

    def process_result(self, result_data: Any) -> Any:
        """
        ハードウェア側からの応答を処理

        Args:
            result_data: ハードウェアからの応答データ

        Returns:
            処理済みの結果値

        Note:
            受信した数値を標準出力に表示し、内部処理用に返します
        """
        if isinstance(result_data, dict):
            # 辞書形式の場合、"result"キーから値を取得
            received_result = result_data.get("result", 0.0)
            print(f"[sim] Received result: {received_result}")
            return received_result
        return 0.0


class NumericLogger(SimulatorLogger):
    """数値通信テスト用ログ記録クラス

    シミュレーション側での送信値と受信値を記録します。
    通信ログ（RTT、タイムアウト等）とカスタムログ（数値データ）の
    両方を CSV ファイルに出力します。
    """

    def __init__(self):
        # 基底クラスを初期化：ファイル名と カスタムログのヘッダーを設定
        super().__init__("numeric_sim", ["step_id", "sent_value", "received_result"])

    def log_custom_data(self, step_id: int, sent_cmd: Dict[str, Any],
                       received_result: Any, deadline_miss_ms: float) -> None:
        """
        数値通信専用のカスタムログを記録

        Args:
            step_id: シミュレーションステップID
            sent_cmd: ハードウェアに送信したコマンド辞書
            received_result: ハードウェアから受信した結果
            deadline_miss_ms: デッドライン超過時間（ms）

        Note:
            送信値と受信値を小数点以下3桁で記録します
        """
        # 送信値を抽出（安全な型変換）
        sent_value = sent_cmd.get("value", 0.0) if isinstance(sent_cmd, dict) else 0.0

        # 受信値を抽出（数値以外は0.0として扱う）
        result_value = received_result if isinstance(received_result, (int, float)) else 0.0

        # カスタムログとして記録
        self.log_custom([step_id, f"{sent_value:.3f}", f"{result_value:.3f}"])