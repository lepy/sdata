# -*- coding: utf-8 -*-
"""Tests für sdata/semantic.py: JSON-LD-Export/Import + Sidecar."""
import json
import os

from sdata.base import Base
from sdata.metadata import Metadata
from sdata import semantic


def _obj():
    b = Base(name="specimen_01")
    b.metadata.add("force_x", 12.5, unit="kN", dtype="float", description="fx",
                   label="Fx", required=True)
    b.metadata.add("stress", 350.0, unit="MPa", dtype="float", ontology="bfo:Quality")
    b.metadata.add("material_id", "DP800")                 # Literal
    b.metadata.add("phase", "martensite", ontology="bfo:Quality")  # getypter Knoten
    return b


def test_to_jsonld_structure():
    doc = _obj().to_jsonld()
    assert doc["@id"].startswith("did:suuid:Base__specimen_01__")
    assert "sdata:Base" in doc["@type"] and "bfo:BFO_0000004" in doc["@type"]
    assert doc["name"] == "specimen_01"
    assert "identifier" in doc and "generatedAtTime" in doc
    # einheitenbehaftet -> qudt:Quantity
    fx = doc["sdata:force_x"]
    assert fx["@type"] == "qudt:Quantity"
    assert fx["value"] == {"@value": 12.5, "@type": "xsd:double"}
    assert fx["unitRef"] == "unit:KiloN" and fx["symbol"] == "kN"
    assert fx["description"] == "fx" and fx["label"] == "Fx" and fx["required"] is True
    # Einheit + ontology -> zwei @type
    assert doc["sdata:stress"]["@type"] == ["qudt:Quantity", "bfo:Quality"]
    # unit-los, kein ontology -> Literal
    assert doc["sdata:material_id"] == {"@value": "DP800", "@type": "xsd:string"}
    # unit-los + ontology -> getypter Knoten
    assert doc["sdata:phase"]["@type"] == "bfo:Quality"


def test_jsonld_roundtrip():
    doc = _obj().to_jsonld()
    m = Metadata.from_jsonld(doc)
    assert m.name == "specimen_01"
    assert m.get("force_x").value == 12.5
    assert m.get("force_x").unit == "kN" and m.get("force_x").dtype == "float"
    assert m.get("material_id").value == "DP800"
    assert m.get("phase").ontology == "bfo:Quality"
    # auch aus JSON-String
    assert Metadata.from_jsonld(json.dumps(doc)).name == "specimen_01"


def test_provenance_links():
    parent = Base(name="parent")
    child = Base(name="child", parent=parent, project=parent)
    doc = child.to_jsonld()
    assert doc["wasDerivedFrom"]["@id"].startswith("did:suuid:Base__parent__")
    assert doc["isPartOf"]["@id"].startswith("did:suuid:Base__parent__")
    m = Metadata.from_jsonld(doc)
    assert m.get("_sdata_parent_sname").value.startswith("Base__parent__")
    assert m.get("_sdata_project_sname").value.startswith("Base__parent__")


def test_bare_metadata_and_special_dtypes():
    m = Metadata()
    m.add("note", "hello")
    m.add("tags", ["a", "b"], dtype="list")
    m.add("blob", b"\x00\x01", dtype="bytes")
    m.add("config", {"k": 1}, dtype="json")
    doc = m.to_jsonld()
    assert "@id" not in doc and "@type" not in doc      # keine reservierten Felder
    rt = Metadata.from_jsonld(doc)
    assert rt.get("tags").value == ["a", "b"] and rt.get("tags").dtype == "list"
    assert rt.get("config").value == {"k": 1} and rt.get("config").dtype == "json"
    assert rt.get("blob").dtype == "bytes"


def test_from_jsonld_scalar_predicate():
    # handgeschriebenes JSON-LD mit blankem Skalar unter einem sdata:-Prädikat
    m = Metadata.from_jsonld({"@type": "sdata:Thing", "sdata:count": 5})
    assert m.get("count").value == "5"           # Skalar -> str (kein XSD-Hint)
    assert m.get("_sdata_class").value == "Thing"


def test_sidecar_roundtrip(tmp_path):
    b = _obj()
    # Verzeichnis -> <sname>.meta.jsonld
    written = b.write_sidecar(str(tmp_path))
    assert written.endswith(".meta.jsonld") and os.path.exists(written)
    assert os.path.basename(written).startswith("Base__specimen_01__")
    m = Base.read_sidecar(written)
    assert m.get("force_x").value == 12.5
    # voller Dateipfad
    target = str(tmp_path / "custom.meta.jsonld")
    assert b.metadata.write_sidecar(target) == target
    assert Metadata.read_sidecar(target).name == "specimen_01"


def test_sidecar_path_helpers():
    assert semantic._sidecar_path(None, "x") == os.path.join(".", "x.meta.jsonld")
    assert semantic._sidecar_path("/tmp/a.jsonld", "x") == "/tmp/a.jsonld"
    assert semantic._sname_from_did("did:suuid:Foo__bar__abc:sdata") == "Foo__bar__abc"
    assert semantic._sname_from_did("plain") == "plain"


def test_sidecar_without_sname(tmp_path):
    m = Metadata()
    m.add("x", 1)
    written = m.write_sidecar(str(tmp_path))
    assert os.path.basename(written) == "metadata.meta.jsonld"
