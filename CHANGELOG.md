# Changelog

All notable changes to **sdata** are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Parquet directory mode (RFC 0007 F5 / RFC 0011).** `ParquetWriter(uri,
  directory=True)` writes one `<sname>.spq` per `write` into a directory instead of
  overwriting a single URI, so `write_group` keeps each table in its own file;
  `ParquetReader(uri, directory=True)` with `keys()` + `read_group` reads the directory
  back into a `DataFrameGroup` (symmetric). Single-file mode is unchanged.
- **Frequency units `Hz`/`kHz`/`MHz`/`GHz` (RFC 0006).** Recognized as named units
  (input, conversion, QUDT `unit:HZ`), interconvertible with the `1/s` family. The
  rate/frequency dimension keeps its **neutral** canonical back-name (`1/s`/`1/ms`) —
  not `Hz` — because the same dimension also denotes strain rate; `_CANON_SYMBOLS` is
  now documented as the preferred-symbol table (energy→`J`, power→`W`, rate→`1/s`).
- **Native per-column HDF5 attributes (RFC 0002).** `to_hdf` now attaches each
  column's `unit`/`label`/`description`/`ontology` **natively** as HDF5 dataset
  attributes (readable by any HDF5 tool — h5py/HDFView/`h5ls`), alongside the `_sdata`
  blob; `from_hdf` merges them back into `column_metadata`, even for foreign files
  without the blob (symmetric to the Arrow field-metadata path).
- **Persistent target unit system (`DataFrame.unit_system`, RFC 0014).** The table's
  target unit system (RFC 0006) now survives serialization: it is stored as a reserved
  `_sdata_unit_system` metadata field (the base-unit list), so it round-trips through
  dict, Parquet, HDF5 and JSON-LD (`sdata:unitSystem`) automatically. A DataFrame loaded
  from Parquet keeps its `convert()` target; `UnitSystem` gains `__eq__`/`__hash__`.

## [1.4.0] - 2026-07-02

The **RFC 0008 improvement program** plus the unit-conversion and writer/reader layers:
a symmetric reader interface, explicit format versioning, persistence consolidation and
a PEP 621 packaging modernization. Strictly additive; core dependencies stay
`numpy`, `pandas`, `suuid`.

### Added

- **DataFrame reader interface (`sdata.iolib.reader`, RFC 0009).** Symmetric to the
  writer: a `DataFrameReader` protocol + `BaseDataFrameReader` template with the same
  `require_*` contract, `ParquetReader`/`StoreReader`/`SqlReader` and a `read_group`
  batch helper — round-tripping each backend with its qualifying metadata.
- **Format versioning (`sdata.format`, RFC 0010).** A `_sdata_format_version` stamped on
  every object, with `read_format_version`/`ensure_compatible`/`register_migration`, a
  `FormatVersionWarning` and an `IncompatibleFormatError`; `Base.from_dict` and the
  `DataFrame` restore paths check compatibility (opt-in `strict=`).
- **Writer interface for DataFrames (`sdata.iolib.writer`, RFC 0007).** A unifying sink
  abstraction over the existing serializers: a `DataFrameWriter` protocol +
  `BaseDataFrameWriter` template method with a `require_metadata`/`require_columns`/
  `require_units` contract, a uniform `WriteReceipt` return, and the `ensure_sdata` /
  `write_with_provenance` bridge (metadata truth source stays `metadata`/`column_metadata`,
  not `df.attrs`). Four sinks: `ParquetWriter` (fsspec URI, embedded `_sdata`),
  `StoreWriter` (object persistence into a `JSON1SQLiteStore`, findable by `suuid`/`sname`
  via a flattening adapter), `SqlWriter` (relational table + shared `sdata_dataframe_meta`
  table, atomic data+metadata write, allowlisted identifiers) and `GraphWriter`
  (RDF/Turtle or JSON-LD, optional named-graph accumulation via `sdata[rdf]`). Runs on the
  stdlib `sqlite3`; a `usage/writer.md` guide and RFC 0007 document it.
- **Unit conversion via dimensional algebra (`sdata.units`, RFC 0006).** A pure-Python
  conversion layer: `convert`/`convert_factor`/`quantity_of`/`dimension_of` and a
  `UnitSystem` that is **solved from its base units** — so a *consistent* system such as
  `["kN", "mm", "ms"]` derives **all** units (stress→`GPa`, energy→`J`, velocity→`m/s`,
  mass→`kg`) from the base set via an exact `fractions`-based solver. Covers length,
  mass, time, temperature (offset units), force, pressure, energy, power, velocity,
  area/volume and rate; works on scalars/lists/NumPy arrays/pandas Series; raises a clear
  `UnitConversionError` on incompatible dimensions or inconsistent systems.
