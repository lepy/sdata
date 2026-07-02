# Offene Punkte / Folge-Backlog (RFC 0001–0007)

Konsolidierte Liste der „Risiken / offene Punkte" aus RFC 0001–0007 (RFC 0008,
Punkt C5). Markiert, was die Folge-RFCs 0009–0013 inzwischen **erledigt** haben und
was als Backlog **offen** bleibt. Diese Seite ist der Einstieg für die nächste
Arbeitsrunde nach der RFC-0008-Roadmap.

## Erledigt durch RFC 0009–0013

| Ursprung | Punkt | Erledigt durch |
|----------|-------|----------------|
| RFC 0007 | Reader-Symmetrie (`DataFrameReader`-Protocol) | **RFC 0009** |
| RFC 0007 | `DataFrameGroup`-Batch (`write_group`/`read_group`) | **RFC 0011** |
| RFC 0002 | `DataFrameGroup`-Serialisierung (mehrere Keys) | **RFC 0011** (Group hält `sclass.DataFrame`) |
| RFC 0008 | Format-/Datenversion (`_sdata_format_version`) | **RFC 0010** |
| RFC 0001 | `logger.warn` → `logger.warning` in `blob.py` | erledigt (kein `logger.warn` mehr im Kern) |
| RFC 0001 | `vault.py` erwartet Alt-Spaltennamen? | **RFC 0011** (`vault.py` entfernt) |

## Offen — Serialisierung / Formate

* **RFC 0002 — native Per-Spalten-HDF5-Attribute.** Seit der h5py-Umstellung
  (RFC 0002 Amendment) ist jede Spalte ein eigenes Dataset — Einheit/Label/Ontologie
  ließen sich nun **nativ** als Dataset-Attribute anhängen (statt nur im
  `_sdata`-Gruppen-Blob). Kleiner Folge-PR.
* **RFC 0002 — In-Memory-Bytes-Pfad für HDF5.** HDF5 hat keinen sauberen Bytes-Pfad
  wie Parquet; derzeit nur Datei-API. Offen, ob es sich lohnt (h5py kann über
  `io.BytesIO`/`driver="core"` in-memory — machbar geworden).
* **RFC 0004 — Prüfsummen-Determinismus.** Parquet ist nicht garantiert byte-stabil;
  für stabile Content-Hashes ggf. CSV als „canonical form" erwägen.
* **RFC 0005 — weitere Bild-Träger.** BigTIFF (8-Byte-Offsets), JPEG Multi-Segment-
  `APP1` >64 KiB, PNG `zTXt`, WebP `VP8X+XMP`. Erweiterung der Handler-Registry.

## Offen — Semantik / Einheiten

* **RFC 0006 — Persistenz des `unit_system`.** Das Zielsystem einer Tabelle ist
  aktuell transient (überlebt Parquet/dict/JSON-LD nicht). → eigener Folge-RFC:
  `_sdata_unit_system` als Metadatenfeld (jetzt über RFC 0010 auch versionierbar).
* **RFC 0006 — mehrdeutige Dimensionsvektoren** (`1/s` vs `Hz`, `N·m` vs `J`):
  Vorzugs-Symbol-Tabelle für die Rück-Benennung.
* **RFC 0006 — Winkel/logarithmische Einheiten** (rad/deg, dB) bewusst noch ausgeklammert.
* **RFC 0006 — `pint`-Interop** außerhalb der kuratierten Tabelle.

## Offen — Writer / Reader / Persistenz

* **RFC 0007 — relationaler `SqlWriter` & Typabbildung.** `df.to_sql` verliert
  Einheiten/Ontologie (nur die Sidecar-Tabelle hält sie); `if_exists="append"` deckt
  Schema-Drift nicht ab. Für semantiktreue Persistenz → `StoreWriter`.
* **RFC 0007 / RFC 0011 — `ParquetWriter`-Verzeichnis-/Append-Modus (F5).** Ein
  partitionierter Modus (`run/part-*.spq`) ist skizziert (RFC 0011 §5.3), aber nicht
  umgesetzt.
* **RFC 0007 — Named-Graph-Persistenz** hängt an `rdflib`; ohne Backend nur
  Einzeldatei-Turtle/JSON-LD.
* **RFC 0003 — fsspec-Fehlerbilder vereinheitlichen** (`content_bytes`/`exists()`).

## Offen — Domäne / Aufräumen (aus RFC 0008 hervorgegangen)

* **`Data`-Ablösung Stufe 2 (2.0):** `Data`/`deprecated/data.py` entfernen, `Pud`/
  `experiments/*` portieren oder entfernen, Format-Migration `Data`→`DataFrame`
  scharfschalten (RFC 0012). Der interne `Data`-Nutzer `iolib/hdf.py`
  (`FlatHDFDataStore`, PyTables) wurde bereits **entfernt** (ersetzt durch
  `DataFrame.to_hdf`/h5py) — ein Baustein weniger für Stufe 2.
* **`contrib`-Einzelnutzer** (`piexif`/`sobol_seq`/`ranger`/`sortedcontainers`/
  `sqlitedict`/`timeflake`): je Paket Dependency/Extra/vendoriert entscheiden
  (RFC 0013 §4.3).
* **Typisierung/Sprache** vollständig durchziehen (per On-Touch-Regel,
  `docs/conventions.md`).

## Hinweis

Diese Liste ist ein **Momentaufnahme-Backlog** (Stand 2026-07-02, v1.3.0). Jeder
Punkt, der aufgegriffen wird, gehört in einen eigenen RFC bzw. PR mit Tests — nicht
in eine Sammel-Änderung.
