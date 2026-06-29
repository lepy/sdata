# Images: embedding sdata metadata

[`sdata.sclass.image.Image`][sdata.sclass.image.Image] is a
[`Blob`][sdata.sclass.blob.Blob] over image content. sdata can write its metadata
**natively into the image file** — and read it back — across **six containers with
one API**: PNG, JPEG, JPEG 2000 (`jp2`), GIF, WebP and TIFF.

The embedding layer [`sdata.imagemeta`][sdata.imagemeta] is **pure Python**
(standard library only): it needs no third-party tool (no `exiftool`) and — crucially
— **no Pillow** to read or write the metadata. Pillow is only used to *decode* pixels
(`img.pil` / `img.to_numpy`) or to *transcode* between formats on `save`.

Any **other** Pillow-writable format without a native metadata container (e.g. BMP)
is handled through the **same API**: `save` writes a lossless
`<filepath>.meta.json` sidecar and `from_file` reads it back — so metadata is never
lost regardless of the container.

| Format | Native carrier of the sdata payload        | Marker          |
| ------ | ------------------------------------------ | --------------- |
| PNG    | `iTXt` chunk before `IEND`                 | keyword `sdata` |
| JPEG   | `APP1` segment right after SOI             | `sdata\0` prefix|
| JP2    | `uuid` box (ISO BMFF) before `jp2c`        | fixed sdata UUID|
| GIF    | comment extension after the header         | `sdata\0` prefix|
| WebP   | dedicated RIFF chunk `sdAT`                | FourCC `sdAT`   |
| TIFF   | private IFD tag (original bytes untouched) | tag `65000`     |

```bash
pip install pillow      # optional: only needed to decode/transcode pixels
```

## Round-trip through `Image`

The same three calls work for every supported format — the container is chosen from
the file suffix on `save`:

```python
import io
import PIL.Image
from sdata.sclass.image import Image

# some image bytes (here a freshly encoded JPEG)
buf = io.BytesIO()
PIL.Image.new("RGB", (640, 480), (30, 60, 90)).save(buf, "JPEG")

img = Image.from_bytes("specimen.jpg", buf.getvalue())
img.metadata.add("operator", "ada", description="who acquired the image")
img.metadata.add("exposure", 1.5, unit="s", dtype="float")

img.save("specimen.jpg")                 # sdata metadata embedded in the APP1 segment

reloaded = Image.from_file("specimen.jpg")
reloaded.metadata.get("operator").value  # 'ada'
reloaded.metadata.get("exposure").value  # 1.5
```

`save` is lossless when the stored bytes already use the target container: the
metadata is embedded **without re-encoding** the pixels (and without Pillow). Only a
*format change* (e.g. a PNG saved as `.webp`) transcodes via Pillow:

```python
png = Image.from_bytes("a.png", png_bytes)
png.metadata.add("note", "converted")
png.save("a.webp")                       # transcodes to WebP, then embeds the metadata
```

Reading the embedded metadata never needs Pillow:

```python
md = Image.from_file("specimen.jpg").embedded_metadata()  # a Metadata, or None
```

## Inherited `Blob` capabilities

Because `Image` is a `Blob`, every image is also a content-addressable asset
(see [RFC 0003](../rfc/0003-blob-as-data-foundation.md)):

```python
img.size           # content size in bytes
img.sha256         # SHA-256 of the content
img.update_checksum()   # store the checksum in metadata
img.verify()       # check the content against the stored checksum
img.write("s3://bucket/specimen.jpg")    # fsspec target (needs sdata[blob])
```

!!! note "Checksum vs. embedded metadata"
    Embedding metadata **changes the file bytes** (and therefore its hash). If you
    need a stable content hash, compute it **before** embedding, or hash the decoded
    pixels — analogous to the data-vs-metadata hash split for `DataFrame`
    ([RFC 0004](../rfc/0004-dataframe-and-blob.md)).

## Low-level API (`sdata.imagemeta`)

To embed an arbitrary text payload directly into image bytes — independent of
`Image` and of Pillow — use the façade:

```python
from sdata import imagemeta

imagemeta.detect_format(data)        # 'png' | 'jpeg' | 'jp2' | 'gif' | 'webp' | None
out = imagemeta.embed(data, '{"k": 1}')   # format auto-detected; replace semantics
imagemeta.extract(out)               # '{"k": 1}'  (None if absent/unknown format)
imagemeta.supported_formats()        # ('png', 'jpeg', 'jp2', 'gif', 'webp', 'tiff')
```

* **Replace semantics:** embedding again **replaces** the previous sdata payload
  rather than appending a second one (idempotent).
* **Lenient reads:** `extract` returns `None` for an unknown format or an image
  without an sdata payload; `embed` raises
  [`UnsupportedImageFormatError`][sdata.imagemeta.UnsupportedImageFormatError] for an
  unsupported format and
  [`PayloadTooLargeError`][sdata.imagemeta.PayloadTooLargeError] when a JPEG payload
  exceeds the single-`APP1` limit (~64 KiB).
* **Extensible registry:** further containers (e.g. BMP, BigTIFF) plug in as two
  small functions plus one registry entry.

## Sidecars

For a container **without** a native metadata slot, `save` automatically writes a
lossless `<filepath>.meta.json` sidecar (same payload as the embedded form), and
`from_file` merges it back — the API is identical to the embedded case:

```python
img = Image.from_bytes("scan.bmp", bmp_bytes)
img.metadata.add("station", "lab-3")
img.save("scan.bmp")                       # writes scan.bmp + scan.bmp.meta.json
Image.from_file("scan.bmp").metadata.get("station").value   # 'lab-3'
```

The sidecar policy is controllable: `save(..., sidecar=True)` always writes one
(in addition to embedding, e.g. for tooling that only reads sidecars),
`sidecar=False` never does, and the default (`None`) writes one only when the format
has no native container.

When metadata must stay external (read-only originals) or machine-readable as Linked
Data, the JSON-LD **sidecar** remains the complement — see
[Machine-readable metadata](metadata-jsonld.md). Embedding and sidecars share the
same metadata model and are not mutually exclusive.

The design and the per-format details are specified in
[RFC 0005 — Native image metadata](../rfc/0005-native-image-metadata.md).
