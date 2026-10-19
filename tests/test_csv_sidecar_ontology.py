# -*- coding: utf-8 -*-
"""Tests: die Spalten-Ontologie überlebt den CSV-Sidecar (JSON-LD)."""
import pandas as pd

from sdata import semantic
from sdata.sclass.dataframe import DataFrame


def _sdf():
    sdf = DataFrame(pd.DataFrame({"F": [1.0, 2.0], "t": [0.0, 0.1]}), name="curve")
    sdf.set_column("F", unit="kN", label="F", ontology="mto:AppliedForce")
    sdf.set_column("t", unit="s")
    return sdf


def test_column_node_carries_rdf_type():
    node = semantic.column_node(_sdf().get_column("F"))
    assert node["rdfType"] == "mto:AppliedForce"


def test_column_node_without_ontology_has_no_rdf_type():
    assert "rdfType" not in semantic.column_node(_sdf().get_column("t"))


def test_csv_sidecar_roundtrip_keeps_ontology(tmp_path):
    path = str(tmp_path / "curve.csv")
    _sdf().to_csv(filename=path, sidecar=True)
    back = DataFrame.from_csv(path)
    col = back.get_column("F")
    assert col.ontology == "mto:AppliedForce"
    assert col.unit == "kN"
    assert col.label == "F"
    assert back.get_column("t").ontology == ""
