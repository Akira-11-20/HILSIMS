import csv
import os
import queue
import socket
import subprocess
import sys
import threading
import time

sys.path.append("/app")
from common.protocol import now_ns, pack, recv_obj

ACT_HOST = os.environ.get("ACT_HOST", "act")
ACT_PORT = int(os.environ.get("ACT_PORT", "5001"))
STEP_MS = int(os.environ.get("STEP_MS", "10"))
REPLY_TIMEOUT_MS = int(os.environ.get("REPLY_TIMEOUT_MS", "2"))
TOTAL_STEPS = int(os.environ.get("TOTAL_STEPS", "1000"))
NETWORK_DELAY_MS = int(os.environ.get("NETWORK_DELAY_MS", "0"))

PERIOD_NS = STEP_MS * 1_000_000
TIMEOUT_S = REPLY_TIMEOUT_MS / 1000.0


def setup_network_delay():
    """tc コマンドで遅延を設定（sudo使用）"""
    if NETWORK_DELAY_MS > 0:
        try:
            # 既存の設定をクリア
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", "eth0", "root"],
                capture_output=True,
                check=False,
            )
            # 遅延を設定
            subprocess.run(
                [
                    "sudo",
                    "tc",
                    "qdisc",
                    "add",
                    "dev",
                    "eth0",
                    "root",
                    "netem",
                    "delay",
                    f"{NETWORK_DELAY_MS}ms",
                ],
                check=True,
            )
            print(f"[sim] Network delay set to {NETWORK_DELAY_MS}ms")
        except subprocess.CalledProcessError as e:
            print(f"[sim] Failed to set network delay: {e}")
        except FileNotFoundError:
            print("[sim] tc command not found, skipping network delay setup")


# 遅延設定
setup_network_delay()

# ログ準備
sys.path.append("/app")
from common.logging_utils import get_log_directory

log_dir = get_log_directory()
log_file = (log_dir / "sim_log.csv").open("w", newline="")
log = csv.writer(log_file)
log.writerow(
    [
        "step_id",
        "t_sim_send_ns",
        "t_sim_recv_ns",
        "t_act_recv_ns",
        "t_act_send_ns",
        "timeout",
        "deadline_miss_ms",
        "sent_value",
        "received_result",
    ]
)

# 非同期受信キュー（(受信時刻, メッセージ)）
rxq: queue.Queue = queue.Queue(maxsize=1024)


def rx_thread(sock):
    while True:
        try:
            obj = recv_obj(sock, timeout=None)
            rx_time = now_ns()
            try:
                rxq.put_nowait((rx_time, obj))
            except queue.Full:
                # 古いものを捨てる方針
                rxq.get_nowait()
                rxq.put_nowait((rx_time, obj))
        except Exception as e:
            print(f"[sim] rx closed: {e}")
            break


# シミュレーション状態（簡単な値生成例）
simulation_state = {"counter": 0.0}


def generate_command(step_id):
    """簡単なコマンド生成（ステップごとに増加する値）"""
    simulation_state["counter"] += 0.1
    return {"value": simulation_state["counter"]}


def process_result(result_data):
    """結果の処理（ここでは単純に記録）"""
    if isinstance(result_data, dict):
        received_result = result_data.get("result", 0.0)
        print(f"[sim] Received result: {received_result}")
        return received_result
    return 0.0


with socket.create_connection((ACT_HOST, ACT_PORT)) as sock:
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    print(f"[sim] connected to {ACT_HOST}:{ACT_PORT}")

    # 受信スレッド起動
    threading.Thread(target=rx_thread, args=(sock,), daemon=True).start()

    step_id = 0
    next_deadline = time.monotonic_ns()

    while step_id < TOTAL_STEPS:
        next_deadline += PERIOD_NS

        # コマンド生成（足し算用の値）
        cmd = generate_command(step_id)
        t_sim_send = now_ns()

        sock.sendall(
            pack(
                {
                    "command": {
                        "step_id": step_id,
                        "timestamp_ns": t_sim_send,
                        "cmd": cmd,
                    }
                }
            )
        )

        # 返信待ち：キューをポーリング
        got_reply = False
        t_sim_recv = None
        t_act_recv = None
        t_act_send = None
        received_result = 0.0

        deadline_wait = time.monotonic() + TIMEOUT_S
        while time.monotonic() < deadline_wait:
            try:
                rx_time, obj = rxq.get_nowait()
            except queue.Empty:
                # 少しだけ待つ（busy waitを避ける）
                time.sleep(0.0002)
                continue

            tel = obj.get("telemetry") if isinstance(obj, dict) else None
            if tel and tel.get("step_id") == step_id:
                got_reply = True
                t_sim_recv = rx_time
                t_act_recv = int(tel.get("t_act_recv_ns", 0))
                t_act_send = int(tel.get("t_act_send_ns", 0))
                received_result = tel.get("result", 0.0)
                break

        # 結果処理
        if got_reply:
            process_result({"result": received_result})

        # 周期境界まで待機
        now_ns_ = time.monotonic_ns()
        slack_ns = next_deadline - now_ns_
        deadline_miss_ms = 0.0
        if slack_ns > 0:
            time.sleep(slack_ns / 1_000_000_000)
        else:
            deadline_miss_ms = -slack_ns / 1_000_000
            print(f"[sim] DEADLINE MISS {deadline_miss_ms:.3f} ms @ step {step_id}")

        # ログ書き出し
        log.writerow(
            [
                step_id,
                t_sim_send,
                t_sim_recv or 0,
                t_act_recv or 0,
                t_act_send or 0,
                (not got_reply),
                f"{deadline_miss_ms:.3f}",
                cmd.get("value", 0.0),
                received_result,
            ]
        )
        log_file.flush()

        step_id += 1

print("[sim] finished by TOTAL_STEPS")
log_file.close()
