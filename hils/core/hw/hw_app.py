import os
import sys
import socket
import json
import time

sys.path.append("/app")
from common.protocol import pack, recv_obj, now_ns

from ..simulation_factory import SimulationFactory


def apply_hw_to_sim_delay(delay_ms: int) -> None:
    """
    ハードウェアからシミュレータへの送信時に遅延を適用

    Args:
        delay_ms: 遅延時間（ミリ秒）

    Note:
        time.sleep()のオーバーヘッドを考慮して補正
        実測で約0.26ms/msのオーバーヘッドがあるため補正
    """
    if delay_ms > 0:
        # sleep()オーバーヘッド補正（実測値に基づく調整）
        # 2ms実測→1.9ms なので0.1ms増やす必要がある（補正を減らす）
        overhead_correction = delay_ms * 0.2 / 1000.0  # 20%のオーバーヘッド補正
        corrected_delay = max(0, (delay_ms / 1000.0) - overhead_correction)
        time.sleep(corrected_delay)


def main():
    """汎用ハードウェアメイン"""
    # 環境変数でハードウェア種類を指定
    hw_type = os.environ.get("HW_TYPE", "numeric")

    # 設定取得
    host = os.environ.get("ACT_HOST", "0.0.0.0")
    port = int(os.environ.get("ACT_PORT", "5001"))

    print(f"[hw] Starting {hw_type} hardware")
    print(f"[hw] Listening on {host}:{port}")

    try:
        processor, logger = SimulationFactory.create_hardware(hw_type)

        # サーバー開始
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(1)

        print(f"[hw] Waiting for simulator connection...")

        conn, addr = server_sock.accept()
        print(f"[hw] Connected from {addr}")

        try:
            while True:
                try:
                    # メッセージ受信 (共通プロトコル使用)
                    message = recv_obj(conn, timeout=None)
                    t_recv = now_ns()

                    command = message.get("command", {})
                    step_id = command.get("step_id", 0)
                    cmd_data = command.get("cmd", {})
                    hw_to_sim_delay_ms = command.get("hw_to_sim_delay_ms", 0)

                    # 処理実行
                    result = processor.process_command(cmd_data)

                    # 送信タイムスタンプを遅延適用前に記録（RTT測定用）
                    t_send = now_ns()

                    # 送信前遅延適用（ハードウェア→シミュレータ）
                    apply_hw_to_sim_delay(hw_to_sim_delay_ms)

                    # 実際の送信タイムスタンプ（遅延適用後）
                    t_send_actual = now_ns()

                    # 応答送信
                    telemetry_msg = {
                        "telemetry": {
                            "step_id": step_id,
                            "t_act_recv_ns": t_recv,
                            "t_act_send_ns": t_send,  # RTT測定用（遅延前）
                            "t_act_send_actual_ns": t_send_actual,  # 実際の送信時刻
                            "missing_cmd": False,
                            "result": result,
                            "note": "processed",
                            "applied_hw_to_sim_delay_ms": hw_to_sim_delay_ms
                        }
                    }
                    conn.sendall(pack(telemetry_msg))

                    # ログ記録
                    logger.log_step(
                        step_id, t_recv, t_send, False, "processed", result
                    )

                except ConnectionError:
                    break
                except Exception as e:
                    print(f"[hw] Error processing message: {e}")
                    break

        finally:
            conn.close()
            server_sock.close()
            logger.close()

    except ValueError as e:
        print(f"[hw] Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[hw] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()