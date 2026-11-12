# Sink layout

`--sink` is a directory:

- `tables/<table>.jsonl` — one JSON object per current row: `{"key":..., "row":{...}, "lsn":..., "op":"upsert"|"delete"}`
  Deletes may be tombstones (op=delete) that compaction should drop when a later upsert doesn't exist — after replay, run implicit compaction so deleted keys are absent and each key appears once (last committed writer wins).
- `schema.json` — the current registry
- `meta.json` — `{"last_commit_lsn": N, "applied_txids": [...]}`

`--checkpoint` is a JSON file: `{"last_commit_lsn": N}`. On restart, skip WAL frames with lsn <= this value,
except you still need to finish a transaction that committed after the checkpoint. (Frames of an in-flight
tx before the checkpoint should already have been dropped if it didn't commit.)

`python -m walcdc verify --sink DIR --expect fixtures/shop.expected.json` is also required:
compare compacted table contents to the expected keys/rows (ignore key order).
