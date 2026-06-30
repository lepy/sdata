# RFC 0006 — Einheitensystem: Umrechnung beim Setzen & Relabeling falscher Einheiten

| Feld        | Wert                                                              |
|-------------|------------------------------------------------------------------|
| Status      | Proposed (Entwurf) — noch nicht implementiert                    |
| Datum       | 2026-06-30                                                       |
| Autor       | lepy <lepy@tuta.io>                                              |
| Komponente  | `sdata/sclass/dataframe.py`, `sdata/units.py`                    |
| Betrifft    | `DataFrame.unit_system`, `DataFrame.convert`, neu `set_unit_system` |
| Validierung | (geplant) 100 % Line-Coverage; Round-Trip- und Relabel-Tests     |

> **Umsetzungsstand.** Vorschlag. Baut auf dem in PR #86–#88 ausgelieferten
> `units.convert`/`UnitSystem`, `DataFrame.convert` und der settbaren Property
> `DataFrame.unit_system` (heute *record-only*) auf.

## 1. Zusammenfassung

Dieser RFC ergänzt zwei **optionale** Verhaltensweisen rund um das Ziel-Einheiten­system
eines `DataFrame`:

1. **Umrechnung beim Setzen.** `set_unit_system(system)` rechnet die Spalten direkt um
   (Zahlenwerte skalieren **und** Einheiten umschreiben), statt — wie heute der
   Property-Setter — nur die Absicht zu speichern.
2. **Relabeling ohne Umrechnung.** Für **fehlerhaft zugewiesene** Einheiten sollen die
   Spalten auf die neuen Einheiten gesetzt werden, **ohne** die Zahlenwerte zu ändern
   (Korrektur falscher Labels) — `set_unit_system(system, mode="relabel")` bzw.
   `convert(..., rescale=False)`.

Die Property `unit_system` bleibt bewusst **record-only**: ein `=` skaliert nie still
die Daten. Aktive Effekte laufen ausschließlich über benannte, sichtbare Aufrufe.

## 2. Motivation

* **Ein Schritt statt zwei.** Heute ist „System setzen" und „umrechnen" getrennt
  (`sdf.unit_system = …; sdf.convert(inplace=True)`). Häufig ist gemeint: *„diese
  Tabelle ist ab jetzt in diesem System"* — das soll ein Aufruf leisten.
* **Falsche Labels kommen vor.** Reale Daten tragen oft falsche Einheiten-Annotationen:
  ein Export liefert bereits **kN**, ist aber als **N** gelabelt; oder eine Kraft-Spalte
  trägt versehentlich **kg**. Eine normale Umrechnung würde die Werte (fälschlich)
  skalieren. Gebraucht wird ein **Relabel ohne Skalierung**, das nur die Annotation
  korrigiert.
