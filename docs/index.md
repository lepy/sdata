# sdata — structured data format

[![PyPI](https://img.shields.io/pypi/v/sdata.svg?style=flat-square)](https://pypi.python.org/pypi/sdata/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.4311323.svg)](https://doi.org/10.5281/zenodo.4311323)

**sdata** is an open, self-describing data format for open-science projects: a
simple object model where every object carries a deterministic, content-addressable
identity ([SUUID](https://github.com/lepy/suuid)), reserved `_sdata_*` attributes
and freely extensible, fully-qualified user metadata — all machine-readable
(JSON-LD / Linked Data).

## Install

```bash
pip install sdata                 # core: numpy, pandas, suuid
pip install "sdata[parquet]"      # pyarrow -> Parquet/Arrow/Feather DataFrame I/O
pip install "sdata[hdf]"          # tables  -> HDF5 DataFrame I/O
pip install "sdata[rdf]"          # rdflib  -> real Turtle/N-Triples/RDF-XML
pip install "sdata[units]"        # pint    -> validate/normalise units
pip install "sdata[schema]"       # jsonschema -> JSON-Schema validation
```

The optional backends degrade gracefully to pure Python — the core install has
no hard dependency on any of them.

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

## Where to next

- **[Cookbook (end to end)](usage/cookbook.md)** — one tensile-test dataset through
  image → table → schema → JSON-LD/RDF → Verifiable Credential.
- **[Tabular data (DataFrame)](usage/dataframe.md)** — the self-describing table
  container: column metadata, Parquet/CSV/Arrow/Feather I/O, table-schema validation.
- **[Image metadata](usage/image-metadata.md)** — embed sdata metadata natively into
  PNG/JPEG/JP2/GIF/WebP with one API (pure Python, no Pillow needed to read/write it).
- **[Machine-readable metadata](usage/metadata-jsonld.md)** — JSON-LD / RDF, units
  (QUDT/UCUM), ontology classes (BFO), provenance, schema validation and signing.
- **[API reference](api.md)** — the full Python API.

## Design goals

- open, self-describing data format for open-science projects
- flexible, extendable, hierarchical data structures
- platform-independent, simple object model
- standard metadata (key/value, units, ontology) and dataset formats
  (Parquet, CSV, Arrow/Feather, HDF5, JSON)
- physical units, content-addressable identity, (de-)serialization of every type

## Cite

Ingolf Lepenies. *Das sdata-Format.* Zenodo.
[10.5281/zenodo.4311323](https://doi.org/10.5281/zenodo.4311323)
