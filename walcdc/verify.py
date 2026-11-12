"""Sink vs expected — you may implement this as part of the task.

A default, incomplete stub is provided so the command exists.
"""
from __future__ import annotations

import json
from pathlib import Path


def verify(sink: str, expect: str) -> tuple[bool, str]:
    exp = json.loads(Path(expect).read_text())
    # Implementation should load compacted rows from the sink and compare by table/key.
    sink_dir = Path(sink)
    meta_path = sink_dir / "meta.json"
    if not meta_path.exists():
        return False, f"sink meta missing: {meta_path}"
    meta = json.loads(meta_path.read_text())

    actual: dict[str, dict] = {}
    for table_file in sorted((sink_dir / "tables").glob("*.jsonl")):
        table_name = table_file.name[: -len(".jsonl")]
        rows = {}
        seen: set = set()
        for line in table_file.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("op") == "delete":
                return False, f"tombstone for key {record['key']!r} survives compaction in {table_name}"
            key = record["key"]
            if key in seen:
                return False, f"key {key!r} appears more than once in compacted {table_name}"
            seen.add(key)
            rows[key] = record["row"]
        if rows:
            actual[table_name] = rows

    expected_lsn = exp.get("last_commit_lsn")
    if expected_lsn is not None and meta.get("last_commit_lsn") != expected_lsn:
        return (
            False,
            f"last_commit_lsn mismatch: sink={meta.get('last_commit_lsn')} expect={expected_lsn}",
        )

    expected_tables = exp.get("tables", {})
    if set(actual) != set(expected_tables):
        return (
            False,
            f"table set mismatch: sink={sorted(actual)} expect={sorted(expected_tables)}",
        )
    for table_name, expected_rows in expected_tables.items():
        actual_rows = actual.get(table_name, {})
        if set(actual_rows) != set(expected_rows):
            return (
                False,
                f"key mismatch in {table_name}: sink={sorted(actual_rows)} "
                f"expect={sorted(expected_rows)}",
            )
        for key, expected_row in expected_rows.items():
            actual_row = actual_rows[key]
            if actual_row != expected_row:
                return (
                    False,
                    f"row mismatch for {table_name}/{key}: "
                    f"sink={json.dumps(actual_row, ensure_ascii=False)} "
                    f"expect={json.dumps(expected_row, ensure_ascii=False)}",
                )
    return True, f"OK: {sum(len(rows) for rows in actual.values())} rows across {len(actual)} tables, last_commit_lsn={meta.get('last_commit_lsn')}"