* **Sicherheit vor Bequemlichkeit.** Ein `=` darf keine Zahlenwerte still verändern
  (Datenkorruptionsrisiko, „principle of least astonishment"). Die aktiven Operationen
  bekommen daher explizite, lesbare Namen/Flags.

## 3. Entwurf

### 3.1 Zwei orthogonale Operationen

| Operation   | Wirkung                                  |
|-------------|------------------------------------------|
| **Rescale** | Zahlenwerte umrechnen (`from` → `to`)    |
| **Relabel** | nur das `unit`-Feld der Spalte setzen    |

Daraus ergeben sich drei Modi:

* **convert** = Rescale **+** Relabel (die normale Umrechnung, heutiges Verhalten),
* **relabel** = nur Relabel (Korrektur falscher Einheiten, **ohne** Wertänderung),
* **record**  = keins von beiden (nur das Ziel-System merken — heutiger Setter).

### 3.2 API

```python
# Basis-Primitive: convert() bekommt ein rescale-Flag
DataFrame.convert(units=None, inplace=False, rescale=True)
#   rescale=True  -> wie bisher: Werte skalieren + Einheiten umschreiben
#   rescale=False -> nur Einheiten umschreiben (Relabel), Werte unverändert

# Ergonomische Hülle: Setzen + (optional) Anwenden in einem Aufruf
DataFrame.set_unit_system(system, mode="convert")
#   mode="convert" (Default) -> record + convert(system, inplace=True, rescale=True)
#   mode="relabel"           -> record + convert(system, inplace=True, rescale=False)
#   mode="record"            -> nur record (identisch zum Property-Setter)

# unverändert: Property-Setter bleibt record-only (== mode="record")
sdf.unit_system = ["kN", "mm", "ms"]
```

`set_unit_system` mutiert **in place** (der Name sagt „auf diesem Objekt setzen") und
gibt `self` zurück. Wer eine umgerechnete **Kopie** will, nutzt weiterhin
`copy = sdf.convert(system)` (non-inplace).

### 3.3 Semantik je Spalte

Die Zielbestimmung ist identisch zu `convert` (System: pro Größe eine Einheit, aus der
*aktuellen* Spalten-Einheit abgeleitet; Dict: explizit pro Spalte). Der Unterschied
liegt nur in *Rescale ja/nein* und in der Behandlung von Sonderfällen:

| Aktuell | Ziel | `convert` (rescale=True) | `relabel` (rescale=False) |
|---------|------|--------------------------|---------------------------|
| Kraft `N` | `kN` | Werte ÷1000, Einheit→`kN` | Einheit→`kN`, **Werte unverändert** |
| Länge `mm` | `mm` | no-op | no-op |
| Druck `MPa` | (nicht im System) | unverändert | unverändert |
| ohne Einheit, Dict `{"force":"kN"}` | `kN` | Warnung + übersprungen | Einheit→`kN` (Label-Fix), Werte unverändert |
| inkompatibel, Dict `{"force":"mm"}` | `mm` | `UnitConversionError` | Einheit→`mm` (überschreiben, **kein Fehler**) |

**Zentrale Unterschiede des `relabel`-Modus:**

* **Keine Skalierung** der Zahlenwerte und keine dtype-Änderung.
* **Keine Quantity-Prüfung / kein `UnitConversionError`.** Mislabels sind genau die
  Fälle, in denen das alte Label (und damit seine Größe) falsch ist — ein
  Kompatibilitäts-Check würde den Use-Case verhindern. Daher: **überschreiben**.
* **System-Pfad:** relabelt nur Spalten mit *bekannter* aktueller Einheit (deren Größe
  ableitbar ist); Spalten ohne/mit unbekannter Einheit werden übersprungen (die Größe
  ist nicht bestimmbar).
* **Dict-Pfad:** relabelt **jede genannte Spalte** — auch ohne oder mit falscher
  aktueller Einheit. Das ist das eigentliche Werkzeug für Mislabels.
* **Optional:** Warnung loggen, wenn die Ziel-Einheit unbekannt ist
  (`units.validate_unit`), ohne den Vorgang abzubrechen.

### 3.4 Beispiele

```python
# 1) Setzen = umrechnen (der Primärwunsch dieses RFC)
sdf.set_unit_system(["kN", "mm", "ms"])           # Werte umgerechnet + Einheiten gesetzt
# äquivalent zu:  sdf.unit_system = [...]; sdf.convert(inplace=True)

# 2) Fehlerhaftes Label korrigieren, Zahlenwerte NICHT ändern
#    (force-Spalte ist faktisch in kN, aber als "N" gelabelt)
sdf.set_unit_system(["kN", "mm", "ms"], mode="relabel")   # nur Annotationen
#    oder gezielt für einzelne Spalten:
sdf.convert({"force": "kN"}, inplace=True, rescale=False)

# 3) record-only (unverändertes Verhalten)
sdf.unit_system = ["kN", "mm", "ms"]              # nur Absicht; convert() wendet an
si = sdf.convert()                                # umgerechnete Kopie im gemerkten System
```

## 4. Designentscheidungen

* **Property bleibt record-only.** `sdf.unit_system = …` darf keine Daten skalieren
  (Astonishment + Datenkorruptionsrisiko). Aktive Effekte nur über benannte Aufrufe
  (`set_unit_system`, `rescale=`). Rückwärtskompatibel zu PR #88.
* **`rescale`-Flag statt Policy-Attribut.** Ein zustandsbehaftetes
  `unit_system_policy`, das still ändert, *was* `=` tut, wäre versteckt und
  überraschend. Ein explizites Argument am Aufrufpunkt ist lokal lesbar.
* **`mode=` (drei Werte) statt mehrerer Booleans.** Ein Aufzählungs-Argument vermeidet
  widersprüchliche Kombinationen (`convert=True, relabel=True`).
* **Relabel erzwingt keine Kompatibilität.** Bewusst — siehe 3.3. Optionale Warnung bei
  unbekannter Zieleinheit statt Fehler.
* **`convert(rescale=)` als Basis-Primitive, `set_unit_system` nur als Hülle.** Hält
  die testbare Oberfläche klein; `set_unit_system` ist reine Komposition aus
  „record" + `convert(..., inplace=True, rescale=…)`.

## 5. Tests / Coverage (geplant)

* `set_unit_system` in `mode="convert"` / `"relabel"` / `"record"` (inkl. Default).
* `convert(rescale=False)`:
  * System-Pfad-Relabel (z. B. `N`→`kN` **ohne** Skalierung der Werte),
  * Dict-Pfad-Relabel: Label einer einheitenlosen Spalte setzen; inkompatible Einheit
    überschreiben **ohne** `UnitConversionError`,
  * optionale Warnung bei unbekannter Zieleinheit.
* Property-Setter bleibt nachweislich **record-only** (keine Wertänderung).
* **100 % Line-Coverage**; die bestehenden `convert`/`unit_system`-Tests bleiben grün.

## 6. Kompatibilität / Migration

Strikt **additiv** und rückwärtskompatibel:

* `convert` erhält den **neuen Default** `rescale=True` → unverändertes Verhalten.
* `set_unit_system` und `mode=` sind **neu**.
* Der `unit_system`-Property-Setter bleibt **unverändert** (record-only).
* Keine Breaking Changes; keine neue Abhängigkeit (reine Standardbibliothek).

## 7. Offene Punkte / Zukunft

* **Kopie vs. in place für `set_unit_system`.** Vorschlag: `set_unit_system` mutiert
  immer in place (Name impliziert das); für Kopien dient `convert(system)`.
* **Strict-Modus beim Relabel.** Optionales `strict=`/Warnung, wenn die Zieleinheit
  unbekannt ist (`units.validate_unit`, mit `pint` erweiterbar).
* **dtype-Verhalten dokumentieren.** Relabel ändert nie Werte/dtype; Convert kann
  `int` → `float` heben (Division).
* **Persistenz** des `unit_system` über die Serialisierung (Parquet/dict/JSON-LD) —
  eigenständig von diesem RFC.