- **`DataFrame.convert(units=None, inplace=False)`.** Convert a table's columns into a
  target unit system (a unit list, a `UnitSystem`, or an explicit `{column: unit}`
  mapping) — **including derived units** — and update the per-column `unit` annotations,
  returning a converted copy by default. Columns without a unit or whose dimension the
  system does not span are left unchanged.
- **`DataFrame.relabel_units(mapping, *, force=False)`.** Fix mislabeled units: set the
  `unit` of named columns **without rescaling** the values; same-dimension relabels are
  logged, a dimension change requires `force=True`. Returns a report.
- **`DataFrame.unit_system`.** A settable target unit system on the table (a
  `UnitSystem` or unit list, also via the `unit_system=` constructor keyword);
  `convert()` with no argument converts into it. Setting only records the target
  (the data is rescaled by `convert()`), and a converted copy carries it over.
- **Docs.** A worked tensile-test example (`force [N]` / `time [s]` /
  `displacement [mm]`, fully semantically described, converted to `[kN, mm, ms]`) and a
  unit-conversion reference in `usage/dataframe.md`; RFC 0006 v2 (dimensional algebra).

### Changed

- **HDF5 backend uses `h5py`** instead of PyTables (RFC 0002 amendment): each column is a
  native HDF5 dataset under a `key` group (readable by any HDF5 tool), the sdata metadata
  rides along as the group's `_sdata` attribute; the `hdf` extra now installs `h5py`.
  Legacy PyTables kwargs (`format`/`complevel`/`complib`) are accepted and ignored.
- **Packaging modernized to PEP 621 (RFC 0013).** Metadata and extras live in a single
  `[project]` table in `pyproject.toml`; the version resolves via `dynamic = ["version"]`
  from `sdata/__init__.py` (single source). Core deps stay `numpy`/`pandas`/`suuid>=0.2.0`.
- **`DataFrameGroup` members are now `DataFrame` objects (RFC 0011)** with symmetric
  `write_group`/`read_group` batch helpers, replacing the ad-hoc raw-pandas layout.
- **`Data` (deprecated) warns on direct instantiation (RFC 0012);** `DataFrame` is the
  primary export in `__all__`/`SDATACLS`, while `Data` stays resolvable for
  deserialization (subclasses like `Pud` are undisturbed — port is stage 2 / 2.0).

### Removed

- `setup.py` and `requirements.txt` — folded into the PEP 621 `[project]` table and
  extras (RFC 0013); `setup.cfg` (RFC 0008 A5).
- Orphaned vendored `contrib` packages with no importers: `attrdict`, `semver`,
  `simple_graph_db`; the legacy `iolib/vault.py` and `node.py` (RFC 0011); and the dead
  `FlatHDFDataStore` (`iolib/hdf.py`, superseded by `DataFrame.to_hdf`/h5py).

### Fixed

- `logging.basicConfig` removed from library modules — a library must not configure the
  root logger; a `NullHandler` is attached at the package root instead (RFC 0008 A1).
- `Metadata.from_json` with no source raises a clear `ValueError` instead of
  `UnboundLocalError` (A2); a German topology-class value that failed to resolve now uses
  its canonical English term (A6).

### Docs

- RFCs 0009 (reader), 0010 (format versioning), 0011 (persistence consolidation),
  0012 (`Data` deprecation), 0013 (packaging), an open-points backlog and an RFC 0002
  h5py amendment.
- Contributor `conventions.md` (English code/docs, typing, lenient/`strict` error
  policy); an honest README design-goal status table; license set to **MIT**.

## [1.3.0] - 2026-06-29 (unreleased — shipped as part of 1.4.0)

A large, strictly **additive** increment: a content/integrity foundation under all
data containers (`Blob`), a much broader `DataFrame` serialization portfolio, and
native, format-agnostic metadata embedding for images. Core dependencies remain
`numpy`, `pandas`, `suuid`; every new backend stays optional with a pure-Python path.

### Added

- **New attribute dtypes** `date`, `time`, `duration`, `decimal`, `complex`,
  `floatlist` and `langstring` (pure stdlib): `date`/`time` (`xsd:date`/`xsd:time`),
  `duration` as a `datetime.timedelta` parsed from ISO 8601 (`xsd:duration`), `decimal`
  as `decimal.Decimal` for exact numerics (`xsd:decimal`), `complex` numbers and
  `floatlist` (typed `list[float]`, also from numpy arrays) — the latter two use the
  custom datatype CURIEs `sdata:complex` / `sdata:floatlist`, and `langstring`
  (`rdf:langString`, `"Hallo@de"`) renders via JSON-LD `@language` — all with a lossless
  round-trip. Lenient/`strict=` coercion as for the existing dtypes.
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

[Unreleased]: https://github.com/lepy/sdata/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/lepy/sdata/compare/v1.2.0...v1.4.0
[1.2.0]: https://github.com/lepy/sdata/releases/tag/v1.2.0
