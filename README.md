# HiLSim-3 リアルタイムシミュレーション

10ms周期のリアルタイムシミュレーションシステムです。

## 機能

- **sim**: 周期制御を行うマスター（足し算コマンドを送信）
- **act**: アクチュエーター（受信した値を累積加算）
- **遅延シミュレーション**: tc コマンドによるネットワーク遅延
- **詳細ログ**: RTT測定用のタイムスタンプ記録

## 実行方法

```bash
# ヘルプ表示
make help

# シミュレーション実行（推奨）
make run

# バックグラウンド実行
make run-bg

# ログ確認
make logs
make logs-sim  # simのみ
make logs-act  # actのみ

# 最新ログディレクトリ確認
make show-latest-logs

# 停止
make down

# クリーンアップ
make clean
make clean-logs  # ログディレクトリ削除
```

## 設定

環境変数で設定を変更できます（docker-compose.yml内）:

- `TOTAL_STEPS`: 総実行ステップ数（デフォルト: 10000）
- `STEP_MS`: 周期（ms、デフォルト: 10）
- `REPLY_TIMEOUT_MS`: 応答待ち時間（ms、デフォルト: 2）
- `NETWORK_DELAY_MS`: ネットワーク遅延（ms、デフォルト: 1）

## ログファイル

ログは実行日時のディレクトリに保存されます：

- `./logs/YYYYMMDD_HHMMSS/sim_log.csv`: シミュレーターのログ
- `./logs/YYYYMMDD_HHMMSS/act_log.csv`: アクチュエーターのログ

例: `./logs/20240926_143022/sim_log.csv`

各ログにはRTT測定用のタイムスタンプが含まれています。

## 実装内容

**シミュレーション処理**: ステップごとに0.1ずつ増加する値を送信
**アクチュエーター処理**: 受信した値を累積加算して返信