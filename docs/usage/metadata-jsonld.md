# Machine-readable metadata (JSON-LD, schema, signing)

The metadata is the backbone of the data description. It lives next to every data
blob, *fully qualifies* the data and is fully machine-readable: units (QUDT/UCUM),
ontology classes (BFO), provenance (PROV/DCAT), tabular columns (CSVW) and a
content-addressable identity (DID).

The semantic backends are **optional** and degrade gracefully to pure Python:

```bash
pip install sdata            # core only: numpy, pandas, suuid
pip install "sdata[rdf]"     # rdflib  -> real Turtle/N-Triples/RDF-XML
pip install "sdata[units]"   # pint    -> validate/normalise arbitrary units
pip install "sdata[schema]"  # jsonschema -> JSON-Schema validation
```

## The metadata model

Every [`Attribute`][sdata.metadata.Attribute] carries
`name, value, unit, dtype, description, label, required, ontology`. Supported
`dtype` values are `str, int, float, bool, list, timestamp, bytes, json, uri,
date, time, duration, decimal, complex, floatlist, langstring`. Each maps to an XSD
type for JSON-LD (e.g. `date` → `xsd:date`, `duration` → `xsd:duration` as ISO 8601 /
`timedelta`, `decimal` → `xsd:decimal` for exact numerics); `complex` and `floatlist`
(a typed `list[float]`) have no standard XSD type and use the custom datatype CURIEs
`sdata:complex` / `sdata:floatlist`; `langstring` is a language-tagged string
(`"Hallo@de"` → `{"@value": "Hallo", "@language": "de"}` in JSON-LD). Coercion is
lenient by default; pass `strict=True` to raise `sdata.dtypes.DtypeError` on invalid
values.

```python
import pandas as pd
from sdata.sclass.dataframe import DataFrame

df = pd.DataFrame({"force": [1.0, 2.0, 3.0]})
data = DataFrame(df=df, name="specimen_01", description="a tension test")
data.metadata.add("max_force", 12.5, unit="kN", dtype="float",
                  description="max force", ontology="bfo:Quality")
```

Reserved `_sdata_*` attributes (`name, sname, suuid, class, ctime, parent_sname,
project_sname, topology_class, version`) are populated automatically and back the
identity/provenance of the object.

## JSON-LD / RDF

```python
doc = data.to_jsonld()       # dict, self-describing JSON-LD
ttl = data.to_turtle()       # RDF/Turtle via rdflib, else the JSON-LD
```

The object's `@id` is its DID (`did:suuid:<sname>:sdata`); `@type` combines the
sdata class and the BFO topology IRI. Attributes **with a unit** become
`qudt:Quantity` nodes, unit-less ones become typed literals; the `ontology` field
is always the `@type`/class of the value. DataFrame columns are emitted as an
ordered `csvw:column` list.

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

`from_jsonld` reconstructs a [`Metadata`][sdata.metadata.Metadata] from such a
document. The JSON-LD `@context` is published and resolvable at
<https://lepy.github.io/sdata/ns/context.jsonld>.

## Sidecar files

Metadata can be written as an independent `<sname>.meta.jsonld` file right next to
the data blob (default off, so existing behaviour is unchanged):

```python
data.to_json("specimen_01.sjson", sidecar=True)   # writes both files
data.to_parquet(path="out", sidecar=True)         # <sname>.spq + sidecar

from sdata.base import Base
md = Base.read_sidecar("out/DataFrame__specimen_01__3003....meta.jsonld")
```

## Schema / templates

A [`MetadataSchema`][sdata.schema.MetadataSchema] declares the expected attributes
of a data class and can *validate* and *auto-complete* metadata:

```python
from sdata.schema import MetadataSchema, AttrSpec

schema = MetadataSchema("TensileTest", [
    AttrSpec("max_force", dtype="float", unit="kN", required=True,
             ontology="bfo:Quality"),
    AttrSpec("phase", dtype="str", allowed=["ferrite", "martensite"]),
])

report = data.metadata.validate(schema)   # ValidationReport (truthy if ok)
data.metadata.apply_schema(schema)         # fill defaults/units/ontology
schema.to_json_schema()                    # JSON Schema (Draft 2020-12)
```

A [`Base`][sdata.base.Base] subclass may set `SDATA_SCHEMA` to have its metadata
auto-completed on construction; `obj.validate()` checks against it.

## Verifiable Credentials

The JSON-LD can be signed as a W3C Verifiable Credential using the bundled,
pure-Python Ed25519 stack (no external crypto dependency):

```python
from sdata.did import keys, pub_from_priv_jwk

priv = keys.gen_ed25519_jwk()
vc = data.metadata.to_verifiable_credential("did:example:issuer", priv)
subject = data.metadata.from_verifiable_credential(vc, pub_from_priv_jwk(priv))
```

## Interactive use

```python
data.metadata.a.max_force          # attribute access + Jupyter tab-completion
data.metadata.get_prefixed("_sdata")  # subset by attribute-name prefix
data.metadata                       # rich _repr_html_ table in Jupyter
```
