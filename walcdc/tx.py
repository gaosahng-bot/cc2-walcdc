"""Transaction assembly — NOT implemented yet."""
from __future__ import annotations

from walcdc.types import Frame


def committed_transactions(frames: list[Frame]) -> list[dict]:
    """Group frames into transactions, drop aborted ones, keep commit order.

    Each item: {"txid", "commit_lsn", "events": [insert/update/delete/schema frames]}.
    Schema events may appear inside a tx or as their own tx. They become visible at commit.
    A BEGIN without COMMIT/ABORT at end-of-file is in-flight and must be ignored.
    """
    raise NotImplementedError("implement transaction assembly")
