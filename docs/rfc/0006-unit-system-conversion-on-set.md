# RFC 0006 — Konsistente Einheitensysteme via Dimensions-Algebra

| Feld        | Wert                                                                 |
|-------------|----------------------------------------------------------------------|
| Status      | Accepted — implementiert (**v2**, ersetzt den v1-Entwurf)           |
| Datum       | 2026-06-30                                                           |
| Autor       | lepy <lepy@tuta.io>                                                  |
| Komponente  | `sdata/units.py`, `sdata/sclass/dataframe.py`                       |
| Betrifft    | `UnitSystem`, `DataFrame.convert`, `DataFrame.unit_system`, `DataFrame.relabel_units` |
| Validierung | `units.py` 100 %, `sclass/dataframe.py` 100 %; Solver- und Round-Trip-Tests |

> **Umsetzungsstand.** Implementiert. `sdata/units.py` trägt die Dimensions-Algebra
> (Dimvektoren, exakter `Fraction`-Solver, `UnitSystem` aus Basis-Einheiten,
> `dimension_of`/`convert_value`); `DataFrame.convert` rechnet abgeleitete Einheiten
> mit, `DataFrame.relabel_units` korrigiert falsche Einheiten ohne Skalierung. v2
> **ersetzt** den v1-Entwurf nach dem Review.

## 0. Was sich gegenüber v1 ändert

Der v1-Entwurf (flacher `Größe→Einheit`-Lookup, `set_unit_system(mode=…)`) hatte im
Review fünf belastbare Schwächen. v2 adressiert sie:

| # | v1-Problem | v2-Antwort |
|---|------------|------------|
| 1 | „Unit system" war **nicht konsistent**: abgeleitete Größen (Spannung, Energie, Geschwindigkeit) wurden still **nicht** umgerechnet (`MPa`-Spalte blieb bei `[kN, mm, ms]` unverändert). | **Dimensions-Algebra**: das System wird aus Basis-Einheiten gelöst, **jede** abgeleitete Einheit wird hergeleitet (Spannung→`GPa`, Energie→`J`, Geschwindigkeit→`m/s`). |
| 2/3 | Relabel hing am **System-Pfad**, der echte Mislabels (falsche Dimension) verfehlt; Zielbestimmung aus dem als falsch erklärten Label ist zirkulär. | Relabel **nur** über expliziten Dict (`relabel_units({col: unit})`); System-Pfad-Relabel gestrichen. |
| 4 | Inkompatibles Relabel überschrieb still, nur optionale Warnung. | Inkompatibler Dimensionswechsel verlangt `force=True`, **immer** geloggt, gibt einen **Report** zurück. |
| 5/6/7 | `set_unit_system` kollidierte namentlich mit dem Setter, war als einzige Op inplace-by-default, `mode="record"` war redundant. | `set_unit_system` **gestrichen**. „Setzen = umrechnen" ist `convert(system, inplace=True)`; die Property bleibt record-only. |
| 8 | `rescale=False` benannte die Wirkung nicht. | Eigene Methode `relabel_units(...)`; `convert` bleibt rein „umrechnen". |

## 1. Zusammenfassung

Ein **konsistentes Einheitensystem** (z. B. `[kN, mm, ms]`) wird über **Dimensions-Algebra**
modelliert: aus den angegebenen Basis-Einheiten werden die Skalen der Basis-Dimensionen
(Länge L, Masse M, Zeit T, Temperatur Θ) gelöst, und **jede** Spalten-Einheit — auch
abgeleitete wie Spannung, Energie, Geschwindigkeit, Dehnrate — wird daraus deterministisch
hergeleitet und umgerechnet.

* **Umrechnen** in ein System: `DataFrame.convert(system, inplace=True)` (rechnet Werte um
  **und** schreibt die abgeleiteten Einheiten). Das ist zugleich „beim Setzen umrechnen".
* **Merken** ohne Datenänderung: `sdf.unit_system = system` (record-only, unverändert).
* **Falsche Einheiten korrigieren** ohne Wertänderung: `relabel_units({col: unit})` —
  explizit pro Spalte, gibt einen Report zurück, verlangt `force=True` für
  Dimensionswechsel.

## 2. Motivation

