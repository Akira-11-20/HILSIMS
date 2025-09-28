import os
import sys
import socket
import time
import json
import subprocess
import random

sys.path.append("/app")
from common.protocol import pack, recv_obj, now_ns

from ..simulation_factory import SimulationFactory


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


def setup_network_delay(delay_ms: int, variance_ms: float = 0, distribution: str = "normal") -> None:
    """
    ネットワーク遅延をtcコマンドで設定（レガシー関数、分散対応）

    Args:
        delay_ms: 基本遅延時間（ミリ秒）
        variance_ms: 遅延の分散（標準偏差、ミリ秒）
        distribution: 分布タイプ ("normal", "uniform", "pareto")

    Note:
        下位互換性のため維持。新しいコードでは setup_bidirectional_delay を使用
        tcのnetemは双方向遅延のため、個別方向制御には制限あり
    """
    if delay_ms > 0:
        try:
            # 既存の設定をクリア
            subprocess.run(
                ["sudo", "tc", "qdisc", "del", "dev", "eth0", "root"],
                capture_output=True,
                check=False,
            )

            # tcコマンドを構築
            cmd = [
                "sudo", "tc", "qdisc", "add", "dev", "eth0", "root", "netem",
                "delay", f"{delay_ms}ms"
            ]

            # 分散を追加
            if variance_ms > 0:
                cmd.append(f"{variance_ms}ms")

                # 分布タイプを追加
                if distribution == "uniform":
                    cmd.extend(["distribution", "uniform"])
                elif distribution == "pareto":
                    cmd.extend(["distribution", "pareto"])
                # normalはデフォルトなので指定不要

            # 遅延を設定
            subprocess.run(cmd, check=True)

            if variance_ms > 0:
                print(f"[sim] Network delay set to {delay_ms}ms±{variance_ms}ms ({distribution}) (bidirectional)")
            else:
                print(f"[sim] Network delay set to {delay_ms}ms (bidirectional)")

        except subprocess.CalledProcessError as e:
            print(f"[sim] Failed to set network delay: {e}")
        except FileNotFoundError:
            print("[sim] tc command not found, skipping network delay setup")


def apply_sim_to_hw_delay(delay_ms: int, variance_ms: float = 0, distribution: str = "normal") -> None:
    """
    シミュレータからハードウェアへの送信時に遅延を適用

    Args:
        delay_ms: 基本遅延時間（ミリ秒）
        variance_ms: 遅延の分散（標準偏差、ミリ秒）
        distribution: 分布タイプ ("normal", "uniform", "exponential")

    Note:
        time.sleep()のオーバーヘッドを考慮して補正
        実測で約0.2ms/msのオーバーヘッドがあるため補正
    """
    if delay_ms > 0:
        # 分散を適用した遅延時間を計算
        actual_delay_ms = _calculate_delay_with_variance(delay_ms, variance_ms, distribution)

        # sleep()オーバーヘッド補正（実測値に基づく調整）
        # 1ms実測→1.2ms なので0.2ms減らす必要がある
        overhead_correction = actual_delay_ms * 0 / 1000.0  # 35%のオーバーヘッド補正
        corrected_delay = max(0, (actual_delay_ms / 1000.0) - overhead_correction)
        time.sleep(corrected_delay)


def cleanup_tc_delay() -> None:
    """
    tcネットワーク遅延設定をクリーンアップ
    """
    try:
        # 既存設定をクリア
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "eth0", "root"], capture_output=True, check=False)
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", "eth0", "ingress"], capture_output=True, check=False)

        # IFBデバイスを削除
        subprocess.run(["sudo", "ip", "link", "del", "ifb0"], capture_output=True, check=False)

        print("[sim] TC network delay settings cleaned up")
    except Exception as e:
        print(f"[sim] Warning: TC cleanup failed: {e}")


