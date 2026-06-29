# RFC 0004 — `DataFrame` und `Blob`: Content-Layer vs. Multi-Format-Modell

| Feld        | Wert                                                         |
|-------------|--------------------------------------------------------------|
| Status      | Accepted — Option B (Integritäts-Mixin) **und** C (`as_blob`) implementiert |
| Datum       | 2026-06-29                                                  |
| Autor       | lepy <lepy@tuta.io>                                          |
| Komponente  | `sdata/sclass/content.py`, `dataframe.py`, `blob.py`        |
| Betrifft    | ob/wie `DataFrame` auf `Blob` aufbaut (Folge von RFC 0003)  |
| Validierung | Option B + C umgesetzt; content/blob/dataframe je 100 %     |

> **Umsetzungsstand.** **Option B** umgesetzt: `ContentIntegrityMixin`
> (`sdata/sclass/content.py`) liefert `sha1`/`md5`/`sha256`/`size` sowie
> `update_checksum`/`verify` über einen `content_bytes`-Hook + `self.metadata`.
> `Blob` und `DataFrame` erben den Mixin (keine Vererbung untereinander — RFC-Befund).
> `DataFrame.content_bytes` = **reines Daten-Parquet** (`self.df.to_parquet()`, *ohne*
> eingebettete Metadaten): der Hash erfasst die Daten, sodass das Speichern der
> Prüfsumme in den Metadaten den Hash nicht verändert (Selbstreferenz vermieden).
>
> **Option C** umgesetzt: `DataFrame.as_blob(fmt="parquet"|"csv"|"arrow"|"feather")`
> rendert die Tabelle in **einem gewählten Format** zu einem `bytes`-Content-`Blob`
> (Name/Description geerbt, `mime_type` gesetzt, `update_checksum` ausgeführt → `verify`
> sofort nutzbar). Damit erbt die Tabelle indirekt **alle** Blob-Fähigkeiten
> (Hash/`verify`/`size`/`write`/`open`/Sidecar) — strikt additiv, ohne Basiswechsel,
> ohne `to_dict`-Bruch. Unbekanntes `fmt` → `ValueError`.

## 1. Zusammenfassung

RFC 0003 hat `Blob` zur Content-/Integritäts-/Provenienz-Grundlage gemacht;
`FileReference` und `Image` bauen bereits darauf auf. Offen blieb **`DataFrame`**.

