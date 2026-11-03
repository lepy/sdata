# RFC 0017 — Achsen für Stromstärke und Stoffmenge im Dimensionsvektor

| Feld        | Wert                                                                                     |
|-------------|------------------------------------------------------------------------------------------|
| Status      | Angenommen — umgesetzt                                                                    |
| Datum       | 2026-11-03                                                                                |
| Autor       | lepy <lepy@tuta.io>                                                                       |
| Komponente  | `sdata/units.py` (`_DIM_NAMES`, `_UNITS`, `UNIT_MAP`, `_PINT_AXIS`, `_QUANTITY_BY_DIM`), Tests `tests/test_units_*.py`, `tests/test_dtypes.py` |
| Betrifft    | Rückgabeform von `dimension_of`; Umrechnung und Größennamen elektrischer Einheiten        |
| Vorgeschichte | RFC 0006 (Dimensions-Algebra), RFC 0014 (Persistenz des Einheitensystems); Anlass: scale-result-api RFC-001 §2.1.1 (SDM-Attribute als sdata-Attribute) |
| Validierung | `tests/test_units_electrical.py`, `test_units_qudt_coverage.py`, `test_units_convert.py`, `test_units_angle.py`, `test_units_frequency.py`, `test_units_pint_interop.py` |

## 1. Problem

Der Dimensionsvektor hat fünf feste Achsen: Länge, Masse, Zeit, Temperatur und
ebener Winkel (`sdata/units.py:170`, `_DIM_NAMES = ("L", "M", "T", "Theta", "A")`).
pint wird nur auf vier davon abgebildet (`sdata/units.py:288`, `_PINT_AXIS`). Hat
eine Einheit eine andere Achse, gibt `_pint_dimvector` `None` zurück
(`sdata/units.py:291`).

Elektrische Einheiten und Stoffmengen haben deshalb weder Dimension noch Größe.
Gemessen auf `origin/master` (2d87aa3) mit pint:

```text
dimension_of('A')   -> None
dimension_of('C')   -> None
dimension_of('mol') -> None
convert(1, 'C', 'K') -> UnitConversionError: unknown source unit 'C'
```

Das trifft echte Daten. Das MDM der SCALE-SDM-Instanz `demo.sdm.scale.eu` hat
108 Einheiten. `sdata.units` 1.5.0 gibt 26 davon keine Dimension, 17 davon
elektrische Größen oder Stoffmengen: `A`, `mA`, `A/m`, `A/(m*m)`, `V`, `mV`, `kV`,
`V/m`, `V/A`, `ohm`, `kohm`, `Mohm`, `mohm`, `C`, `Ah`, `kg/(s*s/A)`, `mol`
(lesende Abfrage am 2026-11-03 aus scale-result-api). `kg/(s*s/A)` ist
kg·A·s⁻² und keine benannte Größe. Gemeint war vermutlich Tesla (kg·A⁻¹·s⁻²),
der MDM-Eintrag ist dann fehlerhaft. Mit der Strom-Achse bekäme er trotzdem eine
Dimension. Die MDM-Dimensionen
*Current*, *Voltage*, *Resistance* und *Charge* gibt es dort bereits.

Folgen: `mV` lässt sich nicht nach `V` umrechnen, `quantity_of` liefert keinen
Namen, und ein Abgleich gegen die MDM-Dimension ist für diese Einheiten nicht
möglich.

## 2. Vorschlag

### 2.1 Zwei neue Achsen am Ende

Der Vektor wächst auf sieben Achsen `(L, M, T, Θ, A, I, N)`. Neu sind
**I = elektrische Stromstärke** und **N = Stoffmenge**. Sie kommen ans Ende,
damit die Indizes 0–4 ihre Bedeutung behalten:

```python
_DIM_NAMES = ("L", "M", "T", "Theta", "A", "I", "N")
_PINT_AXIS = {"[length]": 0, "[mass]": 1, "[time]": 2, "[temperature]": 3,
              "[current]": 5, "[substance]": 6}
```

