# HiLSim-3 シミュレーション構成ドキュメント

## 概要

HiLSim-3は、リアルタイム通信を重視したハードウェア・イン・ザ・ループ（HiL）シミュレーションシステムです。Dockerベースの分散アーキテクチャで、シミュレーター（Simulator）とハードウェア（Hardware）間の通信遅延（RTT: Round Trip Time）の詳細な分析機能を提供します。

## アーキテクチャ

### システム構成

```
┌─────────────────┐    TCP通信    ┌─────────────────┐
│   Simulator     │ ◄──────────► │    Hardware     │
│   Container     │              │   Container     │
└─────────────────┘              └─────────────────┘
```

- **Simulator Container**: シミュレーション計算を実行し、各ステップの結果をHardwareに送信
- **Hardware Container**: Hardwareの動作を模擬し、Simulatorからのコマンドに応答
- **通信方式**: カスタムTCPプロトコル（JSON + バイナリヘッダー）

## プロジェクト構造

```
hilsim-3/
├── hils/                       # メインパッケージ
│   ├── core/                   # コアシステム
│   │   ├── hw/                 # Hardware用Dockerコンテナ
│   │   │   ├── Dockerfile      # Hardware用イメージ
│   │   │   ├── hardware_base.py # Hardware基底クラス
│   │   │   └── hw_app.py       # Hardwareアプリケーション
│   │   ├── sim/                # Simulator用Dockerコンテナ
│   │   │   ├── Dockerfile      # Simulator用イメージ
│   │   │   ├── simulator_base.py # Simulator基底クラス
│   │   │   └── sim_app.py      # Simulatorアプリケーション
│   │   └── simulation_factory.py # 動的シミュレーション生成
│   ├── hardware/               # Hardware実装
│   │   ├── numeric_hw.py       # 数値計算Hardware
│   │   └── vehicle.py          # 車両Hardware
│   └── simulators/             # Simulator実装
│       ├── numeric_sim.py      # 数値計算Simulator
│       └── vehicle.py          # 車両Simulator
├── common/                     # 共通ライブラリ
│   ├── protocol.py             # 通信プロトコル
│   └── logging_utils.py        # ログ管理
├── analysis/                   # 分析ツール
│   ├── analyze_rtt.py          # RTT分析スクリプト
│   └── plot_rtt_timeline.py    # RTT可視化
├── logs/                       # ログ出力ディレクトリ
├── docker-compose.yml          # Docker構成
├── Makefile                    # 実行コマンド
├── pyproject.toml              # Python設定
└── .env.example                # 環境変数テンプレート
```

## 設定システム

### 環境変数 (.env)

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| `SIM_TYPE` | `numeric` | シミュレーター種類 (`numeric`, `vehicle`) |
| `HW_TYPE` | `numeric` | ハードウェア種類 (`numeric`, `vehicle`) |
| `STEP_MS` | `10` | シミュレーションステップ間隔（ミリ秒） |
| `REPLY_TIMEOUT_MS` | `2` | ステップ応答タイムアウト（ミリ秒） |
| `TOTAL_STEPS` | `1000` | 総シミュレーションステップ数 |
| `NETWORK_DELAY_MS` | `0` | ネットワーク遅延シミュレーション（ミリ秒） |
| `ACT_HOST` | `hardware` | Hardware接続ホスト名 |
| `ACT_PORT` | `5001` | 通信ポート番号 |
| `LOG_TIMESTAMP` | 自動生成 | ログタイムスタンプ |

### シミュレーション種類

#### Numeric シミュレーション
- **用途**: 基本通信テスト、プロトコル検証
- **特徴**: 単純な数値計算、最小限のオーバーヘッド
- **Simulator**: 連続する数値を送信
- **Hardware**: 受信した値を倍にして返信

#### Vehicle シミュレーション
- **用途**: 車両動力学シミュレーション
- **特徴**: 物理法則に基づく車両モデル
- **Simulator**: 車両の位置・速度・加速度を計算
- **Hardware**: アクセル・ブレーキ・ステアリング制御をシミュレート

## 通信プロトコル

### プロトコル仕様

```python
# ヘッダー構造 (8バイト)
MAGIC = 0xFEEDBEEF        # マジックナンバー (4バイト)
LENGTH = len(payload)      # ペイロード長 (4バイト)

# メッセージ形式
[HEADER(8)] + [JSON_PAYLOAD(n)]
```

### メッセージ例

```json
{
  "step": 123,
  "timestamp": 1234567890123456789,
  "data": {
    "position": [1.0, 2.0],
    "velocity": [0.5, 0.0],
    "acceleration": [0.1, 0.0]
  }
}
```

## Docker構成

### コンテナ構成

