# Tabular data: the `DataFrame` container

[`sdata.sclass.dataframe.DataFrame`][sdata.sclass.dataframe.DataFrame] is the
self-describing tabular container (it supersedes the deprecated `Data` class). It
wraps a pandas `DataFrame` together with **per-column metadata** and **dataset-level
metadata**, and serializes to Parquet, Arrow/Feather, CSV, dict/JSON, JSON-LD/RDF, a
Frictionless Data Package and HDF5 — with the qualifying metadata either embedded or
written as an independent sidecar.

```python
import pandas as pd
from sdata.sclass.dataframe import DataFrame

df = pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})
sdf = DataFrame(df=df, name="specimen_01", description="a tension test")
```

`__init__` accepts `df`, `column_metadata` (a dict `{col: {unit, label, ...}}` or a
[`Metadata`][sdata.metadata.Metadata]) and any `Base` keyword (`name`,
`description`, `project`, …). Passing no `df` yields an empty table.

## The pandas frame

The wrapped frame is always available via `sdf.df` (settable). Thin convenience
pass-throughs delegate to it:

```python
sdf.df                 # the pandas DataFrame
len(sdf)               # number of rows
sdf.shape              # (3, 2)
sdf.columns            # Index(['weight', 'height'])
sdf.dtypes             # per-column pandas dtypes
sdf.head(2)            # first n rows
sdf.describe()         # descriptive statistics
repr(sdf)              # (DataFrame <…> shape=(3, 2))
```

