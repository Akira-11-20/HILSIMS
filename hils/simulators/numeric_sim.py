import sys
from typing import Any, Dict

sys.path.append("/app")
from hils.core.simulator_base import SimulatorState, SimulatorProcessor, SimulatorLogger


class NumericState(SimulatorState):
    def __init__(self):
        self.counter = 0.0

    def copy(self) -> Dict[str, Any]:
        return {"counter": self.counter}

    def reset(self) -> None:
        self.counter = 0.0


class NumericProcessor(SimulatorProcessor):
    def _create_state(self) -> SimulatorState:
        return NumericState()

    def generate_command(self, step_id: int) -> Dict[str, Any]:
        """簡単なコマンド生成（ステップごとに増加する値）"""
        self.state.counter += 0.1
        return {"value": self.state.counter}

    def process_result(self, result_data: Any) -> Any:
        """結果の処理（ここでは単純に記録）"""
        if isinstance(result_data, dict):
            received_result = result_data.get("result", 0.0)
            print(f"[sim] Received result: {received_result}")
            return received_result
        return 0.0


class NumericLogger(SimulatorLogger):
    def __init__(self):
        # 通信ログ + カスタムログを初期化
        super().__init__("numeric_sim", ["step_id", "sent_value", "received_result"])

    def log_custom_data(self, step_id: int, sent_cmd: Dict[str, Any],
                       received_result: Any, deadline_miss_ms: float) -> None:
        """数値計算専用のカスタムログを記録"""
        sent_value = sent_cmd.get("value", 0.0) if isinstance(sent_cmd, dict) else 0.0
        result_value = received_result if isinstance(received_result, (int, float)) else 0.0

        self.log_custom([step_id, f"{sent_value:.3f}", f"{result_value:.3f}"])