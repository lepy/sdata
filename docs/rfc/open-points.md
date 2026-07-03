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

* ~~**RFC 0002 — native Per-Spalten-HDF5-Attribute.**~~ **Erledigt:**
  `unit`/`label`/`description`/`ontology` liegen jetzt zusätzlich **nativ** als
  HDF5-Dataset-Attribute (tool-agnostisch lesbar); `from_hdf` merged sie zurück
  (auch ohne `_sdata`-Blob), symmetrisch zu Arrow.
* **RFC 0002 — In-Memory-Bytes-Pfad für HDF5.** HDF5 hat keinen sauberen Bytes-Pfad
  wie Parquet; derzeit nur Datei-API. Offen, ob es sich lohnt (h5py kann über
  `io.BytesIO`/`driver="core"` in-memory — machbar geworden).
* ~~**RFC 0004 — Prüfsummen-Determinismus.** Parquet ist nicht garantiert byte-stabil;
  für stabile Content-Hashes ggf. CSV als „canonical form" erwägen.~~ **Erledigt:**
  `DataFrame.content_bytes` (Hash-Basis für `sha256`/`update_checksum`/`verify`) ist
  jetzt die kanonische CSV-Form (`to_csv(index=False)`, UTF-8, ohne Index) statt Parquet
  — reproduzierbar, portabel, ohne pyarrow. `as_blob(fmt)`-Blobs hashen weiter die
  echten Format-Bytes (Asset-Integrität), getrennt von der logischen Daten-Identität.
* **RFC 0005 — weitere Bild-Träger.** BigTIFF (8-Byte-Offsets), JPEG Multi-Segment-
  `APP1` >64 KiB, PNG `zTXt`, WebP `VP8X+XMP`. Erweiterung der Handler-Registry.

## Offen — Semantik / Einheiten

* ~~**RFC 0006 — Persistenz des `unit_system`.**~~ **Erledigt (RFC 0014):** das
  Zielsystem reist jetzt als reserviertes Metadatenfeld `_sdata_unit_system`
  (Basis-Einheiten-Liste) durch dict/Parquet/HDF5/JSON-LD.
* ~~**RFC 0006 — mehrdeutige Dimensionsvektoren** (`1/s` vs `Hz`, `N·m` vs `J`).~~
  **Erledigt:** `Hz`/`kHz`/`MHz`/`GHz` als benannte Einheiten erkannt (QUDT-gemappt);
  `_CANON_SYMBOLS` als Vorzugs-Symbol-Tabelle dokumentiert (Energie→`J`, Rate bleibt
  neutral `1/s`, da = Dehnrate). `N·m`→`J` war bereits korrekt.
* ~~**RFC 0006 — Winkel-Einheiten** (rad/deg/gon).~~ **Erledigt:** eigene Dimensions-
  Achse „A" (ebener Winkel); rad/deg/gon/mrad konvertieren untereinander, sind aber
  gegen dimensionslos (`-`/`%`) abgegrenzt. QUDT-gemappt (`unit:RAD`/`DEG`/`GON`). Ein
  `UnitSystem` mit `rad`/`deg` in der Basis normalisiert Winkel; ein rein mechanisches
  lässt sie unberührt. **Logarithmische Einheiten** (dB) bleiben bewusst ausgeklammert
  (kein linearer Faktor).
* ~~**RFC 0006 — `pint`-Interop** außerhalb der kuratierten Tabelle.~~ **Erledigt:**
  ist das Extra `[units]` (pint) installiert, werden nicht kuratierte Einheiten
  (imperial/abgeleitet: `psi`, `inch`, `lbf`, `degF` …) über pint auf denselben
  5-Achsen-Dimensionsvektor abgebildet und sind damit in `dimension_of`/`convert`/
  `convert_factor`/`UnitSystem` nutzbar. Die kuratierte Tabelle hat Vorrang; ohne pint
  unverändert. Grenzen: Achsen außerhalb `(L,M,T,Θ,A)` (Strom/Stoffmenge) sind nicht
  darstellbar, Winkel folgen pints (dimensionslosem) Modell — dafür die kuratierten
  rad/deg/gon nutzen.

## Offen — Writer / Reader / Persistenz

* **RFC 0007 — relationaler `SqlWriter` & Typabbildung.** `df.to_sql` verliert
  Einheiten/Ontologie (nur die Sidecar-Tabelle hält sie); `if_exists="append"` deckt
  Schema-Drift nicht ab. Für semantiktreue Persistenz → `StoreWriter`.
* ~~**RFC 0007 / RFC 0011 — `ParquetWriter`-Verzeichnis-/Append-Modus (F5).**~~
  **Erledigt:** `ParquetWriter(uri, directory=True)` schreibt je Mitglied eine
  `<sname>.spq`; `ParquetReader(uri, directory=True)` + `keys()` + `read_group` lesen
  symmetrisch zurück.
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
