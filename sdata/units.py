# -*- coding: utf-8 -*-
"""Einheiten-Vokabular: kuratierte Abbildung Einheit → QUDT-IRI / UCUM-Code.

Reine-Python-Tabelle (keine Abhängigkeit). Optionales Extra ``[units]`` = pint
erweitert (a) die **Validierung** (:func:`validate_unit`) auf beliebige parsebare
Einheiten und (b) die **Umrechnung** (:func:`dimension_of`/:func:`convert`/
:class:`UnitSystem`): Einheiten außerhalb der kuratierten Tabelle (imperiale,
abgeleitete …) werden über pint auf denselben Dimensionsvektor abgebildet. Die
kuratierte Tabelle hat dabei stets Vorrang; ohne pint greift ausschließlich sie.
"""
__all__ = [
    "UNIT_MAP", "normalize_symbol", "qudt_iri", "ucum_code", "unit_node",
    "validate_unit", "has_pint",
    "UnitConversionError", "quantity_of", "dimension_of", "convert",
    "convert_factor", "UnitSystem",
]

try:  # optionales Backend
    import pint as _pint
except ImportError:  # pragma: no cover - abhängig vom Environment
    _pint = None

#: gespeichertes Einheiten-Symbol -> (QUDT-IRI-CURIE | None, UCUM-Code)
UNIT_MAP = {
    "mm":   ("unit:MilliM",  "mm"),
    "cm":   ("unit:CentiM",  "cm"),
    "m":    ("unit:M",       "m"),
    "kN":   ("unit:KiloN",   "kN"),
    "N":    ("unit:N",       "N"),
    "MPa":  ("unit:MegaPA",  "MPa"),
    "GPa":  ("unit:GigaPA",  "GPa"),
    "Pa":   ("unit:PA",      "Pa"),
    "degC": ("unit:DEG_C",   "Cel"),
    "K":    ("unit:K",       "K"),
    "s":    ("unit:SEC",     "s"),
    "1/s":  ("unit:PER-SEC", "/s"),
    "Hz":   ("unit:HZ",      "Hz"),
    "kHz":  ("unit:KiloHZ",  "kHz"),
    "MHz":  ("unit:MegaHZ",  "MHz"),
    "GHz":  ("unit:GigaHZ",  "GHz"),
    "kg":   ("unit:KiloGM",  "kg"),
    "g":    ("unit:GM",      "g"),
    "rad":  ("unit:RAD",     "rad"),
    "mrad": ("unit:MilliRAD","mrad"),
    "deg":  ("unit:DEG",     "deg"),
    "gon":  ("unit:GON",     "gon"),
    "%":    ("unit:PERCENT", "%"),
    "-":    (None,           "1"),     # dimensionslos
    "":     (None,           "1"),
}

#: Symbol-Aliasse -> kanonisches UNIT_MAP-Symbol
_ALIASES = {
    "°C": "degC", "celsius": "degC", "C": "degC",
    "µm": "mm", "um": "mm", "mpa": "MPa", "gpa": "GPa", "kn": "kN",
    "°": "deg", "degree": "deg", "degrees": "deg",
    "radian": "rad", "radians": "rad", "gradian": "gon",
}


def has_pint():
    """True, falls das optionale pint-Backend verfügbar ist."""
    return _pint is not None


def normalize_symbol(symbol):
    """Trimme/normalisiere ein Einheiten-Symbol auf einen kanonischen Schlüssel."""
    if symbol is None:
        return "-"
    text = str(symbol).strip()
    if text in UNIT_MAP:
        return text
    return _ALIASES.get(text, _ALIASES.get(text.lower(), text))


def qudt_iri(symbol):
    """QUDT-Einheiten-IRI-CURIE für ein Symbol oder ``None`` (unbekannt/dimensionslos)."""
    entry = UNIT_MAP.get(normalize_symbol(symbol))
    return entry[0] if entry else None


def ucum_code(symbol):
    """UCUM-Code für ein Symbol; Fallback ist das (getrimmte) Symbol selbst."""
    entry = UNIT_MAP.get(normalize_symbol(symbol))
    if entry:
        return entry[1]
    return str(symbol).strip() if symbol is not None else "1"


