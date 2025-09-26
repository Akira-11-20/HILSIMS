from hils.core.simulator_base import SimulatorState, SimulatorProcessor, SimulatorLogger
import sys
sys.path.append("/app")

class VehicleState(SimulatorState):
    def __init__(self):
        self.speed = 0.0
        self.position = 0.0
        self.target_speed = 0.0

    def copy(self):
        return {
            "speed": self.speed,
            "position": self.position,
            "target_speed": self.target_speed
        }

    def reset(self):
        self.speed = 0.0
        self.position = 0.0
        self.target_speed = 0.0

class VehicleProcessor(SimulatorProcessor):
    def _create_state(self):
        return VehicleState()

    def generate_command(self, step_id):
        # 車両の制御コマンドを生成（例：速度制御）
        if step_id < 1000:
            self.state.target_speed = 10.0  # 10 m/s を目標
        else:
            self.state.target_speed = 5.0   # 5 m/s に減速

        return {
            "target_speed": self.state.target_speed,
            "step_id": step_id
        }

    def process_result(self, result_data):
        # ハードウェアから実際の速度・位置を受信
        if isinstance(result_data, dict):
            actual_speed = result_data.get("actual_speed", 0.0)
            actual_position = result_data.get("actual_position", 0.0)
            print(f"[vehicle_sim] Speed: {actual_speed:.2f} m/s, Position: {actual_position:.2f} m")
            return result_data
        return {}

class VehicleLogger(SimulatorLogger):
    def __init__(self):
        # 通信ログ + カスタムログを初期化
        super().__init__("vehicle_sim", ["step_id", "target_speed", "actual_speed", "actual_position"])

    def log_custom_data(self, step_id, sent_cmd, received_result, deadline_miss_ms):
        """車両シミュレーション専用のカスタムログを記録"""
        target_speed = sent_cmd.get("target_speed", 0.0) if isinstance(sent_cmd, dict) else 0.0
        actual_speed = received_result.get("actual_speed", 0.0) if isinstance(received_result, dict) else 0.0
        actual_position = received_result.get("actual_position", 0.0) if isinstance(received_result, dict) else 0.0

        self.log_custom([step_id, f"{target_speed:.3f}", f"{actual_speed:.3f}", f"{actual_position:.3f}"])