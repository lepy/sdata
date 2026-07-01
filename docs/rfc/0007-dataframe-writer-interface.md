# RFC 0007 — Writer-Interface für `sclass.DataFrame` (einheitliche Sink-Abstraktion)

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Accepted — implementiert (**v2**, nach adversariellem Review überarbeitet)                |
| Datum       | 2026-07-01                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | **neu:** `sdata/iolib/writer.py`; nutzt `sdata/sclass/dataframe.py`, `sdata/semantic.py`, `sdata/iolib/json1sqlitestore.py` |
| Betrifft    | `DataFrameWriter` (Protocol), `BaseDataFrameWriter` (ABC), `WriteReceipt`, `ParquetWriter`, `StoreWriter`, `SqlWriter`, `GraphWriter`, `ensure_sdata`, `write_with_provenance` |
| Vorgeschichte | Folge von RFC 0002 (HDF5), RFC 0003 (Blob), RFC 0004 (DataFrame/Blob), RFC 0006 (Units) |
| Validierung | `sdata/iolib/writer.py` **100 %**; 19 Tests (`tests/iolib/test_dataframe_writer.py`); Gesamtsuite grün |

> **Umsetzungsstand.** Implementiert und getestet. Ein adversarieller Review des
> v1-Entwurfs deckte zwei **belastbare Fehler** und mehrere Designschwächen auf; v2
> adressiert sie:
>
> | # | v1-Problem (Entwurf) | v2-Antwort (implementiert) |
> |---|----------------------|-----------------------------|
> | F1 | „SQL-Dokumentmodus reused `JSON1SQLiteStore` verlustfrei, Metadaten reisen im Payload" war **falsch**: `Base.to_dict()` nestet `_sdata_*` unter `$.metadata.*.value`, der Store extrahiert aber `$._sdata_*` (top-level) → alle generierten Spalten NULL, Objekt un-auffindbar. | Eigene Klasse **`StoreWriter`** mit **Flatten-Adapter** `store_payload`: `_sdata_*` top-level + volles `to_dict` unter `"sdata"`. Test beweist Auffindbarkeit per `suuid`/`sname`. |
> | F2 | `GraphWriter("run42.ttl")` gab die Turtle nur **zurück**, schrieb aber **nie** die Datei. | Einzeldatei-Modus schreibt jetzt tatsächlich nach `target` (Turtle **oder** JSON-LD). |
> | F3 | Relationales SQL: `to_sql` + separater Meta-Insert **ohne** Transaktionsgrenze (pandas committet `to_sql` intern → verwaiste Datenzeilen möglich). | **`SqlWriter`** atomar: Meta-Insert zuerst (pending), dann `to_sql` (dessen finaler commit beide festschreibt); `try/except → rollback` verwirft die pending Metazeile bei Fehler. |
> | F4 | `sdf.suuid` ist ein `SUUID`-Objekt, als SQL-Bind-Parameter/IRI ungültig. | Überall `str(sdf.suuid)`. |
> | F6 | `write() -> Any` (Pfad/ID/IRI/Str) untergrub die Polymorphie. | Einheitliches **`WriteReceipt`** (`backend`/`sname`/`suuid`/`target`/`detail`) aus **jedem** `write`. |
> | F7 | „SqlWriter mit Dokumentmodus" vermischte Objekt-Persistenz und relationale Tabellen. | Sauber getrennt: **`StoreWriter`** (Objekt) vs. **`SqlWriter`** (relational). |
> | F8 | `for k,v in contract.items(): setattr(self,k,v)` schluckte Tippfehler still. | Explizite `require_metadata`/`require_columns`/`require_units`-Parameter am ABC-Konstruktor. |
> | C1 | Statische Analyse (Codacy/Bandit) meldete den interpolierten Metatabellennamen im `SqlWriter`-SQL als **SQL-Injection (critical)**. | Feste Metatabelle `sdata_dataframe_meta` über **statisches SQL-Literal**; Datentabellenname per Allowlist (`_safe_identifier`) validiert; `_check_contract` unter die Komplexitätsgrenze refaktoriert. |
>
> Bestätigt und übernommen: `as_blob("parquet")` bettet `_sdata` ein (nutzt `to_parquet()`);
> die Wahrheitsquelle bleibt `metadata`/`column_metadata`, nicht `df.attrs`.

## 1. Zusammenfassung

