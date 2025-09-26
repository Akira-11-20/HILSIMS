from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..base_logger import BaseLogger


class SimulatorState(ABC):
    """シミュレーター状態の基底クラス"""

    @abstractmethod
    def copy(self) -> Dict[str, Any]:
        """状態の辞書形式コピーを返す"""
        pass

    @abstractmethod
    def reset(self) -> None:
        """状態をリセットする"""
        pass


class SimulatorProcessor(ABC):
    """シミュレーター処理の基底クラス"""

    def __init__(self, dt: float = 0.01):
        self.dt = dt
        self.state: SimulatorState = self._create_state()

    @abstractmethod
    def _create_state(self) -> SimulatorState:
        """状態オブジェクトを生成"""
        pass

    @abstractmethod
    def generate_command(self, step_id: int) -> Dict[str, Any]:
        """制御コマンドを生成"""
        pass

    @abstractmethod
    def process_result(self, result_data: Any) -> Any:
        """ハードウェアからの結果を処理"""
        pass

    def get_state(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        return self.state.copy()

    def reset(self) -> None:
        """シミュレーターをリセット"""
        self.state.reset()


class SimulatorLogger(BaseLogger):
    """シミュレーターログの基底クラス（通信ログ + カスタムログ）"""

    def log_step(self, step_id: int, t_sim_send: Optional[int], t_sim_recv: Optional[int],
                 t_act_recv: Optional[int], t_act_send: Optional[int], timeout: bool,
                 deadline_miss_ms: float, sent_cmd: Dict[str, Any], received_result: Any) -> None:
        """ステップのログを記録（通信ログ + カスタムログ）"""
        # 通信ログを記録
        self.log_communication(step_id, t_sim_send, t_sim_recv, t_act_recv,
                              t_act_send, timeout, deadline_miss_ms)

        # カスタムログを記録（サブクラスで実装）
        self.log_custom_data(step_id, sent_cmd, received_result, deadline_miss_ms)

    @abstractmethod
    def log_custom_data(self, step_id: int, sent_cmd: Dict[str, Any],
                       received_result: Any, deadline_miss_ms: float) -> None:
        """カスタムデータのログを記録（サブクラスで実装）"""
        pass