def unit_node(symbol):
    """JSON-LD-Fragment für eine Einheit: ``{"unitRef": <iri>, "symbol": <sym>}``.

    ``unitRef`` entfällt, wenn keine QUDT-IRI bekannt ist (z.B. ``"-"`` oder
    unbekannte Einheit) – das rohe ``symbol`` bleibt stets erhalten.
    """
    node = {}
    iri = qudt_iri(symbol)
    if iri is not None:
        node["unitRef"] = iri
    raw = "" if symbol is None else str(symbol).strip()
    node["symbol"] = raw
    return node


def validate_unit(symbol):
    """True, wenn die Einheit bekannt (kuratierte Tabelle) oder – mit pint – parsebar ist."""
    if normalize_symbol(symbol) in UNIT_MAP:
        return True
    if _pint is not None:
        try:
            _pint.Unit(str(symbol))
            return True
        except Exception:
            return False
    return False


# --------------------------------------------------------------- Konvertierung
#
# Dimensions-Algebra (RFC 0006): jede Einheit trägt einen Dimensionsvektor über den
# Basis-Dimensionen (Länge L, Masse M, Zeit T, Temperatur Θ, ebener Winkel A). Ein
# :class:`UnitSystem` wird aus seinen Basis-Einheiten *gelöst*, sodass jede abgeleitete
# Einheit (Spannung, Energie, Geschwindigkeit, …) hergeleitet werden kann. Reine
# Standardbibliothek (``fractions`` für exakte Exponenten); das optionale ``pint``
# bleibt der Validierung.
#
# Der Winkel ist eine *eigene* Achse (nicht dimensionslos), damit rad/deg/gon
# untereinander konvertieren, aber nicht mit reinen Zahlen/Prozent (``-``/``%``)
# verwechselt werden. Logarithmische „Einheiten" (dB) bleiben bewusst außen vor:
# sie passen nicht in das lineare Faktor-Modell.

import math
from fractions import Fraction


class UnitConversionError(ValueError):
    """Eine Einheit ist unbekannt oder die Dimensionen sind inkompatibel (z. B. mm → kN)."""


#: Basis-Dimensionen: Länge, Masse, Zeit, Temperatur, ebener Winkel.
_DIM_NAMES = ("L", "M", "T", "Theta", "A")

