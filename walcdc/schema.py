"""Schema registry and row upcast — NOT implemented yet."""
from __future__ import annotations

from typing import Any


class SchemaError(ValueError):
    pass


class Registry:
    def __init__(self) -> None:
        self.tables: dict[str, dict] = {}

    def apply(self, event: dict) -> None:
        """Apply a committed schema event. Reject illegal widens or unknown tables."""
        raise NotImplementedError("implement schema apply")

    def upcast(self, table: str, row: dict[str, Any], schema_id: int) -> dict[str, Any]:
        """Return `row` rewritten to the latest schema of `table`.

        Missing columns introduced later get their default. Renames are applied in order.
        int values must become int (Python int is fine for bigint).
        """
        raise NotImplementedError("implement upcast")

    def dump(self) -> dict:
        raise NotImplementedError
