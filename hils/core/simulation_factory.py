import importlib
import os
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .sim.simulator_base import SimulatorProcessor, SimulatorLogger
    from .hw.hardware_base import HardwareProcessor, HardwareLogger


class SimulationFactory:
    """シミュレーションの種類を設定ベースで切り替えるファクトリー

    対応シミュレーション: numeric (基本通信テスト), vehicle (車両シミュレーション)
    """

    @staticmethod
    def create_simulator(sim_type: str) -> Tuple:
        """シミュレーター種類に応じてProcessor/Loggerを生成"""

        if sim_type == "numeric":
            from hils.simulators.numeric_sim import NumericProcessor, NumericLogger
            return NumericProcessor(), NumericLogger()


        elif sim_type == "vehicle":
            from hils.simulators.vehicle import VehicleProcessor, VehicleLogger
            dt = float(os.environ.get("STEP_MS", "10")) / 1000.0
            return VehicleProcessor(dt=dt), VehicleLogger()

        else:
            # カスタムシミュレーション（動的インポート）
            try:
                module = importlib.import_module(f"hils.simulators.{sim_type}")
                processor_class = getattr(module, f"{sim_type.title()}Processor")
                logger_class = getattr(module, f"{sim_type.title()}Logger")
                dt = float(os.environ.get("STEP_MS", "10")) / 1000.0
                return processor_class(dt=dt), logger_class()
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Unknown simulation type: {sim_type}. Error: {e}")

    @staticmethod
    def create_hardware(hw_type: str) -> Tuple:
        """ハードウェア種類に応じてProcessor/Loggerを生成"""

        if hw_type == "numeric":
            from hils.hardware.numeric_hw import NumericProcessor, NumericLogger
            return NumericProcessor(), NumericLogger()


        elif hw_type == "vehicle":
            from hils.hardware.vehicle import VehicleProcessor, VehicleLogger
            dt = float(os.environ.get("STEP_MS", "10")) / 1000.0
            return VehicleProcessor(dt=dt), VehicleLogger()

        else:
            # カスタムハードウェア（動的インポート）
            try:
                module = importlib.import_module(f"hils.hardware.{hw_type}")
                processor_class = getattr(module, f"{hw_type.title()}Processor")
                logger_class = getattr(module, f"{hw_type.title()}Logger")
                dt = float(os.environ.get("STEP_MS", "10")) / 1000.0
                return processor_class(dt=dt), logger_class()
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Unknown hardware type: {hw_type}. Error: {e}")