#: Einheit -> (Dimvektor ``(L, M, T, Θ, A)``, Faktor zur SI-kohärenten Einheit, Offset).
#: ``si = wert * faktor + offset``; ``offset != 0`` nur bei reiner Temperatur.
_UNITS = {
    # Länge (1,0,0,0,0) – SI m
    "km": ((1, 0, 0, 0, 0), 1e3, 0.0), "m": ((1, 0, 0, 0, 0), 1.0, 0.0),
    "dm": ((1, 0, 0, 0, 0), 1e-1, 0.0), "cm": ((1, 0, 0, 0, 0), 1e-2, 0.0),
    "mm": ((1, 0, 0, 0, 0), 1e-3, 0.0), "um": ((1, 0, 0, 0, 0), 1e-6, 0.0),
    "nm": ((1, 0, 0, 0, 0), 1e-9, 0.0),
    # Masse (0,1,0,0,0) – SI kg
    "t": ((0, 1, 0, 0, 0), 1e3, 0.0), "kg": ((0, 1, 0, 0, 0), 1.0, 0.0),
    "g": ((0, 1, 0, 0, 0), 1e-3, 0.0), "mg": ((0, 1, 0, 0, 0), 1e-6, 0.0),
    # Zeit (0,0,1,0,0) – SI s
    "h": ((0, 0, 1, 0, 0), 3600.0, 0.0), "min": ((0, 0, 1, 0, 0), 60.0, 0.0),
    "s": ((0, 0, 1, 0, 0), 1.0, 0.0), "ms": ((0, 0, 1, 0, 0), 1e-3, 0.0),
    "us": ((0, 0, 1, 0, 0), 1e-6, 0.0), "ns": ((0, 0, 1, 0, 0), 1e-9, 0.0),
    # Temperatur (0,0,0,1,0) – SI K, mit Offset
    "K": ((0, 0, 0, 1, 0), 1.0, 0.0), "degC": ((0, 0, 0, 1, 0), 1.0, 273.15),
    # Kraft (1,1,-2,0,0) – SI N
    "MN": ((1, 1, -2, 0, 0), 1e6, 0.0), "kN": ((1, 1, -2, 0, 0), 1e3, 0.0),
    "N": ((1, 1, -2, 0, 0), 1.0, 0.0), "mN": ((1, 1, -2, 0, 0), 1e-3, 0.0),
    # Druck / Spannung (-1,1,-2,0,0) – SI Pa
    "GPa": ((-1, 1, -2, 0, 0), 1e9, 0.0), "MPa": ((-1, 1, -2, 0, 0), 1e6, 0.0),
    "kPa": ((-1, 1, -2, 0, 0), 1e3, 0.0), "Pa": ((-1, 1, -2, 0, 0), 1.0, 0.0),
    # Energie (2,1,-2,0,0) – SI J
    "kJ": ((2, 1, -2, 0, 0), 1e3, 0.0), "J": ((2, 1, -2, 0, 0), 1.0, 0.0),
    "mJ": ((2, 1, -2, 0, 0), 1e-3, 0.0),
    # Leistung (2,1,-3,0,0) – SI W
    "kW": ((2, 1, -3, 0, 0), 1e3, 0.0), "W": ((2, 1, -3, 0, 0), 1.0, 0.0),
    # Geschwindigkeit (1,0,-1,0,0), Beschleunigung (1,0,-2,0,0)
    "m/s": ((1, 0, -1, 0, 0), 1.0, 0.0), "mm/s": ((1, 0, -1, 0, 0), 1e-3, 0.0),
    "m/s2": ((1, 0, -2, 0, 0), 1.0, 0.0),
    # Fläche (2,0,0,0,0), Volumen (3,0,0,0,0)
    "m2": ((2, 0, 0, 0, 0), 1.0, 0.0), "mm2": ((2, 0, 0, 0, 0), 1e-6, 0.0),
    "m3": ((3, 0, 0, 0, 0), 1.0, 0.0), "mm3": ((3, 0, 0, 0, 0), 1e-9, 0.0),
    # Rate (0,0,-1,0,0) – Dehnrate / Frequenz
    "1/s": ((0, 0, -1, 0, 0), 1.0, 0.0), "1/ms": ((0, 0, -1, 0, 0), 1e3, 0.0),
    # Frequenz: Hz/kHz/MHz/GHz als benannte Eingabe-/Konvertier-Einheiten (gleiche
    # Dimension wie Rate). Die Rück-Benennung bleibt neutral bei 1/s, weil (0,0,-1,0,0)
    # auch die Dehnrate ist – siehe _CANON_SYMBOLS.
    "Hz": ((0, 0, -1, 0, 0), 1.0, 0.0), "kHz": ((0, 0, -1, 0, 0), 1e3, 0.0),
    "MHz": ((0, 0, -1, 0, 0), 1e6, 0.0), "GHz": ((0, 0, -1, 0, 0), 1e9, 0.0),
    # Ebener Winkel (0,0,0,0,1) – SI rad, eigene Achse „A". So konvertieren rad/deg/gon
    # untereinander, sind aber gegen dimensionslos (-/%) abgegrenzt. 1 deg = π/180 rad,
    # 1 gon = π/200 rad. (dB als logarithmische Größe bleibt bewusst außen vor.)
    "rad": ((0, 0, 0, 0, 1), 1.0, 0.0), "mrad": ((0, 0, 0, 0, 1), 1e-3, 0.0),
    "deg": ((0, 0, 0, 0, 1), math.pi / 180.0, 0.0),
    "gon": ((0, 0, 0, 0, 1), math.pi / 200.0, 0.0),
    # dimensionslos (0,0,0,0,0)
    "-": ((0, 0, 0, 0, 0), 1.0, 0.0), "": ((0, 0, 0, 0, 0), 1.0, 0.0),
    "%": ((0, 0, 0, 0, 0), 1e-2, 0.0),
}

#: Symbol-Aliasse speziell für die Konvertierung (verlustfrei, anders als die
#: lockeren Validierungs-Aliasse – z. B. ``µm`` ist hier Mikrometer, nicht ``mm``).
_CONVERT_ALIASES = {
    "µm": "um", "μm": "um", "µs": "us", "μs": "us",
    "°C": "degC", "celsius": "degC", "C": "degC",
    "sec": "s", "second": "s", "seconds": "s", "minute": "min", "hour": "h",
    "hertz": "Hz", "Hertz": "Hz", "khz": "kHz", "mhz": "MHz", "ghz": "GHz",
    # Winkel: „grad" bleibt bewusst *nicht* gemappt (mehrdeutig: engl. gradian vs.
    # dt. „Grad" = deg) – nur eindeutige Aliasse.
    "°": "deg", "degree": "deg", "degrees": "deg",
    "radian": "rad", "radians": "rad", "gradian": "gon",
}

