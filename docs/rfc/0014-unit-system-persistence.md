# RFC 0014 — Persistenz des Ziel-Einheitensystems

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Accepted — implementiert                                                                  |
| Datum       | 2026-07-02                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `sdata/sclass/dataframe.py` (`unit_system`), `sdata/semantic.py` (JSON-LD), `sdata/units.py` (`UnitSystem.__eq__`) |
| Betrifft    | `DataFrame.unit_system` über dict/Parquet/HDF5/JSON-LD                                    |
| Vorgeschichte | RFC 0006 (Einheitensysteme); RFC 0008 Open-points-Backlog; RFC 0010 (Format-Versionierung) |
| Validierung | verifiziert: Round-Trip-Tests (dict/Parquet/HDF5), JSON-LD-Emit, Clear/Convert; `make ci` grün (100 %) |

## 1. Zusammenfassung

`DataFrame.unit_system` (RFC 0006) hält das **Ziel-Einheitensystem** einer Tabelle
(z. B. `["kN", "mm", "ms"]`), in das `convert()` ohne Argument rechnet. Bislang war
dieses Feld **transient** — es lebte in einem Instanz-Attribut `self._unit_system`
und überlebte keine Serialisierung (Parquet/dict/JSON-LD). Ein aus Parquet
geladener DataFrame „vergaß" also sein Zielsystem.

Dieses RFC persistiert `unit_system` als **reserviertes Metadaten-Feld**
`_sdata_unit_system` (die Basis-Einheiten-Liste). Da alle Serialisierungspfade
`metadata` mitschreiben und beim Laden wiederherstellen, reist das Einheitensystem
**automatisch** durch dict, Parquet, HDF5 und JSON-LD mit — ohne dass ein einzelner
Serialisierungspfad angefasst werden muss.

## 2. Motivation

* **Verlust bei Persistenz.** `sdf.unit_system = ["kN", "mm", "ms"]`; nach
  `to_parquet`/`from_parquet` war das Zielsystem `None`. Wer die Umrechnung später
  reproduzieren wollte, musste das System erneut von Hand setzen.
* **Konsistenz mit RFC 0006.** Das Zielsystem gehört zur semantischen Beschreibung
  der Tabelle, genauso wie Einheiten/Ontologie der Spalten — es sollte mit den Daten
  reisen.
* **Versionierbarkeit.** Als Metadaten-Feld unterliegt es der Format-Versionierung
  aus RFC 0010 (`_sdata_format_version`) und kann bei künftigen Formatänderungen
  migriert werden.

## 3. Entwurf

### 3.1 Reserviertes Feld statt Instanz-Attribut

`UnitSystem` ist vollständig durch seine **Basis-Einheiten-Liste** (`self.units`)
bestimmt; `UnitSystem(units)` rekonstruiert alles (Dimensions-Algebra). Die
persistierbare Form ist damit genau diese Liste.

`unit_system` wird von `self._unit_system` (transient) auf ein reserviertes
Metadaten-Feld umgestellt:

```python
SDATA_UNIT_SYSTEM = "_sdata_unit_system"

@property
def unit_system(self):
    attr = self.metadata.get(self.SDATA_UNIT_SYSTEM)
    if attr is None or not attr.value:
        return None
    return UnitSystem(list(attr.value))          # aus der Basis-Einheiten-Liste

@unit_system.setter
def unit_system(self, value):
    if value is None:
        self.metadata.pop(self.SDATA_UNIT_SYSTEM)  # falls vorhanden
        return
    system = value if isinstance(value, UnitSystem) else UnitSystem(value)
    self.metadata.set_attr(self.SDATA_UNIT_SYSTEM, list(system.units), dtype="list", ...)
```

Damit ist `metadata` die **Single Source of Truth**. `convert()` und die
nicht-mutierende Kopie (`_converted_copy`) lesen/schreiben über die Property; die
`metadata.copy()`-Kopie trägt das Feld ohne Sonderbehandlung mit.

### 3.2 Automatische Persistenz über alle Pfade

Weil das Feld in `metadata` liegt, greift es überall, wo Metadaten reisen — **ohne
Änderung** an `to_dict`/`from_dict`, `to_parquet`/`from_parquet`,
`to_hdf`/`from_hdf` oder `_restore_from_attrs`:

* `metadata.to_dict()` serialisiert **alle** Attribute (reserviert + User) →
  dict/Parquet/HDF5 tragen `_sdata_unit_system` automatisch.
* Beim Laden stellt jeder Pfad `metadata` wieder her → der Getter liest das Feld.

### 3.3 JSON-LD

Reservierte `_sdata_*`-Felder sind aus der User-Attribut-Schleife ausgenommen und
werden separat gemappt (`semantic.py`). Ein Eintrag im Mapping genügt:

```python
_RESERVED_TERMS = { ..., "_sdata_unit_system": "sdata:unitSystem" }
```

Das gibt sowohl den **Emit** (`doc["sdata:unitSystem"] = ["kN", "mm", "ms"]`) als
auch den **Rück-Parse** (`from_jsonld` → `_sdata_unit_system`) gratis.

### 3.4 `UnitSystem.__eq__`

Für Round-Trip-Vergleiche (und allgemein) erhält `UnitSystem` ein `__eq__`/`__hash__`
auf Basis der Einheiten-Liste — zwei Systeme mit gleicher Basis sind gleich.

## 4. Designentscheidungen

* **Metadaten-Feld statt separatem Deskriptor-Schlüssel.** Die Alternative — einen
  eigenen `unit_system`-Schlüssel in jeden Deskriptor (`to_dict`/`to_parquet`/`to_hdf`
  …) und jeden Restore-Pfad einzeln einzubauen — wäre invasiver und JSON-LD-blind.
  Das reservierte Feld nutzt die vorhandene Metadaten-Maschinerie und ist damit
  minimal-invasiv und pfad-vollständig.
* **Basis-Einheiten-Liste als Form.** Kein Serialisieren des gelösten Dimensions-
  Zustands — die Liste rekonstruiert ihn deterministisch; das ist kompakt,
  menschenlesbar und robust gegen interne Änderungen an `UnitSystem`.
* **`dtype="list"`.** Einheiten-Symbole sind Strings → `list` (list of strings),
  verlustfreier JSON-Roundtrip wie die übrigen dtypes.
* **Präzedenz.** Analog zu `_sdata_format_version` (RFC 0010): ein optionales,
  reserviertes `_sdata_*`-Feld, das über `metadata` mitreist.

## 5. Kompatibilität

* **Additiv.** Alt-Dateien ohne `_sdata_unit_system` laden mit `unit_system == None`
  (Getter-None-Zweig) — kein Bruch.
* **Öffentliche API unverändert:** `sdf.unit_system` (get/set), `unit_system=`-
  Konstruktor-Keyword und `convert()` verhalten sich wie zuvor, jetzt persistent.
* Das Feld erscheint in `metadata.df`/`sdata_attributes` wie andere reservierte
  `_sdata_*`-Attribute; es ist **kein** User-Attribut.

## 6. Tests / Validierung

`tests/test_unit_system_persistence.py`: Set/Get (Liste **und** `UnitSystem`),
Round-Trip über dict/Parquet/HDF5 (`importorskip("h5py")`), JSON-LD-Emit, Clear
(Feld entfernt), `convert()` ohne Argument nutzt das persistierte System,
`convert()` setzt es auf dem Ergebnis, `UnitSystem`-Gleichheit/Hash. `make ci` grün,
Line-Coverage 100 %.
