# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/metadata.py (Attribute + Metadata)."""
import datetime
import hashlib

import numpy as np
import pandas as pd
import pytest

from sdata.metadata import Metadata, Attribute, extract_name_unit, _to_utc


# --- Modulfunktionen ----------------------------------------------------
def test_extract_name_unit_variants():
    assert extract_name_unit("Target Strain Rate (1/s) ")[0].strip() == "Target Strain Rate"
    assert extract_name_unit("Gauge Length [mm] x")[1] == "mm"
    assert extract_name_unit("Gauge Length <mm> y")[1] == "mm"
    assert extract_name_unit("plain") == ("plain", "")


def test_to_utc_naive_and_aware():
    import zoneinfo
    naive = datetime.datetime(2020, 1, 1, 12, 0, 0)
    assert _to_utc(naive).tzinfo is not None
    aware = naive.replace(tzinfo=zoneinfo.ZoneInfo("Europe/Berlin"))
    assert _to_utc(aware).tzinfo == datetime.timezone.utc


# --- Attribute ----------------------------------------------------------
def test_attribute_name_setter_branches():
    a = Attribute("  ok  ", "v")
    assert a.name == "ok"
    Attribute("", "v")            # leer -> Warnung (kein Crash)
    assert Attribute(123, "v").name == "123"   # non-str


def test_attribute_value_list():
    assert Attribute("l", "a, b ,c", dtype="list").value == ["a", "b", "c"]
    assert Attribute("l", ["x", 1], dtype="list").value == ["x", "1"]
    assert Attribute("l", None, dtype="list").value == []
    Attribute("l", 123, dtype="list")            # nicht castbar -> Fehler geloggt


def test_attribute_value_special_dtypes():
    assert Attribute("s", "", dtype="str").value == ""
    assert Attribute("x", None, dtype="str").value is None
    assert np.isnan(Attribute("i", None, dtype="int").value)
    assert np.isnan(Attribute("f", float("nan"), dtype="float").value)
    assert Attribute("b", 0, dtype="bool").value is False
    assert Attribute("b", 1, dtype="bool").value is True
    assert Attribute("n", 3, dtype="int").value == 3


def test_attribute_guess_dtype():
    assert Attribute.guess_dtype(3) is int
    assert Attribute.guess_dtype(3.1) is float
    assert Attribute.guess_dtype("x") is str
    assert Attribute.guess_dtype([1, 2]) == "list[str]"
    assert Attribute.guess_dtype((1,)) == "list[str]"
    assert Attribute.guess_dtype(None) is str


def test_attribute_dtype_setter():
    a = Attribute("a", 1)
    a.dtype = None
    a.dtype = "float64"
    assert a.dtype == "float"
    a.dtype = "int32"
    assert a.dtype == "int"
    a.dtype = float            # Klasse -> via DTYPES_INV
    assert a.dtype == "float"


def test_attribute_text_setters_none():
    a = Attribute("a", 1)
    a.description = None
    a.label = None
    a.ontology = None
    assert a.description == "" and a.label == "" and a.ontology == ""
    a.required = "true"
    assert a.required is True
    a.required = 0
    assert a.required is False


def test_attribute_serialisation():
    a = Attribute("a", None, dtype="str", unit="N", description="d", label="L", ontology="o")
    assert a.to_dict()["name"] == "a"
    assert a.to_list()[0] == "a"
    assert a.to_csv(prefix="#", sep=";").startswith("#")
    assert "Attr" in str(a)


# --- Metadata -----------------------------------------------------------
def _md():
    m = Metadata()
    m.add("a", 1.2, unit="MPa", dtype="float", description="a float")
    m.add("b", 1, dtype="int")
    m.add("foo", "bar")
    return m


def test_metadata_name_and_attributes_setter():
    m = Metadata()
    m.name = "meta1"
    assert m.name == "meta1"
    m.attributes = m.attributes      # setter
    assert isinstance(m.attributes, type(m._attributes))


def test_metadata_add_attribute_and_accessors():
    m = _md()
    m.add_attribute(Attribute("x", 5, dtype="int"))
    assert m.get_attr("x").value == 5
    assert "a" in [k for k in m.keys()]
    assert len(m.values()) == len(m.items()) == m.size
    assert m["a"].value == 1.2
    assert m.get("missing") is None
    assert "a" in m
    assert m.pop("missing") is None
    assert list(iter(m))