`sclass.DataFrame` besitzt heute **viele** Ein-Format-Serialisierer (`to_parquet`,
`to_csv`, `to_arrow`, `to_feather`, `to_hdf`, `to_datapackage`, `to_jsonld`/`to_turtle`,
`as_blob`, `to_dict`). Was fehlt, ist eine **einheitliche Sink-Abstraktion**: ein
gemeinsamer `write()`-Vertrag, unter dem Backends (Parquet-Datei/Objektspeicher, SQL,
Knowledge Graph) **austauschbar** sind, der **Ressourcen-Lebenszyklus** (offene
DB-Verbindung, RDF-Store, Dateihandle) hält und einen **Metadaten-Vertrag** erzwingt.

Dieses RFC schlägt ein `DataFrameWriter`-**Protocol** plus eine `BaseDataFrameWriter`-**ABC**
(Template-Method mit Metadaten-Prüfung) und drei konkrete Writer vor.

**Kernbefund (Neurahmung).** Die naive Writer-Diskussion dreht sich um pandas'
`df.attrs` als (fragile) Metadatenquelle — `attrs` wird über `groupby`/`concat`/`merge`
meist **nicht** propagiert, ist also schon vor dem Writer oft verloren. sdata hat dieses
Problem **architektonisch bereits gelöst**: die Wahrheitsquelle ist nicht `df.attrs`,
sondern die erstklassigen Felder `DataFrame.metadata` (`Metadata`) und
`DataFrame.column_metadata` (Per-Spalten-`Metadata`, inkl. `unit`/`label`/`ontology`).
`df.attrs["_sdata"]` dient in sdata nur als **Transport der letzten Meile** beim
Serialisieren (`to_dataframe`/`to_parquet`, `dataframe.py:495/542`). Der Writer bekommt
folglich **kein** dünnes `attrs`-Dict, sondern das sdata-`DataFrame`, das seine Semantik
robust **mitträgt**. Für alle drei Backends muss der Writer die Metadaten nicht *retten*,
sondern nur **korrekt platzieren**.

## 2. Motivation / Kontext

* **Polymorphe Ziele.** Ein Aufrufer (Pipeline, `DataFrameGroup`, CLI) soll `writer.write(sdf)`
  aufrufen, ohne zu wissen, *wohin* geschrieben wird. Heute ist jeder Serialisierer eine
  eigene Methode mit eigener Signatur — ein Wechsel Parquet↔SQL↔Graph bedeutet
  Umschreiben des Aufrufers.
* **Lebenszyklus.** Die `to_*`-Methoden sind **Ein-Schuss**-Serialisierer ohne Zustand.
  Eine SQL-Verbindung, ein rdflib-`Dataset` (Named-Graph-Akkumulation über mehrere
  Tabellen) oder ein partitioniertes Ausgabeverzeichnis brauchen **Öffnen → mehrfach
  schreiben → flush/commit → schließen**. Das ist genau die `write`/`flush`/`close`/
  Context-Manager-Form, die den `to_*`-Methoden fehlt.
* **Metadaten-Vertrag an einer Stelle.** „Diese Senke akzeptiert nur Tabellen mit
  `license` **und** Einheiten auf `force`/`stroke`" gehört in **einen** Prüf-Hook, nicht
  verstreut in jeden Aufrufer.
* **Backends behandeln Metadaten grundverschieden** — das ist der eigentliche Knackpunkt:

  | Backend        | natürlicher Ort für Dataset-Metadaten                                             |
  |----------------|-----------------------------------------------------------------------------------|
  | **Parquet**    | nativer Key-Value-Schema-Slot → sdata legt sie schon als `_sdata` ab              |
  | **SQL**        | *kein* Ort für tabellenglobale Metadaten → Dokument-JSON **oder** Sidecar-Tabelle |
  | **Graph**      | der *natürliche* Ort → Metadaten **sind** die Provenienz (QUDT/PROV-O-Tripel)     |

* **Vorhandenes bleibt.** RFC 0001 lieferte `JSON1SQLiteStore` (nimmt `to_dict()`-JSON mit
  `_sdata_*`-Spalten); RFC 0003/0004 den `Blob`/`as_blob`-Pfad (fsspec-`write(uri)`); die
  Semantik-Schicht (`sdata/semantic.py`) erzeugt bereits **QUDT + PROV-O + CSVW + DCAT**
  aus `metadata` und Spalten. Der Writer **verdrahtet** dieses Vorhandene, er ersetzt es
  nicht.

