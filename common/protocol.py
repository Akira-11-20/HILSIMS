import json
import struct
import time

MAGIC = 0xFEEDBEEF
HEADER = struct.Struct("!II")  # magic, length (big-endian)

now_ns = time.monotonic_ns  # 単調時刻（ns）


def pack(obj: dict) -> bytes:
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return HEADER.pack(MAGIC, len(payload)) + payload


def recv_exact(sock, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed")
        buf.extend(chunk)
    return bytes(buf)


def recv_obj(sock, timeout: float | None = None) -> dict:
    if timeout is not None:
        sock.settimeout(timeout)
    header = recv_exact(sock, HEADER.size)
    magic, ln = HEADER.unpack(header)
    if magic != MAGIC:
        raise ValueError("bad magic")
    payload = recv_exact(sock, ln)
    return json.loads(payload.decode("utf-8"))
