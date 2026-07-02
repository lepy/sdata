# RFC 0010 — Format-Versionierung und Migrationspfad

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Accepted — implementiert (RFC 0008 Paket B, gemergt)                                                                                     |
| Datum       | 2026-07-02                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `sdata/base.py` (`Base`, `to_dict`/`from_dict`), `sdata/sclass/dataframe.py` (`_restore_from_attrs`), neu: `sdata/format.py` (Konstanten + Migrations-Registry) |
| Betrifft    | `_sdata_format_version` (neues reserviertes Feld), `read_format_version`, `migrate_payload`, `FormatVersionWarning`, `IncompatibleFormatError` |
| Vorgeschichte | RFC 0008 (Roadmap, B5); Vorbild: `PRAGMA user_version` + `migrate()` in `json1sqlitestore.py:391–406` |
| Validierung | verifiziert: Toleranz-/Migrations-Tests; 100 % Line-Coverage für `format.py` |

## 1. Zusammenfassung

sdata versteht sich als **offenes Datenformat** („data format versions" ist ein
erklärtes README-Designziel), besitzt aber **keine** Formatversion. Das Feld
`_sdata_version` (`base.py:98`) trägt die **Paket**-Version (`__version__`,
z. B. `"1.3.0"`) — sie ändert sich bei jedem Release, auch wenn das serialisierte
Format identisch bleibt, und kein `from_*` wertet sie aus. Ein 2020 geschriebenes
Objekt lädt heute nur, *weil sich die Shape zufällig nicht geändert hat*; bricht sie
einmal, gibt es weder Erkennung noch Migrationspfad.

Dieses RFC führt ein **separates, monoton steigendes Integer-Feld**
`_sdata_format_version` ein (unabhängig von der Paketversion), definiert
**Toleranzregeln** (lesbar / migrierbar / inkompatibel) und einen **einen**
Migrations-Choke-Point, durch den bereits **alle** `from_*`-Pfade laufen
(`Metadata.from_dict` bzw. `_restore_from_attrs`). Vorbild ist der schon
vorhandene `PRAGMA user_version` + `migrate()`-Mechanismus des Stores — nur auf
Objekt- statt DB-Schema-Ebene.

## 2. Motivation / Kontext

* **Paketversion ≠ Formatversion.** `_sdata_version = "1.3.0"` koppelt Format und
  Release. Sie taugt nicht als Kompatibilitätssignal: sie steigt bei reinen
  Bugfixes und sagt nichts über die serialisierte Struktur.
* **Kein Lese-Check.** `Base.from_dict` (`base.py`) und die
  `_restore_from_attrs`-basierten Pfade (`dataframe.py:557`) übernehmen die
  Metadaten **ungeprüft**. Ein zukünftiger Shape-Bruch (umbenanntes Feld, neue
  Nesting-Ebene) führt zu stillen `None`-Werten oder `KeyError` tief im Code —
  statt einer klaren „dieses Objekt ist Format vN, ich kann bis vM".
* **Ein natürlicher Choke-Point existiert bereits.** Jeder Reader
  (`from_dict`/`from_parquet(_bytes)`/`from_arrow`/`from_feather`/
  `from_datapackage`/`from_hdf`, und der neue Reader aus RFC 0009) rekonstruiert
  die Metadaten über **denselben** Pfad. Die Versionsprüfung + Migration gehört
  genau dorthin — sie muss nicht in jeden Reader dupliziert werden.
* **Der Mechanismus ist im Repo erprobt.** `JSON1SQLiteStore` nutzt
  `PRAGMA user_version` + eine `migrate()`-Treppe (`json1sqlitestore.py:391–406`)
  für **DB-Schema**-Migrationen. Dieses RFC überträgt das Muster auf das
  **Objekt-JSON**.

## 3. Ziele / Nicht-Ziele

**Ziele**

* Neues reserviertes Feld `_sdata_format_version` (Integer, aktuell **1**),
  getrennt von `_sdata_version` (Paketversion, bleibt informativ erhalten).
