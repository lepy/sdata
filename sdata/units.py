# -*- coding: utf-8 -*-
"""Einheiten-Vokabular: kuratierte Abbildung Einheit → QUDT-IRI / UCUM-Code.

Reine-Python-Tabelle (keine Abhängigkeit). Optionales Extra ``[units]`` = pint
erweitert die Validierung auf beliebige parsebare Einheiten; ohne pint greift
die kuratierte Tabelle.
"""
__all__ = [
    "UNIT_MAP", "normalize_symbol", "qudt_iri", "ucum_code", "unit_node",
    "validate_unit", "has_pint",
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