def test_metadata_setitem_new_and_existing():
    m = Metadata()
    m["new"] = 7
    assert m["new"].value == 7
    m["new"] = 9                       # vorhandenes -> update
    assert m["new"].value == 9


def test_metadata_relabel():
    m = _md()
    m.relabel("foo", "foo2")
    assert m.get("foo") is None and m.get("foo2") is not None
    m.relabel("does_not_exist", "y")   # Warnung


def test_metadata_dataframes():
    m = _md()
    m.add("_sdata_sname", "Meta__x__abc")     # für dft / get_dft-Default
    m.add("_sdata_uuid", "abc123")            # für sdft
    assert not m.df.empty
    assert isinstance(m.udf, pd.DataFrame)
    assert isinstance(m.sdf, pd.DataFrame)
    assert m.dft is not None
    assert m.get_dft() is not None            # Default index_name -> Zeile 510
    assert m.get_dft(index_name="a") is not None
    assert m.sdft is not None
    assert isinstance(m.to_dataframe(), pd.DataFrame)
    assert Metadata.from_dataframe(m.df).get("a") is not None


def test_metadata_dicts():
    m = _md()
    m.add("_sdata_sname", "Meta__x__abc")
    assert "a" in m.get_dict()
    assert "_sdata_sname" in m.get_sdict()    # sdata_attributes-Schleife
    assert "a" in m.get_udict()


def test_add_attribute_typeerror():
    with pytest.raises(TypeError):
        Metadata().add_attribute("not an Attribute")


def test_update_from_dict_branches():
    m = Metadata()
    m.update_from_dict({"x": 1, "s": "txt"}, guess_dtype=False)   # value=v, dtype=None
    assert m.get("x") is not None
    m2 = Metadata()
    m2.update_from_dict({"lst": [1, 2]})                          # else-Branch
    assert m2.get("lst") is not None


def test_guess_value_dtype_non_float():
    m = Metadata()
    m.add("txt", "abc")          # float("abc") schlägt fehl -> except -> str
    m.guess_value_dtype()
    assert m.get("txt").value == "abc"


def test_to_csv_header_filepath_and_oserror(tmp_path):
    m = _md()
    p = tmp_path / "hdr.csv"
    m.to_csv_header(prefix="#", filepath=str(p))
    assert p.exists()
    # OSError-Zweige: Schreiben auf ein Verzeichnis
    m.to_csv(filepath=str(tmp_path))
    m.to_csv_header(filepath=str(tmp_path))


def test_metadata_csv_json_roundtrip(tmp_path):
    m = _md()
    csv = tmp_path / "m.csv"
    m.to_csv(str(csv))
    assert m.to_csv_header(prefix="#").startswith("#")
    m_csv = Metadata.from_csv(str(csv))
    assert m_csv.get("foo") is not None

    js = m.to_json()
    assert Metadata.from_json(jsonstr=js).get("foo") is not None
    jf = tmp_path / "m.json"
    m.to_json(str(jf))
    assert Metadata.from_json(filepath=str(jf)).get("foo") is not None


def test_metadata_list_roundtrip():
    m = _md()
    lst = m.to_list()
    assert isinstance(lst, list)
    m2 = Metadata.from_list([["fx", 1.2, "kN", "float", "force"], ["bad"]])
    assert m2.get("fx") is not None and m2.get("bad") is None


def test_metadata_update_from_usermetadata():
    m = _md()
    m2 = Metadata()
    m2.update_from_usermetadata(m)
    assert m2.get("foo") is not None


def test_metadata_hash_and_helpers():
    m = _md()
    assert len(m.sha3_256) == 64
    m.update_hash(hashlib.sha3_256())
    with pytest.raises(Exception):
        m.update_hash(object())        # ungültiges hashobject
    assert isinstance(m.copy(), Metadata)
    assert "Metadata" in repr(m) and "Metadata" in str(m)


def test_metadata_set_unit_from_name_and_guess():
    m = Metadata()
    m.add("Length (mm)", 1.0)
    m.set_unit_from_name()
    assert m.get("Length") is not None and m.get("Length").unit == "mm"
    m2 = Metadata()
    m2.add("v", "3.5")
    m2.guess_value_dtype()
    assert m2.get("v").value == 3.5


def test_metadata_is_complete():
    m = Metadata()
    m.add("req", None, required=True)
    assert m.is_complete() is False
    m.add("req", 5, required=True)
    assert m.is_complete() is True
