#!/usr/bin/env python3
"""
RTT時系列プロット - シミュレーション開始からの経過時間 vs RTT
"""

import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
import glob
import os

def load_and_process_data(log_dir):
    """ログデータを読み込んで処理"""
    sim_log = Path(log_dir) / 'sim_log.csv'
    if not sim_log.exists():
        raise FileNotFoundError(f"sim_log.csv not found in {log_dir}")

    df = pd.read_csv(sim_log)

    # 有効なデータのみ抽出
    valid_mask = (df['t_sim_recv_ns'] > 0) & (df['t_act_recv_ns'] > 0) & (df['t_act_send_ns'] > 0)
    valid_df = df[valid_mask].copy()

    # 開始時刻を基準とした経過時間（秒）
    start_time_ns = valid_df['t_sim_send_ns'].iloc[0]
    valid_df['elapsed_time_s'] = (valid_df['t_sim_send_ns'] - start_time_ns) / 1_000_000_000

    # RTT計算（マイクロ秒）
    valid_df['e2e_rtt_us'] = (valid_df['t_sim_recv_ns'] - valid_df['t_sim_send_ns']) / 1000
    valid_df['sim_to_act_us'] = (valid_df['t_act_recv_ns'] - valid_df['t_sim_send_ns']) / 1000
    valid_df['act_to_sim_us'] = (valid_df['t_sim_recv_ns'] - valid_df['t_act_send_ns']) / 1000

    return valid_df

def create_rtt_timeline_plot(df, output_file='rtt_timeline.png'):
    """RTT時系列プロットを作成"""
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(12, 6))

    # プロット
    ax.plot(df['elapsed_time_s'], df['e2e_rtt_us'], 'b-', linewidth=0.5, alpha=0.8, label='E2E RTT')
    ax.plot(df['elapsed_time_s'], df['sim_to_act_us'], 'g-', linewidth=0.5, alpha=0.7, label='Sim→Act')
    ax.plot(df['elapsed_time_s'], df['act_to_sim_us'], 'r-', linewidth=0.5, alpha=0.7, label='Act→Sim')

    # 平均線
    ax.axhline(df['e2e_rtt_us'].mean(), color='blue', linestyle='--', alpha=0.7,
               label=f'E2E Mean: {df["e2e_rtt_us"].mean():.0f}μs')

    # 軸設定
    ax.set_xlabel('Simulation Time (s)', fontsize=12)
    ax.set_ylabel('RTT (μs)', fontsize=12)
    ax.set_title('RTT vs Simulation Time - HiLSim-3', fontsize=14, fontweight='bold')

    # 凡例とグリッド
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # 統計情報をテキストで追加
    stats_text = f"""Statistics (E2E RTT):
Mean: {df['e2e_rtt_us'].mean():.1f} μs
Std:  {df['e2e_rtt_us'].std():.1f} μs
Min:  {df['e2e_rtt_us'].min():.1f} μs
Max:  {df['e2e_rtt_us'].max():.1f} μs
95%%ile: {df['e2e_rtt_us'].quantile(0.95):.1f} μs"""

    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"RTT timeline plot saved to: {output_file}")
    plt.close(fig)

    return output_file

def find_latest_log_dir():
    """最新のログディレクトリを見つける"""
    log_dirs = glob.glob('logs/*/sim_log.csv')
    if not log_dirs:
        raise FileNotFoundError("No log directories found in logs/")

    # 最新のディレクトリを取得
    latest = max(log_dirs, key=os.path.getmtime)
    return Path(latest).parent

def main():
    parser = argparse.ArgumentParser(description='RTT Timeline Plot for HiLSim-3')
    parser.add_argument('--log-dir', type=str, help='Log directory path (default: latest)')
    parser.add_argument('--output', '-o', type=str, help='Output PNG file path (default: save to log directory)')
    parser.add_argument('--show', action='store_true', help='Show plot window')

    args = parser.parse_args()

    try:
        # ログディレクトリの決定
        if args.log_dir:
            log_dir = Path(args.log_dir)
        else:
            log_dir = find_latest_log_dir()
            print(f"Using latest log directory: {log_dir}")

        # 出力ファイル名の決定
        if args.output:
            output_file = args.output
        else:
            output_file = log_dir / 'rtt_timeline.png'

        # データ読み込みと処理
        print(f"Loading data from: {log_dir}")
        df = load_and_process_data(log_dir)

        print(f"Processing {len(df)} valid data points...")
        print(f"Simulation duration: {df['elapsed_time_s'].max():.1f} seconds")

        # プロット作成
        output_path = create_rtt_timeline_plot(df, output_file)

        if args.show:
            plt.show()

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())