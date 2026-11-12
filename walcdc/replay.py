"""Replay a WAL into the file sink with exactly-once checkpointing."""
from __future__ import annotations

from walcdc.sink import Sink
from walcdc.tx import committed_transactions
from walcdc.wal import read_wal

def replay(wal: str, snapshot: str | None, sink: str, checkpoint: str) -> None:
    frames = read_wal(wal)
    transactions = committed_transactions(frames)

    store = Sink(sink)
    store.load(snapshot)
    resume_lsn = max(store.read_checkpoint(checkpoint), store.last_commit_lsn)

    for tx in transactions:
        if tx["commit_lsn"] <= resume_lsn or tx["txid"] in store.applied_txids:
            continue
        store.apply_committed(tx, store.registry)
        store.write_checkpoint(checkpoint, tx["commit_lsn"])
