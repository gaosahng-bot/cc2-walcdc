"""Transaction assembly: group WAL frames into committed transactions."""
from __future__ import annotations

from walcdc.types import Frame


def committed_transactions(frames: list[Frame]) -> list[dict]:
    """Group frames into transactions, drop aborted ones, keep commit order.

    Each item: {"txid", "commit_lsn", "events": [insert/update/delete/schema frames]}.
    Schema events may appear inside a tx or as their own tx. They become visible at commit.
    A BEGIN without COMMIT/ABORT at end-of-file is in-flight and must be ignored.
    """
    open_tx: dict[int, list[Frame]] = {}
    committed: list[dict] = []
    for frame in frames:
        if frame.type_name == "begin":
            open_tx[frame.txid] = []
        elif frame.type_name in ("commit", "abort"):
            events = open_tx.pop(frame.txid, None)
            if events is None:
                raise ValueError(
                    f"{frame.type_name} frame for unknown txid={frame.txid} at lsn={frame.lsn}"
                )
            if frame.type_name == "commit":
                committed.append(
                    {
                        "txid": frame.txid,
                        "commit_lsn": frame.lsn,
                        "events": events,
                    }
                )
        else:
            if frame.txid not in open_tx:
                raise ValueError(
                    f"{frame.type_name} frame at lsn={frame.lsn} "
                    f"belongs to txid={frame.txid} without an active begin"
                )
            open_tx[frame.txid].append(frame)
    # Any txids left in open_tx are in-flight at end-of-file: ignore them.
    committed.sort(key=lambda item: item["commit_lsn"])
    return committed