#: Vorzugs-Symbol-Tabelle für die kanonische Rück-Benennung hergeleiteter Einheiten:
#: für ein ``(Dimension, Faktor)`` gewinnt das **erste** passende Symbol. Nur
#: Offset-freie Einheiten. Bewusste Entscheidungen bei mehrdeutigen Dimensionen:
#:   * Energie ``(2,1,-2,0)`` -> ``J`` (statt einer zusammengesetzten ``N*m``-Form).
#:   * Leistung ``(2,1,-3,0)`` -> ``W``.
#:   * Rate/Frequenz ``(0,0,-1,0)`` -> neutral ``1/s``/``1/ms``, **nicht** ``Hz``:
#:     die Dimension bezeichnet auch die Dehnrate. ``Hz``/``kHz``/``MHz``/``GHz`` sind
#:     als Einheiten erkannt (Eingabe/Konvertierung/QUDT), werden aber nicht
#:     automatisch zugewiesen, um eine Dehnrate nicht fälschlich als Frequenz zu benennen.
#:   * Winkel ``(0,0,0,0,1)`` -> ``rad`` (SI-kohärent); ``deg``/``gon`` nur, wenn das
#:     System explizit darauf basiert (eindeutig über den Faktor, keine Kollision).
_CANON_SYMBOLS = (
    "m", "mm", "cm", "km", "um", "nm",
    "kg", "g", "t",
    "s", "ms", "us",
    "K",
    "N", "kN", "MN",
    "Pa", "kPa", "MPa", "GPa",
    "J", "kJ", "W", "kW",
    "m/s", "mm/s", "m/s2",
    "1/s", "1/ms",
    "rad", "mrad", "deg", "gon",
)

#: Dimvektor -> Größenname (Komfort/Backward-Compat). Dimensionslos ``(0,0,0,0)`` ist
#: absichtlich *nicht* benannt, damit ``quantity_of("-")`` wie bisher ``None`` liefert.
_QUANTITY_BY_DIM = {
    (1, 0, 0, 0, 0): "length", (0, 1, 0, 0, 0): "mass", (0, 0, 1, 0, 0): "time",
    (0, 0, 0, 1, 0): "temperature", (1, 1, -2, 0, 0): "force",
    (-1, 1, -2, 0, 0): "pressure", (2, 1, -2, 0, 0): "energy",
    (2, 1, -3, 0, 0): "power", (1, 0, -1, 0, 0): "velocity",
    (1, 0, -2, 0, 0): "acceleration", (2, 0, 0, 0, 0): "area",
    (3, 0, 0, 0, 0): "volume", (0, 0, -1, 0, 0): "rate", (0, 0, 0, 0, 1): "angle",
}
_DIM_BY_QUANTITY = {name: dim for dim, name in _QUANTITY_BY_DIM.items()}


def _norm_convert(symbol):
    """Normalisiere ein Symbol auf einen Schlüssel der Einheitentabelle."""
    if symbol is None:
        return "-"
    text = str(symbol).strip()
    if text in _UNITS:
        return text
    return _CONVERT_ALIASES.get(text, _CONVERT_ALIASES.get(text.lower(), text))


#: pint-Dimensionsname -> Index in unserem ``(L, M, T, Θ, A)``-Vektor. Achsen außerhalb
#: (Strom/Stoffmenge/Lichtstärke) sind nicht darstellbar; der Winkel ist in pint
#: dimensionslos (dafür die kuratierten rad/deg/gon nutzen).
_PINT_AXIS = {"[length]": 0, "[mass]": 1, "[time]": 2, "[temperature]": 3}


def _pint_dimvector(dimensionality):
    """pint-``dimensionality`` (Mapping Name->Exponent) -> 5-Achsen-Tupel, oder ``None``.

    ``None``, sobald eine Achse außerhalb ``(L, M, T, Θ, A)`` mit Exponent ≠ 0 auftaucht
    (z. B. elektrischer Strom) – solche Einheiten kann unser Modell nicht darstellen.
    """
    vec = [0, 0, 0, 0, 0]
    for name, exp in dimensionality.items():
        idx = _PINT_AXIS.get(name)
        if idx is None:
            return None
        vec[idx] = int(exp) if float(exp).is_integer() else exp
    return tuple(vec)


