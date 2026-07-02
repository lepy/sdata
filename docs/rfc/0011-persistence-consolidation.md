# RFC 0011 — Persistenz-Konsolidierung (Store, Vault, Group auf `sclass`-Basis)

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Draft                                                                                     |
| Datum       | 2026-07-02                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `sdata/iolib/jsonsqlitestore.py` (deprecaten), `sdata/iolib/json1sqlitestore.py` (opt. zlib), `sdata/iolib/vault.py` (portieren/entfernen), `sdata/sclass/dataframegroup.py` (auf `Metadata`+`sclass.DataFrame` heben), `sdata/iolib/writer.py`/`reader.py` (`write_group`/`read_group`) |
| Betrifft    | `JSONSQLiteStore` (Alt-Zwilling), `JSON1SQLiteStore.compression`, `Vault`/`FileSystemVault`/`Hdf5Vault`, `DataFrameGroup`, `GroupWriter`/`GroupReader` |
| Vorgeschichte | RFC 0001 (Store), RFC 0002 (§ „DataFrameGroup-Serialisierung separat"), RFC 0007 (§11 „DataFrameGroup-Batch vorbereitet"), RFC 0008 (Roadmap, B8–B10) |
| Validierung | geplant: portierte Module aus der Coverage-`omit` heben und messen; Roundtrip-/Batch-Tests |

## 1. Zusammenfassung

Die Persistenzschicht trägt **drei überlappende, halb zusammenpassende** Bausteine:

1. **Zwei SQLite-Stores.** `JSON1SQLiteStore` (neu, aktiv verdrahtet von Writer/
   Reader) und `JSONSQLiteStore` (alt, nur noch in eigenen Tests lebendig) teilen
   **24 gleichnamige Methoden**. Einziges echtes Alleinstellungsmerkmal des Alten:
   **zlib-Kompression** (`jsonsqlitestore.py:157-189`).
2. **Ein halbfertiger `Vault`.** `vault.py` hängt an der deprecated `Data`-Klasse
   (`vault.py:8`), die `Vault`-Basis ist großteils `NotImplementedError`, und
   `FileSystemVault.reindex` ist **doppelt definiert** (`:372` tot, `:384` gewinnt).
3. **Eine abweichende `DataFrameGroup`.** Sie erbt von `Base` (nicht `DataFrame`),
   hält **rohe pandas-Frames** mit **dict-basierter** `{label,unit}`-Spaltenbeschreibung
   (`dataframegroup.py:57-63`) statt des `Metadata`-Modells, und hat **keine**
   Anbindung an Store/Writer/Vault.

Dieses RFC führt sie auf **ein** Konzept auf `sclass`-Basis zusammen: ein
kanonischer Store (`JSON1SQLiteStore`, zlib-Frage explizit entschieden), ein
`DataFrameGroup`, das das `Metadata`-Spaltenmodell und `sclass.DataFrame`-Elemente
nutzt, und eine `write_group`/`read_group`-Semantik über die RFC-0007/0009-
Interfaces. `vault.py` wird auf `sclass` portiert **oder** kontrolliert entfernt.

## 2. Motivation / Kontext

* **Zwilling driftet.** Zwei Stores mit fast identischer Oberfläche bedeuten
  doppelte Wartung und Divergenzrisiko; Bugfixes/Features landen nur in einem.
  Der Alte ist nirgends im Produktivcode importiert (nur `test_jsonsqlitestore*.py`).
* **`Metadata` vs. dict.** `DataFrame` trägt reiche Per-Spalten-`Metadata`
  (unit/label/ontology/dtype, RFC 0006); `DataFrameGroup` kann nur `{label,unit}`.
  Wer eine Gruppe persistiert, **verliert** Ontologie/dtype/Einheitensemantik —
  genau das, was sdata ausmacht.
* **`write_group` fehlt.** RFC 0007 §11 hält fest: die `with writer: for sdf in
  group: writer.write(sdf)`-Schleife ist *vorbereitet*, aber es gibt keine
  Batch-Semantik (ein Parquet-Verzeichnis, **eine** DB-Transaktion, ein Dataset).
  RFC 0002 nennt dasselbe für HDF5.
* **`vault.py` ist eine Altlast.** Es kann nur `Data`-HDF5 lesen/schreiben
  (`to_hdf5`/`from_hdf5`/`metadata_from_hdf5`), nicht das `sclass`-Modell; die
  doppelte `reindex` zeigt, dass es nicht gepflegt wird. Es steht bewusst in der
  Coverage-`omit` — d. h. ungetesteter Code im Distributionspaket.

## 3. Ziele / Nicht-Ziele

**Ziele**

