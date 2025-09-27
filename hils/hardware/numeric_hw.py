"""
数値処理テスト用ハードウェアエミュレーションモジュール

このモジュールは、HILSシステムのハードウェア側をエミュレートし、
シミュレータからの数値コマンドを受信・処理します。
実際のハードウェア制御は行わず、数値演算（累積加算）を実行して
結果を返すシンプルな処理を行います。

主な機能:
- シミュレータからの数値コマンド受信
- 累積加算による数値処理
- 処理結果の送信・ログ記録
"""

import sys
from typing import Any, Dict

# TODO: アプリケーションパス設定を環境変数化
sys.path.append("/app")
from hils.core.hw.hardware_base import HardwareState, HardwareProcessor, HardwareLogger


class NumericState(HardwareState):
    """数値処理ハードウェアの状態クラス

    累積加算された数値の合計値を保持します。
    シミュレータからの値を順次加算していく状態を管理します。
    """

    def __init__(self):
        # 累積加算の合計値
        self.sum = 0.0

    def copy(self) -> Dict[str, Any]:
        """状態の辞書形式コピーを返す"""
        return {"sum": self.sum}

    def reset(self) -> None:
        """状態を初期値にリセット"""
        self.sum = 0.0


class NumericProcessor(HardwareProcessor):
    """数値処理ハードウェアエミュレータ

    シミュレータからの数値コマンドを受信し、累積加算処理を実行します。
    実際のハードウェア制御の代わりに、数学的演算により応答を生成します。
    """

    def _create_state(self) -> HardwareState:
        """NumericState インスタンスを生成"""
        return NumericState()

    def process_command(self, cmd: Any) -> Any:
        """
        シミュレータからのコマンドを処理して結果を返す

        Args:
            cmd: シミュレータから受信したコマンド
                - dict: {"value": 数値} 形式の場合、value を累積加算
                - list: 数値リストの場合、全要素を累積加算
                - その他: 0.0 として扱う

        Returns:
            累積加算後の合計値

        処理内容:
            受信した数値を内部状態の sum に加算し、
            更新後の合計値を応答として返します
        """
        result = 0.0

        if isinstance(cmd, dict):
            # 辞書形式: 'value' キーの値を抽出して加算
            value = float(cmd.get("value", 0.0))
            self.state.sum += value
            result = self.state.sum
        elif isinstance(cmd, list):
            # リスト形式: 全要素の合計を計算して加算
            value = sum(float(x) for x in cmd)
            self.state.sum += value
            result = self.state.sum
        # その他の形式は無視（result = 0.0のまま）

        return result


class NumericLogger(HardwareLogger):
    """数値処理ハードウェア用ログ記録クラス

    ハードウェア側での処理結果を記録します。
    通信ログ（受信・送信タイミング等）とカスタムログ（処理結果）の
    両方を CSV ファイルに出力します。
    """

    def __init__(self):
        # 基底クラスを初期化：ファイル名とカスタムログのヘッダーを設定
        super().__init__("numeric_hw", ["step_id", "result"])

    def log_custom_data(self, step_id: int, result: Any) -> None:
        """
        数値処理専用のカスタムログを記録

        Args:
            step_id: シミュレーションステップID
            result: ハードウェア処理結果（累積加算値）

        Note:
            処理結果を小数点以下3桁で記録します
        """
        # 結果値を抽出（数値以外は0.0として扱う）
        result_value = result if isinstance(result, (int, float)) else 0.0

        # カスタムログとして記録
        self.log_custom([step_id, f"{result_value:.3f}"])