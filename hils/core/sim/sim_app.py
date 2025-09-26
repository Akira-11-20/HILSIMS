import os
import sys
import socket
import time
import json

sys.path.append("/app")
from common.protocol import pack, recv_obj, now_ns

from ..simulation_factory import SimulationFactory


def main():
    """汎用シミュレーターメイン"""
    # 環境変数でシミュレーション種類を指定
    sim_type = os.environ.get("SIM_TYPE", "numeric")

    # 設定取得
    act_host = os.environ.get("ACT_HOST", "hardware")
    act_port = int(os.environ.get("ACT_PORT", "5001"))
    step_ms = int(os.environ.get("STEP_MS", "10"))
    total_steps = int(os.environ.get("TOTAL_STEPS", "1000"))

    print(f"[sim] Starting {sim_type} simulation")
    print(f"[sim] Target: {act_host}:{act_port}, Steps: {total_steps}, Interval: {step_ms}ms")

    try:
        processor, logger = SimulationFactory.create_simulator(sim_type)

        # ハードウェアに接続
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((act_host, act_port))
        print(f"[sim] connected to {act_host}:{act_port}")

        try:
            for step_id in range(total_steps):
                # コマンド生成
                cmd = processor.generate_command(step_id)

                # 送信 (共通プロトコル使用)
                t_sim_send = now_ns()
                command_msg = {
                    "command": {
                        "step_id": step_id,
                        "timestamp_ns": t_sim_send,
                        "cmd": cmd
                    }
                }
                sock.sendall(pack(command_msg))

                # 受信 (共通プロトコル使用)
                response = recv_obj(sock, timeout=2.0)
                t_sim_recv = now_ns()

                if response:
                    telemetry = response.get("telemetry", {})
                    processed_result = processor.process_result(telemetry)

                    # ハードウェア側のタイムスタンプを取得
                    t_act_recv = telemetry.get("t_act_recv_ns", 0)
                    t_act_send = telemetry.get("t_act_send_ns", 0)

                    # ログ記録（processed_resultを使用）
                    logger.log_step(
                        step_id, t_sim_send, t_sim_recv, t_act_recv, t_act_send,
                        False, 0.0, cmd, processed_result
                    )

                time.sleep(step_ms / 1000.0)

        finally:
            sock.close()
            logger.close()

    except ValueError as e:
        print(f"[sim] Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[sim] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()