* **Ein** kanonischer Store: `JSON1SQLiteStore`. `JSONSQLiteStore` wird mit
  `DeprecationWarning` versehen und in einem Major entfernt.
* **zlib-Entscheidung explizit treffen** (§5.1): entweder als optionales Feature
  in `JSON1SQLiteStore` **portieren** oder bewusst als Nicht-Ziel dokumentieren
  (der Neue verzichtet laut Docstring „to prioritize speed" bereits absichtlich).
* `DataFrameGroup` auf das **`Metadata`-Spaltenmodell** heben und `sclass.DataFrame`
  als Element halten (statt roher pandas + `{label,unit}`), **abwärtskompatibel**
  über `from_dict`.
* **`write_group`/`read_group`**: Batch-Persistenz einer Gruppe über die
  RFC-0007/0009-Writer/Reader (ein Store, eine Transaktion, ein Ausgabeverzeichnis).
* `vault.py` **portieren oder entfernen** (§5.4) — inkl. Fix der doppelten `reindex`.
* **Coverage-Ehrlichkeit** (RFC 0008): portierte Module aus der `omit`-Liste in die
  Messung heben (`jsonsqlitestore.py` bleibt bis zur Entfernung, aber der Neue
  bleibt 100 %; `dataframegroup.py` ist schon gemessen).

**Nicht-Ziele**

* **Keine** Änderung am `JSON1SQLiteStore`-Schema (generierte `_sdata_*`-Spalten,
  RFC 0001) — nur additive Ergänzungen.
* Kein neues Query-DSL (der `tinydb_json1sqlite.py`-Aufsatz bleibt experimentell).
* Keine Migration der Domänen-Reader (`isomme.py`, `pud.py`) — die hängen an
  `Data` und gehören zur `Data`-Ablösung (RFC 0012, B4).
* Keine hierarchische Nesting-Semantik über die flache Gruppe hinaus (eigenes RFC).

## 4. Ist-Zustand (Beleg)

| Baustein | Befund | Beleg |
|----------|--------|-------|
| Store-Zwilling | 24 gleichnamige Methoden; Alt nur in eigenen Tests | `json1sqlitestore.py` / `jsonsqlitestore.py` |
| zlib | nur im Alten (`compression`-Flag, `_serialize`/`_deserialize`) | `jsonsqlitestore.py:55/157-189` |
| Neu-exklusiv | generierte Spalten + JSON1-Pfadops (`extract`/`set_path`/…) | `json1sqlitestore.py:45/114-127/437-481` |
| Vault an `Data` | `from sdata import Data`; `to_hdf5`/`from_hdf5`/`metadata_from_hdf5` | `vault.py:8/438/447/455` |
| doppelte `reindex` | erste (`:372`) tot, zweite (`:384`) überschreibt | `vault.py:372-398` |
| Group-Modell | erbt `Base`; dict `{label,unit}`; rohe pandas; nur `to_dict`/`from_dict` | `dataframegroup.py:9/57-63/111-141` |
| Group-Anbindung | keine Referenz aus Store/Writer/Reader/Vault | grep `DataFrameGroup` |

## 5. Entwurf

### 5.1 Store: einer bleibt, zlib wird entschieden

`JSON1SQLiteStore` ist der kanonische Store. `JSONSQLiteStore` bekommt beim Import/
Konstruktor ein `DeprecationWarning` („use JSON1SQLiteStore; removal in sdata 2.0")
und bleibt eine Release-Linie als Fallback erhalten.

**zlib — Option A (empfohlen): als optionales Feature portieren.** Ein
`compression: bool = False`-Flag am `JSON1SQLiteStore`-Konstruktor, das den
`payload`-Text transparent zlib-komprimiert. **Bedingung:** die generierten Spalten
(`json_extract(payload, '$._sdata_*')`) brauchen **Text-JSON** — mit Kompression
müsste das `payload` roh (BLOB) und die `_sdata_*`-Werte in **separaten** realen
Spalten gehalten werden (kein `GENERATED ALWAYS AS`). Das ist ein echter
Schema-Zweig; deshalb: `compression=True` **deaktiviert** die JSON1-Pfadoperationen
und dokumentiert das (Kompression *xor* In-DB-JSON-Queries).

**zlib — Option B: Nicht-Ziel.** Der Neue verzichtet laut Docstring bewusst
(`json1sqlitestore.py:29`, „to prioritize speed"); wer komprimieren will, legt
Blobs komprimiert ab (RFC 0003/0004) oder nutzt SQLite-Seitenkompression (VFS).
Dann wird `JSONSQLiteStore` **ersatzlos** deprecated.

> **Empfehlung:** Option B, sofern kein konkreter Kompressionsbedarf dokumentiert
> ist — sie hält den kanonischen Store einfach und die generierten Spalten intakt.
> Option A nur, wenn große Payloads real anfallen; dann als separater `BlobStore`
> statt als Schalter am schnellen Pfad.

### 5.2 `DataFrameGroup` auf `Metadata` + `sclass.DataFrame`

```python
class DataFrameGroup(Base):
    """Geordnete Sammlung benannter sdata-DataFrames (eine flache Ebene)."""

    def add(self, sdf, key=None):
        from sdata.sclass.dataframe import DataFrame
        sdf = DataFrame(df=sdf) if not isinstance(sdf, DataFrame) else sdf
        self._members[key or sdf.sname] = sdf        # sclass.DataFrame, nicht rohes df

    def get(self, key):
        return self._members.get(key)
```

* **Elemente sind `sclass.DataFrame`** — jedes trägt sein volles `Metadata`/
  `column_metadata` (unit/label/ontology/dtype). Ein übergebenes rohes pandas-`df`
  wird gewrappt (wie `ensure_sdata`, RFC 0007).
* **Kein** `{label,unit}`-dict mehr; die Spaltensemantik lebt in den Elementen.
* **Abwärtskompatibel:** `from_dict` erkennt das **alte** Layout
  (`data.dataframes[key] = {df, column_metadata:{label,unit}}`) und hebt es auf das
  neue (Spalten-`Metadata` aus `{label,unit}` erzeugt); ein
  `_sdata_format_version`-Sprung (RFC 0010!) macht das explizit und migrierbar.
* `to_dict` serialisiert jedes Element über dessen eigenes verlustfreies
  `DataFrame.to_dict` (base64-Parquet mit `_sdata`), nicht über eine Sonderform.

### 5.3 `write_group` / `read_group`

Batch-Semantik über die vorhandenen Interfaces, ohne die Einzel-`write`-Verträge
zu brechen:

```python
# sdata/iolib/writer.py
def write_group(writer, group):
    """Alle Mitglieder einer Gruppe in EINE Senke; gibt eine Liste WriteReceipts.

    Für transaktionale Senken (StoreWriter/SqlWriter) in EINER Transaktion.
    """
    receipts = []
    with writer:                                     # ein offener Store/Conn
        for key, sdf in group.items():
            receipts.append(writer.write(sdf))
    return receipts

# sdata/iolib/reader.py
def read_group(reader, keys):
    """Mehrere Mitglieder aus EINER Quelle zu einer DataFrameGroup zusammenführen."""
    group = DataFrameGroup(name="group")
    for key in keys:
        group.add(reader.read(key), key=key)
    return group
```

* **StoreWriter/SqlWriter:** die Schleife läuft in einer Transaktion (der Store
  committet bei `close`), also **alles-oder-nichts** je Gruppe.
* **ParquetWriter:** ein **Verzeichnis** (`run/<sname>.spq` je Mitglied) statt
  Überschreiben derselben URI (F5 aus RFC 0007) — die einzige Stelle, die einen
  echten neuen Modus braucht.
* **GraphWriter:** die Named-Graph-Akkumulation (RFC 0007 §6.3) ist bereits die
  Gruppen-Form — jedes Mitglied ein Named Graph, ein Dataset.

### 5.4 `vault.py` — portieren oder entfernen

Zwei saubere Wege (Entscheidung im Implementierungs-PR, nicht offen lassen):

* **Entfernen (empfohlen):** `vault.py` ist ein `Data`-HDF5-Index, den
  `StoreWriter`/`StoreReader` (RFC 0007/0009) funktional ersetzen — ein
  `JSON1SQLiteStore` **ist** der auffindbare, indizierte Objektspeicher, den der
  Vault sein wollte. `node.py` nutzt `FileSystemVault` nur im `__main__`-Demoblock;
  der wird auf `StoreWriter`/`StoreReader` umgeschrieben. `test_vault.py` entfällt.
* **Portieren:** falls der Dateisystem-Layout-Aspekt (ein Verzeichnis je Objekt)
  gebraucht wird, wird `FileSystemVault` auf `sclass.DataFrame`/`Blob` + den
  fsspec-Pfad (RFC 0004) umgestellt, die doppelte `reindex` auf **eine** Definition
  reduziert und das Modul aus der `omit`-Liste in die Messung genommen.

> **Empfehlung:** Entfernen. Der Vault dupliziert konzeptionell den Store, hängt an
> `Data` und ist ungetestet; sein einziger Eigenwert (Verzeichnis-Layout) lässt
> sich bei Bedarf als dünner `ParquetWriter`-Verzeichnismodus (§5.3) nachrüsten.

## 6. Designentscheidungen / Optionen

* **`JSON1SQLiteStore` als kanonisch**, nicht der Alte: er ist verdrahtet
  (Writer/Reader), hat die generierten Spalten und JSON1-Pfadops; der Alte hat nur
  zlib. Verworfen: beide behalten (Drift), oder den Alten zum Kanon machen
  (bräche Writer/Reader).
* **`DataFrameGroup` bleibt `Base`-Subklasse**, wird **nicht** zu `DataFrame`: eine
  Gruppe *ist keine* Tabelle. Aber ihre **Elemente** werden vollwertige
  `DataFrame`s — das behebt den Semantikverlust, ohne die Ist-a-Beziehung zu
  verbiegen (dieselbe Vorsicht wie RFC 0004 zu Blob/DataFrame).
* **`write_group` als Funktion, nicht als Writer-Methode:** hält das
  `DataFrameWriter`-Protocol (RFC 0007) minimal (`write`/`flush`/`close`); die
  Batch-Schleife ist orthogonal und funktioniert mit **jedem** Writer.
* **Format-Version für die Group-Migration** (RFC 0010): das alte
  `{label,unit}`-Layout wird über eine registrierte Migration gehoben — genau der
  Anwendungsfall, für den RFC 0010 die Treppe gebaut hat.
* **Deprecation statt Sofort-Löschung** des Alt-Stores: ein Release Vorlauf mit
  Warnung, Entfernung im Major (konsistent zur `Data`-Ablösung, RFC 0012).

## 7. Tests / Coverage (geplant)

* **Store:** `JSONSQLiteStore` löst beim Konstruktor ein `DeprecationWarning` aus
  (`pytest.warns`); `JSON1SQLiteStore` unverändert 100 %. Bei Option A zusätzlich:
  `compression=True`-Roundtrip + dokumentierter Fehler bei JSON1-Pfadop mit
  Kompression.
* **Group:** Roundtrip mit **erhaltenen** Einheiten/Ontologie je Element;
  `from_dict` auf einem **alten** `{label,unit}`-Payload migriert verlustarm
  (label/unit erhalten, Rest leer) und setzt die Formatversion.
* **Batch:** `write_group` in einen Store → alle per `read_group` wiederfindbar;
  `SqlWriter`-Transaktionalität (ein Fehler in der Mitte → Rollback der ganzen
  Gruppe); `ParquetWriter`-Verzeichnismodus schreibt N Dateien.
* **Vault:** bei „Entfernen" entfällt `test_vault.py` und der `node.py`-Demoblock
  wird auf Store umgestellt (Rauchtest); bei „Portieren" wandert `vault.py` aus
  `omit` und wird gemessen.

## 8. Kompatibilität / Migration

* **Alt-Store:** `JSONSQLiteStore` bleibt eine Release-Linie mit `DeprecationWarning`
  nutzbar; bestehende DBs des Neuen sind unberührt (kein Schemawechsel bei Option B).
* **Group:** altes `to_dict`-Layout lädt über die registrierte Format-Migration
  (RFC 0010) weiter; neues Schreiben nutzt das `Metadata`-Modell. Die öffentliche
  API (`add_dataframe`/`get_dataframe`) bleibt als Alias erhalten, gibt aber
  gewrappte `DataFrame`s zurück (Doku-Hinweis).
* **Vault:** bei Entfernung ein Breaking Change für direkte
  `sdata.iolib.vault`-Importer — daher Deprecation-Stufe (`ImportError` mit
  Verweis auf `StoreWriter`/`StoreReader`) im Minor, Entfernung im Major.

## 9. Risiken / offene Punkte

* **zlib-Schemazweig (Option A)** ist invasiver als er aussieht (BLOB-Payload vs.
  generierte Spalten) — die Empfehlung (Option B) vermeidet das; die Entscheidung
  gehört in den Implementierungs-PR, nicht in ein „vielleicht".
* **Group-Abwärtskompatibilität** hängt an einer korrekten Format-Migration; ein
  altes Layout ohne `_sdata_format_version` (v1) muss am `{label,unit}`-Shape
  erkannt werden, nicht nur an der Versionsnummer.
* **`ParquetWriter`-Verzeichnismodus** ist der einzige echt neue Writer-Zweig;
  Partitionierung/append (RFC 0007 F5) bleibt bewusst außen vor.
* **`vault.py`-Entfernung** trifft `node.py` und `test_vault.py`; `node.py` ist
  ohnehin `omit`, aber der Demoblock sollte lauffähig bleiben.
* **Reihenfolge zu RFC 0012:** die `Data`-Ablösung (B4) und diese Konsolidierung
  berühren beide `vault.py`/`pud.py`/`isomme.py` — dieses RFC nimmt nur den
  Store/Group/Vault-Teil, die `Data`-abhängigen Domänen-Reader bleiben RFC 0012.
