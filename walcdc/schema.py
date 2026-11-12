"""Schema registry, schema evolution and row upcast."""
from __future__ import annotations

from typing import Any


class SchemaError(ValueError):
    pass


class Registry:
    def __init__(self) -> None:
        # tables[name] = {"columns": [col, ...], "history": [event, ...]}
        # col: {"name", "type", "nullable"}
        self.tables: dict[str, dict] = {}

    def apply(self, event: dict) -> None:
        """Apply a committed schema event. Reject illegal widens or unknown tables."""
        action = event.get("action")
        table_name = event.get("table")
        if action == "create":
            if table_name in self.tables:
                raise SchemaError(f"table {table_name!r} already exists")
            columns = event.get("columns")
            if not isinstance(columns, list) or not columns:
                raise SchemaError(f"create table {table_name!r} requires a columns list")
            names = [col["name"] for col in columns]
            if len(set(names)) != len(names):
                raise SchemaError(f"duplicate columns in create table {table_name!r}")
            self.tables[table_name] = {
                "columns": [dict(col) for col in columns],
                "history": [dict(event)],
            }
            return
        table = self._require_table(table_name)
        columns: list[dict] = table["columns"]
        if action == "add_column":
            column = event["column"]
            name = column["name"]
            if any(col["name"] == name for col in columns):
                raise SchemaError(
                    f"column {name!r} already exists on table {table_name!r}"
                )
            if "default" not in event:
                raise SchemaError(
                    f"add_column for {table_name!r}.{name} requires a default"
                )
            columns.append(dict(column))
        elif action == "widen":
            column = self._require_column(columns, event["column"], table_name)
            if event.get("from") != column["type"] or (event.get("from"), event.get("to")) != (
                "int",
                "bigint",
            ):
                raise SchemaError(
                    f"illegal widen {event.get('from')} -> {event.get('to')} "
                    f"on {table_name!r}.{column['name']} (only int -> bigint is allowed)"
                )
            column["type"] = "bigint"
        elif action == "rename":
            column = self._require_column(columns, event["from"], table_name)
            new_name = event["to"]
            if any(col["name"] == new_name for col in columns):
                raise SchemaError(
                    f"cannot rename {event['from']!r} to {new_name!r} on "
                    f"{table_name!r}: target name already exists"
                )
            column["name"] = new_name
        else:
            raise SchemaError(f"unknown schema action {action!r}")
        table["history"].append(dict(event))

    def upcast(self, table: str, row: dict[str, Any], schema_id: int) -> dict[str, Any]:
        """Return `row` rewritten to the latest schema of `table`.

        Missing columns introduced later get their default. Renames are applied in order.
        int values must become int (Python int is fine for bigint).
        """
        entry = self._require_table(table)
        history: list[dict] = entry["history"]
        events = [event for event in history if event["schema_id"] > schema_id]
        result = dict(row)
        for event in events:
            action = event["action"]
            if action == "add_column":
                name = event["column"]["name"]
                if name not in result:
                    result[name] = event["default"]
            elif action == "rename":
                old_name = event["from"]
                new_name = event["to"]
                if old_name in result:
                    result[new_name] = result.pop(old_name)
            # "create" and "widen" do not change row key names; Python ints hold bigint.
        return result

    def dump(self) -> dict:
        return {
            name: {
                "columns": [dict(col) for col in entry["columns"]],
                "history": [dict(event) for event in entry["history"]],
            }
            for name, entry in self.tables.items()
        }

    @classmethod
    def load(cls, data: dict | None) -> "Registry":
        registry = cls()
        if data:
            registry.tables = {
                name: {
                    "columns": [dict(col) for col in entry["columns"]],
                    "history": [dict(event) for event in entry["history"]],
                }
                for name, entry in data.items()
            }
        return registry

    def _require_table(self, name: str) -> dict:
        table = self.tables.get(name)
        if table is None:
            raise SchemaError(f"unknown table {name!r}")
        return table

    def schema_id(self, table: str) -> int:
        """Latest schema_id known for `table` (0 if the table is unknown/empty)."""
        entry = self.tables.get(table)
        if not entry or not entry["history"]:
            return 0
        return max(event["schema_id"] for event in entry["history"])

    @staticmethod
    def _require_column(columns: list[dict], name: str, table_name: str) -> dict:
        for column in columns:
            if column["name"] == name:
                return column
        raise SchemaError(f"unknown column {name!r} on table {table_name!r}")
