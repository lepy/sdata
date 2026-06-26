# -*- coding: utf-8 -*-
"""Tests für sdata/schema.py (MetadataSchema/Templates, Validierung)."""
import numpy as np

from sdata.base import Base, sdata_factory
from sdata.metadata import Metadata
from sdata.schema import AttrSpec, MetadataSchema, ValidationReport
from sdata import schema as schema_mod


def _schema():
    return MetadataSchema("TensileTest", [
        AttrSpec("force_x", dtype="float", unit="kN", required=True,
                 ontology="bfo:Quality", description="force x"),
        AttrSpec("strain", dtype="float", unit="-", default=1.0),
        AttrSpec("phase", dtype="str", allowed=["ferrite", "martensite"]),
    ], topology_class="IndependentContinuant", sdata_class="sdata.base:Base")


# --- AttrSpec / MetadataSchema (de)serialisierung ---------------------------
def test_spec_and_schema_roundtrip():
    s = _schema()
    d = s.to_dict()
    s2 = MetadataSchema.from_dict(d)
    assert s2.name == "TensileTest"
    assert {sp.name for sp in s2.specs} == {"force_x", "strain", "phase"}
    assert AttrSpec.from_dict({"name": "x", "dtype": "int", "extra": "ignored"}).dtype == "int"


# --- validate ---------------------------------------------------------------
def test_validate_missing():
    m = Metadata()                                     # force_x fehlt -> required
    assert "force_x" in _schema().validate(m).missing


def test_validate_type_unit_enum_extra():
    s = _schema()
    m = Metadata()
    m.add("force_x", "abc", dtype="str", unit="MPa")   # type- (str/float) + unit-Fehler (MPa/kN)
    m.add("phase", "austenite")                        # enum-Fehler
    m.add("note", "frei")                              # extra
    rep = s.validate(m)
    assert not rep and rep.ok is False
    assert ("force_x", "float") in rep.type_errors
    assert "force_x" in rep.unit_errors
    assert "phase" in rep.enum_errors
    assert "note" in rep.extra


def test_validate_ok():
    s = _schema()
    m = Metadata()
    m.add("force_x", 12.5, dtype="float", unit="kN")
    m.add("phase", "ferrite")
    rep = s.validate(m)
    assert rep and bool(rep) is True


# --- apply ------------------------------------------------------------------
def test_apply_fills_defaults_and_blanks():
    s = _schema()
    m = Metadata()
    m.add("force_x", 10.0, dtype="float")              # ohne unit/ontology
    s.apply(m)
    assert m.get("force_x").unit == "kN"               # Einheit ergänzt
    assert m.get("force_x").ontology == "bfo:Quality"  # Ontologie ergänzt
    assert m.get("force_x").description == "force x"
    assert m.get("strain").value == 1.0                # Default angelegt
    assert "phase" in m                                # angelegt (Default None)


# --- to_json_schema + validate_jsonschema -----------------------------------
def test_to_json_schema():
    js = _schema().to_json_schema()
    assert js["type"] == "object"
    assert js["properties"]["force_x"]["type"] == "number"
    assert js["properties"]["phase"]["enum"] == ["ferrite", "martensite"]
    assert js["required"] == ["force_x"]


def test_validate_jsonschema_native_fallback():
    # ohne jsonschema -> native validate
    s = _schema()
    m = Metadata()
    m.add("force_x", 1.0, dtype="float", unit="kN")
    m.add("phase", "ferrite")
    assert s.validate_jsonschema(m).ok is True


def test_validate_jsonschema_with_fake(monkeypatch):
    class _Err(Exception):
        pass

    class _FakeJsonschema:
        ValidationError = _Err

        @staticmethod
        def validate(instance, schema):
            if "force_x" not in instance:
                raise _Err("'force_x' is a required property\nmore")

    monkeypatch.setattr(schema_mod, "_jsonschema", _FakeJsonschema)
    s = _schema()
    ok = Metadata()
    ok.add("force_x", 1.0, dtype="float", unit="kN")
    assert s.validate_jsonschema(ok).ok is True
    bad = Metadata()
    rep = s.validate_jsonschema(bad)
    assert rep.ok is False and "required property" in rep.messages[0]


# --- ValidationReport -------------------------------------------------------
def test_validation_report_html():
    rep = ValidationReport(ok=False, missing=["a"], messages=["m"])
    html = rep._repr_html_()
    assert "INVALID" in html and "missing" in html
    assert "OK" in ValidationReport(ok=True)._repr_html_()


def test_is_empty_branches():
    assert schema_mod._is_empty(None) is True
    assert schema_mod._is_empty("") is True
    assert schema_mod._is_empty(np.nan) is True
    assert schema_mod._is_empty("x") is False
    assert schema_mod._is_empty(0) is False           # 0 ist nicht "leer"


# --- Base-Wiring ------------------------------------------------------------
def test_base_schema_wiring():
    # Default-Base ohne Schema -> validate trivially ok
    assert Base(name="x").validate().ok is True
    # Factory-Klasse mit Schema -> Init qualifiziert voll + validate
    Material = sdata_factory("Material", name="DP800",
                             sdata_attrs={"SDATA_SCHEMA": _schema()})
    assert Material.metadata.get("force_x").unit == "kN"   # apply lief im Init
    assert "strain" in Material.metadata
    rep = Material.validate()
    assert "force_x" in rep.missing                        # force_x leer (nur Default)


def test_metadata_validate_delegators():
    s = _schema()
    m = Metadata()
    m.apply_schema(s)
    assert "strain" in m
    assert isinstance(m.validate(s), ValidationReport)
