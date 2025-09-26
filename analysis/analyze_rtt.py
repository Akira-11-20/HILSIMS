#!/usr/bin/env python3
"""
RTT解析スクリプト - HiLSim-3シミュレーションログのRTT分析とプロット
"""

import argparse
import glob
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def load_sim_data(log_dir):
    """シミュレーションログを読み込む"""
    sim_log = Path(log_dir) / "sim_log.csv"
    if not sim_log.exists():
        raise FileNotFoundError(f"sim_log.csv not found in {log_dir}")

    df = pd.read_csv(sim_log)

    # 必要な列が存在するかチェック
    required_cols = [
        "step_id",
        "t_sim_send_ns",
        "t_sim_recv_ns",
        "t_act_recv_ns",
        "t_act_send_ns",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")

    return df


def calculate_rtt_metrics(df):
    """RTT関連メトリクスを計算"""
    # 有効なデータのみ抽出（タイムアウトしていないもの）
    valid_mask = (
        (df["t_sim_recv_ns"] > 0)
        & (df["t_act_recv_ns"] > 0)
        & (df["t_act_send_ns"] > 0)
    )
    valid_df = df[valid_mask].copy()

    print(f"Total steps: {len(df)}")
    print(f"Valid responses: {len(valid_df)} ({len(valid_df)/len(df)*100:.1f}%)")

    # RTT計算（nanosecond -> microsecond）
    valid_df["e2e_rtt_us"] = (
        valid_df["t_sim_recv_ns"] - valid_df["t_sim_send_ns"]
    ) / 1000
    valid_df["sim_to_act_us"] = (
        valid_df["t_act_recv_ns"] - valid_df["t_sim_send_ns"]
    ) / 1000
    valid_df["act_to_sim_us"] = (
        valid_df["t_sim_recv_ns"] - valid_df["t_act_send_ns"]
    ) / 1000

    # 処理時間（アクチュエーター内）
    valid_df["act_processing_us"] = (
        valid_df["t_act_send_ns"] - valid_df["t_act_recv_ns"]
    ) / 1000

    # 時間軸（秒）
    start_time_ns = valid_df["t_sim_send_ns"].iloc[0]
    valid_df["time_s"] = (valid_df["t_sim_send_ns"] - start_time_ns) / 1_000_000_000

    return valid_df


def print_statistics(df):
    """RTT統計情報を表示"""
    print("\n=== RTT Statistics ===")

    metrics = {
        "E2E RTT": "e2e_rtt_us",
        "Sim->Act": "sim_to_act_us",
        "Act->Sim": "act_to_sim_us",
        "Act Processing": "act_processing_us",
    }

    for name, col in metrics.items():
        values = df[col]
        print(f"\n{name}:")
        print(f"  Mean:   {values.mean():.1f} μs")
        print(f"  Median: {values.median():.1f} μs")
        print(f"  Std:    {values.std():.1f} μs")
        print(f"  Min:    {values.min():.1f} μs")
        print(f"  Max:    {values.max():.1f} μs")
        print(f"  95%ile: {values.quantile(0.95):.1f} μs")
        print(f"  99%ile: {values.quantile(0.99):.1f} μs")


def create_plots(df, output_dir=None):
    """RTTプロットを作成"""
    # フィギュアサイズとスタイル設定
    plt.style.use("default")
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle("RTT Analysis - HiLSim-3", fontsize=16, fontweight="bold")

    # 1. 時系列RTTプロット
    ax1 = axes[0, 0]
    ax1.plot(
        df["time_s"], df["e2e_rtt_us"], "b-", alpha=0.7, linewidth=0.5, label="E2E RTT"
    )
    ax1.plot(
        df["time_s"],
        df["sim_to_act_us"],
        "g-",
        alpha=0.7,
        linewidth=0.5,
        label="Sim->Act",
    )
    ax1.plot(
        df["time_s"],
        df["act_to_sim_us"],
        "r-",
        alpha=0.7,
        linewidth=0.5,
        label="Act->Sim",
    )
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("RTT (μs)")
    ax1.set_title("RTT Time Series")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. RTTヒストグラム
    ax2 = axes[0, 1]
    ax2.hist(df["e2e_rtt_us"], bins=50, alpha=0.7, color="blue", edgecolor="black")
    ax2.axvline(
        df["e2e_rtt_us"].mean(),
        color="red",
        linestyle="--",
        label=f'Mean: {df["e2e_rtt_us"].mean():.1f}μs',
    )
    ax2.axvline(
        df["e2e_rtt_us"].median(),
        color="green",
        linestyle="--",
        label=f'Median: {df["e2e_rtt_us"].median():.1f}μs',
    )
    ax2.set_xlabel("E2E RTT (μs)")
    ax2.set_ylabel("Frequency")
    ax2.set_title("E2E RTT Distribution")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 処理時間分析
    ax3 = axes[1, 0]
    ax3.plot(df["time_s"], df["act_processing_us"], "purple", alpha=0.7, linewidth=0.5)
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Processing Time (μs)")
    ax3.set_title("Actuator Processing Time")
    ax3.grid(True, alpha=0.3)

    # 4. RTTボックスプロット
    ax4 = axes[1, 1]
    box_data = [
        df["e2e_rtt_us"],
        df["sim_to_act_us"],
        df["act_to_sim_us"],
        df["act_processing_us"],
    ]
    box_labels = ["E2E RTT", "Sim->Act", "Act->Sim", "Act Proc"]

    bp = ax4.boxplot(box_data, labels=box_labels, patch_artist=True)
    colors = ["lightblue", "lightgreen", "lightcoral", "plum"]
    for patch, color in zip(bp["boxes"], colors, strict=False):
        patch.set_facecolor(color)

    ax4.set_ylabel("Time (μs)")
    ax4.set_title("RTT Components Distribution")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存
    if output_dir:
        output_path = Path(output_dir) / "rtt_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"\nPlot saved to: {output_path}")

    plt.show()


def find_latest_log_dir():
    """最新のログディレクトリを見つける"""
    log_dirs = glob.glob("logs/*/sim_log.csv")
    if not log_dirs:
        raise FileNotFoundError("No log directories found in logs/")

    # 最新のディレクトリを取得
    latest = max(log_dirs, key=os.path.getmtime)
    return Path(latest).parent


def main():
    parser = argparse.ArgumentParser(description="RTT Analysis for HiLSim-3")
    parser.add_argument(
        "--log-dir", type=str, help="Log directory path (default: latest)"
    )
    parser.add_argument("--no-plot", action="store_true", help="Skip plotting")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output directory for plots (default: log directory)",
    )

    args = parser.parse_args()

    try:
        # ログディレクトリの決定
        if args.log_dir:
            log_dir = Path(args.log_dir)
        else:
            log_dir = find_latest_log_dir()
            print(f"Using latest log directory: {log_dir}")

        # データ読み込み
        print(f"Loading data from: {log_dir}")
        df = load_sim_data(log_dir)

        # RTT計算
        print("Calculating RTT metrics...")
        rtt_df = calculate_rtt_metrics(df)

        # 統計表示
        print_statistics(rtt_df)

        # 出力ディレクトリの決定（デフォルトはログディレクトリ）
        output_dir = Path(args.output) if args.output else log_dir

        # プロット作成
        if not args.no_plot:
            print("\nCreating plots...")
            create_plots(rtt_df, output_dir)

        # CSV出力
        output_csv = output_dir / "rtt_analysis.csv"
        rtt_df.to_csv(output_csv, index=False)
        print(f"\nRTT analysis saved to: {output_csv}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
