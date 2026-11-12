# walcdc

Change-data-capture over a custom binary WAL.

Already in the tree:

- `walcdc.wal` — record writer/reader for the WAL format (see `docs/wal-format.md`)
- `walcdc.types` — logical event types and schema descriptors
- Fixtures under `fixtures/` : a source WAL with commits, aborts, schema evolution and a snapshot

Not implemented:

- Transaction assembly and abort dropping (`walcdc.tx`)
- Schema registry + upcast of old rows (`walcdc.schema`)
- Idempotent sink with LSN checkpoint (`walcdc.sink`)
- The replay CLI

```
python -m walcdc replay --wal fixtures/shop.wal --snapshot fixtures/shop.snapshot.json --sink /tmp/walcdc-out/sink --checkpoint /tmp/walcdc-out/cp.json
```

Then crash-restart the same command; committed transactions must not be duplicated or skipped.