## 3. Ziele / Nicht-Ziele

**Ziele**

* `DataFrameWriter`-Protocol (`write`/`flush`/`close`, Context-Manager) als struktureller
  Vertrag jeder Senke.
* `BaseDataFrameWriter`-ABC: zieht `metadata`/`column_metadata`/`description` **getrennt**
  vom Datenrahmen heraus, prüft einen konfigurierbaren Vertrag, ruft `_write_impl(sdf, meta)`.
* Drei Referenz-Writer: `ParquetWriter` (fsspec-URI), `SqlWriter` (Dokument- **oder**
  relationaler Modus), `GraphWriter` (RDF/JSON-LD, Named-Graph-Akkumulation).
* `ensure_sdata(df)`-Bridge: nimmt eine sdata-`DataFrame` **oder** eine reine pandas-`df`
  (restauriert `df.attrs["_sdata"]` über den vorhandenen `_restore_from_attrs`-Pfad).
* Strikt **additiv**; Optional-Abhängigkeiten (`sdata[sql]`, `sdata[rdf]`, `sdata[parquet]`,
  `sdata[blob]`) über die etablierten Guards.

**Nicht-Ziele (dieses RFC)**

* Kein **Reader**-Gegenstück (die `from_*`-Methoden bleiben; ein `DataFrameReader`-Protocol
  ist ein Folge-RFC).
* Kein Query-/Selektions-API und kein ORM; der Writer **schreibt** nur.
* Keine Ablösung der `to_*`-Methoden — der Writer **komponiert** sie.
* `DataFrameGroup`-Batch-Schreiben ist nur **vorbereitet** (die `write`-Schleife passt),
  nicht ausspezifiziert.

## 4. Der Metadaten-Vertrag

Die entscheidende Designentscheidung (wie im naiven Entwurf, aber in sdata korrekt
verankert): `_write_impl` bekommt `sdf` **und** `meta` **getrennt**. So platziert jedes
Backend die Metadaten dort, wo sie hingehören, statt sie an den pandas-Rahmen gekoppelt zu
lassen, wo sie beim Serialisieren verschwinden.

`meta` wird **nicht** aus `df.attrs` gezogen, sondern aus der Wahrheitsquelle:

```python
meta = {
    "metadata":        sdf.metadata.to_dict(),          # Dataset-Ebene
    "column_metadata": sdf.column_metadata.to_dict(),   # Per-Spalte: unit/label/ontology
    "description":     sdf.description,
}
```

Das ist reicher als ein `dict(df.attrs)`: es trägt **Per-Spalten-Semantik** (Einheiten aus
RFC 0006, Ontologie-Terme), die ein flaches `attrs`-Dict gar nicht ausdrücken kann.

## 5. Entwurf — Protocol + ABC

```python
# sdata/iolib/writer.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable, TYPE_CHECKING
import logging

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from sdata.sclass.dataframe import DataFrame


@dataclass
class WriteReceipt:                          # F6: einheitlicher Rückgabetyp aller Senken
    backend: str; sname: str; suuid: str; target: Any = None
    detail: dict = field(default_factory=dict)


@runtime_checkable
class DataFrameWriter(Protocol):
    """Struktureller Vertrag jeder Senke."""
    def write(self, sdf: "DataFrame") -> WriteReceipt: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...


class BaseDataFrameWriter(ABC):
    """Template-Method: Vertrag prüfen, Metadaten trennen, an das Backend delegieren."""

    def __init__(self, require_metadata=(), require_columns=(), require_units=()):
        self.require_metadata = tuple(require_metadata)   # F8: explizite Parameter,
        self.require_columns  = tuple(require_columns)    # kein setattr-Schlucken von Tippfehlern
        self.require_units    = tuple(require_units)
        self._count = 0

    def write(self, sdf: "DataFrame") -> WriteReceipt:
        sdf = ensure_sdata(sdf)                       # Bridge: plain pandas -> sdata
        self._check_contract(sdf)
        meta = {
            "metadata":        sdf.metadata.to_dict(),
            "column_metadata": sdf.column_metadata.to_dict(),
            "description":     sdf.description,
        }
        receipt = self._write_impl(sdf, meta)         # sdf UND meta getrennt
        self._count += 1
        logger.info("%s wrote %r -> %s", type(self).__name__, sdf.sname, receipt.target)
        return receipt

    def _check_contract(self, sdf: "DataFrame") -> None:
        miss_m = [k for k in self.require_metadata if sdf.metadata.get(k) is None]
        miss_c = [c for c in self.require_columns if c not in sdf.df.columns]
        units  = sdf.column_units                      # {col: unit} (RFC 0006)
        miss_u = [c for c in self.require_units if not units.get(c)]
        if miss_m or miss_c or miss_u:
            raise ValueError(
                f"writer contract violated: metadata={miss_m}, columns={miss_c}, units={miss_u}")

    @abstractmethod
    def _write_impl(self, sdf: "DataFrame", meta: dict[str, Any]) -> WriteReceipt: ...

    def flush(self) -> None: pass
    def close(self) -> None: self.flush()
    def __enter__(self): return self
    def __exit__(self, *exc): self.close()
```

