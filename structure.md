# 概要（更新版）

* **目的**: 同一ホスト上で `sim`（マスター）と `act`（アクチュエーター）を10ms周期で動作。**終了条件は総ステップ数**で管理。
* **通信**: TCP + 長さ付きJSON。**非同期受信キュー**を導入して、返信はバックグラウンドで受信・時刻記録。`sim`のメインループは周期を守り、**期限内にキューに無ければゼロ指令**。
* **可変コマンド**: `cmd`は任意のJSON（配列でも辞書でも可）。シミュレーション内容に応じて自由に拡張可能。
* **時刻記録**: `t_sim_send` と **最終的に受信した時刻** `t_sim_recv` を保持。さらに `act`側で `t_act_recv` / `t_act_send` を記録。**RTT/E2E**を後からCSVで解析可能。
* **CSVログ**: `sim` と `act`の双方で詳細CSVを保存（コンテナ内 `/app/logs`）。

---

## ディレクトリ構成

```
rt-sim/
├─ docker-compose.yml
├─ common/
│  └─ protocol.py   # フレーミング、型ユーティリティ
├─ sim/
│  ├─ Dockerfile
│  └─ sim.py        # マスター（周期制御、非同期受信キュー、CSVログ）
└─ act/
   ├─ Dockerfile
   └─ actuator.py   # アクチュエーター（任意返信、CSVログ）
```

---

## docker-compose.yml（総ステップで終了）

```yaml
version: "3.9"
services:
  act:
    build: ./act
    container_name: rt_act
    environment:
      - ACT_HOST=0.0.0.0
      - ACT_PORT=5001
      - STEP_MS=10
    networks: [ simnet ]

  sim:
    build: ./sim
    container_name: rt_sim
    environment:
      - ACT_HOST=act
      - ACT_PORT=5001
      - STEP_MS=10
      - REPLY_TIMEOUT_MS=2      # ステップ内で待つ時間
      - TOTAL_STEPS=10000       # 総ステップ（例：100秒＝10000*10ms）
    depends_on:
      - act
    networks: [ simnet ]

networks:
  simnet:
    driver: bridge
```

> 実用時は `TOTAL_STEPS` を必要な総時間(秒)×100 で設定してください。

---

## common/protocol.py（可変コマンド＆フレーミング）

```python
import json, struct, time
from typing import Any, Optional

MAGIC = 0xfeedbeef
HEADER = struct.Struct('!II')  # magic, length (big-endian)

now_ns = time.monotonic_ns  # 単調時刻（ns）

def pack(obj: dict) -> bytes:
    payload = json.dumps(obj, ensure_ascii=False, separators=(',',':')).encode('utf-8')
    return HEADER.pack(MAGIC, len(payload)) + payload

def recv_exact(sock, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError('socket closed')
        buf.extend(chunk)
    return bytes(buf)

def recv_obj(sock, timeout: Optional[float]=None) -> dict:
    if timeout is not None:
        sock.settimeout(timeout)
    header = recv_exact(sock, HEADER.size)
    magic, ln = HEADER.unpack(header)
    if magic != MAGIC:
        raise ValueError('bad magic')
    payload = recv_exact(sock, ln)
    return json.loads(payload.decode('utf-8'))
```

---

## act/actuator.py（返信任意・CSVログ）

```python
import os, socket, csv, pathlib
from common.protocol import pack, recv_obj, now_ns

HOST = os.environ.get('ACT_HOST','0.0.0.0')
PORT = int(os.environ.get('ACT_PORT','5001'))
STEP_MS = int(os.environ.get('STEP_MS','10'))

logs = pathlib.Path('/app/logs'); logs.mkdir(parents=True, exist_ok=True)
log_file = (logs / 'act_log.csv').open('w', newline='')
log = csv.writer(log_file)
log.writerow(['step_id','t_act_recv_ns','t_act_send_ns','missing_cmd','note'])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[act] listening on {HOST}:{PORT}")
    conn, addr = srv.accept()
    with conn:
        print(f"[act] connected: {addr}")
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        expected_step = 0
        while True:
            try:
                msg = recv_obj(conn, timeout=None)  # simがペースメーカー
                t_recv = now_ns()
                cmd = msg.get('command') or {}
                step_id = cmd.get('step_id', -1)
                # ここでアクチュエーターの実計算を行う（省略）
                # 任意に返信する（ここでは毎回返信）
                t_send = now_ns()
                tel = {
                    'telemetry': {
                        'step_id': step_id,
                        't_act_recv_ns': t_recv,
                        't_act_send_ns': t_send,
                        'missing_cmd': False,
                        'note': ''
                    }
                }
                conn.sendall(pack(tel))
                log.writerow([step_id, t_recv, t_send, False, ''])
            except Exception as e:
                print(f"[act] error/closed: {e}")
                break

log_file.close()
```

