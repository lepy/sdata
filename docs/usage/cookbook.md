# Cookbook: a self-describing dataset end to end

This walkthrough threads the whole library together on one realistic scenario — a
**tensile test**: an image of the specimen, the measured stress–strain curve, a
declarative schema, machine-readable export, and a cryptographic signature. Each step
builds on the previous one; the snippets run as shown.

```bash
pip install sdata pillow         # core + Pillow (for images)
pip install "sdata[parquet]"     # pyarrow  -> DataFrame Parquet/Arrow
pip install "sdata[rdf]"         # rdflib   -> real Turtle/RDF (optional)
```

## 1. An image with provenance and integrity

[`Image`][sdata.sclass.image.Image] is a [`Blob`][sdata.sclass.blob.Blob]: binary
content plus provenance and integrity. Annotate it, fix the checksum, and save — the
sdata metadata is embedded **natively** into the file (here a PNG `iTXt` chunk).

```python
import io
import PIL.Image
from sdata.sclass.image import Image

buf = io.BytesIO()
PIL.Image.new("RGB", (64, 48), (90, 90, 90)).save(buf, "PNG")

img = Image.from_bytes("specimen_01.png", buf.getvalue(), project="TensileTest")
img.metadata.add("operator", "ada", description="who acquired the image")
img.metadata.add("magnification", 200, unit="-", dtype="int")

img.update_checksum()                 # store the SHA-256 in the checksum metadata
img.sha256[:12], img.size, img.verify()      # ('d354ab02639d', 138, True)
img.metadata.get("mime_type").value          # 'image/png'  (autofilled)

img.save("specimen_01.png")           # embeds the sdata metadata into the PNG
Image.from_file("specimen_01.png").metadata.get("operator").value   # 'ada'
```

See [Image metadata](image-metadata.md) for the six native containers and the sidecar
fallback.

## 2. A table with column metadata

[`DataFrame`][sdata.sclass.dataframe.DataFrame] wraps a pandas frame with **per-column**
metadata and **dataset-level** metadata.

```python
import pandas as pd
from sdata.sclass.dataframe import DataFrame

df = pd.DataFrame({"strain": [0.0, 0.01, 0.02], "stress": [0.0, 210.0, 250.0]})
sdf = DataFrame(df=df, name="tensile_curve_01",
                description="engineering stress-strain curve",
                column_metadata={"strain": {"unit": "-", "label": "strain"},
                                 "stress": {"unit": "MPa", "label": "engineering stress"}})
sdf.set_column("stress", ontology="qudt:Stress")

sdf.column_units      # {'strain': '-', 'stress': 'MPa'}
sdf.shape             # (3, 2)
```

More table I/O (Parquet/CSV/Arrow/Feather/Data Package/HDF5) in
[Tabular data](dataframe.md).

## 3. A declarative schema: validate and complete

A [`MetadataSchema`][sdata.schema.MetadataSchema] declares the expected attributes of a
data class. `apply_schema` **completes** the metadata (defaults, units, ontology);
`validate` returns a truthy [`ValidationReport`][sdata.schema.ValidationReport].

```python
from sdata.schema import MetadataSchema, AttrSpec

schema = MetadataSchema("TensileTest", [
    AttrSpec("max_force", dtype="float", unit="kN", required=True, ontology="bfo:Quality"),
    AttrSpec("temperature", dtype="float", unit="degC", default=23.0),
])

sdf.metadata.apply_schema(schema)
report = sdf.metadata.validate(schema)
bool(report), report.missing                    # (False, ['max_force'])
sdf.metadata.get("temperature").value           # 23.0  (default filled in)

sdf.metadata.add("max_force", 18.2, dtype="float", unit="kN")
bool(sdf.metadata.validate(schema))             # True
```

A schema can also be wired onto a class via the `SDATA_SCHEMA` hook so that every
instance is auto-completed and `obj.validate()` works — see
[Machine-readable metadata](metadata-jsonld.md#schema-templates).

## 4. Machine-readable export: JSON-LD, RDF, sidecar

The metadata (including the per-column annotations as csvw columns) serializes to
JSON-LD, and to an independent `<sname>.meta.jsonld` sidecar.

```python
doc = sdf.to_jsonld()
doc["@id"]        # 'did:suuid:DataFrame__tensile_curve_01__…:sdata'
doc["columns"]    # [{'name': 'strain', 'datatype': 'xsd:double'},
                  #  {'name': 'stress', 'datatype': 'xsd:double',
                  #   'unitRef': 'unit:MegaPA', 'symbol': 'MPa', 'label': 'engineering stress'}]

sdf.write_sidecar(".")            # writes <sname>.meta.jsonld next to your data
sdf.to_turtle()                   # real Turtle with sdata[rdf]; JSON-LD fallback otherwise
```

The stable `@id` is the dataset's `did:suuid:<sname>:sdata` DID. Details on the vocab,
units (QUDT/UCUM) and ontology classes (BFO) are in
[Machine-readable metadata](metadata-jsonld.md).

## 5. Sign it: a Verifiable Credential

Finally, sign the (fully-qualified) metadata as a **W3C Verifiable Credential** — a
compact JWS over the JSON-LD, using the pure-Python EdDSA stack in `sdata.did` (no
external crypto dependency).

```python
from sdata.metadata import Metadata
from sdata import semantic
from sdata.did import keys, pub_from_priv_jwk

priv = keys.gen_ed25519_jwk()                 # issuer key (Ed25519, as a JWK)
pub = pub_from_priv_jwk(priv)

jws = sdf.metadata.to_verifiable_credential("did:example:lab", priv)
jws.count(".")                                # 2  -> compact JWS (header.payload.sig)

subject = semantic.verify_credential(jws, pub)        # raises on tampering
subject["@id"]                                # the dataset DID

restored = Metadata.from_verifiable_credential(jws, pub)
restored.get("max_force").value               # 18.2
```

Tampering with the payload makes `verify_credential` raise — the metadata is now
**verifiable and trustworthy**. See
[Verifiable Credentials](metadata-jsonld.md#verifiable-credentials).

## 6. Bundle a table as a binary asset

To hand a table around as a single hashable/signable file, render it to a `Blob` in a
chosen format ([`as_blob`][sdata.sclass.dataframe.DataFrame.as_blob]):

```python
blob = sdf.as_blob("parquet")                 # or "csv" / "arrow" / "feather"
blob.filetype, blob.verify(), blob.size       # ('parquet', True, 14453)
blob.write("s3://bucket/tensile_curve_01.parquet")   # fsspec target (sdata[blob])
```

## Where to go next

- [Tabular data (DataFrame)](dataframe.md) — the full table I/O portfolio.
- [Image metadata](image-metadata.md) — native embedding across six formats + sidecar.
- [Machine-readable metadata](metadata-jsonld.md) — JSON-LD/RDF, schema, units, VC.
- [API reference](../api.md) — the complete Python API.