`_check_contract` nutzt den bestätigten `Metadata.get(k) is None`-Zugriff (robust
gegenüber der Nesting-Struktur von `to_dict()`); die Attributnamen (`"license"`, …) sind
gültige Pflichtschlüssel.

## 6. Backends

### 6.1 Parquet — Metadaten reisen **im** Format mit

Parquet ist der saubere Fall: das Format hat einen Metadaten-Slot, und sdata füllt ihn
bereits (`to_parquet` bettet `_sdata` über `df.attrs` ein, Arrow über den Schema-Key
`b"_sdata"`, `dataframe.py:542/694`). Der Writer muss also **keinen** Sidecar bauen — er
schreibt die metadatentragenden Bytes an eine beliebige fsspec-URI (lokal, `s3://`, `gcs://`)
über den `Blob`-Pfad aus RFC 0003/0004:

```python
class ParquetWriter(BaseDataFrameWriter):
    def __init__(self, uri, **contract):           # contract = require_metadata/columns/units
        super().__init__(**contract)
        self.uri = uri

    def _write_impl(self, sdf, meta):
        blob = sdf.as_blob("parquet")              # to_parquet()-Bytes: _sdata eingebettet
        target = blob.write(self.uri)              # fsspec (lokal, s3://, …)
        return WriteReceipt("parquet", sdf.sname, str(sdf.suuid), target,
                            {"bytes": blob.size})
```

Beim Zurücklesen (`DataFrame.from_parquet_bytes`) landet `_sdata` via
`_restore_from_attrs` wieder in `metadata`/`column_metadata` — die Provenienz überlebt den
Roundtrip, was reines `pandas.to_parquet()` nicht leistet.

### 6.2 SQL — zwei **getrennte** Klassen (F7): `StoreWriter` und `SqlWriter`

SQL hat keinen tabellenglobalen Metadaten-Ort. Der v1-Entwurf wollte das mit **einer**
`SqlWriter`-Klasse mit `mode="document"`/`"relational"` lösen — der Review verwarf das:
der Dokumentpfad war (a) **falsch** (F1) und (b) semantisch eine *andere* Sache
(Objekt-Persistenz statt relationaler Tabellen). v2 trennt beides sauber.

**`StoreWriter` — Objekt-Persistenz in einen `JSON1SQLiteStore` (RFC 0001).** Der
Knackpunkt (F1): `Base.to_dict()` liefert `{"metadata": {…}, "data": {…}, …}` — die
`_sdata_*`-Schlüssel liegen **genestet** unter `$.metadata.<key>.value`, der Store
extrahiert aber `json_extract(payload, '$._sdata_*')` (top-level). Ein naives
`store.insert(sdf.to_dict())` ergäbe also **durchweg NULL**-Spalten und ein
**un-auffindbares** Objekt. Lösung: ein **Flatten-Adapter**, der die `_sdata_*` nach oben
zieht und das verlustfreie `to_dict` unter `"sdata"` mitführt:

