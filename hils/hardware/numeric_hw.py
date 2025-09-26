import sys
from typing import Any, Dict

sys.path.append("/app")
from hils.core.hardware_base import HardwareState, HardwareProcessor, HardwareLogger


class NumericState(HardwareState):
    def __init__(self):
        self.sum = 0.0

    def copy(self) -> Dict[str, Any]:
        return {"sum": self.sum}

    def reset(self) -> None:
        self.sum = 0.0


class NumericProcessor(HardwareProcessor):
    def _create_state(self) -> HardwareState:
        return NumericState()

    def process_command(self, cmd: Any) -> Any:
        """簡単な足し算処理"""
        result = 0.0
        if isinstance(cmd, dict):
            # 辞書の場合: 'value' キーの値を足し算
            value = float(cmd.get("value", 0.0))
            self.state.sum += value
            result = self.state.sum
        elif isinstance(cmd, list):
            # リストの場合: 全要素を足し算
            value = sum(float(x) for x in cmd)
            self.state.sum += value
            result = self.state.sum
        return result


class NumericLogger(HardwareLogger):
    def __init__(self):
        # 通信ログ + カスタムログを初期化
        super().__init__("numeric_hw", ["step_id", "result"])

    def log_custom_data(self, step_id: int, result: Any) -> None:
        """数値計算専用のカスタムログを記録"""
        result_value = result if isinstance(result, (int, float)) else 0.0
        self.log_custom([step_id, f"{result_value:.3f}"])