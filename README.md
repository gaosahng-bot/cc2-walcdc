# walcdc

Change-data-capture over a custom binary WAL.

Already in the tree:

- `walcdc.wal` — record writer/reader for the WAL format (see `docs/wal-format.md`)
- `walcdc.types` — logical event types and schema descriptors
- Fixtures under `fixtures/` : a source WAL with commits, aborts, schema evolution and a snapshot

Implemented:

- Transaction assembly and abort dropping (`walcdc.tx`): aborted and end-of-file
  in-flight transactions never reach the sink; visibility follows commit order.
- Schema registry + upcast of old rows (`walcdc.schema`): `create`, `add_column`,
  `widen` (int → bigint only) and `rename`, with old rows rewritten to the latest
  schema on every committed change.
- Idempotent compacted file sink with per-commit LSN checkpoint (`walcdc.sink`).
- The `replay` and `verify` CLI commands.

```
python -m walcdc replay --wal fixtures/shop.wal --snapshot fixtures/shop.snapshot.json --sink /tmp/walcdc-out/sink --checkpoint /tmp/walcdc-out/cp.json
```

Then crash-restart the same command; the checkpoint (`last_commit_lsn`) makes replay
skip already-committed transactions, so committed work is neither duplicated nor skipped.
Check the result with:

```
python -m walcdc verify --sink /tmp/walcdc-out/sink --expect fixtures/shop.expected.json
```
