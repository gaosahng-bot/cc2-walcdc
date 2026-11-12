"""Logical event types. Complete."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BEGIN, INSERT, UPDATE, DELETE, COMMIT, ABORT, SCHEMA = range(1, 8)
TYPE_NAME = {
    BEGIN: "begin",
    INSERT: "insert",
    UPDATE: "update",
    DELETE: "delete",
    COMMIT: "commit",
    ABORT: "abort",
    SCHEMA: "schema",
}


@dataclass
class Frame:
    typ: int
    lsn: int
    txid: int
    payload: dict[str, Any]

    @property
    def type_name(self) -> str:
        return TYPE_NAME.get(self.typ, str(self.typ))
