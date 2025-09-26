import os
import sys
import socket
import time
import json

sys.path.append("/app")

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

                # 送信
                t_sim_send = time.time_ns()
                sock.send(json.dumps(cmd).encode() + b'\n')

                # 受信
                response = sock.recv(1024).decode().strip()
                t_sim_recv = time.time_ns()

                if response:
                    result = json.loads(response)
                    processor.process_result(result)

                    # ログ記録
                    logger.log_step(
                        step_id, t_sim_send, t_sim_recv, None, None,
                        False, 0.0, cmd, result
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