def _pint_entry(symbol):
    """``(dimvektor, factor, offset)`` einer **nicht kuratierten** Einheit via pint.

    ``None``, wenn pint fehlt, das Symbol nicht parsebar ist oder seine Dimension
    außerhalb der fünf Achsen liegt. ``factor`` überführt in die SI-kohärente Einheit
    (pints Basiseinheiten sind m/kg/s/K – deckungsgleich mit der kuratierten Tabelle);
    affine Einheiten (nur Temperatur, z. B. ``degF``) liefern zusätzlich den Offset.
    """
    if _pint is None:
        return None
    try:
        unit = _pint.Unit(str(symbol).strip())
    except Exception:
        return None
    dim = _pint_dimvector(unit.dimensionality)
    if dim is None:
        return None
    try:
        factor = float(_pint.Quantity(1.0, unit).to_base_units().magnitude)
        offset = 0.0
    except _pint.OffsetUnitCalculusError:
        # affine Einheit: zwei Stützpunkte in Kelvin -> (Steigung, Offset)
        k0 = float(_pint.Quantity(0.0, unit).to("kelvin").magnitude)
        k1 = float(_pint.Quantity(1.0, unit).to("kelvin").magnitude)
        factor, offset = k1 - k0, k0
    return dim, factor, offset


def _lookup(symbol):
    """``(dim, factor, offset)`` einer Einheit – erst kuratierte Tabelle, dann pint.

    Die kuratierte Tabelle hat **Vorrang** (feste Faktoren, eigene Winkel-Achse);
    das optionale pint füllt nur Lücken (imperiale/abgeleitete Einheiten außerhalb der
    Tabelle). Ohne pint bleibt das Verhalten unverändert (``None`` für Unbekanntes).
    """
    entry = _UNITS.get(_norm_convert(symbol))
    if entry is not None:
        return entry
    return _pint_entry(symbol)


def dimension_of(symbol):
    """Dimensionsvektor ``(L, M, T, Θ, A)`` einer Einheit als Tupel, oder ``None``.

    :param symbol: Einheiten-Symbol (z. B. ``"MPa"``).
    :return: das Dimvektor-Tupel, oder ``None`` bei unbekannter Einheit.
    """
    entry = _lookup(symbol)
    return entry[0] if entry else None


def quantity_of(symbol):
    """Physikalische Größe einer Einheit (``"force"``/``"length"``/…) oder ``None``.

    Komfort-Name, aus dem Dimensionsvektor abgeleitet; dimensionslose Einheiten
    (``"-"``/``""``/``"%"``) liefern ``None``.

    :param symbol: Einheiten-Symbol (z. B. ``"kN"``).
    :return: Name der Größe, oder ``None``.
    """
    dim = dimension_of(symbol)
    return _QUANTITY_BY_DIM.get(dim) if dim is not None else None


def _entry(symbol, role):
    """Tabellen-Eintrag für ``symbol`` holen oder mit klarer Meldung scheitern."""
    entry = _lookup(symbol)
    if entry is None:
        raise UnitConversionError(f"unknown {role} unit {symbol!r}")
    return entry


def convert(value, from_unit, to_unit):
    """Rechne ``value`` von ``from_unit`` in ``to_unit`` um.

    Funktioniert für Skalare, Listen/Tupel, NumPy-Arrays und pandas-Series (alle
    elementweise). Beide Einheiten müssen dieselbe **Dimension** haben.

    :param value: Zahl(en) in ``from_unit``.
    :param from_unit: Quell-Einheit (z. B. ``"N"``).
    :param to_unit: Ziel-Einheit (z. B. ``"kN"``).
    :return: der umgerechnete Wert (gleiche Containerform wie ``value``; Listen/
      Tupel werden als Liste zurückgegeben).
    :raises UnitConversionError: bei unbekannter Einheit oder inkompatibler Dimension.
    """
    df, ff, fo = _entry(from_unit, "source")
    dt, tf, to = _entry(to_unit, "target")
    if df != dt:
        raise UnitConversionError(
            f"incompatible units: {from_unit!r} -> {to_unit!r} (different dimension)")
    # si = wert*ff + fo ; ziel = (si - to) / tf
    if isinstance(value, (list, tuple)):
        return [(v * ff + fo - to) / tf for v in value]
    return (value * ff + fo - to) / tf


