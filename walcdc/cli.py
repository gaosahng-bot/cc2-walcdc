"""CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="walcdc")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump", help="print WAL frames (already works)")
    d.add_argument("--wal", required=True)
    r = sub.add_parser("replay", help="replay WAL into a sink")
    r.add_argument("--wal", required=True)
    r.add_argument("--snapshot", default=None)
    r.add_argument("--sink", required=True)
    r.add_argument("--checkpoint", required=True)
    v = sub.add_parser("verify", help="compare a sink with an expected image")
    v.add_argument("--sink", required=True)
    v.add_argument("--expect", required=True)
    args = p.parse_args(argv)
    if args.cmd == "dump":
        from walcdc.wal import read_wal
        for fr in read_wal(args.wal):
            print(f"lsn={fr.lsn} tx={fr.txid} {fr.type_name} {json.dumps(fr.payload, ensure_ascii=False)}")
        return 0
    if args.cmd == "replay":
        from walcdc.replay import replay
        replay(args.wal, args.snapshot, args.sink, args.checkpoint)
        return 0
    if args.cmd == "verify":
        from walcdc.verify import verify
        ok, msg = verify(args.sink, args.expect)
        print(msg)
        return 0 if ok else 1
    return 2