```yaml
services:
  simulator:
    container_name: hilsim_simulator
    environment:
      - SIM_TYPE=${SIM_TYPE:-numeric}
      - ACT_HOST=${ACT_HOST:-hardware}
      - STEP_MS=${STEP_MS:-10}
      # ... その他の環境変数

  hardware:
    container_name: hilsim_hardware
    environment:
      - HW_TYPE=${HW_TYPE:-numeric}
      - ACT_PORT=${ACT_PORT:-5001}
      # ... その他の環境変数
```

### ネットワーク
- **ネットワーク名**: `simnet`
- **ドライバー**: `bridge`
- **特権機能**: `NET_ADMIN` (tcコマンドによる遅延シミュレーション用)

## 実行方法

### Makefileコマンド

| コマンド | 説明 |
|----------|------|
| `make run` | 現在の設定でシミュレーション実行 |
| `make run-vehicle` | 車両シミュレーション実行 |
| `make run-numeric` | 数値シミュレーション実行 |
| `make config` | 現在の設定表示 |
| `make logs` | コンテナログ表示 |
| `make status` | コンテナ状態確認 |
| `make clean` | コンテナとイメージ削除 |

### 実行例

```bash
# 基本実行
make run

# 車両シミュレーション
make run-vehicle

# 設定確認
make config

# ログ確認
make logs
```

## ログシステム

### ログ構造

```
logs/
└── 20240926_143022/          # タイムスタンプディレクトリ
    ├── simulator_rtt.csv     # Simulator側RTT記録
    ├── hardware_rtt.csv      # Hardware側RTT記録
    ├── simulator.log         # Simulatorアプリケーションログ
    └── hardware.log          # Hardwareアプリケーションログ
```

### RTTログ形式

```csv
step,send_ns,recv_ns,rtt_ns,rtt_ms
1,1234567890123456789,1234567890125456789,2000000,2.0
2,1234567890135456789,1234567890137456789,2000000,2.0
```

## 分析機能

### RTT分析
- **スクリプト**: `analysis/analyze_rtt.py`
- **機能**: RTT統計、タイムアウト検出、外れ値分析
- **出力**: 統計レポート、可視化グラフ

### 可視化
- **スクリプト**: `analysis/plot_rtt_timeline.py`
- **機能**: RTT時系列プロット、ヒストグラム、分布分析

## 拡張性

### カスタムシミュレーション追加

1. **Simulatorの追加**:
   ```python
   # hils/simulators/custom.py
   class CustomProcessor(SimulatorProcessor):
       def process_step(self, step: int) -> dict:
           # カスタム処理
           pass

   class CustomLogger(SimulatorLogger):
       # カスタムログ処理
       pass
   ```

2. **Hardwareの追加**:
   ```python
   # hils/hardware/custom.py
   class CustomProcessor(HardwareProcessor):
       def process_command(self, data: dict) -> dict:
           # カスタム処理
           pass

   class CustomLogger(HardwareLogger):
       # カスタムログ処理
       pass
   ```

3. **環境変数設定**:
   ```bash
   export SIM_TYPE=custom
   export HW_TYPE=custom
   ```

### 動的ロード
- `SimulationFactory`が自動的にカスタムモジュールを検出
- クラス名規則: `{type.title()}Processor`, `{type.title()}Logger`

## 開発・テスト

### 開発環境セットアップ
```bash
# 依存関係インストール
make install

# テスト実行
make test

# コード品質チェック
make lint

# コードフォーマット
make format
```

### テスト構成
- **フレームワーク**: pytest
- **リンター**: ruff, mypy
- **フォーマッター**: black
- **プリコミット**: pre-commit

## パフォーマンス特性

### 想定性能
- **ステップ間隔**: 1-100ms
- **RTT**: <10ms (ローカル環境)
- **スループット**: >100 steps/sec
- **遅延シミュレーション**: 0-1000ms

### モニタリング
- リアルタイムRTT記録
- タイムアウト検出
- コンテナリソース使用量追跡

## トラブルシューティング

### よくある問題

1. **コンテナ起動失敗**
   - ポート衝突確認: `docker ps`
   - ログ確認: `make logs`

2. **通信タイムアウト**
   - `REPLY_TIMEOUT_MS`増加
   - ネットワーク遅延確認

3. **ログ出力なし**
   - 権限確認: `logs/`ディレクトリ
   - `LOG_TIMESTAMP`設定確認

### デバッグ手順
1. `make config` で設定確認
2. `make status` でコンテナ状態確認
3. `make logs` でエラーログ確認
4. `make show-logs` で最新ログファイル確認

---

**更新日**: 2024年9月26日
**バージョン**: HiLSim-3 v1.0.0