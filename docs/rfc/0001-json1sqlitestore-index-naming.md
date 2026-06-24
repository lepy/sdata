# RFC 0001 — Fix der generierten Spalten in `JSON1SQLiteStore` (sdata.iolib)

| Feld        | Wert                                                        |
|-------------|-------------------------------------------------------------|
| Status      | Proposed                                                    |
| Datum       | 2026-06-24                                                  |
| Autor       | lepy <lepy@tuta.io>                                          |
| Komponente  | `sdata/iolib/json1sqlitestore.py`                           |
| Betrifft    | `tests/iolib/test_json1sqlitestore.py` (32 Tests)           |
| Validierung | Empfohlene Lösung lokal verifiziert: **32/32 grün**         |

## 1. Zusammenfassung

`JSON1SQLiteStore` ist derzeit **nicht instanziierbar**: bereits der Konstruktor
wirft `sqlite3.OperationalError: no such column: _sdata_project_sname`. Ursache
ist eine grundsätzliche Inkonsistenz darüber, **welche** `_sdata_*`-Felder als
generierte Spalten existieren und **wie** sie heißen.

Dieses RFC schlägt vor, die Menge der generierten Spalten als **Single Source of
Truth** (`GENERATED_COLUMNS`) zu definieren und alle abhängigen Stellen daraus
abzuleiten. Die Lösung wurde lokal verifiziert (alle 32 Tests grün).

## 2. Kontext

`JSON1SQLiteStore` speichert sdata-Objekte als JSON-Payload und legt zur
Beschleunigung **generierte Spalten** (`GENERATED ALWAYS AS json_extract(...)
STORED`) für `_sdata_*`-Attribute an, auf denen Indizes erzeugt werden. Alle 32
Tests scheitern, weil schon die Fixture `JSON1SQLiteStore(':memory:', …)` im
Konstruktor abbricht.

## 3. Reproduktion

```python
from sdata.iolib.json1sqlitestore import JSON1SQLiteStore
JSON1SQLiteStore(':memory:', index_keys=['age'], unique_index_keys=['email'])
# sqlite3.OperationalError: no such column: _sdata_project_sname
```

## 4. Ursachenanalyse

Es liegen **drei** ineinandergreifende Defekte vor:

### 4.1 Fehlerhafte Heuristik „jeder `_sdata_*`-Key ist eine Spalte"

An **acht** Stellen entscheidet der Code per
`column = key if key.startswith('_sdata_') else None`, ob direkt eine Spalte
adressiert oder auf `json_extract(payload, …)` zurückgefallen wird
(`__init__` 2×, `get_id_by_key`, `find_by` und weitere). Das Schema materialisiert
aber nur eine **feste Teilmenge** der `_sdata_*`-Felder. Für jeden `_sdata_*`-Key
**ohne** zugehörige Spalte entsteht SQL auf eine nicht existierende Spalte.

### 4.2 Inkonsistente Spaltennamen (parent/project)

| JSON-Key (Payload)     | generierte Spalte (Schema) | konsistent? |
|------------------------|----------------------------|:-----------:|
| `_sdata_class`         | `_sdata_class`             | ✅ |
| `_sdata_name`          | `_sdata_name`              | ✅ |
| `_sdata_sname`         | `_sdata_sname`             | ✅ |
| `_sdata_parent_sname`  | `_sdata_parent`            | ❌ |
| `_sdata_project_sname` | `_sdata_project`           | ❌ |

`__init__` indiziert `_sdata_parent_sname`/`_sdata_project_sname` (Spaltenname =
Key), die Spalten heißen aber gekürzt → **Konstruktor-Crash** (beobachtetes
Symptom). Dieselbe Diskrepanz betrifft `get_index_df` (Filter auf
`_sdata_project_sname`/`_sdata_parent_sname`).

### 4.3 Fehlende Spalte `_sdata_suuid`

`_sdata_suuid` wird im Schema **gar nicht** als Spalte angelegt, aber:
* `test_init` erwartet die Spalte `_sdata_suuid` **und** einen unique Index
  `idx__sdata_suuid`,
* `get_id_by_key('_sdata_suuid', …)` (genutzt von `update_by_suuid`) adressiert
  die Spalte `_sdata_suuid` direkt → `no such column: _sdata_suuid`.

## 5. Lösungsoptionen

### Option A — nur parent/project-Spalten umbenennen (verworfen)

Nur die zwei Spaltennamen an die Keys angleichen.