---

## sim/sim.py（非同期受信キュー・総ステップで終了・CSVログ）

```python
import os, socket, time, threading, queue, csv, pathlib
from common.protocol import pack, recv_obj, now_ns

ACT_HOST = os.environ.get('ACT_HOST','act')
ACT_PORT = int(os.environ.get('ACT_PORT','5001'))
STEP_MS = int(os.environ.get('STEP_MS','10'))
REPLY_TIMEOUT_MS = int(os.environ.get('REPLY_TIMEOUT_MS','2'))
TOTAL_STEPS = int(os.environ.get('TOTAL_STEPS','1000'))

PERIOD_NS = STEP_MS * 1_000_000
TIMEOUT_S = REPLY_TIMEOUT_MS / 1000.0

# ログ準備
logs = pathlib.Path('/app/logs'); logs.mkdir(parents=True, exist_ok=True)
log_file = (logs / 'sim_log.csv').open('w', newline='')
log = csv.writer(log_file)
log.writerow([
    'step_id','t_sim_send_ns','t_sim_recv_ns','t_act_recv_ns','t_act_send_ns',
    'timeout','deadline_miss_ms'
])

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

# 例：状態更新（デモ）
state = {'x': 0.0}

def plant_step(cmd_any):
    # cmdが配列なら合計を速度と解釈、辞書なら 'v' を見る（柔軟）
    v = 0.0
    if isinstance(cmd_any, list):
        v = sum(float(x) for x in cmd_any)
    elif isinstance(cmd_any, dict):
        v = float(cmd_any.get('v', 0.0))
    state['x'] += v * (STEP_MS/1000.0)

with socket.create_connection((ACT_HOST, ACT_PORT)) as sock:
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    print(f"[sim] connected to {ACT_HOST}:{ACT_PORT}")

    # 受信スレッド起動
    threading.Thread(target=rx_thread, args=(sock,), daemon=True).start()

    step_id = 0
    next_deadline = time.monotonic_ns()

    while step_id < TOTAL_STEPS:
        next_deadline += PERIOD_NS
        # 任意のコマンド（配列でも辞書でもOK）
        cmd = {'v': 0.1}  # 例：速度0.1 [units/s]
        t_sim_send = now_ns()
        sock.sendall(pack({'command': {
            'step_id': step_id,
            'timestamp_ns': t_sim_send,
            'cmd': cmd
        }}))

        # 返信待ち：キューをポーリング
        got_reply = False
        t_sim_recv = None
        t_act_recv = None
        t_act_send = None

        deadline_wait = time.monotonic() + TIMEOUT_S
        while time.monotonic() < deadline_wait:
            try:
                rx_time, obj = rxq.get_nowait()
            except queue.Empty:
                # 少しだけ待つ（busy waitを避ける）
                time.sleep(0.0002)
                continue
            tel = obj.get('telemetry') if isinstance(obj, dict) else None
            if tel and tel.get('step_id') == step_id:
                got_reply = True
                t_sim_recv = rx_time
                t_act_recv = int(tel.get('t_act_recv_ns', 0))
                t_act_send = int(tel.get('t_act_send_ns', 0))
                break
            # 他ステップの返信は保持せず破棄（必要ならバッファリング方針に変更）

        # プラント更新（返信なしはゼロ指令）
        plant_step(cmd if got_reply else ( {'v':0.0} if isinstance(cmd, dict) else [0.0] ))

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
        log.writerow([
            step_id,
            t_sim_send,
            t_sim_recv or 0,
            t_act_recv or 0,
            t_act_send or 0,
            (not got_reply),
            f"{deadline_miss_ms:.3f}"
        ])

        step_id += 1

print('[sim] finished by TOTAL_STEPS')
log_file.close()
```

---

## 解析のヒント（RTT計算）

* 最終的に受け取った時刻 `t_sim_recv` と 送信時刻 `t_sim_send` の差で **E2E RTT**（ns）
* 片方向（推定）：

  * sim→act ≈ `t_act_recv - t_sim_send`
  * act→sim ≈ `t_sim_recv - t_act_send`
* CSVは `/app/logs/sim_log.csv`, `/app/logs/act_log.csv` に保存。

---

## 運用フロー

```bash
# プロジェクト直下
docker compose up --build
# 終了は TOTAL_STEPS 到達で自動。ログは ./sim/logs と ./act/logs の各コンテナ内 /app/logs に出力
```

---

## 今後の拡張ポイント

* `cmd`と`telemetry`のスキーマをバージョン付け（`schema_ver`）
* 遅延・欠損の統計要約を定期出力
* ログのローテーション、Parquet対応
* 厳密なステップ整合を求めるなら**ACK必須化**や**遅延返信の無効化ルール**を追加
