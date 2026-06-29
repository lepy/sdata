# Tabular data: the `DataFrame` container

[`sdata.sclass.dataframe.DataFrame`][sdata.sclass.dataframe.DataFrame] is the
self-describing tabular container (it supersedes the deprecated `Data` class). It
wraps a pandas `DataFrame` together with per-column metadata and serializes to
Parquet, CSV, Arrow/Feather, dict/JSON and JSON-LD/RDF — with the qualifying
metadata either embedded or written as an independent sidecar.

```python
import pandas as pd
from sdata.sclass.dataframe import DataFrame

df = pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})
sdf = DataFrame(df=df, name="specimen_01", description="a tension test")
```

The pandas frame is always available via `sdf.df`; convenience pass-throughs
(`len(sdf)`, `sdf.shape`, `sdf.columns`, `sdf.dtypes`, `sdf.head()`,
`sdf.describe()`) delegate to it.

## Column metadata

Each column carries an [`Attribute`][sdata.metadata.Attribute]
(`unit`/`label`/`description`/`ontology`/`required`) in `sdf.column_metadata`.
Annotate columns with `set_column` (only the fields you pass are changed; existing
annotations are preserved):

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

When the df is reassigned (`sdf.df = other`), `column_metadata` is kept in sync:
new columns are added and annotations for removed columns are pruned, while
surviving columns keep their `unit`/`label`. Column metadata supplied at
construction time is preserved as-is (orphan keys are only logged as a warning).

## Serialization

All writers take an optional `path` and a `sidecar` flag; without a path they
return bytes (or, for CSV, a string). The metadata travels embedded in the binary
formats and via the optional `<sname>.meta.jsonld` sidecar everywhere.

```python
# Parquet (.spq) — metadata embedded in df.attrs / schema
sdf.to_parquet(path="out", sidecar=True)        # -> out/<sname>.spq + sidecar
DataFrame.from_parquet("out/<sname>.spq")
raw = sdf.to_parquet()                           # in-memory bytes
DataFrame.from_parquet_bytes(raw)

# CSV — data only (pure pandas); metadata via the sidecar
sdf.to_csv(path="out", sidecar=True)             # index dropped by default
DataFrame.from_csv("out/<sname>.csv")
text = sdf.to_csv()                              # CSV string

# Arrow / Feather — metadata embedded in the Arrow schema
table = sdf.to_arrow()                           # pyarrow.Table
DataFrame.from_arrow(table)
sdf.to_feather(path="out")                       # -> out/<sname>.feather
DataFrame.from_feather("out/<sname>.feather")

# dict / JSON-LD / RDF
d = sdf.to_dict();  DataFrame.from_dict(d)
sdf.to_jsonld();    sdf.to_turtle();    sdf.write_sidecar("out")
```

!!! note "Optional backend"
    Arrow, Feather and Parquet need pyarrow (`pip install "sdata[parquet]"`); CSV,
    dict and JSON-LD work with the core install. A missing backend raises a clear
    `ImportError` pointing at the extra.

!!! tip "Native per-column metadata (Arrow / Feather)"
    Besides the `_sdata` JSON blob, `to_arrow()` (and therefore `to_feather()`)
    attaches each column's `unit`/`label`/`description`/`ontology` **natively** to
    that column's Arrow field metadata. Arrow-aware tools (DuckDB, Polars, pyarrow)
    can read the per-column annotations without sdata, and `from_arrow()` merges
    field metadata from foreign Arrow tables back into `column_metadata`.

    ```python
    table = sdf.to_arrow()
    table.schema.field("weight").metadata   # {b'unit': b'kg', b'label': b'Gewicht', ...}
    ```

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
analogous to `Base.SDATA_SCHEMA` for metadata.