Beide kommen in einem Schritt. Jede Längenänderung des Vektors bricht Aufrufer, die
mit festen Tupeln vergleichen. `mol` steht im selben MDM, eine eigene Änderung nur
für N wäre ein zweiter Bruch.

### 2.2 Kuratierte Einheiten

| Symbol | Vektor `(L, M, T, Θ, A, I, N)` | Faktor | Größe |
|---|---|---|---|
| `A`, `mA`, `kA` | `(0, 0, 0, 0, 0, 1, 0)` | 1, 1e-3, 1e3 | `current` |
| `V`, `mV`, `kV` | `(2, 1, -3, 0, 0, -1, 0)` | 1, 1e-3, 1e3 | `voltage` |
| `ohm`, `mohm`, `kohm`, `Mohm` | `(2, 1, -3, 0, 0, -2, 0)` | 1, 1e-3, 1e3, 1e6 | `resistance` |
| `C`, `Ah`, `mAh` | `(0, 0, 1, 0, 0, 1, 0)` | 1, 3600, 3.6 | `charge` |
| `mol`, `mmol` | `(0, 0, 0, 0, 0, 0, 1)` | 1, 1e-3 | `amount_of_substance` |

Abgeleitete Formen wie `V/m`, `A/m` oder `V/A` löst pint über die neuen Achsen auf.

`UNIT_MAP` braucht QUDT-IRI und UCUM-Code für **jede** neue Einheit der Tabelle, nicht
nur für die Basissymbole: `test_every_convertible_unit_has_qudt_iri`
(`tests/test_units_qudt_coverage.py:34`) verlangt eine IRI für jeden Eintrag in
`_UNITS`. Vorgesehen sind `unit:A`, `unit:MilliA`, `unit:KiloA`, `unit:V`,
`unit:MilliV`, `unit:KiloV`, `unit:OHM`, `unit:MilliOHM`, `unit:KiloOHM`,
`unit:MegaOHM`, `unit:C`, `unit:A-HR`, `unit:MilliA-HR`, `unit:MOL` und
`unit:MilliMOL`. Die Namen sind noch nicht gegen das QUDT-Vokabular geprüft, das
geschieht bei der Umsetzung.

`C` heißt Coulomb. Auf `origin/master` gibt es kein Alias von `C` auf `degC`
(`_CONVERT_ALIASES`, `sdata/units.py:226`). `test_bare_c_is_not_celsius`
(`tests/test_units_qudt_coverage.py:46`) hält das heute fest, indem er
`qudt_iri("C") is None` und `quantity_of("C") is None` verlangt. Mit diesem RFC
werden daraus `unit:C` und `"charge"`. Der Test wird umgeschrieben und behält seinen
Zweck: `normalize_symbol("C") == "C"` bleibt gleich, und `convert(20, "C", "K")`
wirft weiter `UnitConversionError`, jetzt weil Ladung und Temperatur verschiedene
Dimensionen haben.

### 2.3 Was gleich bleibt

- **Persistenz:** RFC 0014 speichert ein `UnitSystem` als Liste seiner
  Basiseinheiten, nicht als Vektoren (RFC 0014 §3.1). Gespeicherte Dateien bleiben
  lesbar und unverändert.
- **`UnitSystem`:** Bestehende Basislisten haben keine Einheit auf I oder N. Eine
  Spalte in `V` lässt sich mit ihnen nicht auflösen. Sie bleibt dann unverändert,
  wie heute jede Dimension, die das System nicht aufspannt: `convert_value` gibt
  `None` zurück, `DataFrame` überspringt die Spalte (`sdata/sclass/dataframe.py:412`),
  und `test_convert_leaves_unspanned_dimension_unchanged`
  (`tests/test_sclass_dataframe_units.py:81`) hält das fest. Wer elektrische Spalten
  umrechnen will, nimmt `A` in die Basis auf.
- **`relabel_units`** (`sdata/sclass/dataframe.py:466`) vergleicht zwei Ergebnisse
  von `dimension_of` miteinander und funktioniert mit sieben Achsen unverändert.

### 2.4 Was bricht

