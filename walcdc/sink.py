"""Idempotent compacted sink — NOT implemented yet."""
from __future__ import annotations


class Sink:
    def __init__(self, path: str) -> None:
        self.path = path

    def load(self, snapshot: str | None = None) -> None:
        """Create the sink dir. If snapshot is given and the sink is empty, copy it in."""
        raise NotImplementedError

    def apply_committed(self, tx: dict, registry) -> None:
        """Apply one committed transaction and fsync a consistent image.

        Upsert/delete by key. After each commit, a key exists at most once.
        """
        raise NotImplementedError

    def write_checkpoint(self, path: str, lsn: int) -> None:
        raise NotImplementedError

    def read_checkpoint(self, path: str) -> int:
        """Return last_commit_lsn or 0 if the file does not exist."""
        raise NotImplementedError
