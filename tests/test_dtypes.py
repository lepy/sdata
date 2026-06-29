# -*- coding: utf-8 -*-
"""Tests für die dtype-Registry (sdata/dtypes.py) und die Attribute-Anbindung."""
import datetime

import numpy as np
import pytest

from sdata import dtypes
from sdata.dtypes import DtypeError
from sdata.metadata import Attribute, Metadata
from sdata.timestamp import TimeStamp


# --- resolve ----------------------------------------------------------------
def test_resolve_class_string_and_unknown():
    assert dtypes.resolve(float) == "float"
    assert dtypes.resolve(int) == "int"
    assert dtypes.resolve(datetime.datetime) == "timestamp"
    assert dtypes.resolve(bytes) == "bytes"
    assert dtypes.resolve(dict) == "json"
    assert dtypes.resolve("float64") == "float"
    assert dtypes.resolve("int32") == "int"
    assert dtypes.resolve("boolean") == "bool"
    assert dtypes.resolve("mylist") == "list"
    assert dtypes.resolve("timestamp") == "timestamp"
    assert dtypes.resolve("banana") == "str"
    assert dtypes.resolve(None) is None


def test_xsd_map_and_names():
    xsd = dtypes.xsd_map()
    for name, iri in {
        "str": "xsd:string", "int": "xsd:integer", "float": "xsd:double",
        "bool": "xsd:boolean", "timestamp": "xsd:dateTime",
        "bytes": "xsd:base64Binary", "uri": "xsd:anyURI",
    }.items():
        assert xsd[name] == iri
    assert set(["str", "int", "float", "bool", "timestamp", "list",
                "bytes", "json", "uri"]).issubset(set(dtypes.names()))
    assert dtypes.get("nope") is None


# --- str / int / float (lenient = Altverhalten) -----------------------------
def test_str_coercion():
    assert Attribute("a", "", dtype="str").value == ""
    assert Attribute("a", None, dtype="str").value is None
    assert Attribute("a", 0, dtype="str").value is None
    assert Attribute("a", "x", dtype="str").value == "x"
    assert Attribute("a", float("nan"), dtype="str").value == "nan"


def test_int_float_empty_and_cast():
    assert np.isnan(Attribute("a", 0, dtype="int").value)
    assert np.isnan(Attribute("a", None, dtype="int").value)
    assert np.isnan(Attribute("a", float("nan"), dtype="int").value)    # truthy NaN -> _isna
    assert np.isnan(Attribute("a", 0.0, dtype="float").value)           # falsy float
    assert np.isnan(Attribute("a", float("nan"), dtype="float").value)
    assert Attribute("a", "5", dtype="int").value == 5
    assert Attribute("a", "1.5", dtype="float").value == 1.5


def test_int_uncastable_lenient_vs_strict():
    # lenient: Wert bleibt unverändert (None aus init), nur geloggt
    assert Attribute("a", "abc", dtype="int").value is None
    # list -> int trifft _isna(array)-Zweig, dann DtypeError (lenient -> None)
    assert Attribute("a", [1, 2], dtype="int").value is None
    with pytest.raises(DtypeError):
        Attribute("a", "abc", dtype="int", strict=True)
    with pytest.raises(DtypeError):
        Attribute("a", "x", dtype="float", strict=True)


# --- bool -------------------------------------------------------------------
@pytest.mark.parametrize("value,expected", [
    (True, True), (1, True), ("1", True), ("true", True), ("True", True),
    (False, False), (0, False), ("0", False), ("false", False), ("x", False),
])
def test_bool_lenient_matrix(value, expected):
    assert Attribute("b", value, dtype="bool").value is expected


@pytest.mark.parametrize("value,expected", [
    ("yes", True), ("on", True), ("t", True), (1, True),
    ("no", False), ("off", False), ("", False), (0, False),
])
def test_bool_strict_recognized(value, expected):
    assert Attribute("b", value, dtype="bool", strict=True).value is expected