`dimension_of` gibt sieben statt fünf Werte zurück. Wer Ergebnisse mit festen
5er-Tupeln vergleicht, muss nachziehen. In sdata selbst betrifft das 25 Tupel in
fünf Testdateien (`test_units_angle.py` 9, `test_units_convert.py` 8,
`test_units_pint_interop.py` 3, `test_units_frequency.py` 3, `test_dtypes.py` 2)
und die Tabelle `_UNITS`.

## 3. Migration

1. In einem Commit:
   - `_DIM_NAMES`, `_UNITS` (alle Einträge um `0, 0` verlängert), `_PINT_AXIS`,
     `_QUANTITY_BY_DIM` und die neuen Einheiten;
   - `_pint_dimvector`: `vec = [0, 0, 0, 0, 0]` (`sdata/units.py:297`) wird zu
     `[0] * len(_DIM_NAMES)`, sonst gibt es mit den Indizes 5 und 6 einen
     `IndexError`. Docstrings und Kommentare, die fünf Achsen nennen, ziehen mit;
   - `UNIT_MAP` für alle neuen Einheiten (§2.2);
   - die 25 Testtupel und `test_bare_c_is_not_celsius` (§2.2).

   Die Längenänderung lässt sich nicht additiv aufteilen: Zwischen „Tabelle
   verlängert" und „Tests verlängert" wäre die Suite rot.
2. Tests für die Grenzfälle: `C` ist Coulomb, `mV → V`, `Ah → C`, `V/A` hat die
   Dimension von `ohm`, `UnitSystem` ohne Strom-Basis lässt eine Spalte in `V`
   unverändert.
3. CHANGELOG mit Hinweis auf die neue Tupellänge, Versionssprung (§5.1).
4. Konsumenten nachziehen: scale-result-api hebt die Abhängigkeit auf die neue
   Version und ergänzt seine Bezugseinheiten für die MDM-Dimensionen *Current*,
   *Voltage*, *Resistance* und *Charge*.

Rückweg: Bis zum Release ist alles mit einem Revert umkehrbar. Danach können
Konsumenten auf sieben Achsen bauen, ein Zurück wäre wieder ein Bruch.

## 4. Verworfene Alternativen

- **Status quo.** Elektrische Einheiten bleiben ohne Dimension. Jeder Konsument
  braucht eigene Tabellen, und Umrechnungen wie `mV → V` fehlen.
- **Neue Funktion neben `dimension_of`.** Etwa `dimension_vector()` mit sieben
  Achsen, während `dimension_of` bei fünf bleibt. Das vermeidet den Bruch, aber
  `quantity_of`, `convert` und `UnitSystem` hängen an der Tabelle. Es gäbe zwei
  Wahrheiten, und `dimension_of('V')` bliebe `None`.
- **Nur Größennamen ohne Algebra.** Eine Liste „`V` ist Spannung" ohne Vektor
  ergibt keine Umrechnung und keine abgeleiteten Einheiten.
- **Alles an pint abgeben.** Widerspricht RFC 0006: Die kuratierte Tabelle hat
  Vorrang, der Winkel ist eine eigene Achse, und ohne das Extra `[units]` muss
  `sdata` weiter rechnen können.
- **Alle sieben SI-Basisgrößen einschließlich Lichtstärke J.** J hat in den
  vorliegenden Daten keinen Fall. Der Preis: Kommt J später, bricht die Tupellänge
  noch einmal (§5.3).

## 5. Offene Punkte

1. **Version:** 1.6.0 oder 2.0.0. Die Rückgabeform einer öffentlichen Funktion
   ändert sich, das Paket ist als Alpha klassifiziert (`pyproject.toml`,
   „Development Status :: 3 - Alpha"). Entscheidung beim Release.
2. **`grad`** bleibt unübersetzt (Gon oder Grad, `_CONVERT_ALIASES`). Das ist nicht
   Teil dieses RFC.
3. **Benannte Achsen statt Tupel:** Ein Mapping wie `{"L": 1, "T": -2}` würde
   künftige Achsen ohne Bruch erlauben. Das ist ein größerer Umbau von `units.py` und
   wird erst entschieden, wenn eine weitere Achse ansteht.
