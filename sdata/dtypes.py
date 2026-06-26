# -*- coding: utf-8 -*-
"""Reine-stdlib dtype-Registry für :class:`sdata.metadata.Attribute`.

Single Source of Truth für Wert-Coercion, JSON-(De)Serialisierung, die zu einem
dtype gehörige Python-Klasse und das XSD-Typ-Mapping (das die JSON-LD-Schicht
konsumiert).

Designziele:

* **Rückwärtskompatibel** – im *lenienten* Default-Modus (``strict=False``)
  verhält sich die Coercion byte-genau wie der bisherige
  ``Attribute._set_value``: leere/falsy Werte werden je dtype zu ``np.nan`` /
  ``None`` / ``""`` / ``False``; nicht-castbare Werte lösen ``DtypeError`` aus
  (vom Setter geloggt, Wert bleibt unverändert).
* **Strikt opt-in** – ``strict=True`` wirft ``DtypeError`` statt still zu
  degradieren.
* **Erweiterbar** – neben den 6 Alt-dtypes (str/int/float/bool/timestamp/list)
  zusätzlich ``bytes`` (base64), ``json`` (dict/list) und ``uri``.
"""
import base64
import binascii
import datetime
import json as _json
from urllib.parse import urlsplit

import numpy as np
import pandas as pd

from sdata.timestamp import TimeStamp

__all__ = [
    "DtypeError", "DtypeSpec", "register", "get", "names", "resolve",
    "coerce", "xsd_map", "json_default", "XSD", "DTYPES", "DTYPES_INV",
]


class DtypeError(ValueError):
    """Wert kann nicht in den Ziel-dtype überführt werden (v.a. im strict-Modus)."""


def _isna(value):
    """``pd.isna`` skalar; Array-Eingaben (Liste o.ä.) gelten als nicht-NA."""
    result = pd.isna(value)
    return bool(result) if isinstance(result, (bool, np.bool_)) else False


# --- Coercion-Funktionen (value, strict) -> python value --------------------
def _c_str(value, strict):
    if value == "":
        return ""
    if not value:
        return None
    return str(value)


def _c_int(value, strict):
    if not value:                 # 0/None/""/False/[]  -> nan (Altverhalten)
        return np.nan
    if _isna(value):
        return np.nan
    try:
        return int(value)
    except (ValueError, TypeError) as exp:
        raise DtypeError("int: {!r}".format(value)) from exp


def _c_float(value, strict):
    if not value:
        return np.nan
    if _isna(value):
        return np.nan
    try:
        return float(value)
    except (ValueError, TypeError) as exp:
        raise DtypeError("float: {!r}".format(value)) from exp


# leniente bool-Abbildung = exakt das bisherige Verhalten
_LEGACY_BOOL_TRUE = [1, "1", "true", "True"]
# strenge, case-insensitive Erweiterung
_STRICT_TRUE = {"1", "true", "yes", "y", "on", "t", "wahr"}
_STRICT_FALSE = {"0", "false", "no", "n", "off", "f", "falsch", ""}


def _c_bool(value, strict):
    if isinstance(value, bool):
        return value
    if not strict:
        # Altverhalten: True genau dann, wenn value in {1,"1","true","True"}
        return value in _LEGACY_BOOL_TRUE
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    token = str(value).strip().lower()
    if token in _STRICT_TRUE:
        return True
    if token in _STRICT_FALSE:
        return False
    raise DtypeError("bool: {!r}".format(value))


def _c_timestamp(value, strict):
    if value is None or value == "":
        return None
    if isinstance(value, TimeStamp):
        return value
    if isinstance(value, datetime.datetime):
        return TimeStamp(value.isoformat())
    try:
        return TimeStamp(str(value))
    except Exception as exp:                       # ParseError u.ä.
        raise DtypeError("timestamp: {!r}".format(value)) from exp


def _c_list(value, strict):
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    raise DtypeError("list[str]: {!r}".format(value))


def _c_bytes(value, strict):
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    if isinstance(value, str):
        try:
            return base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            return value.encode("utf-8")
    raise DtypeError("bytes: {!r}".format(value))


def _c_json(value, strict):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return _json.loads(value)
        except (ValueError, TypeError) as exp:
            raise DtypeError("json: {!r}".format(value)) from exp
    raise DtypeError("json: {!r}".format(value))


