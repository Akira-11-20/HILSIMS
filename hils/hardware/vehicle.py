from hils.core.hardware_base import HardwareState, HardwareProcessor, HardwareLogger
import sys
sys.path.append("/app")

class VehicleState(HardwareState):
    def __init__(self):
        self.speed = 0.0      # 現在速度
        self.position = 0.0   # 現在位置
        self.acceleration = 0.0

    def copy(self):
        return {
            "speed": self.speed,
            "position": self.position,
            "acceleration": self.acceleration
        }

    def reset(self):
        self.speed = 0.0
        self.position = 0.0
        self.acceleration = 0.0

class VehicleProcessor(HardwareProcessor):
    def _create_state(self):
        return VehicleState()

    def process_command(self, cmd):
        # 車両の物理モデル（簡単な例）
        if isinstance(cmd, dict):
            target_speed = float(cmd.get("target_speed", 0.0))

            # 簡単なP制御
            speed_error = target_speed - self.state.speed
            self.state.acceleration = speed_error * 0.5  # ゲイン0.5

            # 物理モデル更新（オイラー法）
            self.state.speed += self.state.acceleration * self.dt
            self.state.position += self.state.speed * self.dt

            # 速度制限
            if self.state.speed < 0:
                self.state.speed = 0.0

            return {
                "actual_speed": self.state.speed,
                "actual_position": self.state.position,
                "acceleration": self.state.acceleration
            }

        return {"actual_speed": 0.0, "actual_position": 0.0}

class VehicleLogger(HardwareLogger):
    def __init__(self):
        # 通信ログ + カスタムログを初期化
        super().__init__("vehicle_hw", ["step_id", "actual_speed", "actual_position", "acceleration"])

    def log_custom_data(self, step_id, result):
        """車両ハードウェア専用のカスタムログを記録"""
        if isinstance(result, dict):
            self.log_custom([
                step_id,
                f"{result.get('actual_speed', 0.0):.3f}",
                f"{result.get('actual_position', 0.0):.3f}",
                f"{result.get('acceleration', 0.0):.3f}"
            ])