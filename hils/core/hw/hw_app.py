import os
import sys
import socket
import json
import time
import random
import subprocess

sys.path.append("/app")
from common.protocol import pack, recv_obj, now_ns

from ..simulation_factory import SimulationFactory


def setup_tc_egress_delay(
    delay_ms: int, variance_ms: float = 0, distribution: str = "normal", container_type: str = "hw"
) -> bool:
    """
    tcを使ったegress（送信）遅延設定

    Args:
        delay_ms: 遅延時間（ms）
        variance_ms: 遅延の分散（標準偏差、ms）
        distribution: 分布タイプ ("normal", "uniform", "pareto")
        container_type: コンテナタイプ ("sim" or "hw")

    Returns:
        True: 設定成功, False: 設定失敗

    Note:
        各コンテナで送信側のみを制御するシンプルなアプローチ
    """
    if delay_ms <= 0:
        return True  # 遅延なしの場合は何もしない

    try:
        # 既存設定をクリア
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "eth0", "root"], capture_output=True, check=False)

        # egress遅延を設定
        cmd = ["sudo", "tc", "qdisc", "add", "dev", "eth0", "root", "netem", "delay", f"{delay_ms}ms"]

        if variance_ms > 0:
            cmd.append(f"{variance_ms}ms")
            if distribution == "uniform":
                cmd.extend(["distribution", "uniform"])
            elif distribution == "pareto":
                cmd.extend(["distribution", "pareto"])
            # normalはデフォルトなので指定不要

        subprocess.run(cmd, check=True)
        print(f"[{container_type}] TC egress delay set: {delay_ms}ms±{variance_ms}ms ({distribution})")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[{container_type}] Failed to set TC egress delay: {e}")
        return False
    except FileNotFoundError:
        print(f"[{container_type}] tc command not found")
        return False


def cleanup_tc_delay() -> None:
    """
    tcネットワーク遅延設定をクリーンアップ
    """
    try:
        # 既存設定をクリア
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "eth0", "root"], capture_output=True, check=False)
        print("[hw] TC network delay settings cleaned up")
    except Exception as e:
        print(f"[hw] Warning: TC cleanup failed: {e}")


def _calculate_delay_with_variance(base_delay_ms: int, variance_ms: float, distribution: str) -> float:
    """
    分散を考慮した遅延時間を計算

    Args:
        base_delay_ms: 基本遅延時間（ミリ秒）
        variance_ms: 分散の標準偏差（ミリ秒）
        distribution: 分布タイプ ("normal", "uniform", "exponential")

    Returns:
        実際の遅延時間（ミリ秒）、負の値は0にクリップ
    """
    if variance_ms <= 0:
        return float(base_delay_ms)

    if distribution == "normal":
        # 正規分布: N(base_delay, variance^2)
        delay = random.gauss(base_delay_ms, variance_ms)
    elif distribution == "uniform":
        # 一様分布: [base_delay - variance, base_delay + variance]
        delay = random.uniform(base_delay_ms - variance_ms, base_delay_ms + variance_ms)
    elif distribution == "exponential":
        # 指数分布: 平均がbase_delayになるようにスケール
        # variance_msは変動の度合いとして使用
        scale = base_delay_ms / (1 + variance_ms / base_delay_ms)
        delay = random.expovariate(1.0 / scale)
    else:
        # 不明な分布タイプの場合は正規分布を使用
        delay = random.gauss(base_delay_ms, variance_ms)

    # 負の遅延は0にクリップ
    return max(0.0, delay)


def apply_hw_to_sim_delay(delay_ms: int, variance_ms: float = 0, distribution: str = "normal") -> None:
    """
    ハードウェアからシミュレータへの送信時に遅延を適用

    Args:
        delay_ms: 基本遅延時間（ミリ秒）
        variance_ms: 遅延の分散（標準偏差、ミリ秒）
        distribution: 分布タイプ ("normal", "uniform", "exponential")

    Note:
        time.sleep()のオーバーヘッドを考慮して補正
        実測で約0.26ms/msのオーバーヘッドがあるため補正
    """
    if delay_ms > 0:
        # 分散を適用した遅延時間を計算
        actual_delay_ms = _calculate_delay_with_variance(delay_ms, variance_ms, distribution)

        # sleep()オーバーヘッド補正（実測値に基づく調整）
        # 2ms実測→1.9ms なので0.1ms増やす必要がある（補正を減らす）
        overhead_correction = actual_delay_ms * 0 / 1000.0  # 20%のオーバーヘッド補正
        corrected_delay = max(0, (actual_delay_ms / 1000.0) - overhead_correction)
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

    # tc設定状態を追跡
    tc_hw_configured = False

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
                    hw_to_sim_variance_ms = command.get("hw_to_sim_variance_ms", 0)
                    hw_to_sim_distribution = command.get("hw_to_sim_distribution", "normal")
                    use_tc_egress = command.get("use_tc_egress", False)

                    # tcベース遅延設定（一回だけ実行）
                    if use_tc_egress and not tc_hw_configured:
                        print(f"[hw] Setting up tc egress delay for hw→sim communication")
                        tc_hw_success = setup_tc_egress_delay(
                            hw_to_sim_delay_ms, hw_to_sim_variance_ms, hw_to_sim_distribution, "hw"
                        )
                        tc_hw_configured = tc_hw_success

                    # 処理実行
                    result = processor.process_command(cmd_data)

                    # 送信タイムスタンプを遅延適用前に記録（RTT測定用）
                    t_send = now_ns()

                    # 送信前遅延適用（ハードウェア→シミュレータ）
                    # tc設定が成功した場合はsleep遅延をスキップ
                    if not tc_hw_configured:
                        apply_hw_to_sim_delay(hw_to_sim_delay_ms, hw_to_sim_variance_ms, hw_to_sim_distribution)

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
            # tcネットワーク遅延設定をクリーンアップ
            if tc_hw_configured:
                cleanup_tc_delay()

    except ValueError as e:
        print(f"[hw] Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[hw] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()