def _c_uri(value, strict):
    if value is None or value == "":
        return None if value is None else ""
    text = str(value).strip()
    if strict and not (urlsplit(text).scheme or urlsplit(text).path):
        raise DtypeError("uri: {!r}".format(value))
    return text


# --- JSON-Serialisierung je dtype -------------------------------------------
def _ts_to_json(value):
    return str(value.utc) if isinstance(value, TimeStamp) else value


def _bytes_to_json(value):
    return base64.b64encode(value).decode("ascii") if isinstance(value, bytes) else value


class DtypeSpec:
    """Beschreibt einen dtype: Coercion, JSON-Repräsentation, Klasse, XSD-Typ."""

    def __init__(self, name, pytype, coerce, xsd, to_json=None):
        self.name = name
        self.pytype = pytype
        self._coerce = coerce
        self.xsd = xsd
        self._to_json = to_json or (lambda v: v)

    def coerce(self, value, strict=False):
        return self._coerce(value, strict)

    def to_json(self, value):
        return self._to_json(value)


_REGISTRY = {}


def register(spec):
    _REGISTRY[spec.name] = spec


for _spec in [
    DtypeSpec("str", str, _c_str, "xsd:string"),
    DtypeSpec("int", int, _c_int, "xsd:integer"),
    DtypeSpec("float", float, _c_float, "xsd:double"),
    DtypeSpec("bool", bool, _c_bool, "xsd:boolean"),
    DtypeSpec("timestamp", datetime.datetime, _c_timestamp, "xsd:dateTime", _ts_to_json),
    DtypeSpec("list", list, _c_list, "xsd:string"),
    DtypeSpec("bytes", bytes, _c_bytes, "xsd:base64Binary", _bytes_to_json),
    DtypeSpec("json", dict, _c_json, "xsd:string"),
    DtypeSpec("uri", str, _c_uri, "xsd:anyURI"),
]:
    register(_spec)


def get(name):
    """DtypeSpec zum kanonischen Namen oder ``None``."""
    return _REGISTRY.get(name)


def names():
    """Liste aller kanonischen dtype-Namen."""
    return list(_REGISTRY.keys())


# Kompat-Aliasse (entsprechen exakt den bisherigen Attribute.DTYPES/_INV
# für die 6 Alt-dtypes; neue dtypes hängen hinten an, str bleibt -> 'str').
DTYPES = {name: spec.pytype for name, spec in _REGISTRY.items()}
DTYPES_INV = {
    float: "float", int: "int", str: "str",
    datetime.datetime: "timestamp", bool: "bool", list: "list",
    bytes: "bytes", dict: "json",
}
XSD = {name: spec.xsd for name, spec in _REGISTRY.items()}


def xsd_map():
    """Kopie der ``{dtype_name: xsd_iri}``-Tabelle (für die JSON-LD-Schicht)."""
    return dict(XSD)


def resolve(dtype):
    """Normalisiere einen dtype-Input (String ODER Klasse) auf einen Registry-Key.

    Spiegelt die bisherigen ``_set_dtype``-Regeln: Klassen via ``DTYPES_INV``,
    ``'float64'``/``'int32'`` -> ``'float'``/``'int'``, Unbekanntes -> ``'str'``.
    ``None`` -> ``None`` (kein dtype-Wechsel).
    """
    if dtype is None:
        return None
    if isinstance(dtype, type):
        return DTYPES_INV.get(dtype, "str")
    token = str(dtype).strip().lower()
    if token in _REGISTRY:
        return token
    if "float" in token:
        return "float"
    if "int" in token:
        return "int"
    if "bool" in token:
        return "bool"
    if "list" in token:
        return "list"
    return "str"


def coerce(value, dtype, strict=False):
    """Überführe ``value`` in ``dtype`` (String oder Klasse)."""
    spec = _REGISTRY[resolve(dtype) or "str"]
    return spec.coerce(value, strict=strict)


def json_default(obj):
    """``default=`` für ``json.dumps``: serialisiert TimeStamp/bytes JSON-sicher."""
    if isinstance(obj, TimeStamp):
        return str(obj.utc)
    if isinstance(obj, (bytes, bytearray)):
        return base64.b64encode(bytes(obj)).decode("ascii")
    raise TypeError("not JSON serializable: {!r}".format(type(obj)))
