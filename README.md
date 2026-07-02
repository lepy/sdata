
[![PyPI](https://img.shields.io/pypi/v/sdata.svg?style=flat-square)](https://pypi.python.org/pypi/sdata/)
[![Python versions](https://img.shields.io/pypi/pyversions/sdata.svg?style=flat-square)](https://pypi.python.org/pypi/sdata/)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue?style=flat-square)](https://lepy.github.io/sdata/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.4311323.svg)](https://doi.org/10.5281/zenodo.4311323)

# Structured data format (sdata)

## Design goals & status

sdata is an open, self-describing data format for open-science projects. The
table below is an honest status of the original design goals (triaged in
[RFC 0008](docs/rfc/0008-bestandsaufnahme-roadmap.md)) — **implemented**,
**partial**, on the **roadmap**, or an explicit **non-goal**.

| Goal | Status | Notes |
|------|--------|-------|
| Open, self-describing data | **implemented** | metadata embedded in every format |
| Platform independent, simple object model | **implemented** | pure Python / numpy / pandas |
| Standard metadata formats (key/value, JSON-LD, …) | **implemented** | `Metadata`, QUDT/BFO/PROV/CSVW/DID/VC |
| Physical units + conversion | **implemented** | `sdata.units` (RFC 0006) |
| Standard dataset formats — HDF5, CSV, Parquet, Arrow, Data Package | **implemented** | HDF5 via `sdata[hdf]` |
| (De-)serialization of data + metadata | **implemented** | lossless round-trips |
| Data format versions | **implemented** | `_sdata_format_version` + migration (RFC 0010) |
| Project standards (e.g. tensile test) | **partial** | schema templates (`MetadataSchema`/`TableSchema`) |
| Series | **partial** | as a one-column table |
| Hierarchical structure / nested groups | **partial** | `DataFrameGroup` (flat) + `parent`/`project` relations |
| Transparent compression | **partial** | Parquet-internal (zstd); zlib is a **non-goal** for the store (speed) |
| Standard dataset formats — **netCDF** | **roadmap** | not implemented |
| Dataset types — **datacubes** | **roadmap** | not implemented |
| Optional encryption (gpg, …) | **non-goal** | encrypt blobs/filesystem out of band |
| posix-path syntax, change management, tensor-library interop, SWMR | **non-goal** | not planned; revisit on demand |

Machine-readable metadata is the backbone (see below); the optional semantic
backends degrade gracefully to pure Python.

## Quickstart

```python
import pandas as pd
from sdata.sclass.dataframe import DataFrame

df = pd.DataFrame({"force": [1.0, 2.0, 3.0]})
data = DataFrame(df=df, name="specimen_01", description="a tension test")
data.metadata.add("max_force", 12.5, unit="kN", dtype="float",
                  description="max force", ontology="bfo:Quality")

print(data.metadata.df[["value", "unit", "dtype", "ontology"]])
```

```
                                          value unit  dtype     ontology
key
_sdata_name                         specimen_01    -    str
_sdata_sname    DataFrame__specimen_01__3003...    -    str
...
max_force                                  12.5   kN  float  bfo:Quality
```

Every object has a deterministic, content-addressable identity (`SUUID`), a set
of reserved `_sdata_*` attributes (name, sname, suuid, class, ctime, parent,
project, topology class) and freely extensible, fully-described user attributes.

## Machine-readable metadata (JSON-LD / Linked Data)

The metadata is the backbone of the data description: it lives next to every
data blob and fully qualifies the data — units (QUDT/UCUM), ontology classes
(BFO), provenance (PROV/DCAT), tabular columns (CSVW) and identity (DID).

```python
# self-describing JSON-LD (qudt:Quantity units, BFO @type, did:suuid @id, csvw columns)
doc = data.to_jsonld()

# RDF/Turtle (uses rdflib if installed, otherwise returns the JSON-LD)
print(data.to_turtle())

# write the data + a sidecar <sname>.meta.jsonld right next to it
data.to_json("specimen_01.sjson", sidecar=True)

# validate / auto-complete against a schema template
from sdata.schema import MetadataSchema, AttrSpec
schema = MetadataSchema("TensileTest", [
    AttrSpec("max_force", dtype="float", unit="kN", required=True, ontology="bfo:Quality"),
])
report = data.metadata.validate(schema)      # ValidationReport (truthy if ok)

# sign the metadata as a W3C Verifiable Credential (pure-Python Ed25519)
from sdata.did import keys, pub_from_priv_jwk
priv = keys.gen_ed25519_jwk()
vc = data.metadata.to_verifiable_credential("did:example:issuer", priv)
subject = data.metadata.from_verifiable_credential(vc, pub_from_priv_jwk(priv))

# interactive: attribute autocomplete + rich Jupyter display
data.metadata.a.max_force        # -> Attribute; tab-completion in Jupyter
data.metadata                    # -> _repr_html_ table
```

Resulting JSON-LD for `max_force` (excerpt):

```json
{
  "@id": "did:suuid:DataFrame__specimen_01__3003...:sdata",
  "@type": ["sdata:DataFrame", "bfo:BFO_0000004"],
  "name": "specimen_01",
  "sdata:max_force": {
    "@type": ["qudt:Quantity", "bfo:Quality"],
    "value": {"@value": 12.5, "@type": "xsd:double"},
    "unitRef": "unit:KiloN", "symbol": "kN"
  },
  "columns": [{"name": "force", "datatype": "xsd:double"}]
}
```

The optional semantic backends degrade gracefully to pure Python (no hard
dependency): `pip install "sdata[rdf]"` (rdflib), `sdata[units]` (pint),
`sdata[schema]` (jsonschema). Core install needs only `numpy`, `pandas`, `suuid`.

## Tabular data (`DataFrame`)

`DataFrame` wraps a pandas frame plus per-column metadata and serializes to many
formats — Parquet, Arrow/Feather, CSV, dict/JSON, JSON-LD, a Frictionless **Data
Package** and **HDF5** — with the qualifying metadata embedded or written as a
sidecar.

```python
import pandas as pd
from sdata.sclass.dataframe import DataFrame

sdf = DataFrame(df=pd.DataFrame({"weight": [10, 20], "height": [1.5, 1.6]}),
                name="specimen_01", description="a tension test")

# per-column annotations (only the fields you pass are changed)
sdf.set_column("weight", unit="kg", label="Gewicht", ontology="bfo:Quality")
sdf.col["height"].unit = "m"          # mutate the column Attribute in place
sdf.column_units                       # {'weight': 'kg', 'height': 'm'}

# serialize (optional <sname>.meta.jsonld sidecar; bytes/str without a path)
sdf.to_parquet(path="out", sidecar=True)      # out/<sname>.spq + sidecar
sdf.to_csv(path="out")                         # data-only CSV (pure pandas)
sdf.to_feather(path="out")                     # Arrow IPC + native per-column field metadata
sdf.to_datapackage(path="out")                 # Frictionless Data Package (.zip)
sdf.to_hdf(path="out")                         # HDF5 via h5py, one dataset/column (sdata[hdf])
DataFrame.from_parquet("out/specimen_01.spq")

# validate the table against a schema (missing/dtype/unit/extra columns)
from sdata.schema import TableSchema, AttrSpec
schema = TableSchema("TensileTable", [
    AttrSpec("weight", dtype="int", unit="kg", required=True),
])
report = sdf.validate_table(schema)            # ValidationReport (truthy if ok)
```

Arrow/Feather/Parquet need `pip install "sdata[parquet]"`, HDF5 `sdata[hdf]`; CSV,
dict, JSON-LD and the (CSV) Data Package work with the core install. See the
[Tabular data docs](https://lepy.github.io/sdata/usage/dataframe/)
([`docs/usage/dataframe.md`](docs/usage/dataframe.md)) for the full reference.

## Howto

  
* [Das sdata-Format - slides](https://lepy.github.io/sdata/ipynb/Das_sdata_Format.slides.html#)
* https://deepwiki.com/lepy/sdata

## Demo App

* [test the demo app with editor](https://share.streamlit.io/lepy/sdata_streamlit/main/sdata_editor.py)

Try to paste some Excel-Data in the forms ...


## Metadata

### Attributes

* name
* value
* dtype
* unit
* description
* label
* required
* ontology (CURIE/IRI of the value's class, e.g. `bfo:Quality`)

### dtypes for attributes

Every attribute value is coerced to a declared dtype (single source:
`sdata.dtypes`), each with a lossless JSON-LD / XSD mapping:

* `int`, `float`, `str`, `bool`
* `list` (list of strings), `floatlist` (typed list of floats)
* `timestamp` (ISO-8601 with timezone, stdlib `zoneinfo`)
* `date`, `time`, `duration` (ISO-8601 / `datetime` types)
* `decimal` (exact decimal), `complex` (complex number)
* `bytes` (base64 in JSON), `json` (dict/list), `uri`
* `langstring` (language-tagged string, `rdf:langString`, e.g. `"Hallo@de"`)

Coercion is **lenient** by default (invalid values are logged and left unchanged).
Pass `strict=True` (e.g. `metadata.add(..., strict=True)`) to raise `DtypeError`
instead. See the [conventions](https://lepy.github.io/sdata/conventions/) for the
error policy.

## paper

* [Das sdata-Format](https://zenodo.org/record/4311323#.X89yo9-YXys)
    * Ingolf Lepenies. (2020). Das sdata-Format (Version 0.8.4). http://doi.org/10.5281/zenodo.4311323 
    * [slides](https://lepy.github.io/sdata/ipynb/Das_sdata_Format.slides.html#),
    [html](https://lepy.github.io/sdata/paper/2020/Das_sdata-Format.html), 
    [pdf](https://lepy.github.io/sdata/paper/2020/Das_sdata-Format.pdf)
    [temperaturmessung-001.json](https://lepy.github.io/sdata/paper/2020/temperaturmessung-001.json)
    [temperaturmessung-001.xlsx](https://lepy.github.io/sdata/paper/2020/temperaturmessung-001.xlsx)
    
* [sdata](https://doi.org/10.5281/zenodo.4311396)
    * Ingolf Lepenies. (2020, December 8). sdata - a structured data format (Version 0.8.4). Zenodo. http://doi.org/10.5281/zenodo.4311397

