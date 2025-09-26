import os
import sys
import socket
import json
import time

sys.path.append("/app")

from ..simulation_factory import SimulationFactory


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
            step_id = 0
            buffer = ""

            while True:
                data = conn.recv(1024).decode()
                if not data:
                    break

                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        # コマンド受信
                        t_recv = time.time_ns()
                        cmd = json.loads(line.strip())

                        # 処理実行
                        result = processor.process_command(cmd)

                        # 応答送信
                        t_send = time.time_ns()
                        conn.send(json.dumps(result).encode() + b'\n')

                        # ログ記録
                        logger.log_step(
                            step_id, t_recv, t_send, False, "", result
                        )

                        step_id += 1

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