def test_bool_strict_ambiguous_raises():
    with pytest.raises(DtypeError):
        Attribute("b", "maybe", dtype="bool", strict=True)
    with pytest.raises(DtypeError):
        Attribute("b", 2, dtype="bool", strict=True)


# --- timestamp --------------------------------------------------------------
def test_timestamp_coercion():
    attr = Attribute("create", "2017-04-27", dtype="timestamp")
    assert isinstance(attr.value, TimeStamp)
    assert attr.value.utc == "2017-04-27T00:00:00+00:00"
    assert Attribute("t", None, dtype="timestamp").value is None
    # datetime-Eingang
    dt = datetime.datetime(2020, 1, 2, 3, 4, 5)
    assert isinstance(Attribute("t", dt, dtype="timestamp").value, TimeStamp)
    # idempotent
    ts = TimeStamp("2017-04-27")
    assert Attribute("t", ts, dtype="timestamp").value is ts


def test_timestamp_invalid():
    assert Attribute("t", "not-a-date", dtype="timestamp").value is None  # lenient
    with pytest.raises(DtypeError):
        Attribute("t", "not-a-date", dtype="timestamp", strict=True)


# --- list -------------------------------------------------------------------
def test_list_coercion():
    assert Attribute("l", None, dtype="list").value == []
    assert Attribute("l", "a, b ,c", dtype="list").value == ["a", "b", "c"]
    assert Attribute("l", [1, 2], dtype="list").value == ["1", "2"]
    with pytest.raises(DtypeError):
        Attribute("l", 5, dtype="list", strict=True)


# --- bytes / json / uri (neu) ----------------------------------------------
def test_bytes_dtype():
    assert Attribute("b", b"\x00\x01", dtype="bytes").value == b"\x00\x01"
    assert Attribute("b", "AAE=", dtype="bytes").value == b"\x00\x01"   # base64
    assert Attribute("b", "nothex!!", dtype="bytes").value == b"nothex!!"  # utf-8
    assert Attribute("b", bytearray(b"xy"), dtype="bytes").value == b"xy"
    assert Attribute("b", None, dtype="bytes").value is None
    with pytest.raises(DtypeError):
        Attribute("b", 5, dtype="bytes", strict=True)


def test_json_dtype():
    assert Attribute("j", {"a": 1}, dtype="json").value == {"a": 1}
    assert Attribute("j", '{"a": 1}', dtype="json").value == {"a": 1}
    assert Attribute("j", None, dtype="json").value is None
    with pytest.raises(DtypeError):
        Attribute("j", "{bad", dtype="json", strict=True)
    with pytest.raises(DtypeError):
        Attribute("j", 5, dtype="json", strict=True)


def test_uri_dtype():
    assert Attribute("u", "https://x.org/a", dtype="uri").value == "https://x.org/a"
    assert Attribute("u", None, dtype="uri").value is None
    assert Attribute("u", "", dtype="uri").value == ""
    assert Attribute("u", "rel/path", dtype="uri", strict=True).value == "rel/path"
    with pytest.raises(DtypeError):
        Attribute("u", "   ", dtype="uri", strict=True)


# --- date / time / duration / decimal (neu) --------------------------------
def test_date_dtype():
    assert Attribute("d", "2024-01-15", dtype="date").value == datetime.date(2024, 1, 15)
    assert Attribute("d", datetime.date(2024, 1, 15), dtype="date").value == datetime.date(2024, 1, 15)
    # datetime -> date (Subklasse korrekt zuerst behandelt)
    assert Attribute("d", datetime.datetime(2024, 1, 15, 9, 30),
                     dtype="date").value == datetime.date(2024, 1, 15)
    assert Attribute("d", None, dtype="date").value is None
    assert Attribute("d", "", dtype="date").value is None
    assert Attribute("d", "nope", dtype="date").value is None            # lenient
    with pytest.raises(DtypeError):
        Attribute("d", "nope", dtype="date", strict=True)