* Beim Schreiben (`Base.__init__`/`to_dict`) automatisch gesetzt.
* Beim Lesen an **einer** Stelle geprüft: Toleranzregeln + optionale Migration.
* Migrations-Registry `{from_version: callable(payload) -> payload}` als Treppe
  (v1→v2→v3), analog zur `migrate()`-Kette des Stores.
* Rückwärtskompatibel: Objekte **ohne** das Feld gelten als **v1** (der heutige
  Stand), laden ohne Warnung.
* Strikt **additiv**; keine Signaturänderung an `from_*`.

**Nicht-Ziele**

* **Keine** rückwirkende Migration bestehender Dateien auf der Platte (nur beim
  Lesen im Speicher; ein `sdata migrate <file>`-CLI ist ein Folge-RFC).
* Kein SemVer-Schema für das Format (ein simpler Integer-Zähler genügt; die
  Paketversion bleibt für Menschen).
* Keine Formatänderung *in diesem RFC* — es etabliert nur die Infrastruktur;
  die erste echte v2-Migration entsteht, wenn eine Shape-Änderung nötig wird.
* Keine Versionierung der Einheiten-/Ontologie-Vokabulare (orthogonal).

## 4. Das Feld

```python
# sdata/format.py
SDATA_FORMAT_VERSION_KEY = "_sdata_format_version"
CURRENT_FORMAT_VERSION = 1        # steigt nur bei einem Shape-Bruch des Objekt-JSON
```

`Base` bekommt das Feld als reservierten Schlüssel neben `_sdata_version`:

```python
class Base:
    SDATA_FORMAT_VERSION = "_sdata_format_version"
    SDATA_ATTRIBUTES = [
        SDATA_VERSION, SDATA_FORMAT_VERSION, SDATA_NAME, SDATA_CLASS, SDATA_CTIME,
        SDATA_PARENT_SNAME, SDATA_PROJECT_SNAME, SDATA_TOPOLOGY_CLASS,
    ]

    def __init__(self, **kwargs):
        ...
        self.metadata.add(self.SDATA_VERSION, __version__, dtype="str",
                          description="sdata package version", required=True)
        self.metadata.add(self.SDATA_FORMAT_VERSION, CURRENT_FORMAT_VERSION,
                          dtype="int", description="sdata serialization format version",
                          required=True)                        # NEU
```