```python
class StoreWriter(BaseDataFrameWriter):
    def __init__(self, target, **contract):
        super().__init__(**contract)
        from sdata.iolib.json1sqlitestore import JSON1SQLiteStore
        if hasattr(target, "insert"):
            self._store, self._owns = target, False          # übergebener Store
        else:
            self._store, self._owns = JSON1SQLiteStore(target), True

    @staticmethod
    def store_payload(sdf):
        from sdata.iolib.json1sqlitestore import JSON1SQLiteStore
        md = sdf.metadata
        payload = {c: (md.get(c).value if md.get(c) else None)
                   for c in JSON1SQLiteStore.GENERATED_COLUMNS}   # _sdata_* TOP-LEVEL
        payload["_sdata_name"]  = sdf.name
        payload["_sdata_sname"] = sdf.sname
        payload["_sdata_suuid"] = str(sdf.suuid)
        payload["sdata"] = sdf.to_dict()                         # verlustfrei unter "sdata"
        return payload

    def _write_impl(self, sdf, meta):
        rid = self._store.insert(self.store_payload(sdf))
        return WriteReceipt("store", sdf.sname, str(sdf.suuid), rid, {"record_id": rid})

    def close(self):
        self.flush()
        if self._owns: self._store.conn.close()
```

Damit ist das Objekt per `store.get_id_by_key("_sdata_suuid", str(sdf.suuid))` bzw.
`"_sdata_sname"` wieder auffindbar (Test beweist es) und `DataFrame.from_dict(row["sdata"])`
stellt es verlustfrei her.

**`SqlWriter` — flache Daten in eine relationale Tabelle + gemeinsame Metadatentabelle,
atomar (F3/F4).** pandas `to_sql` **committet intern** — der v1-Entwurf (Daten zuerst,
Metadaten danach, ohne Transaktionsgrenze) konnte also verwaiste Datenzeilen ohne
Metadaten hinterlassen. v2 kehrt die Reihenfolge um und macht es atomar. Die Metatabelle
ist **fest** (`sdata_dataframe_meta`) und wird über **statisches SQL-Literal** angelegt/befüllt
(keine Identifier-Interpolation → keine SQL-Injection-Fläche, C1); der Datentabellenname
wird gegen eine Allowlist validiert:

```python
_SQL_META_DDL = ("CREATE TABLE IF NOT EXISTS sdata_dataframe_meta "
                 "(suuid TEXT, sname TEXT, target_table TEXT, sdata TEXT)")
_SQL_META_INSERT = ("INSERT INTO sdata_dataframe_meta(suuid, sname, target_table, sdata) "
                    "VALUES (?, ?, ?, ?)")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

class SqlWriter(BaseDataFrameWriter):
    def __init__(self, conn, table="dataframe", *, if_exists="append", **contract):
        super().__init__(**contract)
        self._conn = conn
        self.table = _safe_identifier(table)         # Allowlist statt Interpolation von Fremd-IDs
        self.meta_table = _SQL_META_TABLE
        self.if_exists = if_exists
        self._conn.execute(_SQL_META_DDL)            # Literal

    def _write_impl(self, sdf, meta):
        suuid = str(sdf.suuid)                       # F4: SUUID -> str für Bind-Parameter
        try:
            self._conn.execute(                      # Metazeile ZUERST (pending), Literal + Params
                _SQL_META_INSERT,
                (suuid, sdf.sname, self.table, json.dumps(sdf.to_dict(), default=str)))
            sdf.df.to_sql(self.table, self._conn,    # dessen finaler commit schreibt BEIDE fest
                          if_exists=self.if_exists, index=False)
        except Exception:
            self._conn.rollback()                    # Fehler -> pending Metazeile verwerfen
            raise
        return WriteReceipt("sql", sdf.sname, suuid, self.table,
                            {"meta_table": self.meta_table})

    def flush(self):
        self._conn.commit()
```

Die zugehörige Datentabelle einer Metazeile steht in der Spalte `target_table`
(`… WHERE target_table = ?`); die feste Metatabelle ersetzt den v1-`<table>__sdata`-Namen.

**Provenienz-Schlüssel `str(sdf.suuid)`** statt eines SHA-256-Hashs der Metadaten: der
`suuid` ist per Konstruktion eindeutig (der Hash kollidiert bei identischen Metadaten) und
ohnehin vorhanden (RFC 0001, `_sdata_suuid`). Wer Provenienz **pro Zeile** braucht, schreibt
`suuid` zusätzlich als Datenspalte.

### 6.3 Knowledge Graph — Metadaten **sind** die Provenienz

