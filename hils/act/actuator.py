import csv
import os
import socket
import sys

sys.path.append("/app")
from common.protocol import now_ns, pack, recv_obj

HOST = os.environ.get("ACT_HOST", "0.0.0.0")
PORT = int(os.environ.get("ACT_PORT", "5001"))
STEP_MS = int(os.environ.get("STEP_MS", "10"))

# ログ準備
from common.logging_utils import get_log_directory

log_dir = get_log_directory()
log_file = (log_dir / "act_log.csv").open("w", newline="")
log = csv.writer(log_file)
log.writerow(
    ["step_id", "t_act_recv_ns", "t_act_send_ns", "missing_cmd", "note", "result"]
)

# アクチュエーター状態（簡単な足し算例）
actuator_state = {"sum": 0.0}


def process_command(cmd):
    """簡単な足し算処理"""
    result = 0.0
    if isinstance(cmd, dict):
        # 辞書の場合: 'value' キーの値を足し算
        value = float(cmd.get("value", 0.0))
        actuator_state["sum"] += value
        result = actuator_state["sum"]
    elif isinstance(cmd, list):
        # リストの場合: 全要素を足し算
        value = sum(float(x) for x in cmd)
        actuator_state["sum"] += value
        result = actuator_state["sum"]
    return result


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[act] listening on {HOST}:{PORT}")
    conn, addr = srv.accept()
    with conn:
        print(f"[act] connected: {addr}")
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        while True:
            try:
                msg = recv_obj(conn, timeout=None)  # simがペースメーカー
                t_recv = now_ns()

                cmd = msg.get("command") or {}
                step_id = cmd.get("step_id", -1)
                cmd_data = cmd.get("cmd", {})

                # アクチュエーター処理（足し算）
                result = process_command(cmd_data)

                t_send = now_ns()
                tel = {
                    "telemetry": {
                        "step_id": step_id,
                        "t_act_recv_ns": t_recv,
                        "t_act_send_ns": t_send,
                        "missing_cmd": False,
                        "result": result,
                        "state": actuator_state.copy(),
                        "note": "addition_processed",
                    }
                }
                conn.sendall(pack(tel))
                log.writerow(
                    [step_id, t_recv, t_send, False, "addition_processed", result]
                )
                log_file.flush()

            except Exception as e:
                print(f"[act] error/closed: {e}")
                break

log_file.close()
