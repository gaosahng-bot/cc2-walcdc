"""WAL codec. Complete."""
from __future__ import annotations

import binascii
import json
import struct
from pathlib import Path

from walcdc.types import Frame

MAGIC = b"WALCDC01"


def encode_frame(frame: Frame) -> bytes:
    payload = json.dumps(frame.payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    body = bytes([frame.typ]) + struct.pack(">QQ", frame.lsn, frame.txid) + payload
    length = len(body)
    crc = binascii.crc32(body) & 0xFFFFFFFF
    return struct.pack(">I", length) + body + struct.pack(">I", crc)


def iter_frames(data: bytes):
    if not data.startswith(MAGIC):
        raise ValueError("bad WAL magic")
    i = len(MAGIC)
    n = len(data)
    while i < n:
        if i + 4 > n:
            raise ValueError("truncated length")
        (length,) = struct.unpack(">I", data[i : i + 4])
        i += 4
        if i + length + 4 > n:
            raise ValueError("truncated frame")
        body = data[i : i + length]
        i += length
        (crc,) = struct.unpack(">I", data[i : i + 4])
        i += 4
        expect = binascii.crc32(body) & 0xFFFFFFFF
        if crc != expect:
            raise ValueError(f"crc mismatch at lsn body, {crc:08x} != {expect:08x}")
        typ = body[0]
        lsn, txid = struct.unpack(">QQ", body[1:17])
        payload = json.loads(body[17:].decode("utf-8"))
        yield Frame(typ, lsn, txid, payload)


def read_wal(path: str | Path) -> list[Frame]:
    return list(iter_frames(Path(path).read_bytes()))


def write_wal(path: str | Path, frames: list[Frame]) -> None:
    blob = MAGIC + b"".join(encode_frame(f) for f in frames)
    Path(path).write_bytes(blob)
