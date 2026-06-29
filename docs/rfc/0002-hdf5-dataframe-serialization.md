# RFC 0002 — HDF5-Serialisierung für `sclass.DataFrame`

| Feld        | Wert                                                         |
|-------------|--------------------------------------------------------------|
| Status      | Proposed                                                     |
| Datum       | 2026-06-29                                                  |
| Autor       | lepy <lepy@tuta.io>                                          |
| Komponente  | `sdata/sclass/dataframe.py` (+ Extra `sdata[hdf]`)          |
| Betrifft    | neue Methoden `DataFrame.to_hdf` / `from_hdf`               |
| Validierung | Designvorschlag — noch nicht implementiert                  |

## 1. Zusammenfassung

`DataFrame` serialisiert heute nach Parquet, Arrow/Feather, CSV, dict/JSON,
JSON-LD und Data Package — aber **nicht** nach **HDF5**, obwohl HDF5 in
wissenschaftlichen Workflows der De-facto-Standard für große, hierarchische,
partiell lesbare Tabellen ist und sdata das Extra `sdata[hdf]` (PyTables) bereits
deklariert.

Dieses RFC schlägt **`to_hdf` / `from_hdf`** vor, die das pandas-`DataFrame` als
HDF5-Dataset schreiben und die qualifizierende sdata-Metadaten als
**Node-Attribut** (`_sdata`-JSON-Blob) ablegen — konsistent zum vorhandenen
`_sdata`-Carrier von Parquet/Arrow. Optional-Abhängigkeit, strikt additiv,
rückwärtskompatibel.

## 2. Kontext

* **Bedarf.** HDF5 bietet gegenüber Parquet/Feather: partielle/chunked Reads sehr
  großer Tabellen, mehrere Datasets pro Datei (Hierarchie), append-/queryfähige
  Tabellen (`format="table"`) und etablierte Tool-Unterstützung (h5py, HDFView,
  MATLAB, …). Für sdata als „offenes Format für Open Science" ist das eine Lücke.
* **Vorhandenes.** `setup.py` deklariert `'hdf': ['tables']` (PyTables). sdata nutzt
  `pd.HDFStore` bereits in `sdata/iolib/hdf.py` (`FlatHDFDataStore`) und
  `sdata/iolib/vault.py`. Beide sind in `pyproject.toml` aus der Coverage genommen
  (im CI nicht installiert).
* **Vorlage.** Die **deprecated** `Data`-Klasse besitzt bereits
  `to_hdf5`/`from_hdf5` (`sdata/deprecated/data.py`), die über
  `pd.HDFStore` schreiben und Metadaten in `store.get_storer(key).attrs` ablegen.
  Dieses Muster ist die natürliche Vorlage für `DataFrame`.
* **Lücke.** `sclass.DataFrame` (der moderne Ersatz für `Data`) hat **kein**
  HDF5-I/O.

## 3. Ziele / Nicht-Ziele

**Ziele**

* `DataFrame.to_hdf(path, key=…, sidecar=…)` und `DataFrame.from_hdf(path, key=…)`.
* Verlustfreier Round-Trip von Daten **und** `metadata`/`column_metadata`/
  `description` — gleicher `_sdata`-Carrier wie Parquet/Arrow.
* Optional-Abhängigkeit `sdata[hdf]`; klare `ImportError`-Meldung ohne Backend.
* Mehrere DataFrames pro Datei über `key` (Vorbereitung für `DataFrameGroup`).

**Nicht-Ziele (dieses RFC)**

* Keine native Per-Spalten-HDF5-Attributierung (offener Punkt, Abschnitt 9).
* Keine Migration/Anbindung des bestehenden `vault.py`/`FlatHDFDataStore`.
* Kein Queryable-Store-API (`where=`-Selektion); nur Voll-Objekt-Round-Trip.

## 4. Vorgeschlagene API

```python
def to_hdf(self, path=None, filename=None, key=None, sidecar=False, **kwargs):
    """Serialize the df to HDF5 (PyTables), embedding sdata metadata as a node attr.

    :param key: HDF5 node/key (default: ``self.sname``).
    :param kwargs: forwarded to ``pandas.DataFrame.to_hdf`` (z. B. ``format``,
        ``complevel``, ``complib``).
    :return: file path; needs ``pip install sdata[hdf]``.
    """

@classmethod
def from_hdf(cls, filepath, key=None):
    """Load a DataFrame from an HDF5 file written by :meth:`to_hdf`."""
```

* Datei-Konvention: `<sname>.h5` (analog `<sname>.spq`/`.feather`/`.zip`).
* `key` default = `self.sname`; explizit setzbar für mehrere Datasets/Datei.
* `sidecar=True` schreibt zusätzlich `<sname>.meta.jsonld` daneben (wie Parquet/CSV).
* Anders als die Bytes-Rückgabe bei Parquet/Feather erzwingt HDF5/PyTables einen
  **Dateipfad** (kein In-Memory-Bytes-Pfad) → `to_hdf` gibt stets den Pfad zurück.

## 5. Design

### 5.1 Backend & Metadaten-Carrier

`pd.HDFStore` (PyTables) — konsistent mit vorhandenem sdata-HDF-Code, **kein** neuer
Dependency (PyTables ist bereits das `[hdf]`-Extra). Die sdata-Metadaten werden als
**Node-Attribut** abgelegt:

```python
with pd.HDFStore(filepath, mode="w", **store_kwargs) as store:
    store.put(key, self.df, format=fmt)
    store.get_storer(key).attrs._sdata = json.dumps({
        "metadata": self.metadata.to_dict(),
        "column_metadata": self.column_metadata.to_dict(),
        "description": self.description,
    })
```

