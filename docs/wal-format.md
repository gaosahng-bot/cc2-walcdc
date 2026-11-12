# WAL format

File starts with 8-byte magic `WALCDC01`. Then a sequence of frames:

```
u32be length   # of (type + lsn + txid + payload)
u8    type     # 1=begin, 2=insert, 3=update, 4=delete, 5=commit, 6=abort, 7=schema
u64be lsn      # strictly increasing
u64be txid
`length-17` payload bytes
u32be crc32    # CRC of (type + lsn + txid + payload), ISO 3309 / binascii.crc32 & 0xffffffff
```

Payloads are UTF-8 JSON:

- begin: `{"t": <ms>}`
- insert: `{"table":"...","key":...,"row":{...},"schema_id":N}`
- update: `{"table":"...","key":...,"row":{...},"schema_id":N}`  (full new row, not a patch)
- delete: `{"table":"...","key":...,"schema_id":N}`
- commit: `{"t": <ms>}`
- abort: `{"t": <ms>}`
- schema: `{"schema_id":N,"table":"...","action":"create"|"add_column"|"widen"|"rename","..."}`

Schema actions:

- create: `columns` list of `{name, type, nullable}` where type is `int|bigint|string|bool|json`
- add_column: `column` + `default` (used when upcasting older rows)
- widen: `column`, `from`, `to` (only `int` → `bigint` is legal here)
- rename: `from`, `to`

A row is only visible to the sink after its transaction commits. Aborted transactions must vanish.
LSN of a commit is the position to checkpoint. Replay must resume after the last checkpointed commit LSN.

`fixtures/shop.snapshot.json` is a compacted sink image *before* this WAL (LSN 0). Replay should
load it, then apply the WAL.