Hier ist `attrs` kein Fremdkörper, sondern das Modell. sdata erzeugt aus `metadata` und den
Spalten bereits **QUDT-Quantities, PROV-O-Provenienz, CSVW-Spalten und DCAT/schema.org**
(`sdata/semantic.py`, `vocab.py`-`PREFIXES`) — die im naiven Entwurf mühsam von Hand
gebaute rdflib-PROV-Konstruktion ist damit **überflüssig**. Der Writer akkumuliert die
Tabellen als **Named Graphs** in einem rdflib-`Dataset` (Graph-IRI aus `suuid`) oder
schreibt eine einzelne Datei:

```python
class GraphWriter(BaseDataFrameWriter):
    def __init__(self, target=None, *, fmt="turtle", named_graphs=False, **contract):
        self.target, self.fmt = target, fmt
        self._dataset = None
        if named_graphs:
            from sdata.semantic import _rdflib          # Optional-Guard (rdf-Extra)
            if _rdflib is None:
                raise ImportError("named_graphs verlangt: pip install sdata[rdf]")
            self._dataset = _rdflib.Dataset()
        for k, v in contract.items(): setattr(self, k, v)

    def _write_impl(self, sdf, meta):
        import json
        from sdata.semantic import _rdflib
        doc = sdf.to_jsonld()                            # QUDT+PROV-O+CSVW, Spalten inklusive
        if self._dataset is not None:
            iri = _rdflib.URIRef(f"urn:sdata:{sdf.suuid}")
            self._dataset.graph(iri).parse(data=json.dumps(doc), format="json-ld")
            return iri
        return sdf.to_turtle()                           # bzw. in self.target-Datei schreiben

    def close(self):
        if self._dataset is not None and self.target:
            self._dataset.serialize(destination=self.target, format="nquads")
```

Bei Parquet/SQL *platziert* man die Metadaten; beim Graph *sind* sie der Inhalt. Die
Per-Spalten-Einheiten (RFC 0006) erscheinen automatisch als `qudt:unit` an den
`csvw:column`-Knoten.

### 6.4 `df.attrs` als Brücke der letzten Meile

Für eine **reine** pandas-`df`, die (noch) kein sdata-Objekt ist, restauriert `ensure_sdata`
die Metadaten aus `df.attrs["_sdata"]` — genau dem Slot, den sdatas `to_dataframe`/
`to_parquet` beschreiben:

```python
def ensure_sdata(obj):
    from sdata.sclass.dataframe import DataFrame
    import pandas as pd
    if isinstance(obj, DataFrame):
        return obj
    if isinstance(obj, pd.DataFrame):
        sdf = DataFrame(df=obj)
        sdf._restore_from_attrs(obj.attrs.get("_sdata"))   # vorhandener Restore-Pfad
        return sdf
    raise TypeError(f"erwartet DataFrame oder pandas.DataFrame, nicht {type(obj)!r}")
```

Und Provenienz kann beim Schreiben **explizit injiziert** werden, statt auf
`attrs`-Propagierung zu hoffen — für zertifizierbare Workflows (RecyPredict-Kontext) der
robuste Weg:

```python
def write_with_provenance(writer, obj, provenance: dict) -> WriteReceipt:
    sdf = ensure_sdata(obj)
    for key, value in provenance.items():
        sdf.metadata.add(key, value)     # in die Wahrheitsquelle, nicht in df.attrs
    return writer.write(sdf)
```

`df.attrs` bleibt damit **Transportmechanismus der letzten Meile**, nicht Wahrheitsquelle
über die Pipeline — dieselbe Schlussfolgerung wie im naiven Entwurf, in sdata aber schon
strukturell eingelöst.

## 7. Nutzung

```python
import sqlite3
from sdata.iolib.writer import ParquetWriter, StoreWriter, SqlWriter, GraphWriter

# austauschbare Senken — der Aufrufer bleibt gleich, jeder write() liefert ein WriteReceipt
for writer in [ParquetWriter("s3://bucket/run42.spq"),
               StoreWriter("runs.db"),                       # Objekt-Persistenz (JSON1-Store)
               SqlWriter(sqlite3.connect("runs.db")),        # relationale Tabelle + Sidecar
               GraphWriter("run42.ttl")]:                    # RDF/Turtle-Datei
    with writer:
        rcpt = writer.write(sdf)                             # rcpt.suuid / rcpt.target / rcpt.backend

# Vertrag erzwingen: nur Tabellen mit Lizenz UND Einheit auf 'force'
ParquetWriter("out.spq", require_metadata=("license",),
              require_units=("force",)).write(sdf)           # -> ValueError, falls verletzt

# mehrere Tabellen in EINEN Store (auffindbar per suuid/sname)
with StoreWriter("runs.db") as w:
    for sdf in group:
        w.write(sdf)                                         # close() schließt den Store
```