Assigning a new frame (`sdf.df = other`) keeps the column metadata in sync — see
[Column metadata](#column-metadata).

## Dataset metadata

Every object carries fully-qualified, machine-readable dataset metadata
(`sdf.metadata`), a free-text `sdf.description`, and a deterministic identity
(`sdf.name` / `sdf.sname` / `sdf.suuid`). Reserved `_sdata_*` attributes
(name, sname, suuid, class, ctime, parent, project, topology) are populated
automatically.

```python
sdf.metadata.add("max_force", 12.5, unit="kN", dtype="float",
                 description="max force", ontology="bfo:Quality")
sdf.metadata.df       # the metadata as a pandas table
sdf.udf               # only the user-defined attributes
```

See [Machine-readable metadata](metadata-jsonld.md) for the metadata model,
JSON-LD/RDF, schema validation and signing.

## Column metadata

Each column carries an [`Attribute`][sdata.metadata.Attribute]
(`unit`/`label`/`description`/`ontology`/`required`) in `sdf.column_metadata`
(a [`Metadata`][sdata.metadata.Metadata]). Three views of the same store:

```python
sdf.column_metadata    # the Metadata (one Attribute per column)
sdf.cmd                # alias of column_metadata
sdf.cmdf               # the column metadata rendered as a pandas DataFrame
```

Annotate columns with `set_column` (only the fields you pass are changed; existing
annotations are preserved) and read them back with `get_column`:

```python
sdf.set_column("weight", unit="kg", label="Gewicht", ontology="bfo:Quality")
sdf.set_column("height", unit="m")

sdf.get_column("weight").unit        # 'kg'
sdf.column_units                     # {'weight': 'kg', 'height': 'm'}
```

The `col` accessor offers attribute-style access with Jupyter tab-completion; the
returned `Attribute` can be mutated in place:

```python
sdf.col.weight                       # -> Attribute (tab-completion on df.col.)
sdf.col["weight"].unit = "kg"        # mutate a field in place
```

**Sync & prune.** When the frame is reassigned (`sdf.df = other`),
`column_metadata` is kept in sync: new columns are added and annotations for
removed columns are pruned, while surviving columns keep their `unit`/`label`.
Column metadata supplied at construction time is preserved as-is (orphan keys —
keys that match no column — are only logged as a warning, never dropped).

## Serialization

sdata writes the **data** in an efficient, typed container and the **metadata**
either embedded in that container or alongside it as a sidecar. Pick the format by
the interop you need:

| Format | Write / read | Metadata carrier | Needs |
|--------|--------------|------------------|-------|
| Parquet `.spq` | `to_parquet` / `from_parquet`, `from_parquet_bytes` | `_sdata` JSON blob in the schema | pyarrow |
| Arrow | `to_arrow` / `from_arrow` | `_sdata` blob **+ native per-column field metadata** | pyarrow |
| Feather | `to_feather` / `from_feather` | same as Arrow | pyarrow |
| dict | `to_dict` / `from_dict` | base64 Parquet + explicit `column_metadata` | pyarrow |
| JSON `.sjson` | `to_json` / `from_json` | via `to_dict` | pyarrow |
| CSV | `to_csv` / `from_csv` | **sidecar only** (data-only file) | — (pure pandas) |
| pandas `df.attrs` | `to_dataframe` | `_sdata` in `df.attrs` | — |
| JSON-LD / RDF | `to_jsonld` / `to_turtle` / `write_sidecar` | the metadata itself | rdflib (optional) |
| Data Package `.zip` | `to_datapackage` / `from_datapackage` | `datapackage.json` (Frictionless) + lossless `sdata` block | — (csv) / pyarrow (parquet) |
| HDF5 `.h5` | `to_hdf` / `from_hdf` | `_sdata` node attribute (PyTables) | tables (`sdata[hdf]`) |

All file writers share the same shape: an optional `path` (writes
`<sname>.<ext>`), an optional exact `filename`, and a `sidecar` flag; without a
path they return bytes (or, for CSV, a string).

```python
# Parquet (.spq) — metadata embedded in the schema; zstd-compressed
sdf.to_parquet(path="out", sidecar=True)        # -> out/<sname>.spq + sidecar
DataFrame.from_parquet("out/<sname>.spq")
raw = sdf.to_parquet()                           # in-memory bytes
DataFrame.from_parquet_bytes(raw)

# Arrow / Feather — metadata in the Arrow schema (+ native per-column field metadata)
table = sdf.to_arrow()                           # pyarrow.Table
DataFrame.from_arrow(table)
sdf.to_feather(path="out")                       # -> out/<sname>.feather
DataFrame.from_feather("out/<sname>.feather")

# dict / JSON — for nesting in JSON documents
d = sdf.to_dict();      DataFrame.from_dict(d)
sdf.to_json("specimen_01.sjson", sidecar=True)   # text; from_json reconstructs

# CSV — data only (pure pandas); metadata via the sidecar
sdf.to_csv(path="out", sidecar=True)             # index dropped by default
DataFrame.from_csv("out/<sname>.csv")
text = sdf.to_csv()                              # CSV string

# hand back a plain pandas frame with sdata metadata in df.attrs["_sdata"]
plain = sdf.to_dataframe()

# linked data
sdf.to_jsonld();   sdf.to_turtle();   sdf.write_sidecar("out")
from sdata.base import Base
Base.read_sidecar("out/<sname>.meta.jsonld")     # read a sidecar back
```

!!! note "Optional backend"
    Arrow, Feather and Parquet (and therefore `to_dict`/`to_json`) need pyarrow
    (`pip install "sdata[parquet]"`); CSV, `to_dataframe` and JSON-LD work with the
    core install. A missing backend raises a clear `ImportError` pointing at the extra.

!!! tip "Native per-column metadata (Arrow / Feather)"
    Besides the `_sdata` JSON blob, `to_arrow()` (and therefore `to_feather()`)
    attaches each column's `unit`/`label`/`description`/`ontology` **natively** to
    that column's Arrow field metadata. Arrow-aware tools (DuckDB, Polars, pyarrow)
    can read the per-column annotations without sdata, and `from_arrow()` merges
    field metadata from foreign Arrow tables back into `column_metadata`.

    ```python
    sdf.to_arrow().schema.field("weight").metadata   # {b'unit': b'kg', b'label': ...}
    ```

### Data Package (portable bundle)

`to_datapackage()` writes a self-contained **Frictionless Data Package** (`.zip`):
a standard `datapackage.json` descriptor (so generic Frictionless tooling can read
it), the data as CSV (default, no extra dependency) or Parquet, and the full sdata
metadata under the descriptor's `"sdata"` key for a **lossless** round-trip. The
JSON-LD sidecar is embedded too (toggle with `sidecar=`).

```python
sdf.to_datapackage(path="out")                  # -> out/<sname>.zip  (CSV inside)
sdf.to_datapackage(path="out", fmt="parquet")   # Parquet inside (needs sdata[parquet])
raw = sdf.to_datapackage()                       # zip bytes (no path)

DataFrame.from_datapackage("out/<sname>.zip")    # restores data + metadata losslessly
```

Column annotations map to Frictionless field properties (`title`←label, `unit`,
`rdfType`←ontology, `description`), and the dtype to a Table Schema `type`
(`integer`/`number`/`boolean`/`datetime`/`string`).

### HDF5

For large/scientific data, `to_hdf()` writes an HDF5 file (PyTables) with the sdata
metadata stored as the node's `_sdata` attribute; `from_hdf()` reads it back.
Several DataFrames can share one file via distinct `key`s (HDF5 has no in-memory
bytes form, so a `path`/`filename` is required). Needs `pip install "sdata[hdf]"`.

```python
sdf.to_hdf(path="out")                           # -> out/<sname>.h5  (key = sname)
DataFrame.from_hdf("out/<sname>.h5")             # default: first key in the file

# several tables in one file
sdf.to_hdf(filename="bundle.h5", key="run1")
other.to_hdf(filename="bundle.h5", key="run2")
DataFrame.from_hdf("bundle.h5", key="run2")
```

See [RFC 0002](../rfc/0002-hdf5-dataframe-serialization.md) for the design rationale.

## Table schema validation

A [`TableSchema`][sdata.schema.TableSchema] declares the expected columns (reusing
[`AttrSpec`][sdata.schema.AttrSpec]) and validates a DataFrame against them —
missing columns, dtype mismatches (against `df.dtypes`), unit mismatches (against
`column_metadata`) and extra, unspecified columns:

```python
from sdata.schema import TableSchema, AttrSpec

schema = TableSchema("TensileTable", [
    AttrSpec("weight", dtype="int", unit="kg", required=True),
    AttrSpec("height", dtype="float", unit="m"),
])

report = sdf.validate_table(schema)   # ValidationReport (truthy if ok)
schema.apply(sdf)                      # fill missing column_metadata from the schema
```

A `DataFrame` subclass may set `TABLE_SCHEMA` to have its `column_metadata`
auto-completed on construction; `sdf.validate_table()` then checks against it —
analogous to `Base.SDATA_SCHEMA` for the dataset metadata.

## Full API

See the [API reference](../api.md#sdatasclassdataframe) for the complete,
auto-generated signature list.