Lesen spiegelt das:

```python
with pd.HDFStore(filepath, mode="r") as store:
    df = store.get(key)
    raw = getattr(store.get_storer(key).attrs, "_sdata", None)
tt = cls(); tt.df = df
tt._restore_from_attrs(json.loads(raw) if raw else None)
```

`_restore_from_attrs` (vorhanden) wird wiederverwendet → identische Restore-Logik
wie Parquet/Arrow. Der JSON-String als Attribut ist portabel und vermeidet
Pickle-Sicherheits-/Versionsthemen.

### 5.2 Format, Kompression, Guard

* **`format`**: Default `"fixed"` (schnell, Voll-Read; passt zur Voll-Objekt-
  Semantik). `format="table"` (queryable/appendable) via `**kwargs` möglich.
* **Kompression**: `complevel`/`complib` durchreichen; Default z. B.
  `complib="blosc:zstd", complevel=5`, sofern verfügbar.
* **Guard**: Helfer `_require_hdf()` analog `_require_parquet` — `import tables`
  → bei Fehlen `ImportError` mit Hinweis `pip install sdata[hdf]`.

### 5.3 Schlüssel-Hygiene

`key` muss ein gültiger HDF5-/PyTables-Pfad sein. `self.sname` ist S3-safe
(alphanumerisch + `_`), damit auch als HDF5-Node gültig; führende Ziffern ggf. mit
`/` -Prefix oder `"k_"`-Prefix absichern (in der Impl. zu prüfen).

## 6. Lösungsoptionen

### Option A — `pd.HDFStore` + Node-Attribut (empfohlen)

* **Pro:** konsistent mit vorhandenem sdata-HDF-Code und der `Data`-Vorlage; kein
  neuer Dependency; `_restore_from_attrs` wiederverwendbar; mehrere Keys/Datei.
* **Contra:** Metadaten liegen in einem PyTables-spezifischen Attribut (für fremde
  HDF5-Tools weniger offensichtlich als ein eigenes Dataset).

### Option B — `h5py` direkt

Volle Kontrolle über Attribute/Gruppen/Kompression, native Per-Spalten-Attribute
einfacher. **Contra:** neuer Dependency (`h5py`), Divergenz zum bestehenden
`pd.HDFStore`-Stil, df↔HDF-Mapping selbst zu bauen. Nicht empfohlen.

### Option C — Metadaten als Sibling-Dataset/Gruppe

Statt Node-Attribut die `_sdata`-JSON als eigenes Dataset (`/<key>/_sdata`)
ablegen → für fremde HDF5-Tools sichtbarer. **Contra:** mehr Eigenlogik; als
Variante von A später nachrüstbar.

## 7. Rückwärtskompatibilität

* Strikt **additiv**: neue Methoden, keine Signatur-/Verhaltensänderung bestehender
  Pfade. `pyproject.toml`-`omit` unverändert (DataFrame bleibt gemessen).
* Optional-Dependency: ohne `sdata[hdf]` bleibt alles unverändert; nur `to_hdf`/
  `from_hdf` werfen die geführte `ImportError`.
* Kein Konflikt mit `iolib/hdf.py`/`vault.py` (eigene, getrennte Zwecke).

## 8. Testplan / Coverage

* Round-Trip Datei: `to_hdf(path)` → `from_hdf` → Spalten + `metadata`/
  `column_metadata`/`description` erhalten.
* `key`-Varianten: Default (`sname`) und expliziter Key; **zwei** DataFrames in
  **einer** Datei unter verschiedenen Keys.
* `format="table"` zusätzlich zu `fixed`; `sidecar=True` schreibt `.meta.jsonld`.
* Fehlerpfade: fehlende Datei → `FileNotFoundError`; fehlendes Backend → `ImportError`
  (über injiziertes Fake/`importorskip("tables")`, nur die `try/except ImportError`-
  Zeile `# pragma: no cover`).
* **Coverage-Konsequenz:** PyTables muss in der lokalen CI installiert sein
  (`ci/local-ci.sh` um `[hdf]` ergänzen) **oder** die HDF-Methoden in `omit`
  aufnehmen. Empfehlung: `[hdf]` in die CI-Installation aufnehmen, damit die
  Methoden gemessen 100 % bleiben (PyTables zieht jedoch HDF5-Systembibliotheken;
  Build-Zeit/-Größe der CI-venv steigt — abzuwägen).

## 9. Risiken / offene Punkte

* **CI-Abhängigkeit.** PyTables/HDF5 in der lokalen venv erhöht Setup-Zeit; Trade-off
  zwischen „HDF-Methoden 100 % gemessen" vs. „in `omit`, nur `importorskip`-Tests".
  Vor Umsetzung entscheiden.
* **Native Per-Spalten-Attribute.** Wie bei Arrow (`field.metadata`) wäre eine
  native Per-Spalten-HDF5-Attributierung wünschenswert; mit `format="table"` über
  Spalten-Attribute denkbar, mit `fixed` nicht trivial → eigener Folge-RFC.
* **In-Memory-Bytes.** HDF5 hat keinen sauberen Bytes-Pfad wie Parquet; bewusst nur
  Datei-API (Abschnitt 4).
* **`DataFrameGroup`.** Mehrere Keys/Datei laden zu einer Group-Serialisierung ein
  (ein HDF5 = eine Group) — separat zu spezifizieren.
* **Schlüssel-Hygiene** (5.3) in der Implementierung verifizieren.