Dieses RFC analysiert, ob `DataFrame` von `Blob` **erben** sollte. Befund: **nein** —
das `Blob`-Modell („**ein** fixer Content-Blob") passt schlecht auf das
`DataFrame`-Modell („eine **lebende** pandas-Tabelle, on-demand in **viele** Formate
kodierbar"). Empfohlen wird stattdessen **Komposition** (`DataFrame.as_blob(fmt)`)
plus optional ein **gemeinsamer Integritäts-/Provenienz-Mixin** — `DataFrame` gewinnt
den `Blob`-Mehrwert (Prüfsumme/`verify`/`size`, Provenienz-Metadaten, Content-Zugriff
in einem gewählten Format) **ohne** Basisklassenwechsel und **ohne** Bruch des
etablierten `to_dict`-Layouts.

## 2. Gegenüberstellung der Modelle

| Aspekt            | `Blob`                                   | `DataFrame`                                          |
| ----------------- | ---------------------------------------- | ---------------------------------------------------- |
| Inhalt            | **ein** fixer Blob (`bytes`/`uri`)       | **lebende** pandas-`df` (mutierbar)                  |
| Speicherort       | `self.data['content']` (serialisiert)    | `self._df` (in-memory, nicht in `data`)              |
| Formate           | genau eines (der Blob selbst)            | **viele**: Parquet/Arrow/Feather/CSV/dict/JSON-LD/HDF5/Data Package |
| `to_dict`-Layout  | `data.content = {type,value,filetype}`   | `data.parquet_bytes` (base64) + `data.column_metadata` |
| Identität/Hash    | Hash **des** Blobs                       | Hash **wovon?** (Parquet? CSV? df?) — formatabhängig |
| Zusatz-Metadaten  | `checksum`/`mime_type`/`license`/…       | `column_metadata` (pro Spalte) + Dataset-Metadaten   |

Kernspannung: `Blob` setzt einen **einzigen, festen** Byte-Inhalt voraus; die
`DataFrame` hat **keinen** kanonischen Byte-Inhalt — erst die Wahl des Formats
erzeugt Bytes, und die Tabelle bleibt danach veränderbar.

## 3. Was `DataFrame` von `Blob` gewinnen würde

`sha256`/`md5`/`sha1`, `verify()`/`update_checksum()`, `size`, `exists()`,
`open()`/`write(uri)`, sowie die Provenienz-Felder (`checksum`, `mime_type`,
`license`, `source_uri`, `created`/`modified`, `publisher`) — alles nützlich, aber
**nicht** an eine Vererbung gebunden.

## 4. Optionen

### Option A — Volle Vererbung `DataFrame(Blob)`

Die df-Standardserialisierung (Parquet) als `Blob`-Content ablegen.

* **Pro:** „is-a Blob"; einheitliche Identität/Integrität.
* **Contra (gravierend):**
  * **`to_dict`-Bruch:** `Blob` erwartet `data.content = {type,value,filetype}`;
    `DataFrame.to_dict` nutzt `data.parquet_bytes`/`data.column_metadata`. Eine
    Vereinheitlichung bricht **bestehende `.sjson`/dict-Artefakte** und alle
    Round-Trips (Tests, evtl. gespeicherte Daten).
  * **Lebende vs. fixe Daten:** der `Blob`-Content müsste bei **jeder**
    df-Mutation neu erzeugt/invalidiert werden (Sync-Problem, Cache-Inkohärenz).
  * **„ein Format" vs. „viele":** Parquet als Content bevorzugt ein Format künstlich;
    CSV/Arrow/HDF5/Data Package sind gleichwertig.
  * **Hash-Semantik:** `checksum` eines `DataFrame` ist mehrdeutig (Parquet ist nicht
    deterministisch byte-gleich; CSV/Arrow ergeben andere Hashes).
* **Bewertung:** hohes Risiko, geringer Zusatznutzen → **nicht empfohlen.**

### Option B — Gemeinsamer Integritäts-/Provenienz-Mixin

Den Hash-/`verify`-/Provenienz-Teil aus `Blob` in einen wiederverwendbaren Mixin
ziehen (über einen `content_bytes`-Hook), den **`Blob` und `DataFrame`** nutzen.
`DataFrame.content_bytes` = Standardserialisierung (z. B. Parquet-Bytes).

* **Pro:** `DataFrame` erhält `sha256`/`verify`/`size`/Provenienz **additiv**, ohne
  Basiswechsel und ohne `to_dict`-Bruch.
* **Contra:** kein „is-a Blob"; leichte Refaktorierung von `Blob` nötig.

### Option C — Komposition: `DataFrame.as_blob(fmt="parquet") -> Blob`

Die df bei Bedarf als `Blob` über die gewählte Serialisierung **ausgeben**
(`bytes`-Content). Damit lässt sich eine Tabelle als binäres Asset behandeln
(speichern/übertragen/signieren/hashen) — in **jedem** Format.

* **Pro:** sauber, additiv, **null** Bruchrisiko; respektiert das Multi-Format-Modell
  (Format ist ein Parameter, nicht die Basisklasse); nutzt die schon vorhandenen
  `to_parquet`/`to_arrow`/`to_csv`/… .
* **Contra:** kein „is-a Blob" (aber semantisch korrekt: eine Tabelle **ist** kein
  einzelner Blob).

### Option D — Status quo (getrennt)

`DataFrame` bleibt `Base`. Klarstellung: `Blob` ist die Grundlage für
**single-content/binäre** Daten (Dateien/Bilder/Blobs); `DataFrame` ist ein
eigenständiges **tabellarisches** Modell mit eigener Multi-Format-Serialisierung.

## 5. Empfehlung

**Komposition (Option C) als primärer Weg, optional ergänzt um den Mixin (Option B);
keine Vererbung (Option A).**

1. **`DataFrame.as_blob(fmt="parquet", content_type="bytes") -> Blob`** (klein,
   additiv): erzeugt aus `to_parquet()`/`to_csv()`/`to_arrow-IPC`/… einen `Blob` mit
   passendem `filetype`/`mime_type`. Damit erbt die Tabelle indirekt **alle**
   Blob-Fähigkeiten (Hash/verify/size/write/open/Sidecar) in einem **gewählten**
   Format.
2. *(Optional, später)* Integritäts-/Provenienz-**Mixin** aus `Blob` extrahieren und
   in `DataFrame` einhängen, falls `df.sha256`/`df.verify()` **direkt** (ohne Umweg
   über `as_blob`) gewünscht sind. Eigener PR, rein additiv.

**Begriffliche Klärung der „Grundlage aller Datenformate" (RFC 0003):** `Blob`
liefert den **Content-/Integritäts-/Provenienz-Layer**. Container mit **einem**
Inhalt (`FileReference`, `Image`) **erben** davon; Container mit **lebenden,
mehrformatigen** Daten (`DataFrame`) **komponieren** damit (`as_blob`). „Grundlage"
heißt also *gemeinsamer Layer*, nicht *zwingende Basisklasse*.

## 6. Kompatibilität / Migration

* Option C ist strikt additiv: keine Änderung an `to_dict`/`from_dict`, keine
  Basisklasse, keine bestehenden Artefakte betroffen.
* `as_blob` baut nur auf vorhandenen Serialisierern auf; `pyproject.toml`-`omit`
  unverändert; optionale Backends (pyarrow) wie gehabt geguardet.

## 7. Testplan (für die spätere Umsetzung von Option C)

* `as_blob()` Default (Parquet): `blob.filetype`/`mime_type` korrekt; `blob.content_bytes`
  == `df.to_parquet()`; `Blob`-`sha256`/`size`/`verify` funktionieren.
* `as_blob(fmt="csv")` / `fmt="arrow"`: jeweils Inhalt == entsprechende Serialisierung.
* Round-Trip-Skizze: `DataFrame.from_parquet_bytes(df.as_blob().content_bytes)` ≡ df.
* Unbekanntes `fmt` → `ValueError`.

## 8. Risiken / offene Punkte

* **Determinismus der Prüfsumme:** Parquet ist nicht garantiert byte-stabil
  (Kompression/Metadaten-Reihenfolge). Für reproduzierbare Hashes ggf. CSV (mit
  fixierten Optionen) als „canonical form" anbieten — zu spezifizieren.
* **`as_blob`-Default-Format:** Parquet (kompakt/typisiert) vs. CSV (deterministisch)
  — Default festlegen.
* Falls später doch eine „is-a"-Beziehung gewünscht ist, müsste ein **getrenntes**
  RFC den `to_dict`-Layout-Übergang inkl. Migration behandeln.