> **Verifiziert: unzureichend.** Lokal getestet → **29/32** grün. `_sdata_suuid`
> (4.3) bleibt offen (`test_init`, `test_update_by_suuid`, `test_get_id_by_key`
> weiter rot). Behebt nur 4.2, nicht 4.1/4.3.

### Option B — Single Source of Truth für generierte Spalten (empfohlen, verifiziert)

Eine kanonische Liste der materialisierten Spalten einführen und **alle**
abhängigen Stellen daraus ableiten. Konvention: `Spaltenname == JSON-Key ==
Index-Key`.

* **Pro:** behebt 4.1, 4.2 und 4.3 gemeinsam; Heuristik wird korrekt
  (Mengen-Mitgliedschaft statt Präfix); unbekannte `_sdata_*`-Keys fallen sauber
  auf `json_extract` zurück statt zu crashen; nur **ein** Ort definiert die Menge.
* **Contra:** Schemaänderung → Migration bestehender DBs (Abschnitt 7).
* **Verifiziert: alle 32 Tests grün.**

### Option C — generierte Spalten ganz vermeiden

Überall `json_extract(payload, '$.<key>')` statt direkter Spalten verwenden.
Robust, aber invasivste Änderung; verzichtet auf die STORED-Spalten als
Index-/Query-Ziel. Nicht empfohlen.

## 6. Empfehlung: Option B

### 6.1 Kanonische Spaltenliste (neu, als Klassenattribut)

```python
# Konvention: Spaltenname == JSON-Key == Index-Key (Single Source of Truth).
GENERATED_COLUMNS = (
    "_sdata_class",
    "_sdata_name",
    "_sdata_sname",
    "_sdata_suuid",
    "_sdata_parent_sname",
    "_sdata_project_sname",
)
```

### 6.2 Schema aus der Liste erzeugen (`_ensure_table`)

```python
generated = ",\n                ".join(
    "{col} TEXT GENERATED ALWAYS AS (json_extract(payload, '$.{col}')) STORED".format(col=col)
    for col in self.GENERATED_COLUMNS
)
# ... CREATE TABLE IF NOT EXISTS data ( id …, payload …, created_at …, {generated} );
```

### 6.3 Heuristik ersetzen (8 Fundstellen)

```python
# vorher: column = key if key.startswith('_sdata_') else None
column = key if key in self.GENERATED_COLUMNS else None
# analog für die Variable `attribute` in find_by
```

### 6.4 `_sdata_suuid` als unique Index registrieren (`__init__`)

```python
# vorher: sdata_unique_keys = ['_sdata_sname']
sdata_unique_keys = ['_sdata_sname', '_sdata_suuid']
```

`__init__` und `get_index_df` brauchen darüber hinaus **keine** Änderung — sie
nutzen bereits die langen Key-Namen, die nun mit den Spaltennamen übereinstimmen.

## 7. Migration / Rückwärtskompatibilität

* Das Schema wird mit `CREATE TABLE IF NOT EXISTS` angelegt → für **bestehende**
  DB-Dateien greift die Umbenennung/Erweiterung **nicht automatisch**; SQLite kann
  generierte Spalten nicht zuverlässig per `ALTER TABLE` migrieren.
* Die Komponente wirkt unveröffentlicht/WIP (undeklarierte Nutzung, komplett rote
  Testsuite). Annahme: **keine** produktiven `.db`-Dateien → keine Migration nötig.
  Vor dem Merge zu bestätigen.
* Falls doch nötig: Schema-Rebuild über `PRAGMA user_version` als separater Schritt
  (`CREATE new … ; INSERT … SELECT … ; DROP old ; ALTER … RENAME`).

## 8. Testplan

* `./ci/local-ci.sh tests/iolib/test_json1sqlitestore.py` → **32/32 grün**
  (lokal mit Option B bereits verifiziert).
* Empfohlener Zusatztest für `get_index_df(project=…, parent=…)`, da dieser Pfad
  bislang von keinem grünen Test abgedeckt war (Defekt 4.2 im Query-Builder).

## 9. Risiken / offene Punkte

* Migrationsannahme (Abschnitt 7) bestätigen.
* Prüfen, ob weitere iolib-Module (`tinydb_json1sqlite.py`, `vault.py`) von den
  alten Spaltennamen ausgehen (aktuelle `grep`-Analyse: nein).
* Separat (nicht Teil dieses RFC): `logger.warn` → `logger.warning` in
  `sdata/sclass/blob.py`; die offenen `test_base`-Fehler.
```