* **Konsistenz ist der Sinn eines Einheitensystems.** In der Mechanik/FE (LS-DYNA u. a.)
  bedeutet `[kN, mm, ms]` *genau*, dass **alle** abgeleiteten Einheiten daraus folgen
  (Spannung `kN/mm² = GPa`, Energie `kN·mm = J`, Geschwindigkeit `mm/ms = m/s`, Masse
  `kg`). Ein Werkzeug, das Kraft/Länge/Zeit umrechnet, eine `MPa`-Spannungsspalte aber
  unangetastet lässt, erzeugt genau die halbkonsistenten Daten, die ein Einheitensystem
  verhindern soll.
* **Ein Aufruf.** „System setzen = Tabelle ist im System" soll ein Schritt sein.
* **Falsche Labels kommen vor**, müssen aber **gezielt** und **sicher** korrigierbar sein
  (nur benannte Spalten, mit Audit-Spur), nicht über einen heuristischen System-Pfad.
* **Sicherheit vor Bequemlichkeit.** `=` skaliert nie still Daten; ein Relabel, das die
  *Bedeutung* ohne die *Zahlen* ändert, ist protokolliert und nachvollziehbar.

## 3. Entwurf

### 3.1 Dimensions-Modell

Jede Größe hat einen **Dimensionsvektor** über den Basis-Dimensionen `(L, M, T, Θ)`
(erweiterbar um I, N, J). Jede Einheit bildet auf `(dimvector, factor, offset)` ab, wobei
`factor` einen Wert in die **SI-kohärente** Einheit dieser Dimension überführt
(`si = wert · factor + offset`; `offset ≠ 0` nur für reine Temperatur):

| Einheit | Dimvektor `(L,M,T,Θ)` | factor | Größe |
|---------|-----------------------|--------|-------|
| `m`, `mm`, `µm` | `(1,0,0,0)` | `1`, `1e-3`, `1e-6` | Länge |
| `kg`, `g`, `t` | `(0,1,0,0)` | `1`, `1e-3`, `1e3` | Masse |
| `s`, `ms`, `µs` | `(0,0,1,0)` | `1`, `1e-3`, `1e-6` | Zeit |
| `K`, `degC` | `(0,0,0,1)` | `1` (offset `0`, `273.15`) | Temperatur |
| `N`, `kN`, `MN` | `(1,1,-2,0)` | `1`, `1e3`, `1e6` | Kraft |
| `Pa`, `MPa`, `GPa` | `(-1,1,-2,0)` | `1`, `1e6`, `1e9` | Druck/Spannung |
| `J`, `kJ` | `(2,1,-2,0)` | `1`, `1e3` | Energie |
| `W` | `(2,1,-3,0)` | `1` | Leistung |
| `m/s` | `(1,0,-1,0)` | `1` | Geschwindigkeit |
| `1/s`, `1/ms` | `(0,0,-1,0)` | `1`, `1e3` | Rate |
| `-`, `%` | `(0,0,0,0)` | `1`, `1e-2` | dimensionslos |

Zwei Einheiten sind **umrechenbar gdw. ihre Dimvektoren gleich sind**; das ersetzt den
alten String-Größennamen-Vergleich. `units.dimension_of(unit) -> DimVector` ist die neue
Kern-Abfrage; `quantity_of` bleibt als Komfort-Name (aus dem Dimvektor abgeleitet).

### 3.2 `UnitSystem` aus Basis-Einheiten (der Solver)

Eine Liste wie `["kN", "mm", "ms"]` liefert Einheiten mit Dimvektoren
Kraft `(1,1,-2,0)`, Länge `(1,0,0,0)`, Zeit `(0,0,1,0)`. Im **Log-Raum** ist die
Umrechnung linear:

```
log(factor_i) = Σ_d  dimvec_i[d] · x_d        mit  x_d = log(Skala der Basis-Dimension d)
```

Die angegebenen Einheiten bilden ein lineares Gleichungssystem in `x_d`. Für `[kN, mm, ms]`:

```
Länge : 1·x_L                 = log(1e-3)   →  x_L = log(1e-3)   (mm)
Zeit  :              1·x_T    = log(1e-3)   →  x_T = log(1e-3)   (ms)
Kraft : x_L + x_M − 2·x_T     = log(1e3)    →  x_M = log(1)      (kg!)
```

→ das System fixiert `L=mm, T=ms, M=kg`. Damit ist die **kohärente System-Einheit jeder
Dimension** `g` bestimmt: `log(system_factor(g)) = Σ_d g[d]·x_d`. Eigenschaften:

* **FLT oder MLT.** Der Nutzer darf Kraft *oder* Masse als Basis geben (`[kN, mm, ms]` ist
  force-length-time; `[kg, mm, ms]` mass-length-time) — der Solver löst beide; bei `[kN,
  mm, ms]` ergibt sich die Masse-Einheit zu `kg`.
* **Temperatur** wird nur abgedeckt, wenn das System eine Temperatur-Einheit (z. B.
  `K`) enthält; sonst bleiben Temperatur-Spalten unverändert (die Θ-Dimension ist nicht
  aufgespannt). Offset-Einheiten (`degC`) sind als Basis **nicht** zulässig.
* **Unter­bestimmt.** Spannen die angegebenen Einheiten eine Dimension nicht auf (z. B.
  `[kN, mm]` ohne Zeit → Geschwindigkeit nicht lösbar), bleiben Spalten dieser Dimension
  **unverändert** (geloggt) — analog „Größe nicht im System".
* **Über­bestimmt.** Redundante, *konsistente* Angaben sind erlaubt (z. B. zusätzlich
  `GPa`, das aus `[kN, mm, ms]` bereits folgt); *widersprüchliche* Angaben sind ein Fehler
  (`UnitConversionError`).
* **Exaktheit.** Der Solver bestimmt die Koeffizienten exakt über `fractions.Fraction`;
  der System-Faktor wird als exaktes rationales **Potenzprodukt** der Basis-Faktoren
  berechnet (kein `log`/`exp`), sodass z. B. `5000 N → 5.0 kN` und `200 MPa → 0.2 GPa`
  exakt herauskommen. Nur bei (seltenen) nicht-ganzzahligen Exponenten — etwa Länge aus
  einem Flächen-Basis `[mm2, s]` über den Exponenten ½ — wird auf `float` zurückgefallen.

### 3.3 Hergeleitete Einheit: Faktor **und** Label

Für eine Spalte mit Einheit `u` (Dimvektor `g`, `factor_u`) ist der Zielwert
`wert · factor_u / system_factor(g)`. Das **Label** der Zieleinheit wird so gewählt:

1. **Kanonischer Registry-Treffer:** gibt es ein Vorzugs-Symbol mit exakt `(g,
   system_factor(g))`, wird es verwendet (`GPa`, `J`, `m/s`, `kN`, `1/ms`, `kg`).
   Bevorzugt, weil lesbar und interoperabel.
2. **Sonst komponiert** aus den **angegebenen Basis-Symbolen** des Systems (den
   Koeffizienten der Lösung), Format `*` (mal), `/` (geteilt), `^n` (Exponent) — z. B.
   Beschleunigung → `mm/ms^2`, Dichte → `kN*ms^2/mm^4` (force-basiert).

Bei `[kN, mm, ms]` liefert das u. a. Spannung→`GPa`, Energie→`J`, Geschwindigkeit→`m/s`,
Dehnrate→`1/ms`, Masse→`kg` (alle **kanonisch**); unbenannte Composites wie
Beschleunigung→`mm/ms^2` werden aus den Basis-Symbolen komponiert — alle numerisch
konsistent.

> **Wrinkle.** Manche Dimvektoren sind mehrdeutig benannt (`1/s` vs. `Hz` vs. `Bq`,
> Drehmoment `N·m` vs. Energie `J`). Schritt 1 nutzt eine **geordnete** Vorzugs-Symbol-
> Liste (`_CANON_SYMBOLS`); ohne eindeutigen Treffer greift Schritt 2 (komponiert). Siehe §7.

### 3.4 API

```python
# umrechnen in ein System (inkl. abgeleiteter Einheiten) — auch "beim Setzen umrechnen"
DataFrame.convert(units=None, inplace=False)
#   units: UnitSystem | Einheiten-Liste | {Spalte: Einheit} | None(=self.unit_system)
#   None+inplace=True  -> die Tabelle ist danach im gemerkten System
#   gibt standardmäßig eine umgerechnete Kopie zurück (Default inplace=False)

# Ziel-System nur MERKEN (kein Daten-Seiteneffekt) — unverändert
sdf.unit_system = ["kN", "mm", "ms"]

# falsche Einheiten KORRIGIEREN, Werte NICHT ändern (explizit pro Spalte, in place)
DataFrame.relabel_units(mapping, *, force=False) -> list[dict]
#   setzt unit der genannten Spalten ohne Skalierung; gleiche Dimension: ok + geloggt;
#   andere Dimension: nur mit force=True, sonst UnitConversionError.
#   Report: Liste von {"column", "old", "new", "dimension_changed"}

# units-Modul
units.dimension_of(unit) -> (L, M, T, Θ) | None
units.UnitSystem(base_units)                    # löst die Basis-Dimensionen (§3.2)
system.target_for(unit) -> label | None         # System-Einheit derselben Dimension
system.convert_value(value, unit) -> (value, label) | None
system.factor_for(dimvector) -> float | None
system.unit_for(quantity_name) -> label | None  # z. B. "force" -> "kN"
units.convert / units.convert_factor            # unverändert (zwei Einheiten gleicher Dim)
```