def convert_factor(from_unit, to_unit):
    """Reiner Skalierungsfaktor ``from_unit`` → ``to_unit`` (nur Offset-freie Einheiten).

    Praktisch, um eine ganze Spalte/Reihe mit *einem* Faktor zu multiplizieren.

    :raises UnitConversionError: bei unbekannten/inkompatiblen Einheiten oder wenn
      eine der Einheiten einen Offset trägt (z. B. ``degC`` – dann ``convert`` nutzen).
    """
    df, ff, fo = _entry(from_unit, "source")
    dt, tf, to = _entry(to_unit, "target")
    if df != dt:
        raise UnitConversionError(
            f"incompatible units: {from_unit!r} -> {to_unit!r} (different dimension)")
    if fo or to:
        raise UnitConversionError(
            f"offset units need convert(): {from_unit!r} -> {to_unit!r}")
    return ff / tf


def _solve_linear(rows, rhs):
    """Löse ``rows @ c = rhs`` exakt über ``Fraction`` (Gauß-Elimination).

    :param rows: Liste von Gleichungen (je eine Liste von Koeffizienten, Länge ``n_unk``).
    :param rhs: rechte Seite (Länge ``n_eq``).
    :return: partikuläre Lösung (freie Variablen ``0``) als Liste ``Fraction``, oder
      ``None``, wenn das System keine Lösung hat.
    """
    n_eq = len(rows)
    n_unk = len(rows[0])
    aug = [[Fraction(x) for x in rows[r]] + [Fraction(rhs[r])] for r in range(n_eq)]
    prow = 0
    pivots = []
    for col in range(n_unk):
        sel = next((r for r in range(prow, n_eq) if aug[r][col] != 0), None)
        if sel is None:
            continue
        aug[prow], aug[sel] = aug[sel], aug[prow]
        pv = aug[prow][col]
        aug[prow] = [x / pv for x in aug[prow]]
        for r in range(n_eq):
            if r != prow and aug[r][col] != 0:
                f = aug[r][col]
                aug[r] = [a - f * b for a, b in zip(aug[r], aug[prow])]
        pivots.append((col, prow))
        prow += 1
    for r in range(prow, n_eq):
        if aug[r][n_unk] != 0:
            return None
    coeffs = [Fraction(0)] * n_unk
    for col, row in pivots:
        coeffs[col] = aug[row][n_unk]
    return coeffs


def _solve_over_basis(basis_vecs, target):
    """Koeffizienten ``c`` mit ``Σ c_j · basis_vecs[j] = target`` (oder ``None``)."""
    ndim = len(_DIM_NAMES)
    rows = [[v[d] for v in basis_vecs] for d in range(ndim)]
    if not basis_vecs:
        rows = [[] for _ in range(ndim)]
    return _solve_linear(rows, [target[d] for d in range(ndim)])


def _factor_from(basis, coeffs):
    """System-Faktor ``Π base_factor ** coeff`` – exakt über ``Fraction`` bei ganzzahligen
    Exponenten (vermeidet ``log``/``exp``-Drift), sonst float für rationale Exponenten."""
    frac = Fraction(1)
    fval = 1.0
    for c, b in zip(coeffs, basis):
        if c.denominator == 1:
            frac *= Fraction(b[1]).limit_denominator(10 ** 12) ** c.numerator
        else:
            fval *= b[1] ** float(c)
    return float(frac) * fval


def _canonical(dim, factor):
    """Bekanntes Vorzugs-Symbol mit exakt ``(dim, factor)`` (offset-frei), sonst ``None``."""
    for sym in _CANON_SYMBOLS:
        d, f, off = _UNITS[sym]
        if off == 0.0 and d == dim and math.isclose(f, factor, rel_tol=1e-9):
            return sym
    return None


def _compose(symbols, coeffs):
    """Komponiere ein Einheiten-Label aus Basis-Symbolen und Exponenten ``coeffs``."""
    num, den = [], []
    for sym, c in zip(symbols, coeffs):
        if c == 0:
            continue
        exp = abs(c)
        term = sym if exp == 1 else f"{sym}^{exp}"
        (num if c > 0 else den).append(term)
    numerator = "*".join(num) if num else "1"
    return numerator + "/" + "/".join(den) if den else numerator


