"""
HILSシミュレーション用ファクトリーモジュール

このモジュールは、シミュレーション種別に応じて適切な
Processor と Logger のペアを動的に生成するファクトリーパターンを実装します。
設定ベースでシミュレーション種別を切り替え可能で、カスタムシミュレーションの
動的ロードもサポートします。
"""

import importlib
import os
from typing import Tuple, TYPE_CHECKING, Any

# 型チェック時のみインポート（循環インポート回避）
if TYPE_CHECKING:
    from .sim.simulator_base import SimulatorProcessor, SimulatorLogger
    from .hw.hardware_base import HardwareProcessor, HardwareLogger


class SimulationFactory:
    """シミュレーションの種類を設定ベースで切り替えるファクトリー

    対応シミュレーション: numeric (基本通信テスト), vehicle (車両シミュレーション)
    """

    @staticmethod
    def create_simulator(sim_type: str) -> Tuple["SimulatorProcessor", "SimulatorLogger"]:
        """
        シミュレーター種類に応じてProcessor/Loggerペアを生成

        Args:
            sim_type: シミュレーション種別
                     - "numeric": 基本的な数値通信テスト用
                     - "vehicle": 車両動力学シミュレーション用
                     - その他: カスタムシミュレーション（動的ロード）

        Returns:
            (SimulatorProcessor, SimulatorLogger) のタプル

        Raises:
            ValueError: 未知のシミュレーション種別が指定された場合

        Note:
            STEP_MS環境変数からシミュレーションステップ時間を取得（デフォルト10ms）
        """

        # ビルトインシミュレーション: 数値通信テスト
        if sim_type == "numeric":
            from hils.simulators.numeric_sim import NumericProcessor, NumericLogger
            return NumericProcessor(), NumericLogger()

        # ビルトインシミュレーション: 車両動力学
        elif sim_type == "vehicle":
            from hils.simulators.vehicle import VehicleProcessor, VehicleLogger
            # 環境変数からステップ時間を取得（ms -> s変換）
            dt = float(os.environ.get("STEP_MS", "10")) / 1000.0
            return VehicleProcessor(dt=dt), VehicleLogger()

        else:
            # カスタムシミュレーション（動的インポート）
            try:
                # hils.simulators.{sim_type} モジュールをインポート
                module = importlib.import_module(f"hils.simulators.{sim_type}")

                # 命名規則に従ってクラスを取得: {Type}Processor, {Type}Logger
                processor_class = getattr(module, f"{sim_type.title()}Processor")
                logger_class = getattr(module, f"{sim_type.title()}Logger")

                # ステップ時間を設定してインスタンス生成
                dt = float(os.environ.get("STEP_MS", "10")) / 1000.0
                return processor_class(dt=dt), logger_class()
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Unknown simulation type: {sim_type}. Error: {e}")

    @staticmethod
    def create_hardware(hw_type: str) -> Tuple["HardwareProcessor", "HardwareLogger"]:
        """
        ハードウェア種類に応じてProcessor/Loggerペアを生成

        Args:
            hw_type: ハードウェア種別
                    - "numeric": 基本的な数値処理テスト用
                    - "vehicle": 車両ハードウェアエミュレーション用
                    - その他: カスタムハードウェア（動的ロード）

        Returns:
            (HardwareProcessor, HardwareLogger) のタプル

        Raises:
            ValueError: 未知のハードウェア種別が指定された場合

        Note:
            ハードウェア側はシミュレータからのコマンドを受信・処理し、
            結果を返すリアクティブな動作をします
        """

        # ビルトインハードウェア: 数値処理テスト
        if hw_type == "numeric":
            from hils.hardware.numeric_hw import NumericProcessor, NumericLogger
            return NumericProcessor(), NumericLogger()

        # ビルトインハードウェア: 車両エミュレーション
        elif hw_type == "vehicle":
            from hils.hardware.vehicle import VehicleProcessor, VehicleLogger
            # 環境変数からステップ時間を取得（ms -> s変換）
            dt = float(os.environ.get("STEP_MS", "10")) / 1000.0
            return VehicleProcessor(dt=dt), VehicleLogger()

        else:
            # カスタムハードウェア（動的インポート）
            try:
                # hils.hardware.{hw_type} モジュールをインポート
                module = importlib.import_module(f"hils.hardware.{hw_type}")

                # 命名規則に従ってクラスを取得: {Type}Processor, {Type}Logger
                processor_class = getattr(module, f"{hw_type.title()}Processor")
                logger_class = getattr(module, f"{hw_type.title()}Logger")

                # ステップ時間を設定してインスタンス生成
                dt = float(os.environ.get("STEP_MS", "10")) / 1000.0
                return processor_class(dt=dt), logger_class()
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Unknown hardware type: {hw_type}. Error: {e}")