`convert` führt **kein** Relabeling-Flag; reines Umlabeln ist `relabel_units` (ehrlich
benannt, mutiert in place, mit Report und `force`).

### 3.5 Semantik je Spalte

| Aktuell | System `[kN, mm, ms]` | `convert` | `relabel_units({col: ziel})` |
|---------|------------------------|-----------|------------------------------|
| Kraft `N` | Ziel `kN` | Werte ÷1000, →`kN` | nur `relabel_units({"f":"kN"})`: →`kN`, Werte unverändert |
| Spannung `MPa` | Ziel `GPa` (**hergeleitet**) | Werte ·1e-3, →`GPa` | nach Bedarf |
| Energie `J` | Ziel `J` (`kN·mm`) | Werte ·1, →`J` | nach Bedarf |
| Geschw. `m/s` | Ziel `m/s` (`mm/ms`) | Werte ·1, →`m/s` | nach Bedarf |
| Länge `mm` | Ziel `mm` | no-op | no-op |
| ohne Einheit | — | übersprungen (Dim unbekannt) | `{"x":"kN"}`: →`kN` (Label-Fix), Werte unverändert |
| Kraft `N`, Ziel `mm` (inkompatibel) | — | n/a | nur `force=True`: →`mm` + Log + Report |

## 4. Worked Example `[kN, mm, ms]`

```python
import pandas as pd
from sdata.sclass.dataframe import DataFrame
from sdata.units import UnitSystem

df = pd.DataFrame({"force":[5000.], "stroke":[2.4], "time":[0.5],
                   "stress":[200.0], "v":[3.0], "energy":[12.0]})
sdf = DataFrame(df=df, name="test")
sdf.set_column("force", unit="N");   sdf.set_column("stroke", unit="mm")
sdf.set_column("time",  unit="s");   sdf.set_column("stress", unit="MPa")
sdf.set_column("v",     unit="m/s"); sdf.set_column("energy", unit="J")

si = sdf.convert(UnitSystem(["kN", "mm", "ms"]))
```

| Spalte | vorher | nachher | Faktor | Herleitung |
|--------|--------|---------|--------|------------|
| force  | `5000 N`   | `5 kN`     | ÷1e3 | Basis |
| stroke | `2.4 mm`   | `2.4 mm`   | ·1   | Basis |
| time   | `0.5 s`    | `500 ms`   | ·1e3 | Basis |
| stress | `200 MPa`  | `0.2 GPa`  | ·1e-3 | `kN/mm² = GPa` |
| v      | `3 m/s`    | `3 m/s`    | ·1   | `mm/ms = m/s` |
| energy | `12 J`     | `12 J`     | ·1   | `kN·mm = J` |

Genau die abgeleiteten Spalten (`stress`, `v`, `energy`), die v1 still ignorierte, werden
jetzt korrekt mitgeführt.

## 5. Designentscheidungen

* **Dimensions-Algebra statt flacher Tabelle.** Nur so ist „konsistentes System" wahr:
  abgeleitete Einheiten werden hergeleitet, nicht zufällig getroffen. Kosten: ein kleiner
  Linearsolver (4×n) — pure Python, `fractions` für exakte Exponenten, kein numpy nötig.
* **Kanonische Labels bevorzugt, sonst komponiert.** `GPa`/`J`/`m/s` sind lesbar und
  interoperabel; ohne Treffer eine ehrliche Komposition aus den Basis-Symbolen.
* **Relabel nur per explizitem Dict.** Der System-Pfad-Relabel aus v1 ist zirkulär und
  verfehlt echte Mislabels — gestrichen. `relabel_units` benennt genau die zu
  korrigierenden Spalten.
