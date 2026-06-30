# -*- coding: utf-8 -*-
"""Einheiten-Vokabular: kuratierte Abbildung Einheit → QUDT-IRI / UCUM-Code.

Reine-Python-Tabelle (keine Abhängigkeit). Optionales Extra ``[units]`` = pint
erweitert die Validierung auf beliebige parsebare Einheiten; ohne pint greift
die kuratierte Tabelle.
"""
__all__ = [
    "UNIT_MAP", "normalize_symbol", "qudt_iri", "ucum_code", "unit_node",
    "validate_unit", "has_pint",
    "UnitConversionError", "quantity_of", "convert", "convert_factor",
    "UnitSystem",
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
    "kg":   ("unit:KiloGM",  "kg"),
    "g":    ("unit:GM",      "g"),
    "%":    ("unit:PERCENT", "%"),
    "-":    (None,           "1"),     # dimensionslos
    "":     (None,           "1"),
}

#: Symbol-Aliasse -> kanonisches UNIT_MAP-Symbol
_ALIASES = {
    "°C": "degC", "celsius": "degC", "C": "degC",
    "µm": "mm", "um": "mm", "mpa": "MPa", "gpa": "GPa", "kn": "kN",
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

class UnitConversionError(ValueError):
    """Eine Einheit ist unbekannt oder die Größen sind inkompatibel (z. B. mm → kN)."""


#: Einheit -> (Größe, Faktor, Offset) für die Umrechnung in die SI-Basis der Größe:
#: ``si = wert * faktor + offset``. Reine Skalierung hat ``offset == 0``; nur
#: Temperatur trägt einen Offset. Zwei Einheiten sind genau dann ineinander
#: umrechenbar, wenn ihre *Größe* übereinstimmt. Die Tabelle deckt die im
#: Ingenieurkontext üblichen mechanischen Einheiten ab (für beliebige Einheiten
#: bliebe das optionale ``pint``-Backend – die Konvertierung bleibt jedoch bewusst
#: deterministisch auf dieser kuratierten Tabelle).
_CONVERT = {
    # Länge (SI: m)
    "km": ("length", 1e3, 0.0), "m": ("length", 1.0, 0.0),
    "dm": ("length", 1e-1, 0.0), "cm": ("length", 1e-2, 0.0),
    "mm": ("length", 1e-3, 0.0), "um": ("length", 1e-6, 0.0),
    "nm": ("length", 1e-9, 0.0),
    # Kraft (SI: N)
    "MN": ("force", 1e6, 0.0), "kN": ("force", 1e3, 0.0),
    "N": ("force", 1.0, 0.0), "mN": ("force", 1e-3, 0.0),
    # Zeit (SI: s)
    "h": ("time", 3600.0, 0.0), "min": ("time", 60.0, 0.0),
    "s": ("time", 1.0, 0.0), "ms": ("time", 1e-3, 0.0),
    "us": ("time", 1e-6, 0.0), "ns": ("time", 1e-9, 0.0),
    # Masse (SI: kg)
    "t": ("mass", 1e3, 0.0), "kg": ("mass", 1.0, 0.0),
    "g": ("mass", 1e-3, 0.0), "mg": ("mass", 1e-6, 0.0),
    # Druck / Spannung (SI: Pa)
    "GPa": ("pressure", 1e9, 0.0), "MPa": ("pressure", 1e6, 0.0),
    "kPa": ("pressure", 1e3, 0.0), "Pa": ("pressure", 1.0, 0.0),
    # Dehnrate (SI: 1/s)
    "1/s": ("strain_rate", 1.0, 0.0), "1/ms": ("strain_rate", 1e3, 0.0),
    # Temperatur (SI: K) – mit Offset
    "K": ("temperature", 1.0, 0.0), "degC": ("temperature", 1.0, 273.15),
}

#: Symbol-Aliasse speziell für die Konvertierung (verlustfrei, anders als die
#: lockeren Validierungs-Aliasse – z. B. ``µm`` ist hier Mikrometer, nicht ``mm``).
_CONVERT_ALIASES = {
    "µm": "um", "μm": "um", "µs": "us", "μs": "us",
    "°C": "degC", "celsius": "degC", "C": "degC",
    "sec": "s", "second": "s", "seconds": "s", "minute": "min", "hour": "h",
}


def _norm_convert(symbol):
    """Normalisiere ein Symbol auf einen Schlüssel der Konvertierungstabelle."""
    if symbol is None:
        return "-"
    text = str(symbol).strip()
    if text in _CONVERT:
        return text
    return _CONVERT_ALIASES.get(text, _CONVERT_ALIASES.get(text.lower(), text))


def quantity_of(symbol):
    """Physikalische Größe einer Einheit (``"force"``/``"length"``/…) oder ``None``.

    :param symbol: Einheiten-Symbol (z. B. ``"kN"``).
    :return: Name der Größe, oder ``None`` wenn die Einheit nicht in der
      Konvertierungstabelle steht (z. B. ``"-"`` oder eine unbekannte Einheit).
    """
    entry = _CONVERT.get(_norm_convert(symbol))
    return entry[0] if entry else None


def _entry(symbol, role):
    """Tabellen-Eintrag für ``symbol`` holen oder mit klarer Meldung scheitern."""
    entry = _CONVERT.get(_norm_convert(symbol))
    if entry is None:
        raise UnitConversionError(f"unknown {role} unit {symbol!r}")
    return entry


def convert(value, from_unit, to_unit):
    """Rechne ``value`` von ``from_unit`` in ``to_unit`` um.

    Funktioniert für Skalare, Listen/Tupel, NumPy-Arrays und pandas-Series (alle
    elementweise). Beide Einheiten müssen dieselbe physikalische Größe haben.

    :param value: Zahl(en) in ``from_unit``.
    :param from_unit: Quell-Einheit (z. B. ``"N"``).
    :param to_unit: Ziel-Einheit (z. B. ``"kN"``).
    :return: der umgerechnete Wert (gleiche Containerform wie ``value``; Listen/
      Tupel werden als Liste zurückgegeben).
    :raises UnitConversionError: bei unbekannter Einheit oder inkompatiblen Größen.
    """
    qf, ff, fo = _entry(from_unit, "source")
    qt, tf, to = _entry(to_unit, "target")
    if qf != qt:
        raise UnitConversionError(
            f"incompatible units: {from_unit!r} ({qf}) -> {to_unit!r} ({qt})")
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
    qf, ff, fo = _entry(from_unit, "source")
    qt, tf, to = _entry(to_unit, "target")
    if qf != qt:
        raise UnitConversionError(
            f"incompatible units: {from_unit!r} ({qf}) -> {to_unit!r} ({qt})")
    if fo or to:
        raise UnitConversionError(
            f"offset units need convert(): {from_unit!r} -> {to_unit!r}")
    return ff / tf


class UnitSystem:
    """Konsistentes Einheitensystem: je physikalischer Größe genau eine Einheit.

    Aus einer Liste von Einheiten (z. B. ``["kN", "mm", "ms"]``) wird eine
    Abbildung *Größe → Einheit* gebaut. :meth:`target_for` liefert die
    System-Einheit derselben Größe wie eine gegebene Einheit – ideal, um einen
    ganzen :class:`~sdata.sclass.dataframe.DataFrame` in ein gemeinsames System
    umzurechnen.

    :param units: iterierbare Einheiten-Symbole; jede muss in der
      Konvertierungstabelle bekannt sein. Bei mehreren Einheiten derselben Größe
      gewinnt die zuletzt genannte.
    :raises UnitConversionError: wenn eine Einheit unbekannt ist.
    """

    def __init__(self, units):
        self.units = []
        self.by_quantity = {}
        for symbol in units:
            quantity = quantity_of(symbol)
            if quantity is None:
                raise UnitConversionError(f"unknown unit in system: {symbol!r}")
            sym = str(symbol).strip()
            self.units.append(sym)
            self.by_quantity[quantity] = sym

    def unit_for(self, quantity):
        """System-Einheit für eine Größe (``"force"`` …) oder ``None``."""
        return self.by_quantity.get(quantity)

    def target_for(self, symbol):
        """System-Einheit derselben Größe wie ``symbol`` – sonst ``None``.

        ``None`` heißt: die Einheit ist unbekannt/dimensionslos oder ihre Größe
        kommt im System nicht vor (die Spalte bleibt dann unverändert).
        """
        return self.by_quantity.get(quantity_of(symbol))

    def __repr__(self):
        return f"UnitSystem({self.units!r})"
