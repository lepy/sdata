# Changelog

All notable changes to **sdata** are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-06-29

A large, strictly **additive** increment: a content/integrity foundation under all
data containers (`Blob`), a much broader `DataFrame` serialization portfolio, and
native, format-agnostic metadata embedding for images. Core dependencies remain
`numpy`, `pandas`, `suuid`; every new backend stays optional with a pure-Python path.

### Added

- **Native image metadata (RFC 0005).** New pure-Python, Pillow-free module
  `sdata.imagemeta` embeds/reads sdata metadata **natively** into six containers with
  one API (`detect_format`/`embed`/`extract`/`supported_formats`): **PNG** (`iTXt`),
  **JPEG** (`APP1`), **JPEG 2000** (`uuid` box), **GIF** (comment extension),
  **WebP** (`sdAT` chunk) and **TIFF** (private IFD tag, original bytes untouched).
  `Image` gains a uniform `save`/`from_file` flow, `embedded_metadata()`, and a
  lossless `<file>.meta.json` **sidecar fallback** for formats without a native
  carrier (e.g. BMP), controllable via `save(sidecar=True|False|None)`.
- **`Blob` as the content/integrity/provenance foundation (RFC 0003).** Hardened
  `Blob` with `sha256`/`sha1`/`md5`, `size`, `verify()`/`update_checksum()`, a lazy
  `content_bytes` cache, `exists()`, `write(uri)`/`open()` (fsspec), standard-vocabulary
  provenance metadata (`dcat:mediaType`, `dcterms:*`, `schema:sha256`) and
  mime/creation-date autofill. `FileReference` and `Image` now build on `Blob`.
- **Shared integrity mixin (RFC 0004, Option B).** `sdata.sclass.content.ContentIntegrityMixin`
  provides the hash/`verify`/`size` layer to both `Blob` and `DataFrame` via a
  `content_bytes` hook (no inheritance between them).
- **`DataFrame.as_blob(fmt)` (RFC 0004, Option C).** Render a table as a standalone
  `Blob` in a chosen format (`parquet`/`csv`/`arrow`/`feather`) — composition that
  grants hash/`verify`/`size`/`write`/`open` without changing the base class.
- **`DataFrame` serialization portfolio.** Native per-column field metadata in
  **Arrow/Feather** (`to_arrow`/`from_arrow`/`to_feather`/`from_feather`), a
  Frictionless **Data Package** bundle (`to_datapackage`/`from_datapackage`, `.zip`),
  and **HDF5** I/O (`to_hdf`/`from_hdf`, optional `sdata[hdf]`, RFC 0002).
- **RFCs.** 0002 (HDF5), 0003 (Blob foundation), 0004 (DataFrame vs. Blob),
  0005 (native image metadata); MkDocs nav, API reference and usage guides extended.

### Changed

- `DataFrame.content_bytes` hashes the **data only** (plain Parquet), so storing the
  checksum in the metadata does not change the hash (no self-reference).
- Documentation reorganized around the full DataFrame serialization portfolio and the
  image-metadata workflow (new `usage/image-metadata.md`).

### Notes

- 100 % line coverage maintained; `mkdocs build --strict` green. `sdata.imagemeta` is
  measured (100 %) via synthetic, Pillow-free tests, so coverage holds even without
  Pillow installed.

## [1.2.0] - 2026-06-26

- **Machine-readable metadata backbone.** Typed dtype registry, a registered JSON-LD
  `@context` (vocab/units/BFO), `to_jsonld`/`to_rdf`/`to_turtle` with `<sname>.meta.jsonld`
  sidecars, declarative `MetadataSchema`/`TableSchema` validation, an interactive
  Jupyter layer (`_repr_html_`, attribute autocomplete) and signed metadata as W3C
  **Verifiable Credentials** over the pure-Python EdDSA stack (`sdata.did`).
- **Self-describing `DataFrame` container** with per-column metadata and Parquet/CSV/
  dict/JSON-LD serialization, superseding the deprecated `Data` class.
- **Docs & packaging.** MkDocs Material + mkdocstrings documentation site; core
  dependencies reduced to `numpy`/`pandas`/`suuid` (stdlib `zoneinfo`); warning-free
  test suite.

[Unreleased]: https://github.com/lepy/sdata/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/lepy/sdata/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/lepy/sdata/releases/tag/v1.2.0