* **Kein magischer Setter.** `set_unit_system` gestrichen; „setzen = umrechnen" ist das
  bereits vorhandene `convert(system, inplace=True)`; die Property bleibt record-only.
  Beseitigt die Namens-Kollision und die inplace-Asymmetrie.
* **Inkompatibles Relabel: `force` + Log + Report.** Für eine semantikzentrierte
  Bibliothek darf ein Dimensionswechsel des Labels nicht still passieren.

## 6. Sicherheit & semantische Schicht

* **Audit-Spur.** `convert` loggt jede umgerechnete Spalte (`alt → neu`); `relabel_units`
  loggt jedes Umlabeln (Warnung) und gibt zusätzlich einen Report (Liste von
  `{column, old, new, dimension_changed}`) zurück.
* **JSON-LD/QUDT bleibt konsistent.** Eine geänderte Einheit fließt direkt in den
  `qudt:Quantity`/`unitRef`-Knoten der Spalte (das `to_jsonld`-Spalten-Mapping liest die
  `unit` der Spalte). Die hinterlegte `ontology`/Größenklasse wird **nicht** automatisch
  überschrieben; bei `relabel_units` mit Dimensionswechsel (`force=True`) macht die
  geloggte Warnung auf eine mögliche Inkonsistenz aufmerksam.

## 7. Tests / Coverage (umgesetzt)

`units.py` **100 %**, `sclass/dataframe.py` **100 %** Line-Coverage; alle bestehenden
`convert`/`unit_system`-Tests bleiben grün. Abgedeckt:

* **Solver:** FLT (`[kN, mm, ms]` → Masse `kg`), MLT (`[t, mm, s]`), unterbestimmt
  (`[kN, mm, ms]` → Temperatur/`degC` unverändert), überbestimmt-konsistent
  (`[kN, mm, ms, GPa]`), überbestimmt-widersprüchlich (`["N","kN"]` → Fehler), rationaler
  Exponent (`[mm2, s]` → Länge über ½); plus White-Box-Test des `_solve_linear`-Pfads.
* **Abgeleitete Umrechnung:** Spannung `MPa→GPa`, Energie `J→J`, Geschwindigkeit `m/s`,
  Dehnrate `1/s→1/ms`, Masse `g→kg`; Komposition (`_compose`) aus Basis-Symbolen.
* **Relabel:** gleiche Dimension (ok + Report), einheitenlose Spalte labeln, inkompatibel
  ohne/mit `force` (Fehler / Override + Warnung + Report).
* **Temperatur:** `degC→K` (Offset, System mit `K`); Offset-Einheit als Basis abgelehnt.
* **Property** bleibt nachweislich record-only.

## 8. Kompatibilität / Migration

* `units.convert` / `units.convert_factor` (zwei Einheiten gleicher Dimension) bleiben
  **unverändert**.
* `UnitSystem(["kN","mm","ms"])` konstruiert weiter; `target_for("N") == "kN"` bleibt.
  **Verhaltens­änderung (gewollt, da unveröffentlicht):** `target_for("MPa")` liefert jetzt
  `GPa` statt `None` — abgeleitete Größen werden umgerechnet.
* `convert(units, inplace=…)` und die `unit_system`-Property bleiben signaturgleich; das
  v1-`rescale`-Flag entfällt (war nie released). `relabel_units` ist neu.
* Strikt additiv ansonsten; keine neue Laufzeit-Abhängigkeit (`fractions` ist stdlib).

## 9. Offene Punkte / Zukunft

* **Mehrdeutige Dimvektoren** (`1/s`/`Hz`, `N·m`/`J`): Vorzugs-Symbol-Tabelle pflegen oder
  bei Ambiguität bewusst komponieren (§3.3-Wrinkle).
* **Persistenz** des `unit_system` über Serialisierung (Parquet/dict/JSON-LD) — separater
  Folge-RFC; ohne sie ist das gemerkte System transient.
* **`pint`-Interop** für Einheiten außerhalb der kuratierten Tabelle (optional, wie bei
  `validate_unit`).
* **Winkel/Logarithmische Einheiten** (rad/deg, dB) sind dimensionslos-aber-distinkt und
  bleiben vorerst außen vor.
* **Über das DataFrame hinaus:** dieselbe Algebra kann skalare `Attribute` (mit `unit`) im
  `Metadata` umrechnen — späterer Schritt.
