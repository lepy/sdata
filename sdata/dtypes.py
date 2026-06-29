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
  zusätzlich ``bytes`` (base64), ``json`` (dict/list), ``uri``, ``date``, ``time``,
  ``duration`` (ISO 8601 / ``timedelta``), ``decimal`` (exakt), ``complex``,
  ``floatlist`` (typisierte Float-Liste) sowie ``langstring`` (sprach-getaggt,
  ``rdf:langString``). ``complex``/``floatlist`` haben keinen Standard-XSD-Typ und
  nutzen eigene Datentyp-CURIEs (``sdata:complex`` / ``sdata:floatlist``);
  ``langstring`` wird in JSON-LD über ``@language`` ausgedrückt.
"""
import base64
import binascii
import datetime
import json as _json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import numpy as np
import pandas as pd

from sdata.timestamp import TimeStamp

__all__ = [
    "DtypeError", "DtypeSpec", "LangString", "register", "get", "names", "resolve",
    "coerce", "xsd_map", "json_default", "XSD", "DTYPES", "DTYPES_INV",
]


class DtypeError(ValueError):
    """Wert kann nicht in den Ziel-dtype überführt werden (v.a. im strict-Modus)."""


class LangString:
    """Ein sprach-getaggter String (``rdf:langString``): ``text`` + BCP-47 ``lang``.

    In JSON-LD als ``{"@value": text, "@language": lang}`` repräsentiert (nicht über
    ``@type``). Die kompakte Textform ist ``"text@lang"`` (z. B. ``"Hallo@de"``).
    """

    __slots__ = ("text", "lang")

    def __init__(self, text, lang=""):
        self.text = str(text)
        self.lang = str(lang or "")

    def __eq__(self, other):
        return (isinstance(other, LangString)
                and self.text == other.text and self.lang == other.lang)

    def __hash__(self):
        return hash((self.text, self.lang))

    def __str__(self):
        return "{}@{}".format(self.text, self.lang) if self.lang else self.text

    def __repr__(self):
        return "LangString({!r}, {!r})".format(self.text, self.lang)


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


def _c_date(value, strict):
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):     # vor date prüfen (Subklasse!)
        return value.date()
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value))
    except (ValueError, TypeError) as exp:
        raise DtypeError("date: {!r} (ISO 8601 'YYYY-MM-DD')".format(value)) from exp


def _c_time(value, strict):
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value.timetz()
    if isinstance(value, datetime.time):
        return value
    try:
        return datetime.time.fromisoformat(str(value))
    except (ValueError, TypeError) as exp:
        raise DtypeError("time: {!r} (ISO 8601 'HH:MM:SS')".format(value)) from exp


#: ISO-8601-Dauer ohne Jahre/Monate (nicht als ``timedelta`` darstellbar).
_ISO_DURATION = re.compile(
    r"^(?P<sign>-?)P"
    r"(?:(?P<weeks>\d+(?:\.\d+)?)W)?"
    r"(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?"
    r")?$"
)


def _c_duration(value, strict):
    if value is None or value == "":
        return None
    if isinstance(value, datetime.timedelta):
        return value
    if isinstance(value, bool):                  # bool ist int-Subklasse → ablehnen
        raise DtypeError("duration: {!r}".format(value))
    if isinstance(value, (int, float)):
        return datetime.timedelta(seconds=value)  # Zahl = Sekunden
    match = _ISO_DURATION.match(str(value).strip())
    parts = ({k: float(v) for k, v in match.groupdict().items()
              if v is not None and k != "sign"} if match else None)
    if not parts:
        raise DtypeError("duration: {!r} (ISO 8601 like 'PT1H30M'; years/months "
                         "are not representable as a timedelta)".format(value))
    td = datetime.timedelta(
        weeks=parts.get("weeks", 0), days=parts.get("days", 0),
        hours=parts.get("hours", 0), minutes=parts.get("minutes", 0),
        seconds=parts.get("seconds", 0))
    return -td if match.group("sign") == "-" else td


def _c_decimal(value, strict):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):                  # bool ist kein Dezimalwert
        raise DtypeError("decimal: {!r}".format(value))
    try:
        return Decimal(str(value))               # via str: keine Float-Binär-Artefakte
    except (InvalidOperation, ValueError, TypeError) as exp:
        raise DtypeError("decimal: {!r}".format(value)) from exp


def _c_complex(value, strict):
    if value is None or value == "":
        return None
    if isinstance(value, complex):
        return value
    if isinstance(value, bool):                  # bool ist kein komplexer Wert
        raise DtypeError("complex: {!r}".format(value))
    try:
        return complex(value.strip()) if isinstance(value, str) else complex(value)
    except (ValueError, TypeError) as exp:
        raise DtypeError("complex: {!r}".format(value)) from exp


def _c_floatlist(value, strict):
    if value is None:
        return []
    if isinstance(value, str):                    # "" / "1,2,3" (Leer-Check skalar-sicher)
        items = [s for s in (p.strip() for p in value.split(",")) if s]
    elif isinstance(value, (list, tuple)):
        items = value
    elif hasattr(value, "tolist"):               # numpy-Array & Co. -> Liste
        items = value.tolist()
    else:
        raise DtypeError("floatlist: {!r}".format(value))
    try:
        return [float(x) for x in items]
    except (ValueError, TypeError) as exp:
        raise DtypeError("floatlist: {!r}".format(value)) from exp


#: Sprach-Tag am Stringende (BCP-47-artig) zum Zerlegen von ``"text@lang"``.
_LANG_TAG = re.compile(r"^(.*)@([A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*)$", re.DOTALL)


def _c_langstring(value, strict):
    if value is None:
        return None
    if isinstance(value, LangString):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return LangString(value[0], value[1])    # (text, lang) explizit & eindeutig
    if isinstance(value, dict):
        return LangString(value.get("@value", value.get("text", "")),
                          value.get("@language", value.get("lang", "")))
    text = str(value)
    if text == "":
        return None
    match = _LANG_TAG.match(text)                 # "text@lang" -> (text, lang)
    return LangString(match.group(1), match.group(2)) if match else LangString(text, "")


# --- JSON-Serialisierung je dtype -------------------------------------------
def _ts_to_json(value):
    return str(value.utc) if isinstance(value, TimeStamp) else value


def _bytes_to_json(value):
    return base64.b64encode(value).decode("ascii") if isinstance(value, bytes) else value


def _date_to_json(value):
    return value.isoformat() if isinstance(value, datetime.date) else value


def _time_to_json(value):
    return value.isoformat() if isinstance(value, datetime.time) else value


def _duration_to_json(value):
    """``timedelta`` → kanonische ISO-8601-Dauer (``PT0S`` für null)."""
    if not isinstance(value, datetime.timedelta):
        return value
    total = value.total_seconds()
    sign = "-" if total < 0 else ""
    total = abs(total)
    days = int(total // 86400)
    rem = total - days * 86400
    hours = int(rem // 3600)
    rem -= hours * 3600
    minutes = int(rem // 60)
    seconds = rem - minutes * 60
    date_part = "{:d}D".format(days) if days else ""
    time_part = ""
    if hours:
        time_part += "{:d}H".format(hours)
    if minutes:
        time_part += "{:d}M".format(minutes)
    if seconds or not (date_part or time_part):
        time_part += "{:g}S".format(seconds)
    return sign + "P" + date_part + ("T" + time_part if time_part else "")


def _decimal_to_json(value):
    return str(value) if isinstance(value, Decimal) else value


def _complex_to_json(value):
    return str(value) if isinstance(value, complex) else value


def _langstring_to_json(value):
    return str(value) if isinstance(value, LangString) else value


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
    DtypeSpec("date", datetime.date, _c_date, "xsd:date", _date_to_json),
    DtypeSpec("time", datetime.time, _c_time, "xsd:time", _time_to_json),
    DtypeSpec("duration", datetime.timedelta, _c_duration, "xsd:duration", _duration_to_json),
    DtypeSpec("decimal", Decimal, _c_decimal, "xsd:decimal", _decimal_to_json),
    # komplexe Zahlen & typisierte Float-Listen haben keinen Standard-XSD-Typ
    # -> eigener Datentyp-CURIE in der sdata-Namespace (verlustfreier JSON-LD-Roundtrip).
    DtypeSpec("complex", complex, _c_complex, "sdata:complex", _complex_to_json),
    DtypeSpec("floatlist", list, _c_floatlist, "sdata:floatlist"),
    # sprach-getaggter String: JSON-LD nutzt @language (nicht @type), siehe semantic.py
    DtypeSpec("langstring", LangString, _c_langstring, "rdf:langString", _langstring_to_json),
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
    datetime.date: "date", datetime.time: "time",
    datetime.timedelta: "duration", Decimal: "decimal",
    complex: "complex", LangString: "langstring",
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
    if token in ("list[float]", "float[]"):      # Alias -> floatlist (vor 'list'/'float')
        return "floatlist"
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
    """``default=`` für ``json.dumps``: serialisiert die nicht-nativen dtype-Werte
    (TimeStamp/bytes/Decimal/timedelta/date/time) JSON-sicher."""
    if isinstance(obj, TimeStamp):
        return str(obj.utc)
    if isinstance(obj, (bytes, bytearray)):
        return base64.b64encode(bytes(obj)).decode("ascii")
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, complex):
        return str(obj)
    if isinstance(obj, LangString):
        return str(obj)
    if isinstance(obj, datetime.timedelta):
        return _duration_to_json(obj)
    if isinstance(obj, datetime.date):           # fängt auch datetime.datetime
        return obj.isoformat()
    if isinstance(obj, datetime.time):
        return obj.isoformat()
    raise TypeError("not JSON serializable: {!r}".format(type(obj)))
