"""
HILSシステム用通信プロトコルモジュール

このモジュールは、シミュレータとハードウェア間の通信に使用される
カスタムプロトコルを実装します。メッセージはJSON形式でエンコードされ、
バイナリヘッダーを持つフレーム形式で送信されます。
"""

import json
import struct
import time
from typing import Any, Union
import socket

# プロトコルマジックナンバー（メッセージの整合性確認用）
MAGIC = 0xFEEDBEEF

# メッセージヘッダー構造体：マジックナンバー(4bytes) + ペイロード長(4bytes)
HEADER = struct.Struct("!II")  # ビッグエンディアン形式

# 高精度タイムスタンプ取得関数（単調時刻をナノ秒で取得）
now_ns = time.monotonic_ns


def pack(obj: dict[str, Any]) -> bytes:
    """
    辞書オブジェクトをプロトコル形式のバイト列にパック

    Args:
        obj: パックする辞書オブジェクト

    Returns:
        ヘッダー + JSONペイロードのバイト列

    フレーム形式:
        [MAGIC(4) | LENGTH(4) | JSON_PAYLOAD(LENGTH)]
    """
    # JSONをUTF-8バイト列に変換（コンパクト形式）
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    # ヘッダー（マジック + ペイロード長）+ ペイロードを結合
    return HEADER.pack(MAGIC, len(payload)) + payload


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """
    ソケットから指定バイト数を確実に受信

    Args:
        sock: 受信対象のソケット
        n: 受信する必要があるバイト数

    Returns:
        受信したバイト列（必ずn バイト）

    Raises:
        ConnectionError: ソケットが閉じられた場合

    Note:
        TCP の特性上、recv() は要求したバイト数より少ない
        データしか返さない場合があるため、ループして確実に
        指定バイト数を受信する
    """
    buf = bytearray()
    while len(buf) < n:
        # 残りバイト数分を受信試行
        chunk = sock.recv(n - len(buf))
        if not chunk:
            # 相手側がソケットを閉じた
            raise ConnectionError("socket closed")
        buf.extend(chunk)
    return bytes(buf)


def recv_obj(sock: socket.socket, timeout: float | None = None) -> dict[str, Any]:
    """
    ソケットからプロトコル形式のオブジェクトを受信

    Args:
        sock: 受信対象のソケット
        timeout: 受信タイムアウト（秒）。Noneの場合はタイムアウトなし

    Returns:
        受信・デシリアライズされた辞書オブジェクト

    Raises:
        ValueError: マジックナンバーが不正な場合
        ConnectionError: ソケットが閉じられた場合
        json.JSONDecodeError: JSONデコードに失敗した場合

    処理フロー:
        1. タイムアウト設定（指定されている場合）
        2. ヘッダー受信（8バイト）
        3. マジックナンバー検証
        4. ペイロード受信
        5. JSONデシリアライズ
    """
    # タイムアウト設定
    if timeout is not None:
        sock.settimeout(timeout)

    # ヘッダー受信・解析
    header = recv_exact(sock, HEADER.size)
    magic, ln = HEADER.unpack(header)

    # マジックナンバー検証
    if magic != MAGIC:
        raise ValueError("bad magic")

    # ペイロード受信・JSONデコード
    payload = recv_exact(sock, ln)
    return json.loads(payload.decode("utf-8"))