def setup_tc_egress_delay(
    delay_ms: int, variance_ms: float = 0, distribution: str = "normal", container_type: str = "sim"
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


def setup_bidirectional_delay(
    sim_to_hw_ms: int, hw_to_sim_ms: int, legacy_ms: int = 0,
    sim_to_hw_variance_ms: float = 0, hw_to_sim_variance_ms: float = 0, legacy_variance_ms: float = 0,
    sim_to_hw_distribution: str = "normal", hw_to_sim_distribution: str = "normal", legacy_distribution: str = "normal"
) -> tuple[int, int, float, float, str, str]:
    """
    双方向ネットワーク遅延設定

    Args:
        sim_to_hw_ms: シミュレータ→ハードウェア遅延（ms）
        hw_to_sim_ms: ハードウェア→シミュレータ遅延（ms）
        legacy_ms: レガシー設定（両方向、優先度低）
        sim_to_hw_variance_ms: シミュレータ→ハードウェア分散（ms）
        hw_to_sim_variance_ms: ハードウェア→シミュレータ分散（ms）
        legacy_variance_ms: レガシー分散設定（両方向）
        sim_to_hw_distribution: シミュレータ→ハードウェア分布タイプ
        hw_to_sim_distribution: ハードウェア→シミュレータ分布タイプ
        legacy_distribution: レガシー分布タイプ

    Returns:
        (sim→hw遅延, hw→sim遅延, sim→hw分散, hw→sim分散, sim→hw分布, hw→sim分布) のタプル

    Note:
        個別設定が0の場合はレガシー設定を使用
        シミュレータ側では送信遅延のみ適用、受信遅延はハードウェア側で適用
    """
    # 個別設定が指定されている場合は優先、そうでなければレガシー設定を使用
    actual_sim_to_hw = sim_to_hw_ms if sim_to_hw_ms > 0 else legacy_ms
    actual_hw_to_sim = hw_to_sim_ms if hw_to_sim_ms > 0 else legacy_ms

    actual_sim_to_hw_variance = sim_to_hw_variance_ms if sim_to_hw_variance_ms > 0 else legacy_variance_ms
    actual_hw_to_sim_variance = hw_to_sim_variance_ms if hw_to_sim_variance_ms > 0 else legacy_variance_ms

    actual_sim_to_hw_distribution = sim_to_hw_distribution if sim_to_hw_ms > 0 else legacy_distribution
    actual_hw_to_sim_distribution = hw_to_sim_distribution if hw_to_sim_ms > 0 else legacy_distribution

    if actual_sim_to_hw > 0 or actual_hw_to_sim > 0:
        print(f"[sim] Network delay configured: SIM→HW {actual_sim_to_hw}ms±{actual_sim_to_hw_variance}ms({actual_sim_to_hw_distribution}), HW→SIM {actual_hw_to_sim}ms±{actual_hw_to_sim_variance}ms({actual_hw_to_sim_distribution})")

    return actual_sim_to_hw, actual_hw_to_sim, actual_sim_to_hw_variance, actual_hw_to_sim_variance, actual_sim_to_hw_distribution, actual_hw_to_sim_distribution


def main():
    """汎用シミュレーターメイン"""
    # 環境変数でシミュレーション種類を指定
    sim_type = os.environ.get("SIM_TYPE", "numeric")

    # 設定取得
    act_host = os.environ.get("ACT_HOST", "hardware")
    act_port = int(os.environ.get("ACT_PORT", "5001"))
    step_ms = int(os.environ.get("STEP_MS", "10"))
    total_steps = int(os.environ.get("TOTAL_STEPS", "1000"))

    # ネットワーク遅延設定（新旧両対応）
    legacy_delay_ms = int(os.environ.get("NETWORK_DELAY_MS", "0"))
    sim_to_hw_delay_ms = int(os.environ.get("NETWORK_DELAY_SIM_TO_HW_MS", "0"))
    hw_to_sim_delay_ms = int(os.environ.get("NETWORK_DELAY_HW_TO_SIM_MS", "0"))

    # 遅延分散設定
    sim_to_hw_variance_ms = float(os.environ.get("NETWORK_DELAY_SIM_TO_HW_VARIANCE_MS", "0"))
    hw_to_sim_variance_ms = float(os.environ.get("NETWORK_DELAY_HW_TO_SIM_VARIANCE_MS", "0"))
    legacy_variance_ms = float(os.environ.get("NETWORK_DELAY_VARIANCE_MS", "0"))

    # 分布タイプ設定
    sim_to_hw_distribution = os.environ.get("NETWORK_DELAY_SIM_TO_HW_DISTRIBUTION", "normal")
    hw_to_sim_distribution = os.environ.get("NETWORK_DELAY_HW_TO_SIM_DISTRIBUTION", "normal")
    legacy_distribution = os.environ.get("NETWORK_DELAY_DISTRIBUTION", "normal")

    print(f"[sim] Starting {sim_type} simulation")
    print(f"[sim] Target: {act_host}:{act_port}, Steps: {total_steps}, Interval: {step_ms}ms")

    # 双方向ネットワーク遅延設定
    actual_sim_to_hw, actual_hw_to_sim, actual_sim_to_hw_variance, actual_hw_to_sim_variance, actual_sim_to_hw_distribution, actual_hw_to_sim_distribution = setup_bidirectional_delay(
        sim_to_hw_delay_ms, hw_to_sim_delay_ms, legacy_delay_ms,
        sim_to_hw_variance_ms, hw_to_sim_variance_ms, legacy_variance_ms,
        sim_to_hw_distribution, hw_to_sim_distribution, legacy_distribution
    )

    # tcベース遅延の適用判定
    tc_sim_success = False
    if legacy_delay_ms > 0 and sim_to_hw_delay_ms == 0 and hw_to_sim_delay_ms == 0:
        # レガシー設定の場合はtcベース双方向遅延を適用
        print("[sim] Using tc-based network delay (legacy mode)")
        setup_network_delay(legacy_delay_ms, legacy_variance_ms, legacy_distribution)
        tc_sim_success = True
    elif actual_sim_to_hw > 0:
        # シミュレータ側のtc egress遅延を設定
        print("[sim] Setting up tc egress delay for sim→hw communication")
        tc_sim_success = setup_tc_egress_delay(
            actual_sim_to_hw, actual_sim_to_hw_variance, actual_sim_to_hw_distribution, "sim"
        )

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

                # 送信タイムスタンプを遅延適用前に記録（RTT測定用）
                t_sim_send = now_ns()

                # 送信前遅延適用（シミュレータ→ハードウェア）
                # tc設定が成功した場合はsleep遅延をスキップ
                if not tc_sim_success:
                    apply_sim_to_hw_delay(actual_sim_to_hw, actual_sim_to_hw_variance, actual_sim_to_hw_distribution)

                # 実際の送信タイムスタンプ（遅延適用後）
                t_sim_send_actual = now_ns()

                # 送信 (共通プロトコル使用)
                command_msg = {
                    "command": {
                        "step_id": step_id,
                        "timestamp_ns": t_sim_send,  # RTT測定用（遅延前）
                        "timestamp_actual_ns": t_sim_send_actual,  # 実際の送信時刻
                        "cmd": cmd,
                        "hw_to_sim_delay_ms": actual_hw_to_sim,  # ハードウェア側に返信遅延を指示
                        "hw_to_sim_variance_ms": actual_hw_to_sim_variance,  # ハードウェア側分散
                        "hw_to_sim_distribution": actual_hw_to_sim_distribution,  # ハードウェア側分布
                        "use_tc_egress": actual_hw_to_sim > 0,  # ハードウェア側でtc egress使用指示
                        "applied_sim_to_hw_delay_ms": actual_sim_to_hw  # 適用した送信遅延
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
            # tcネットワーク遅延設定をクリーンアップ
            if tc_sim_success:
                cleanup_tc_delay()

    except ValueError as e:
        print(f"[sim] Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[sim] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()