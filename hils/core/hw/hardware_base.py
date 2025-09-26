from abc import ABC, abstractmethod
from typing import Any, Dict
from ..base_logger import BaseHwLogger


class HardwareState(ABC):
    """ハードウェア状態の基底クラス"""

    @abstractmethod
    def copy(self) -> Dict[str, Any]:
        """状態の辞書形式コピーを返す"""
        pass

    @abstractmethod
    def reset(self) -> None:
        """状態をリセットする"""
        pass


class HardwareProcessor(ABC):
    """ハードウェア処理の基底クラス"""

    def __init__(self, dt: float = 0.01):
        self.dt = dt
        self.state: HardwareState = self._create_state()

    @abstractmethod
    def _create_state(self) -> HardwareState:
        """状態オブジェクトを生成"""
        pass

    @abstractmethod
    def process_command(self, cmd: Any) -> Any:
        """制御コマンドを処理して結果を返す"""
        pass

    def get_state(self) -> Dict[str, Any]:
        """現在の状態を取得"""
        return self.state.copy()

    def reset(self) -> None:
        """ハードウェアをリセット"""
        self.state.reset()


class HardwareLogger(BaseHwLogger):
    """ハードウェアログの基底クラス（通信ログ + カスタムログ）"""

    def log_step(self, step_id: int, t_recv: int, t_send: int, missing_cmd: bool,
                 note: str, result: Any) -> None:
        """ステップのログを記録（通信ログ + カスタムログ）"""
        # 通信ログを記録
        self.log_communication(step_id, t_recv, t_send, missing_cmd, note)

        # カスタムログを記録（サブクラスで実装）
        self.log_custom_data(step_id, result)

    @abstractmethod
    def log_custom_data(self, step_id: int, result: Any) -> None:
        """カスタムデータのログを記録（サブクラスで実装）"""
        pass