def test_time_dtype():
    assert Attribute("t", "14:30:00", dtype="time").value == datetime.time(14, 30)
    assert Attribute("t", datetime.time(14, 30), dtype="time").value == datetime.time(14, 30)
    assert Attribute("t", datetime.datetime(2024, 1, 15, 14, 30),
                     dtype="time").value == datetime.time(14, 30)
    assert Attribute("t", None, dtype="time").value is None
    assert Attribute("t", "25:99", dtype="time").value is None           # lenient
    with pytest.raises(DtypeError):
        Attribute("t", "25:99", dtype="time", strict=True)


def test_duration_dtype():
    td = datetime.timedelta
    assert Attribute("u", "PT1H30M", dtype="duration").value == td(hours=1, minutes=30)
    assert Attribute("u", "P2DT3H", dtype="duration").value == td(days=2, hours=3)
    assert Attribute("u", "P1W", dtype="duration").value == td(weeks=1)
    assert Attribute("u", "-PT5S", dtype="duration").value == td(seconds=-5)
    assert Attribute("u", 90, dtype="duration").value == td(seconds=90)   # Zahl = Sekunden
    assert Attribute("u", td(minutes=5), dtype="duration").value == td(minutes=5)
    assert Attribute("u", None, dtype="duration").value is None
    assert Attribute("u", True, dtype="duration").value is None          # bool abgelehnt (lenient)
    # ungültig / Jahre-Monate / keine Komponenten -> lenient None, strict raises
    for bad in ["P1Y", "P", "PT", "nope"]:
        assert Attribute("u", bad, dtype="duration").value is None
        with pytest.raises(DtypeError):
            Attribute("u", bad, dtype="duration", strict=True)
    with pytest.raises(DtypeError):
        Attribute("u", True, dtype="duration", strict=True)


def test_decimal_dtype():
    from decimal import Decimal
    assert Attribute("p", "0.1", dtype="decimal").value == Decimal("0.1")
    assert Attribute("p", 0.1, dtype="decimal").value == Decimal("0.1")   # via str -> exakt
    assert Attribute("p", 5, dtype="decimal").value == Decimal("5")
    assert Attribute("p", Decimal("3.14"), dtype="decimal").value == Decimal("3.14")
    assert Attribute("p", None, dtype="decimal").value is None
    assert Attribute("p", "", dtype="decimal").value is None
    assert Attribute("p", "abc", dtype="decimal").value is None          # lenient
    with pytest.raises(DtypeError):
        Attribute("p", "abc", dtype="decimal", strict=True)
    with pytest.raises(DtypeError):
        Attribute("p", True, dtype="decimal", strict=True)               # bool abgelehnt


def test_new_dtypes_resolve_and_xsd():
    from decimal import Decimal
    assert dtypes.resolve(datetime.date) == "date"
    assert dtypes.resolve(datetime.time) == "time"
    assert dtypes.resolve(datetime.timedelta) == "duration"
    assert dtypes.resolve(Decimal) == "decimal"
    assert dtypes.resolve(datetime.datetime) == "timestamp"   # date-Subklasse bleibt timestamp
    assert dtypes.resolve("date") == "date" and dtypes.resolve("decimal") == "decimal"
    xsd = dtypes.xsd_map()
    assert xsd["date"] == "xsd:date" and xsd["time"] == "xsd:time"
    assert xsd["duration"] == "xsd:duration" and xsd["decimal"] == "xsd:decimal"


def test_new_dtypes_to_json_and_default():
    from decimal import Decimal
    td = datetime.timedelta
    assert dtypes.get("date").to_json(datetime.date(2024, 1, 15)) == "2024-01-15"
    assert dtypes.get("time").to_json(datetime.time(14, 30)) == "14:30:00"
    assert dtypes.get("duration").to_json(td(hours=1, minutes=30)) == "PT1H30M"
    assert dtypes.get("duration").to_json(td(days=2)) == "P2D"
    assert dtypes.get("duration").to_json(td(seconds=-5)) == "-PT5S"
    assert dtypes.get("duration").to_json(td(0)) == "PT0S"
    assert dtypes.get("decimal").to_json(Decimal("3.140")) == "3.140"    # Präzision erhalten
    # passthrough (None / falscher Typ) je to_json
    assert dtypes.get("date").to_json(None) is None
    assert dtypes.get("time").to_json(None) is None
    assert dtypes.get("duration").to_json(None) is None
    assert dtypes.get("decimal").to_json(None) is None
    # json_default deckt die Roh-Objekte ab
    assert dtypes.json_default(Decimal("1.5")) == "1.5"
    assert dtypes.json_default(td(minutes=90)) == "PT1H30M"
    assert dtypes.json_default(datetime.date(2024, 1, 15)) == "2024-01-15"
    assert dtypes.json_default(datetime.time(9, 0)) == "09:00:00"


