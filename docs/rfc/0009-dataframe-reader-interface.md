# RFC 0009 — Reader-Interface für `sclass.DataFrame` (symmetrische Source-Abstraktion)

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Accepted — implementiert (RFC 0008 Paket B, gemergt)                                                                                     |
| Datum       | 2026-07-02                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | **neu:** `sdata/iolib/reader.py`; nutzt `sdata/iolib/writer.py`, `sdata/iolib/json1sqlitestore.py`, `sdata/sclass/dataframe.py` |
| Betrifft    | `DataFrameReader` (Protocol), `BaseDataFrameReader` (ABC), `ParquetReader`, `StoreReader`, `SqlReader`, gemeinsame `check_contract`-Funktion |
| Vorgeschichte | RFC 0007 (§11: „Ein `DataFrameReader`-Protocol … ist der natürliche Folge-RFC"); RFC 0001 (Store), RFC 0004 (Blob), RFC 0008 (Roadmap, B4) |
| Validierung | verifiziert: Roundtrip-Tests je Writer/Reader-Paar, 100 % Line-Coverage für `reader.py` |

## 1. Zusammenfassung

RFC 0007 machte Daten-**Senken** austauschbar: `writer.write(sdf)` funktioniert
identisch für Parquet, Objektstore, SQL und Graph. **Lesend** existiert diese
Polymorphie nicht — der Aufrufer muss das Backend kennen und die passende
`from_*`-Classmethod wählen (`from_parquet`, `from_dict(row["sdata"])`,
`read_sql` + Meta-Join, …). Damit ist „Backend austauschen ohne den Aufrufer zu
ändern" nur halb eingelöst.

Dieses RFC schlägt das Gegenstück vor: ein `DataFrameReader`-**Protocol**
(`read`/`close`, Context-Manager), eine `BaseDataFrameReader`-**ABC**
(Template-Method mit **Eingangs**-Metadaten-Vertrag) und drei Referenz-Reader:
`ParquetReader` (fsspec-URI), `StoreReader` (`JSON1SQLiteStore`, Selektor
`suuid`/`sname`/Record-ID, Iteration), `SqlReader` (Rekonstruktion aus der
`sdata_dataframe_meta`-Sidecar-Tabelle). Für jedes Writer/Reader-Paar wird ein
**Roundtrip-Gesetz** festgeschrieben und getestet.

## 2. Motivation / Kontext

* **Symmetrie.** Eine Pipeline ist Lesen → Verarbeiten → Schreiben. RFC 0007
  abstrahiert nur die letzte Stufe; die erste bleibt backend-spezifisch.
  `reader.read()` / `writer.write()` als Paar macht beide Enden austauschbar.
* **Eingangsvertrag.** Der Writer prüft `require_metadata`/`require_columns`/
  `require_units` beim Schreiben. Dieselbe Prüfung gehört an den **Eingang**
  einer Pipeline: „verarbeite nur Tabellen mit `license` und Einheit auf
  `force`" — heute muss das jeder Aufrufer selbst prüfen.
* **Lebenszyklus.** Ein Store/eine DB-Verbindung wird für **mehrere** Lesevorgänge
  geöffnet (Selektor-Zugriff, Iteration) und muss geschlossen werden — dieselbe
  `close`/Context-Manager-Form wie beim Writer.
* **Die Bausteine existieren bereits** und müssen nur verdrahtet werden:
  `DataFrame.from_parquet_bytes` (`dataframe.py:573`), `Blob`/fsspec-Lesen
  (RFC 0004), `JSON1SQLiteStore.get_id_by_key`/`get`/`fetch_all`
  (`json1sqlitestore.py:274/302/306`), der verlustfreie `to_dict`-Payload unter
  `"sdata"` (RFC 0007, `StoreWriter.store_payload`) und die
  `sdata_dataframe_meta`-Tabelle des `SqlWriter` (Spalten
  `suuid/sname/target_table/sdata`).

## 3. Ziele / Nicht-Ziele

**Ziele**

* `DataFrameReader`-Protocol (`read(selector=None)`/`close`, Context-Manager).
* `BaseDataFrameReader`-ABC: delegiert an `_read_impl(selector)`, prüft danach
  den konfigurierbaren Metadaten-Vertrag (Eingangsvalidierung), gibt das
  sdata-`DataFrame` zurück.
* **Gemeinsame Vertragsprüfung:** die Logik aus
  `BaseDataFrameWriter._check_contract` wird als Modul-Funktion
  `check_contract(sdf, require_metadata, require_columns, require_units)`
  extrahiert und von Writer **und** Reader genutzt (kein Verhaltensunterschied,
  reine Entflechtung).
* Drei Referenz-Reader: `ParquetReader`, `StoreReader`, `SqlReader`.
* **Roundtrip-Gesetze** (§6) als Tests je Writer/Reader-Paar.
* Strikt **additiv**; Optional-Guards wie gehabt (`sdata[parquet]`, `sdata[blob]`,
  `sdata[sql]`).

**Nicht-Ziele**

* **Kein `GraphReader`.** Der `GraphWriter` schreibt Metadaten/Provenienz
  (QUDT/PROV-O/CSVW), nicht die Datenzeilen — aus dem Graphen ist kein
  vollständiges `DataFrame` rekonstruierbar. `semantic.from_jsonld` (Metadata
  aus JSON-LD) existiert bereits für die Metadaten-Richtung.
* Kein Query-DSL / keine Selektion über Metadaten-Prädikate (der Store hat
  `find_by`; ein Query-Interface wäre ein eigenes RFC).
* Kein Streaming-/Chunked-Read großer Tabellen (Befund B9, separat).
* Kein `DataFrameGroup`-Batch-Lesen (gehört zu RFC 0011, Persistenz-Konsolidierung).

## 4. Entwurf — Protocol + ABC

```python
# sdata/iolib/reader.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Iterator, Protocol, runtime_checkable, TYPE_CHECKING
import logging

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from sdata.sclass.dataframe import DataFrame


@runtime_checkable
class DataFrameReader(Protocol):
    """Struktureller Vertrag jeder Quelle."""
    def read(self, selector: Any = None) -> "DataFrame": ...
    def close(self) -> None: ...


class BaseDataFrameReader(ABC):
    """Template-Method: vom Backend lesen, dann den Eingangsvertrag prüfen."""

    def __init__(self, require_metadata=(), require_columns=(), require_units=()):
        self.require_metadata = tuple(require_metadata)
        self.require_columns = tuple(require_columns)
        self.require_units = tuple(require_units)
        self._count = 0

    def read(self, selector: Any = None) -> "DataFrame":
        sdf = self._read_impl(selector)
        check_contract(sdf, self.require_metadata,
                       self.require_columns, self.require_units)  # aus writer.py extrahiert
        self._count += 1
        logger.info("%s read %r", type(self).__name__, sdf.sname)
        return sdf

    @abstractmethod
    def _read_impl(self, selector: Any) -> "DataFrame": ...

    def close(self) -> None: pass
    def __enter__(self): return self
    def __exit__(self, *exc): self.close()
```

`read()` gibt das **`DataFrame` selbst** zurück — kein `ReadReceipt`-Pendant.
Begründung: beim Schreiben braucht es das Receipt, weil `write` sonst nichts
Einheitliches zurückgäbe; beim Lesen **ist** das Objekt das Ergebnis und trägt
Identität (`suuid`/`sname`) und Provenienz bereits in seinen Metadaten.

## 5. Backends

### 5.1 `ParquetReader` — eine URI, ein Objekt

```python
class ParquetReader(BaseDataFrameReader):
    def __init__(self, uri: str, **contract):
        super().__init__(**contract)
        self.uri = uri

    def _read_impl(self, selector):
        if selector is not None:
            raise ValueError("ParquetReader liest genau eine URI; selector nicht unterstützt")
        from sdata.sclass.dataframe import DataFrame
        import fsspec                              # sdata[blob]-Guard wie im Writer
        with fsspec.open(self.uri, "rb") as fh:
            return DataFrame.from_parquet_bytes(fh.read())
```

Die Metadaten reisen **im** Format (`_sdata`-Schema-Key, RFC 0002/0007 §6.1);
`from_parquet_bytes` restauriert `metadata`/`column_metadata`/`description`.

### 5.2 `StoreReader` — Selektor-Zugriff und Iteration

Gegenstück zu `StoreWriter` (RFC 0007 §6.2). Der Flatten-Adapter legte
`_sdata_suuid`/`_sdata_sname` **top-level** (auffindbar) und das verlustfreie
`to_dict` unter `"sdata"` ab — der Reader invertiert genau das:

```python
class StoreReader(BaseDataFrameReader):
    def __init__(self, target, **contract):
        super().__init__(**contract)
        from sdata.iolib.json1sqlitestore import JSON1SQLiteStore
        if hasattr(target, "get_id_by_key"):
            self._store, self._owns = target, False       # übergebener Store
        else:
            self._store, self._owns = JSON1SQLiteStore(target), True

    def _read_impl(self, selector):
        from sdata.sclass.dataframe import DataFrame
        row = self._resolve(selector)                     # int-ID | suuid | sname
        if row is None or "sdata" not in row:
            raise KeyError(f"kein DataFrame-Record für {selector!r}")
        return DataFrame.from_dict(row["sdata"])

    def _resolve(self, selector):
        if isinstance(selector, int):
            return self._store.get(selector)
        sel = str(selector)                               # SUUID-Objekte -> str (RFC 0007 F4)
        rid = (self._store.get_id_by_key("_sdata_suuid", sel)
               or self._store.get_id_by_key("_sdata_sname", sel))
        return self._store.get(rid) if rid is not None else None

    def iter(self) -> Iterator["DataFrame"]:
        """Alle DataFrame-Records des Stores (Records ohne "sdata"-Payload werden übersprungen)."""
        from sdata.sclass.dataframe import DataFrame
        for row in self._store.fetch_all():
            if isinstance(row, dict) and "sdata" in row:
                yield DataFrame.from_dict(row["sdata"])

    def close(self):
        if self._owns:
            self._store.conn.close()
```

Selektor-Auflösung ist **dokumentiert deterministisch**: `int` → Record-ID,
sonst erst `_sdata_suuid`, dann `_sdata_sname` (der suuid ist per Konstruktion
eindeutig; snames können bei `from_name`-Konstruktion kollidieren).

### 5.3 `SqlReader` — Rekonstruktion aus der Meta-Tabelle

Der `SqlWriter` (RFC 0007 §6.2) schreibt pro `write` eine Zeile in die feste
Tabelle `sdata_dataframe_meta` (`suuid`, `sname`, `target_table`, `sdata` =
verlustfreies `to_dict`-JSON) **und** die flachen Daten per `to_sql`. Der
Reader nutzt die Metazeile als Wahrheitsquelle:

```python
_SQL_META_SELECT = ("SELECT sdata FROM sdata_dataframe_meta "
                    "WHERE suuid = ? OR sname = ? ORDER BY rowid DESC LIMIT 1")

class SqlReader(BaseDataFrameReader):
    def __init__(self, conn, *, fresh: bool = False, **contract):
        super().__init__(**contract)
        self._conn = conn
        self.fresh = fresh

    def _read_impl(self, selector):
        import json as _json
        from sdata.sclass.dataframe import DataFrame
        sel = str(selector)
        row = self._conn.execute(_SQL_META_SELECT, (sel, sel)).fetchone()
        if row is None:
            raise KeyError(f"kein Eintrag in sdata_dataframe_meta für {selector!r}")
        payload = _json.loads(row[0])
        sdf = DataFrame.from_dict(payload["sdata"] if "sdata" in payload else payload)
        if self.fresh:                                    # aktueller Tabellenstand statt Snapshot
            import pandas as pd
            table = _safe_identifier(payload_target_table)   # Allowlist wie im Writer
            sdf.df = pd.read_sql(f"SELECT * FROM {table}", self._conn)
        return sdf
```

* **`fresh=False` (Default):** Daten + Metadaten aus dem `sdata`-JSON — der
  verlustfreie **Snapshot zum Schreibzeitpunkt** (Einheiten/Ontologie inklusive,
  die `to_sql` selbst verliert).
* **`fresh=True`:** Metadaten aus dem Snapshot, Datenzeilen per `read_sql` aus
  `target_table` — der **aktuelle** Tabellenstand. Bei `if_exists="append"`
  enthält die Tabelle dann ggf. Zeilen **mehrerer** Schreibvorgänge; das ist
  gewollt und dokumentiert (Provenienz pro Zeile: `suuid`-Datenspalte, RFC 0007
  §6.2). Der Tabellenname läuft durch dieselbe `_safe_identifier`-Allowlist wie
  im Writer.

## 6. Roundtrip-Gesetze (testbar)

| Writer → Reader | Gesetz |
|---|---|
| `ParquetWriter(uri)` → `ParquetReader(uri)` | `metadata`, `column_metadata` (inkl. Einheiten, RFC 0006), `description`, Daten ≡ |
| `StoreWriter(db)` → `StoreReader(db).read(str(sdf.suuid))` | `from_dict(to_dict)`-Identität: **vollständig** ≡ |
| `StoreWriter(db)` → `StoreReader(db).read(sdf.sname)` | wie oben (Selektor-Fallback) |
| `SqlWriter(conn)` → `SqlReader(conn).read(suuid)` | Snapshot ≡ (Metadaten **und** Daten zum Schreibzeitpunkt) |
| `SqlWriter(conn)` → `SqlReader(conn, fresh=True)` | Metadaten ≡, Daten = aktueller Stand von `target_table` |

Der Identitätsbegriff folgt den bestehenden Writer-Tests
(`tests/iolib/test_dataframe_writer.py`): Vergleich über `to_dict()` bzw.
`pandas.testing.assert_frame_equal` + Metadaten-Schlüsselvergleich.

## 7. Nutzung

```python
from sdata.iolib.reader import ParquetReader, StoreReader, SqlReader
from sdata.iolib.writer import StoreWriter

# Pipeline: austauschbare Quelle -> Verarbeitung -> austauschbare Senke
with StoreReader("runs.db") as r, StoreWriter("curated.db") as w:
    sdf = r.read("DataFrame__specimen_01__…")     # suuid oder sname
    sdf.df = sdf.df[sdf.df.force > 0]
    w.write(sdf)

# Eingangsvertrag: nur lizenzierte Tabellen mit Einheit auf 'force' verarbeiten
r = ParquetReader("s3://bucket/run42.spq",
                  require_metadata=("license",), require_units=("force",))
sdf = r.read()                                     # -> ValueError bei Verletzung

# Iteration über einen Store
with StoreReader("runs.db") as r:
    for sdf in r.iter():
        print(sdf.sname, sdf.column_units)
```

## 8. Designentscheidungen / Optionen

* **`read()` → `DataFrame`, kein `ReadReceipt`** (§4). Verworfen: ein Receipt-
  Wrapper — er würde jeden Aufrufer zum Auspacken zwingen, ohne Information zu
  tragen, die das Objekt nicht selbst hat.
* **`selector` als ein polymorphes Argument** statt `read_by_suuid`/
  `read_by_sname`/`read_by_id`-Methodenfamilie. Die Auflösungsreihenfolge ist
  dokumentiert (int → ID, str → suuid, dann sname); der häufigste Aufruf
  `read(receipt.suuid)` bleibt einzeilig. Verworfen: Keyword-only-Varianten
  (`read(suuid=…)`) — mehr API-Fläche ohne Mehrwert.
* **Vertragsprüfung nach dem Lesen, nicht vorher.** Der Vertrag braucht das
  vollständige Objekt (Spalten, Einheiten); ein Backend-spezifischer
  „Pre-Check" würde die Prüfl ogik wieder verteilen.
* **`check_contract` als gemeinsame Funktion** in `writer.py` (Import im
  Reader), nicht dupliziert und nicht in ein neues Modul gezogen — die
  Writer-Signatur (`require_*`-Tupel) bleibt unverändert, `BaseDataFrameWriter.
  _check_contract` delegiert (kein Verhaltens-/API-Bruch).
* **Kein `flush()` im Reader-Protocol.** Lesen hat nichts zu flushen; das
  Protocol bleibt minimal (`read`/`close`). Der Context-Manager kommt aus der
  ABC wie beim Writer.
* **`SqlReader.fresh`** statt zweier Klassen: anders als beim Writer (F7:
  Objekt-Persistenz vs. relationale Tabellen sind *verschiedene Senken*) ist es
  hier **eine** Quelle mit zwei wohldefinierten Sichten (Snapshot vs. aktuell);
  ein Bool-Schalter mit dokumentierter Semantik genügt.

## 9. Tests / Coverage (geplant)

`tests/iolib/test_dataframe_reader.py`, Ziel 100 % Line-Coverage für
`reader.py` in der kanonischen CI (`.[did,parquet,blob,sql]`):

* Roundtrip-Gesetze aus §6 für alle fünf Paare (inkl. Einheiten aus RFC 0006).
* Protocol-`isinstance` (strukturell), ABC abstrakt → `TypeError`.
* Eingangsvertrag: erfüllt/verletzt je `require_*` (`ValueError` nennt die
  fehlenden Schlüssel — gleiche Fehlerform wie der Writer).
* Selektoren: `int`-ID, `SUUID`-Objekt, suuid-str, sname-str, unbekannt →
  `KeyError`; `ParquetReader.read(selector)` → `ValueError`.
* `StoreReader.iter()` überspringt Fremd-Records (ohne `"sdata"`-Payload).
* Lebenszyklus: Pfad-Ziel wird bei `close()` geschlossen; übergebener Store
  bleibt offen (`_owns=False`).
* `SqlReader`: unbekannter Selektor → `KeyError`; `fresh=True` nach zweitem
  `append`-Write liest den kumulierten Tabellenstand.

## 10. Kompatibilität / Migration

* Strikt **additiv**: neues Modul `sdata/iolib/reader.py`; `writer.py` erhält
  nur die extrahierte `check_contract`-Funktion (Delegation, kein API-Bruch).
* Alle `from_*`-Classmethods bleiben unverändert — der Reader **komponiert** sie.
* Abhängigkeits-Guards unverändert: `ParquetReader` braucht `sdata[parquet]` +
  `sdata[blob]` (fsspec), `SqlReader` eine DBAPI/PEP-249-Verbindung (stdlib
  `sqlite3` genügt; SQLAlchemy via `engine.raw_connection()`), `StoreReader`
  nur stdlib.

## 11. Risiken / offene Punkte

* **`fresh=True` und Schema-Drift:** bei `append` mit abweichendem Schema
  spiegelt `read_sql` den Drift wider — bewusst; wer Snapshot-Treue braucht,
  nutzt den Default.
* **Store-Iteration und Fremdobjekte:** `iter()` filtert über das
  `"sdata"`-Payload-Feld; speichert jemand fremde Dokumente mit einem
  `"sdata"`-Schlüssel, werden sie fälschlich als DataFrame interpretiert
  (Fehler erst bei `from_dict`). Ein `_sdata_class`-Filter wäre strenger —
  Entscheidung in der Implementierung.
* **Kein Multi-Objekt-Parquet:** eine URI = ein Objekt (wie der Writer, F5);
  partitionierte Layouts (`run/part-*.spq`) bleiben dem Streaming-/Group-Thema
  (B3/B9) vorbehalten.
* **Selektor-Mehrdeutigkeit:** sname ist nicht garantiert eindeutig; die
  dokumentierte Reihenfolge (suuid zuerst, `LIMIT 1`/jüngster Eintrag) macht
  das Verhalten deterministisch, aber nicht kollisionsfrei.