class UnitSystem:
    """Konsistentes Einheitensystem über Dimensions-Algebra (RFC 0006).

    Aus den **Basis-Einheiten** (z. B. ``["kN", "mm", "ms"]``) werden die Skalen der
    Basis-Dimensionen gelöst, sodass **jede** abgeleitete Einheit hergeleitet werden
    kann (Spannung → ``GPa``, Energie → ``J``, Geschwindigkeit → ``m/s`` …).
    :meth:`target_for`/:meth:`convert_value` liefern für eine gegebene Einheit die
    System-Einheit derselben Dimension – ideal, um einen ganzen
    :class:`~sdata.sclass.dataframe.DataFrame` in ein gemeinsames System umzurechnen.

    :param units: iterierbare Basis-Einheiten-Symbole. Redundante, *konsistente*
      Angaben sind erlaubt (z. B. zusätzlich ``"GPa"``); widersprüchliche nicht.
    :raises UnitConversionError: bei unbekannter Einheit, Offset-Einheit als Basis
      oder widersprüchlicher (inkonsistenter) Über­bestimmung.
    """

    def __init__(self, units):
        self.units = []
        self._basis = []   # Liste von (dimvec, log(factor), symbol) für die Basis
        for symbol in units:
            entry = _lookup(symbol)
            if entry is None:
                raise UnitConversionError(f"unknown unit in system: {symbol!r}")
            dim, factor, offset = entry
            if offset:
                raise UnitConversionError(
                    f"offset unit not allowed as system base: {symbol!r}")
            sym = str(symbol).strip()
            self.units.append(sym)
            coeffs = _solve_over_basis([b[0] for b in self._basis], dim)
            if coeffs is None:
                self._basis.append((dim, factor, sym))
            else:
                derived = _factor_from(self._basis, coeffs)
                if not math.isclose(derived, factor, rel_tol=1e-9, abs_tol=1e-12):
                    raise UnitConversionError(
                        f"inconsistent unit in system: {symbol!r}")

    def _resolve(self, dim):
        """``(factor, label)`` für einen Dimensionsvektor, oder ``None`` (nicht abgedeckt)."""
        if not any(dim):
            return None                       # dimensionslos: nicht anfassen
        coeffs = _solve_over_basis([b[0] for b in self._basis], dim)
        if coeffs is None:
            return None
        factor = _factor_from(self._basis, coeffs)
        label = _canonical(dim, factor) or _compose([b[2] for b in self._basis], coeffs)
        return factor, label

    def factor_for(self, dim):
        """Numerischer Faktor der System-Einheit für einen Dimensionsvektor (oder ``None``)."""
        res = self._resolve(tuple(dim))
        return res[0] if res else None

    def unit_for(self, quantity):
        """System-Einheiten-Symbol für eine Größe (``"force"``/``"pressure"``/…) oder ``None``."""
        dim = _DIM_BY_QUANTITY.get(quantity)
        if dim is None:
            return None
        res = self._resolve(dim)
        return res[1] if res else None

    def target_for(self, symbol):
        """System-Einheiten-Symbol derselben Dimension wie ``symbol`` – sonst ``None``.

        ``None`` heißt: die Einheit ist unbekannt/dimensionslos, oder ihre Dimension
        wird vom System nicht aufgespannt (die Spalte bleibt dann unverändert).
        """
        dim = dimension_of(symbol)
        if dim is None:
            return None
        res = self._resolve(dim)
        return res[1] if res else None

    def convert_value(self, value, from_unit):
        """``(umgerechneter Wert, Ziel-Label)`` für ``value`` in ``from_unit``.

        Rechnet in die System-Einheit derselben Dimension um (inkl. hergeleiteter
        Einheiten). Skalare, Listen/Tupel, NumPy-Arrays und pandas-Series.

        :return: Tupel ``(wert, label)``, oder ``None`` wenn ``from_unit`` unbekannt
          ist oder ihre Dimension nicht vom System abgedeckt wird.
        """
        entry = _lookup(from_unit)
        if entry is None:
            return None
        dim, factor_cur, offset_cur = entry
        res = self._resolve(dim)
        if res is None:
            return None
        sys_factor, label = res
        if isinstance(value, (list, tuple)):
            return [(v * factor_cur + offset_cur) / sys_factor for v in value], label
        return (value * factor_cur + offset_cur) / sys_factor, label

    def __eq__(self, other):
        return isinstance(other, UnitSystem) and self.units == other.units

    def __hash__(self):
        return hash(tuple(self.units))

    def __repr__(self):
        return f"UnitSystem({self.units!r})"