`_sdata_version` bleibt (informativ: „mit welchem Release geschrieben"),
`_sdata_format_version` ist das **maschinelle Kompatibilitätssignal**.

## 5. Toleranzregeln

Beim Lesen wird die Formatversion des Payloads (`read`) gegen
`CURRENT_FORMAT_VERSION` (`self`) gestellt:

| Fall | Bedingung | Verhalten |
|------|-----------|-----------|
| **fehlt** | kein `_sdata_format_version` im Payload | als **v1** behandeln, still lesen (Alt-Objekte vor diesem RFC) |
| **gleich** | `read == current` | normal lesen |
| **älter** | `read < current` | **migrieren**: Treppe `read → … → current` anwenden; `logger.info` je Stufe |
| **älter, nicht migrierbar** | Stufe in der Registry fehlt | `IncompatibleFormatError` (klar: „keine Migration v{read}→v{read+1}") |
| **neuer** | `read > current` | `FormatVersionWarning` **und** best-effort lesen (forward-compatible, solange die Shape trägt); per `strict=True` stattdessen `IncompatibleFormatError` |

Der „neuer"-Fall ist der wichtige: eine alte sdata-Installation, die ein neueres
Objekt liest, **warnt** statt still Falsches zu tun — und liest, so weit die
Struktur reicht. Das ist die bewusste Wahl „laut scheitern/warnen" aus RFC 0008
(Fehler-Politik, C4).

## 6. Der eine Choke-Point

Alle `from_*` rekonstruieren die Metadaten über `Metadata.from_dict` (direkt oder
via `_restore_from_attrs`). Die Prüfung/Migration wird **dort** eingehängt — nicht
in jeden Reader:

```python
# sdata/format.py
def read_format_version(payload: dict) -> int:
    """Formatversion aus einem Objekt- oder attrs-Payload (fehlt -> 1)."""
    meta = payload.get("metadata", payload)          # to_dict-Shape oder flach
    node = meta.get(SDATA_FORMAT_VERSION_KEY)
    if isinstance(node, dict):                        # to_dict nestet {"value": …}
        node = node.get("value")
    try:
        return int(node) if node is not None else 1
    except (TypeError, ValueError):
        return 1

def ensure_compatible(payload: dict, *, current=CURRENT_FORMAT_VERSION,
                      strict=False) -> dict:
    """Prüfe/migriere ein Payload auf die aktuelle Formatversion (vor from_dict)."""
    v = read_format_version(payload)
    if v == current:
        return payload
    if v > current:
        msg = f"object format v{v} is newer than supported v{current}"
        if strict:
            raise IncompatibleFormatError(msg)
        warnings.warn(msg, FormatVersionWarning)
        return payload
    while v < current:                                # Migrations-Treppe
        step = _MIGRATIONS.get(v)
        if step is None:
            raise IncompatibleFormatError(f"no migration v{v} -> v{v+1}")
        payload = step(payload)
        logger.info("migrated sdata payload v%d -> v%d", v, v + 1)
        v += 1
    return payload
```

Einbindung an genau einer Stelle (`Base.from_dict`), von der alle Subklassen und
`_restore_from_attrs` erben bzw. sie mitnutzen:

```python
@classmethod
def from_dict(cls, d, *, strict=False):
    d = ensure_compatible(d, strict=strict)          # NEU — vor der Rekonstruktion
    metadata = Metadata.from_dict(d.get("metadata", {}))
    ...
```

`_restore_from_attrs` (`dataframe.py:557`) ruft dieselbe `ensure_compatible` auf
dem `attrs["_sdata"]`-Dict auf, bevor es Metadaten übernimmt — damit sind auch die
Parquet/Arrow/Feather-Pfade abgedeckt, ohne dass jeder einzeln prüft.

## 7. Migrations-Registry

```python
# sdata/format.py — leer bis zum ersten echten Shape-Bruch
_MIGRATIONS: dict[int, "Callable[[dict], dict]"] = {}

def register_migration(from_version):
    def deco(fn):
        _MIGRATIONS[from_version] = fn
        return fn
    return deco

# Beispiel für eine spätere v1->v2 (illustrativ, NICHT Teil dieses RFC):
# @register_migration(1)
# def _v1_to_v2(payload):
#     payload["metadata"]["_sdata_format_version"]["value"] = 2
#     ...  # die konkrete Shape-Umformung
#     return payload
```

Die Treppe ist bewusst **einstufig komponierbar** (v1→v2, v2→v3, …), damit ein
sehr altes Objekt in mehreren dokumentierten Schritten auf aktuell gehoben wird —
identisch zur `migrate()`-Kette des Stores.

## 8. Designentscheidungen / Optionen

* **Integer-Zähler statt SemVer.** Das Format braucht nur „kann ich das lesen?" —
  ein monotoner Integer beantwortet das eindeutig; menschliche Semantik trägt
  weiterhin `_sdata_version` (Paketrelease). Verworfen: `"2.0"`-Strings (laden zu
  Vergleichslogik und Scheindifferenzierung ein).
* **Feld getrennt von `_sdata_version`.** Beide koexistieren: Release-Info bleibt,
  Kompatibilität wird maschinell. Verworfen: `_sdata_version` umzudeuten — bräche
  jedes bestehende Objekt (das dort `"1.3.0"` trägt) und vermischte zwei Zwecke.
* **Fehlend = v1.** Alle heute existierenden Objekte tragen das Feld nicht; sie
  als v1 zu behandeln macht das RFC **rückwärtskompatibel ohne Datei-Migration**.
* **Ein Choke-Point in `from_dict`.** Da alle Reader dorthin (bzw. nach
  `_restore_from_attrs`) führen, ist das die einzige Stelle, die prüfen muss —
  kein Reader-für-Reader-Nachrüsten (dieselbe Ökonomie wie `check_contract` in
  RFC 0009).
* **„Neuer" warnt, statt zu brechen (Default).** Vorwärtskompatibilität ist für
  ein offenes Format wertvoller als strikte Ablehnung; wer Strenge braucht,
  bekommt `strict=True` (konsistent zum lenient/strict-Muster in `dtypes`/
  `metadata`, RFC 0008 C4).
* **`dtype="int"` für das Feld.** Nutzt die bestehende dtype-Registry (RFC-fremde
  Sonderbehandlung vermeiden); `read_format_version` toleriert dennoch String/Fehlen.

## 9. Tests / Coverage (geplant)

`tests/test_format_versioning.py`, Ziel 100 % für `sdata/format.py`:

* **Feld gesetzt:** neues Objekt trägt `_sdata_format_version == CURRENT` (int),
  `to_dict`/`from_dict`-Roundtrip erhält es; `_sdata_version` (Paket) bleibt
  daneben bestehen.
* **Fehlend = v1:** ein Payload ohne das Feld (Alt-Objekt-Simulation) lädt ohne
  Warnung; `read_format_version` liefert 1 bei fehlend/`None`/unparsebar.
* **Gleich:** normaler Roundtrip, keine Migration aufgerufen.
* **Älter + Migration:** eine Test-Migration `register_migration(1)` wird
  angewandt, `from_dict` liefert das migrierte Objekt; mehrstufige Treppe (v1→v3)
  ruft beide Stufen in Reihenfolge.
* **Älter, keine Migration:** `IncompatibleFormatError` mit `v{n} -> v{n+1}`.
* **Neuer:** `FormatVersionWarning` (per `pytest.warns`) + best-effort geladen;
  `strict=True` → `IncompatibleFormatError`.
* **Choke-Point deckt Parquet ab:** ein via `_restore_from_attrs` geladenes
  Objekt mit gefälschter höherer Version warnt ebenfalls (ein Pfad, eine Prüfung).

## 10. Kompatibilität / Migration

* **Bestehende Dateien:** laden unverändert (fehlendes Feld = v1). Kein
  Zwangs-Rewrite; wer neu schreibt, bekommt das Feld automatisch.
* **`_sdata_version`:** unangetastet — Downstream, das es ausliest, bricht nicht.
* **`SDATA_ATTRIBUTES`** wächst um einen Eintrag; Code, der über diese Liste
  iteriert (z. B. Vollständigkeitsprüfungen), sieht das neue Feld als weiteres
  reserviertes Attribut — additiv.
* **Neuer Warn-/Fehlertyp:** `FormatVersionWarning`/`IncompatibleFormatError` in
  `sdata/format.py`; bestehende Aufrufer, die kein `strict=True` setzen, erleben
  nur (im Neuer-Fall) eine Warnung.

## 11. Risiken / offene Punkte

* **Erste echte Migration steht noch aus.** Dieses RFC etabliert die Leerregistry;
  die Praxistauglichkeit der Treppe zeigt sich erst an einer realen v1→v2. Der
  Test nutzt eine Wegwerf-Migration, um den Pfad **jetzt** zu decken.
* **`_restore_from_attrs`-Abdeckung.** Die Prüfung muss wirklich **vor** jeder
  Metadatenübernahme sitzen; ein Reader, der `Metadata.from_dict` künftig umgeht,
  umginge auch die Prüfung — Konvention: neue Reader gehen über `from_dict`
  (RFC 0009 tut das).
* **Store-Doppelung.** Der `JSON1SQLiteStore` hat sein **eigenes**
  `PRAGMA user_version` für das DB-Schema; das ist bewusst getrennt (DB-Schema ≠
  Objekt-Format). RFC 0011 (Persistenz-Konsolidierung) sollte klarstellen, dass
  beide Ebenen unabhängig versioniert bleiben.
* **CLI-Migration** (`sdata migrate <file>` zum Rewrite auf der Platte) ist bewusst
  aus­gelagert — dieses RFC deckt nur die Lese-Zeit-Migration im Speicher.