def test_new_dtypes_json_roundtrip():
    from decimal import Decimal
    m = Metadata()
    m.add("acquired_on", "2024-01-15", dtype="date")
    m.add("start_time", "09:30:00", dtype="time")
    m.add("test_duration", "PT2H", dtype="duration")
    m.add("price", "19.99", dtype="decimal")
    restored = Metadata.from_json(m.to_json())
    assert restored.get("acquired_on").value == datetime.date(2024, 1, 15)
    assert restored.get("start_time").value == datetime.time(9, 30)
    assert restored.get("test_duration").value == datetime.timedelta(hours=2)
    assert restored.get("price").value == Decimal("19.99")


def test_new_dtypes_jsonld_roundtrip():
    from decimal import Decimal
    from sdata import semantic
    m = Metadata(name="probe")
    m.add("acquired_on", "2024-01-15", dtype="date")
    m.add("price", "19.99", dtype="decimal")
    doc = semantic.to_jsonld(m)
    assert doc["sdata:acquired_on"]["@type"] == "xsd:date"
    assert doc["sdata:price"]["@type"] == "xsd:decimal"
    back = semantic.from_jsonld(doc)
    assert back.get("acquired_on").value == datetime.date(2024, 1, 15)
    assert back.get("price").value == Decimal("19.99")


# --- complex / floatlist (neu) ---------------------------------------------
def test_complex_dtype():
    assert Attribute("c", "1+2j", dtype="complex").value == complex(1, 2)
    assert Attribute("c", "(1+2j)", dtype="complex").value == complex(1, 2)   # mit Klammern
    assert Attribute("c", complex(3, -4), dtype="complex").value == complex(3, -4)
    assert Attribute("c", 5, dtype="complex").value == complex(5, 0)
    assert Attribute("c", 2.5, dtype="complex").value == complex(2.5, 0)
    assert Attribute("c", None, dtype="complex").value is None
    assert Attribute("c", "", dtype="complex").value is None
    assert Attribute("c", "nope", dtype="complex").value is None              # lenient
    with pytest.raises(DtypeError):
        Attribute("c", "nope", dtype="complex", strict=True)
    with pytest.raises(DtypeError):
        Attribute("c", True, dtype="complex", strict=True)                    # bool abgelehnt


def test_floatlist_dtype():
    import numpy as np
    assert Attribute("v", "1.0, 2.5, 3", dtype="floatlist").value == [1.0, 2.5, 3.0]
    assert Attribute("v", [1, 2, 3], dtype="floatlist").value == [1.0, 2.0, 3.0]
    assert Attribute("v", (1.5, 2.5), dtype="floatlist").value == [1.5, 2.5]
    assert Attribute("v", np.array([1, 2, 3]), dtype="floatlist").value == [1.0, 2.0, 3.0]
    assert Attribute("v", None, dtype="floatlist").value == []
    assert Attribute("v", "", dtype="floatlist").value == []
    # dtype-Alias "list[float]"
    assert Attribute("v", [1, 2], dtype="list[float]").value == [1.0, 2.0]
    # nicht-castbare Elemente / unzulässiger Typ -> lenient None (Wert unverändert), strict raises
    assert Attribute("v", ["a", "b"], dtype="floatlist").value is None
    assert Attribute("v", 5, dtype="floatlist").value is None
    with pytest.raises(DtypeError):
        Attribute("v", ["a"], dtype="floatlist", strict=True)     # nicht-castbares Element
    with pytest.raises(DtypeError):
        Attribute("v", 5, dtype="floatlist", strict=True)         # unzulässiger Typ


