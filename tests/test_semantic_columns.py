# -*- coding: utf-8 -*-
"""Tests: DataFrame-Spalten-Metadaten (csvw:column) im JSON-LD/RDF/Sidecar."""
import json

import pandas as pd

from sdata.metadata import Metadata, Attribute
from sdata import semantic
from sdata.sclass.dataframe import DataFrame


def _sdf():
    df = pd.DataFrame({"force": [1.0, 2.0], "n": [1, 2], "label": ["x", "y"]})
    sdf = DataFrame(df=df, name="tab")
    # eine Spalte semantisch anreichern
    sdf.column_metadata.set_attr("force", unit="kN", label="Force",
                                 description="axial force")
    return sdf


def test_column_node_helper():
    a = Attribute("force", "float64", unit="kN", label="Force", description="d")
    node = semantic.column_node(a)
    assert node == {"name": "force", "datatype": "xsd:double",
                    "unitRef": "unit:KiloN", "symbol": "kN",
                    "label": "Force", "description": "d"}
    # ohne unit/label -> nur name + datatype
    assert semantic.column_node(Attribute("n", "int64")) == {
        "name": "n", "datatype": "xsd:integer"}


def test_dataframe_to_jsonld_columns():
    doc = _sdf().to_jsonld()
    cols = {c["name"]: c for c in doc["columns"]}
    assert set(cols) == {"force", "n", "label"}
    assert cols["force"]["datatype"] == "xsd:double"
    assert cols["force"]["unitRef"] == "unit:KiloN" and cols["force"]["label"] == "Force"
    assert cols["n"]["datatype"] == "xsd:integer"
    assert cols["label"]["datatype"] == "xsd:string"        # object-dtype
    # @context kennt die CSVW-Terme
    assert doc["@context"]["columns"]["@id"] == "csvw:column"


def test_to_jsonld_columns_none_and_empty():
    m = Metadata()
    m.add("x", 1)
    assert "columns" not in semantic.to_jsonld(m)              # columns=None
    assert "columns" not in semantic.to_jsonld(m, columns=[])  # leer


def test_dataframe_turtle_and_sidecar(tmp_path):
    sdf = _sdf()
    # Turtle-Fallback (kein rdflib) = JSON-LD mit columns
    ttl = sdf.to_turtle()
    assert "columns" in json.loads(ttl)
    # Sidecar enthält die Spalten
    written = sdf.write_sidecar(str(tmp_path))
    assert written.endswith(".meta.jsonld")
    doc = json.loads(open(written).read())
    assert [c["name"] for c in doc["columns"]] == ["force", "n", "label"]