## 8. Designentscheidungen / Optionen

* **Protocol *und* ABC.** Das `Protocol` (`runtime_checkable`) ist der **strukturelle**
  Vertrag (auch Fremdklassen können ihn erfüllen); die ABC liefert die
  **Template-Method** mit Vertrags-Prüfung, damit jeder Writer die Metadaten identisch
  trennt. Verworfen: nur ABC (schließt Duck-Typing aus) bzw. nur Protocol (dupliziert die
  Prüf-Logik in jedem Backend).
* **`write(sdf)` statt `write(df, meta)`.** Das sdata-`DataFrame` trägt seine Semantik
  bereits robust; ein separates `meta`-Argument würde die Wahrheitsquelle spalten. Die
  Trennung passiert **im** Writer (§4), nicht in der Signatur.
* **`StoreWriter` vs. `SqlWriter` getrennt (F7).** Objekt-Persistenz (`JSON1SQLiteStore`,
  RFC 0001, per `suuid`/`sname` auffindbar via Flatten-Adapter) und relationale Tabellen
  (flache Daten + Sidecar) sind verschiedene Dinge — eine Klasse mit `mode=` würde sie
  vermischen und war zudem im Dokumentpfad schlicht falsch (F1).
* **Einheitliches `WriteReceipt` (F6).** Jeder `write` gibt denselben Typ zurück
  (`backend`/`sname`/`suuid`/`target`/`detail`), sonst wäre „Senke austauschen ohne den
  Aufrufer zu ändern" nur halb wahr.
* **`str(suuid)` als Provenienz-Schlüssel** statt Metadaten-Hash (§6.2) — eindeutig statt
  kollisionsanfällig, und ohnehin vorhanden (F4: `SUUID` muss für Bind-Parameter/IRIs
  stringifiziert werden).
* **Graph nutzt die Semantik-Schicht**, statt PROV-O von Hand zu bauen — konsistent zu
  `to_jsonld`/`to_turtle`, QUDT-Einheiten inklusive.
* **Modul in `iolib/`.** Writer sind I/O; die Stores liegen dort. `DataFrame` wird nur
  unter `TYPE_CHECKING`/lazy importiert, um Zyklen zu vermeiden.
* **Warum nicht einfach die `to_*`-Methoden lassen?** Sie bleiben — der Writer ergänzt,
  was sie strukturell nicht können: **einen** polymorphen Vertrag, **Lebenszyklus**
  (flush/commit/close über mehrere Schreibvorgänge) und **einen** Ort für den
  Metadaten-Vertrag.

## 9. Tests / Coverage (umgesetzt)

`sdata/iolib/writer.py` **100 %** Line-Coverage; **19** Tests in
`tests/iolib/test_dataframe_writer.py`; die Gesamtsuite bleibt grün. Abgedeckt:

* **`ensure_sdata`**: sdata-`DataFrame` → identisch; pandas-`df` mit/ohne `df.attrs["_sdata"]`
  → Metadaten restauriert bzw. leer; Fremdtyp → `TypeError`.
* **Vertrag**: `require_metadata`/`require_columns`/`require_units` je erfüllt/verletzt
  (`ValueError` mit den fehlenden Schlüsseln); `BaseDataFrameWriter()` abstrakt → `TypeError`;
  Protocol-`isinstance` (strukturell).
* **ParquetWriter**: Roundtrip über lokale URI (`from_parquet_bytes`) erhält
  `metadata`/`column_metadata`/`description` **und** Spalten-Einheiten (RFC 0006); nimmt auch
  eine reine pandas-`df`.
* **StoreWriter** (F1-Beweis): `store.get(rid)["_sdata_sname"]/["_sdata_suuid"]` top-level
  gesetzt, `from_dict(row["sdata"])` ≡ `sdf`, und `get_id_by_key("_sdata_suuid"/"_sdata_sname", …)`
  **findet** den Record; Pfad-Ziel wird bei `close` geschlossen und über eine **neue**
  Verbindung wieder gelesen (Persistenz).
