
[![PyPI version](https://badge.fury.io/py/sdata.svg)](https://badge.fury.io/py/sdata)
[![PyPI](https://img.shields.io/pypi/v/sdata.svg?style=flat-square)](https://pypi.python.org/pypi/sdata/)
[![readthedocs](https://readthedocs.org/projects/sdata/badge/?version=latest)](http://sdata.readthedocs.io/en/latest/) 
[![Coverage Status](https://coveralls.io/repos/github/lepy/sdata/badge.svg?branch=master)](https://coveralls.io/github/lepy/sdata?branch=master)
[![Das sdata-Format v0.8.4](https://zenodo.org/badge/DOI/10.5281/zenodo.4311323.svg)](https://doi.org/10.5281/zenodo.4311323)

https://lepy.github.io/sdata/

# Structured data format (sdata)

## Design goals

* open data format for open science projects
* self describing data
* flexible data structure layout
    * hierarchical data structure (nesting groups, dictionaries)
    * (posix path syntax support?)
* extendable data structure
   * data format versions
* platform independent
* simple object model
* support of standard metadata formats (key/value, ...)
* support of standard dataset formats (hdf5, netcdf, csv, ...)
* support of standard dataset types (datacubes, tables, series, ...)
* support of physical units (conversion of units)
* transparent, optional data compression (zlib, blosc, ...)
* support of (de-)serialization of every dataset type (group, data, metadata)
* easy defineable (project) standards, e.g. for a uniaxial tension test (UT)
* (optional data encryption (gpg, ...))
* change management support?
* Enable use of data structures from existing tensor libraries transparently
* (single writer/ multiple reader (swmr) support)
* (nested data support)

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

`DataFrame` wraps a pandas frame plus per-column metadata and serializes to
Parquet, CSV, Arrow/Feather, dict/JSON and JSON-LD — embedded or as a sidecar.

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
sdf.to_feather(path="out")                     # Arrow IPC (needs sdata[parquet])
DataFrame.from_parquet("out/specimen_01.spq")

# validate the table against a schema (missing/dtype/unit/extra columns)
from sdata.schema import TableSchema, AttrSpec
schema = TableSchema("TensileTable", [
    AttrSpec("weight", dtype="int", unit="kg", required=True),
])
report = sdf.validate_table(schema)            # ValidationReport (truthy if ok)
```

Arrow/Feather/Parquet need `pip install "sdata[parquet]"`; CSV, dict and JSON-LD
work with the core install. See the [Tabular data docs](https://lepy.github.io/sdata/usage/dataframe/)
([`docs/usage/dataframe.md`](docs/usage/dataframe.md)) for details.

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

* int
* float
* str
* bool
* list (list of strings)
* timestamp (ISO-8601 with timezone, stdlib `zoneinfo`)
* bytes (base64 in JSON)
* json (dict/list)
* uri

Set `strict=True` (e.g. `metadata.add(..., strict=True)`) to raise on invalid
values instead of the lenient default coercion.

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