def test_complex_floatlist_resolve_xsd_json():
    assert dtypes.resolve(complex) == "complex"
    assert dtypes.resolve("complex") == "complex"
    assert dtypes.resolve("floatlist") == "floatlist"
    assert dtypes.resolve("list[float]") == "floatlist"
    assert dtypes.resolve("float[]") == "floatlist"
    xsd = dtypes.xsd_map()
    assert xsd["complex"] == "sdata:complex" and xsd["floatlist"] == "sdata:floatlist"
    # to_json / json_default
    assert dtypes.get("complex").to_json(complex(1, 2)) == "(1+2j)"
    assert dtypes.get("complex").to_json(None) is None                        # passthrough
    assert dtypes.get("floatlist").to_json([1.0, 2.0]) == [1.0, 2.0]          # passthrough (JSON-nativ)
    assert dtypes.json_default(complex(1, 2)) == "(1+2j)"


def test_complex_floatlist_json_roundtrip():
    m = Metadata()
    m.add("impedance", "50+3j", dtype="complex")
    m.add("spectrum", [1.0, 2.5, 3.0], dtype="floatlist")
    restored = Metadata.from_json(m.to_json())
    assert restored.get("impedance").value == complex(50, 3)
    assert restored.get("spectrum").value == [1.0, 2.5, 3.0]


def test_complex_floatlist_jsonld_roundtrip():
    from sdata import semantic
    m = Metadata(name="probe")
    m.add("impedance", "50+3j", dtype="complex")
    m.add("spectrum", [1.0, 2.5, 3.0], dtype="floatlist")
    doc = semantic.to_jsonld(m)
    assert doc["sdata:impedance"]["@type"] == "sdata:complex"
    assert doc["sdata:spectrum"]["@type"] == "sdata:floatlist"
    back = semantic.from_jsonld(doc)
    assert back.get("impedance").value == complex(50, 3)
    assert back.get("spectrum").value == [1.0, 2.5, 3.0]          # floatlist, nicht str-list


# --- langstring (neu) ------------------------------------------------------
def test_langstring_coercion():
    from sdata.dtypes import LangString
    ls = Attribute("l", "Hallo@de", dtype="langstring").value
    assert isinstance(ls, LangString) and ls.text == "Hallo" and ls.lang == "de"
    assert Attribute("l", "Hello@en-US", dtype="langstring").value == LangString("Hello", "en-US")
    assert Attribute("l", "plain", dtype="langstring").value == LangString("plain", "")
    assert Attribute("l", "a@b.com", dtype="langstring").value == LangString("a@b.com", "")  # kein Tag
    assert Attribute("l", ("meeting@noon", "en"), dtype="langstring").value == LangString("meeting@noon", "en")
    assert Attribute("l", {"@value": "Bonjour", "@language": "fr"},
                     dtype="langstring").value == LangString("Bonjour", "fr")
    assert Attribute("l", LangString("x", "de"), dtype="langstring").value == LangString("x", "de")
    assert Attribute("l", None, dtype="langstring").value is None
    assert Attribute("l", "", dtype="langstring").value is None


def test_langstring_class_and_json():
    from sdata.dtypes import LangString
    assert str(LangString("Hallo", "de")) == "Hallo@de"
    assert str(LangString("Hallo", "")) == "Hallo"                  # ohne Tag
    assert repr(LangString("Hallo", "de")) == "LangString('Hallo', 'de')"
    assert LangString("a", "de") != "a@de"                          # != Nicht-LangString
    assert LangString("a", "de") != LangString("a", "en")           # Lang unterscheidet
    assert {LangString("a", "de"): 1}[LangString("a", "de")] == 1   # hashbar
    assert dtypes.resolve("langString") == "langstring"             # case-insensitiv
    assert dtypes.resolve(LangString) == "langstring"
    assert dtypes.xsd_map()["langstring"] == "rdf:langString"
    assert dtypes.get("langstring").to_json(LangString("Hallo", "de")) == "Hallo@de"
    assert dtypes.get("langstring").to_json(None) is None           # passthrough
    assert dtypes.json_default(LangString("Hallo", "de")) == "Hallo@de"


