# Writing DataFrames: the Writer interface

The [`DataFrame`](dataframe.md) container already serializes to many formats
(`to_parquet`, `to_csv`, `to_arrow`, `to_hdf`, `to_jsonld`, `as_blob`, …). The
**writer interface** ([`sdata.iolib.writer`][sdata.iolib.writer], RFC 0007) puts a
single `write()` contract on top of them so that **sinks are interchangeable**, can
**hold resources** (a database connection, an RDF store) across many writes, and
**enforce a metadata contract** at the point of writing.

!!! abstract "The metadata truth source is not `df.attrs`"
    pandas drops `df.attrs` across most operations (`groupby`, `concat`, `merge`), so
    a naive writer that reads `df.attrs` often finds the provenance already gone. In
    sdata the truth source is the first-class [`metadata`][sdata.metadata.Metadata] and
    per-column `column_metadata` carried on the `DataFrame` itself. A writer receives
    the whole `DataFrame` and *places* that already-durable metadata where each backend
    wants it — `df.attrs` is only the last-mile transport for a plain pandas frame
    (see [`ensure_sdata`](#accepting-a-plain-pandas-frame)).

## The contract

Every sink satisfies the [`DataFrameWriter`][sdata.iolib.writer.DataFrameWriter]
protocol — `write(sdf)`, `flush()`, `close()` and the context-manager protocol — and
returns a uniform [`WriteReceipt`][sdata.iolib.writer.WriteReceipt]
(`backend`/`sname`/`suuid`/`target`/`detail`). Because the return type is uniform, the
caller can swap backends without changing anything else:

```python
import sqlite3
from sdata.iolib.writer import ParquetWriter, StoreWriter, SqlWriter, GraphWriter

for writer in [ParquetWriter("out/run42.spq"),                 # a Parquet file / object store
               StoreWriter("runs.db"),                         # object persistence (JSON1 store)
               SqlWriter(sqlite3.connect("runs.db")),          # a relational table + sidecar
               GraphWriter("out/run42.ttl")]:                  # an RDF/Turtle file
    with writer:
        receipt = writer.write(sdf)
        print(receipt.backend, receipt.suuid, receipt.target)
```

Concrete writers derive from [`BaseDataFrameWriter`][sdata.iolib.writer.BaseDataFrameWriter],
a template method that accepts the plain frame or an sdata `DataFrame`, checks the
contract, splits the metadata out (`metadata`/`column_metadata`/`description`) and
delegates to the backend.

## Enforcing a metadata contract

A sink can require dataset metadata keys, columns and units to be present before it
accepts a table. Unmet requirements raise `ValueError` — nothing is written:

```python
w = ParquetWriter("out/run.spq",
                  require_metadata=("license",),   # dataset-level attribute must exist
                  require_columns=("force",),      # column must be present
                  require_units=("force",))        # column must carry a unit annotation
w.write(sdf)          # -> ValueError if any requirement is unmet
```

## Accepting a plain pandas frame

[`ensure_sdata`][sdata.iolib.writer.ensure_sdata] is the bridge: `write()` accepts an
sdata `DataFrame` **or** a plain `pandas.DataFrame`. For a plain frame it restores
`df.attrs["_sdata"]` (the slot written by `DataFrame.to_parquet`/`to_dataframe`) via
the normal restore path, so a round-tripped frame keeps its metadata.

For robust provenance, inject it **explicitly** at write time with
[`write_with_provenance`][sdata.iolib.writer.write_with_provenance] — the values land
in `metadata` (not `df.attrs`), where every writer reads them:

```python
from sdata.iolib.writer import write_with_provenance

write_with_provenance(ParquetWriter("out/run.spq"), sdf,
                      {"wasDerivedFrom": "raw://batch-42", "license": "CC-BY-4.0"})
```

## The writers

### `ParquetWriter` — a Parquet file at any fsspec URI

Writes the Parquet bytes (with the `_sdata` metadata embedded in the schema) to a
local path or any fsspec URI (`s3://`, `gcs://`, …). No sidecar needed — the metadata
travels *in* the file and survives the round-trip via `DataFrame.from_parquet_bytes`.

```python
ParquetWriter("s3://bucket/run42.spq").write(sdf)
```

### `StoreWriter` — object persistence in a JSON1 SQLite store

Persists the whole sdata object into a
[`JSON1SQLiteStore`][sdata.iolib.json1sqlitestore.JSON1SQLiteStore] (RFC 0001). The
payload is **flattened** so the `_sdata_*` fields sit at the top level (indexed as
generated columns) while the lossless `to_dict()` rides under the `"sdata"` key — so
the object stays **findable** by `suuid`/`sname`:

```python
from sdata.iolib.json1sqlitestore import JSON1SQLiteStore

with StoreWriter("runs.db") as w:          # a path -> the writer owns and closes the store
    receipt = w.write(sdf)

store = JSON1SQLiteStore("runs.db")
rid = store.get_id_by_key("_sdata_suuid", receipt.suuid)   # findable
sdf2 = DataFrame.from_dict(store.get(rid)["sdata"])        # lossless round-trip
```

Pass an existing `JSON1SQLiteStore` instead of a path to write many tables into one
store the writer does **not** own (and therefore does not close).

### `SqlWriter` — a relational table plus a shared metadata table

Writes the flat data to a relational table (via `pandas.to_sql`) and the metadata to a
fixed, shared table `sdata_dataframe_meta` (its `target_table` column names the data
table). The two writes are **atomic** — the meta row is written first (pending) and
`to_sql`'s terminal commit makes both durable; any failure rolls the meta row back, so
there are no orphan data rows. The provenance key is `str(suuid)`.

```python
import sqlite3

conn = sqlite3.connect("runs.db")
with SqlWriter(conn, table="runs") as w:   # flush()/commit on close
    w.write(sdf)
```

`SqlWriter` needs a **DBAPI/PEP-249 connection** — stdlib `sqlite3`, or a SQLAlchemy
DBAPI connection via `engine.raw_connection()` (a SQLAlchemy *Engine* passed directly
does **not** work). The data table name is validated against an allowlist, so an
unsafe identifier raises `ValueError`.

### `GraphWriter` — RDF/Turtle or JSON-LD

Serializes the metadata as linked data (QUDT units + PROV-O provenance + CSVW columns)
via the [semantic layer][sdata.semantic]. In single-file mode it writes `target`
directly (`fmt="turtle"` or `fmt="json-ld"`); with `named_graphs=True` it accumulates
several tables as named graphs in an `rdflib` dataset and serializes them on `close`.

```python
GraphWriter("out/run42.ttl").write(sdf)                 # Turtle file
GraphWriter("out/run42.jsonld", fmt="json-ld").write(sdf)
```

## Backends at a glance

| Writer | Target | Metadata lands in | Needs |
|--------|--------|-------------------|-------|
| [`ParquetWriter`][sdata.iolib.writer.ParquetWriter] | fsspec URI (`.spq`) | embedded `_sdata` schema blob | `sdata[parquet,blob]` |
| [`StoreWriter`][sdata.iolib.writer.StoreWriter] | `JSON1SQLiteStore` / db path | flattened `_sdata_*` columns + `sdata` payload | — (stdlib `sqlite3`) |
| [`SqlWriter`][sdata.iolib.writer.SqlWriter] | DBAPI connection | shared `sdata_dataframe_meta` table | — (stdlib `sqlite3`) |
| [`GraphWriter`][sdata.iolib.writer.GraphWriter] | Turtle/JSON-LD file | the RDF itself (QUDT/PROV-O/CSVW) | rdflib only for `named_graphs` |

!!! note "Optional backends"
    `ParquetWriter` needs pyarrow + fsspec (`pip install "sdata[parquet,blob]"`).
    `StoreWriter` and `SqlWriter` run on the stdlib `sqlite3`; `SqlWriter` also accepts
    a SQLAlchemy connection (`sdata[sql]`). `GraphWriter`'s single-file mode works on
    the core install; only named-graph accumulation needs `sdata[rdf]`. A missing
    backend raises a clear `ImportError` pointing at the extra.

## Full API

See the [API reference](../api.md#sdataiolibwriter) for the complete signature list
and [RFC 0007](../rfc/0007-dataframe-writer-interface.md) for the design rationale.
