"""Idempotent, compacted file sink with checkpointing."""
from __future__ import annotations

import json
import os
from pathlib import Path

from walcdc.schema import Registry
from walcdc.types import DELETE, INSERT, SCHEMA, UPDATE


class Sink:
    def __init__(self, path: str) -> None:
        self.path = path
        self.tables_dir = Path(path) / "tables"
        # tables[name][key] = {"row": ..., "lsn": int, "op": "upsert"}
        self.tables: dict[str, dict] = {}
        self.registry = Registry()
        self.applied_txids: list[int] = []
        self.last_commit_lsn = 0

    def load(self, snapshot: str | None = None) -> None:
        """Create the sink dir. If snapshot is given and the sink is empty, copy it in."""
        meta_path = Path(self.path) / "meta.json"
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        if meta_path.exists():
            self._load_existing(meta_path)
            return
        if snapshot is not None:
            snap = json.loads(Path(snapshot).read_text())
            self.registry = Registry.load(snap.get("schema"))
            self.last_commit_lsn = int(snap.get("last_commit_lsn", 0))
            base_lsn = self.last_commit_lsn
            for table_name, rows in (snap.get("tables") or {}).items():
                schema_id = self.registry.schema_id(table_name)
                self.tables[table_name] = {
                    key: {
                        "row": row,
                        "lsn": base_lsn,
                        "op": "upsert",
                        "schema_id": schema_id,
                    }
                    for key, row in rows.items()
                }
            self._persist()

    def apply_committed(self, tx: dict, registry) -> None:
        """Apply one committed transaction and fsync a consistent image.

        Upsert/delete by key. After each commit, a key exists at most once.
        """
        txid = tx["txid"]
        if txid in self.applied_txids:
            return
        commit_lsn = tx["commit_lsn"]
        for event in tx["events"]:
            payload = event.payload
            table_name = payload["table"]
            if event.typ == SCHEMA:
                registry.apply(payload)
                self.tables.setdefault(table_name, {})
                self._upcast_existing(table_name, payload["schema_id"], registry)
                continue
            key = payload["key"]
            rows = self.tables.setdefault(table_name, {})
            if event.typ in (INSERT, UPDATE):
                row = registry.upcast(table_name, payload["row"], payload["schema_id"])
                rows[key] = {
                    "row": row,
                    "lsn": event.lsn,
                    "op": "upsert",
                    "schema_id": registry.schema_id(table_name),
                }
            elif event.typ == DELETE:
                rows.pop(key, None)
            else:
                raise ValueError(f"unsupported event type {event.type_name} in tx {txid}")
        self.applied_txids.append(txid)
        self.last_commit_lsn = commit_lsn
        self.registry = registry
        self._persist()

    def write_checkpoint(self, path: str, lsn: int) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(target, json.dumps({"last_commit_lsn": lsn}, indent=2) + "\n")

    def read_checkpoint(self, path: str) -> int:
        """Return last_commit_lsn or 0 if the file does not exist."""
        target = Path(path)
        if not target.exists():
            return 0
        data = json.loads(target.read_text())
        return int(data["last_commit_lsn"])

    def _load_existing(self, meta_path: Path) -> None:
        meta = json.loads(meta_path.read_text())
        self.last_commit_lsn = int(meta.get("last_commit_lsn", 0))
        self.applied_txids = list(meta.get("applied_txids", []))
        schema_path = Path(self.path) / "schema.json"
        if schema_path.exists():
            self.registry = Registry.load(json.loads(schema_path.read_text()))
        self.tables = {}
        for table_file in sorted(self.tables_dir.glob("*.jsonl")):
            table_name = table_file.name[: -len(".jsonl")]
            rows = {}
            for line in table_file.read_text().splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("op") == "delete":
                    continue
                rows[record["key"]] = {
                    "row": record["row"],
                    "lsn": record.get("lsn", self.last_commit_lsn),
                    "op": "upsert",
                    "schema_id": self.registry.schema_id(table_name),
                }
            self.tables[table_name] = rows

    def _upcast_existing(self, table_name: str, new_schema_id: int, registry) -> None:
        """Rewrite rows of `table_name` so stored rows track the latest schema."""
        for record in self.tables.get(table_name, {}).values():
            if record["schema_id"] < new_schema_id:
                record["row"] = registry.upcast(
                    table_name, record["row"], record["schema_id"]
                )
                record["schema_id"] = new_schema_id

    def _persist(self) -> None:
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        live_tables = set(self.tables) | set(self.registry.tables)
        for table_name in live_tables:
            rows = self.tables.get(table_name, {})
            lines = []
            for key in sorted(rows, key=lambda item: str(item)):
                record = dict(rows[key])
                record["key"] = key
                lines.append(json.dumps(record, ensure_ascii=False))
            self._atomic_write(
                self.tables_dir / f"{table_name}.jsonl",
                ("\n".join(lines) + "\n") if lines else "",
            )
        self._atomic_write(
            Path(self.path) / "schema.json",
            json.dumps(self.registry.dump(), indent=2, ensure_ascii=False) + "\n",
        )
        # meta.json is the commit marker: write it only after tables/schema are durable.
        self._atomic_write(
            Path(self.path) / "meta.json",
            json.dumps(
                {
                    "last_commit_lsn": self.last_commit_lsn,
                    "applied_txids": self.applied_txids,
                },
                indent=2,
            )
            + "\n",
        )

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        tmp = target.with_name(target.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
        parent = target.parent
        fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