def test_langstring_json_roundtrip():
    from sdata.dtypes import LangString
    m = Metadata()
    m.add("label", "Hallo@de", dtype="langstring")
    restored = Metadata.from_json(m.to_json())
    assert restored.get("label").value == LangString("Hallo", "de")


def test_langstring_jsonld_roundtrip():
    from sdata.dtypes import LangString
    from sdata import semantic
    m = Metadata(name="probe")
    m.add("label", "Hallo@de", dtype="langstring")
    m.add("note", "plain", dtype="langstring")          # ohne Tag -> degradiert zu str
    doc = semantic.to_jsonld(m)
    assert doc["sdata:label"] == {"@value": "Hallo", "@language": "de"}   # rdf:langString via @language
    assert doc["sdata:note"] == {"@value": "plain"}                       # kein @language/@type
    back = semantic.from_jsonld(doc)
    assert back.get("label").value == LangString("Hallo", "de")
    assert back.get("note").value == "plain"            # ohne Sprach-Tag -> str


# --- dtype=class & Re-Cast --------------------------------------------------
def test_dtype_class_accepted():
    assert Attribute("a", 1, dtype=int).dtype == "int"
    assert Attribute("f", "1.5", dtype=float).value == 1.5


def test_dtype_recast_on_change():
    a = Attribute("a", "3")            # dtype geraten -> str
    a.dtype = "int"
    assert a.value == 3 and isinstance(a.value, int)
    a.dtype = "float"
    assert a.value == 3.0


# --- DtypeSpec.to_json / json_default --------------------------------------
def test_spec_to_json_and_default():
    assert dtypes.get("timestamp").to_json(TimeStamp("2017-04-27")) == "2017-04-27T00:00:00+00:00"
    assert dtypes.get("bytes").to_json(b"\x00\x01") == "AAE="
    assert dtypes.get("str").to_json("x") == "x"          # passthrough
    assert dtypes.json_default(TimeStamp("2017-04-27")) == "2017-04-27T00:00:00+00:00"
    assert dtypes.json_default(b"\x00\x01") == "AAE="
    with pytest.raises(TypeError):
        dtypes.json_default(object())


def test_coerce_convenience_and_register():
    assert dtypes.coerce("5", "int") == 5
    assert dtypes.coerce(b"x", bytes) == b"x"
    spec = dtypes.DtypeSpec("dummy", str, lambda v, s: "D", "xsd:string")
    dtypes.register(spec)
    assert dtypes.get("dummy").coerce("anything") == "D"


# --- Metadata-Bugfix-Regressionen ------------------------------------------
def test_name_sdata_name_single_source():
    m = Metadata(name="x")
    assert m.name == "x"                       # Fallback _name
    m.set_attr("_sdata_name", "y")
    assert m.name == "y"                        # _sdata_name autoritativ
    m.name = "z"
    assert m.get("_sdata_name").value == "z"    # Setter spiegelt zurück


def test_relabel_explicit_rekey():
    m = Metadata()
    m.add("foo", 1)
    m.relabel("foo", "bar")
    assert "bar" in m and "foo" not in m
    assert m.get("bar").value == 1
    m.relabel("missing", "x")                   # no-op + warning


def test_update_hash_returns_object():
    import hashlib
    m = Metadata()
    m.add("a", 1)
    h = hashlib.sha3_256()
    assert m.update_hash(h) is h


def test_strict_via_set_attr():
    m = Metadata()
    with pytest.raises(DtypeError):
        m.set_attr("i", "abc", dtype="int", strict=True)


def test_timestamp_json_roundtrip():
    m = Metadata()
    m.add("create", "2017-04-27", dtype="timestamp")
    restored = Metadata.from_json(m.to_json())
    assert restored.get("create").value.utc == "2017-04-27T00:00:00+00:00"