* **SqlWriter**: relationaler Roundtrip (`read_sql` ≡ `df`), Metatabelle `sdata_dataframe_meta`
  (`target_table='runs'`) unter `str(suuid)`/`sname`; **Atomarität (F3)**: bei `to_sql`-Fehler
  mit bereits pending Metazeile wird diese durch `rollback` verworfen (keine Waise);
  Interop über `engine.raw_connection()`; unsicherer Tabellenname → `ValueError` (Allowlist).
* **GraphWriter** (F2): `fmt="json-ld"` schreibt die Datei **tatsächlich** (parsebar);
  `fmt="turtle"` ohne Ziel liefert die Turtle im `WriteReceipt.detail`; `named_graphs=True`
  ohne `rdflib` wirft die geführte `ImportError`.
* **`write_with_provenance`**: injiziert in `sdf.metadata` (nicht `df.attrs`), überlebt den
  Parquet-Roundtrip.

Die `rdflib`-only-Zweige (Named-Graph-Akkumulation/`serialize`) sind `# pragma: no cover`
(analog zu den optionalen Backends in RFC 0002); `writer.py` bleibt **gemessen** (nicht in
`omit`) und in der kanonischen CI (`.[did,parquet,blob]`) bei 100 %.

## 10. Kompatibilität / Migration

* Strikt **additiv**: neues Modul `sdata/iolib/writer.py`, keine Signatur-/Verhaltens­
  änderung an `DataFrame` oder den Stores. `to_dict`/`from_dict`, alle `to_*`/`from_*`,
  `as_blob`, `JSON1SQLiteStore` bleiben unverändert.
* `StoreWriter` und `SqlWriter` laufen auf einer **DBAPI/PEP-249-Verbindung** (stdlib
  `sqlite3`, kein neuer Dependency). `SqlWriter` nutzt qmark-Parameter (`?`) und
  `conn.execute/commit/rollback` — eine **SQLAlchemy-Engine direkt** funktioniert damit
  **nicht**; wohl aber deren DBAPI-Verbindung via `engine.raw_connection()` (`sdata[sql]`,
  durch einen gegateten Interop-Test belegt). `ParquetWriter`/`GraphWriter` nutzen die
  vorhandenen `sdata[parquet]`/`sdata[blob]`-Pfade; Named-Graph-Akkumulation braucht
  `sdata[rdf]`.
* Keine neue Laufzeit-Kernabhängigkeit; Guard-Idiome (`_require_*` bzw. `try/except
  ImportError → None`) unverändert übernommen.

## 11. Risiken / offene Punkte

*Im Review geklärt (nicht mehr offen):* `Metadata.add/get` existieren; `as_blob("parquet")`
bettet `_sdata` ein (nutzt `to_parquet()`); die `to_dict()`↔Store-Shape-Diskrepanz ist über
`StoreWriter.store_payload` behoben; SQL-Atomarität über die Meta-first-Ordnung + `rollback`.

Verbleibend:

* **Relationaler `SqlWriter` & Typabbildung.** `df.to_sql` verliert Einheiten/Ontologie
  (nur die Sidecar-Tabelle hält sie); `if_exists="append"` deckt **Schema-Drift** zwischen
  Tabellen nicht ab. Für semantiktreue Persistenz ist `StoreWriter` verlustfrei.
* **`ParquetWriter` = eine Datei pro `write` (F5).** Mehrere `write` auf **dieselbe** URI
  überschreiben; ein append-/partitionierter Modus (`run/part-*.spq`) ist bewusst nicht
  Teil dieses RFC. `flush`/`close` sind für Parquet No-ops — der Lebenszyklus trägt nur bei
  `Store`/`Sql`/`Graph`.
* **Named-Graph-Persistenz.** N-Quads-Ausgabe an `close` hängt an `rdflib`; ohne Backend
  nur Einzeldatei-Turtle/JSON-LD (`# pragma: no cover`).
* **Reader-Symmetrie.** Ein `DataFrameReader`-Protocol (Round-Trip pro Backend) ist der
  natürliche Folge-RFC.
* **`DataFrameGroup`-Batch.** Die `with writer: for sdf in group: writer.write(sdf)`-Schleife
  ist vorbereitet; eine dedizierte `write_group`-Semantik (ein Parquet-Verzeichnis, eine
  DB-Transaktion, ein Dataset) separat spezifizieren.
