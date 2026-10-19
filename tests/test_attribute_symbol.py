# -*- coding: utf-8 -*-
"""Tests für RFC 0016: Formelzeichen als Attributfeld ``symbol``."""
import json
import os

import pandas as pd
import pytest

from sdata import semantic, vocab
from sdata.interactive import attribute_html, metadata_html
from sdata.metadata import Attribute, Metadata
from sdata.sclass.dataframe import DataFrame


def _sdf():
    sdf = DataFrame(pd.DataFrame({"R_p02": [952.1, 948.3]}), name="results")
    sdf.set_column("R_p02", unit="MPa", label="0,2-%-Dehngrenze",
                   symbol="R_p0,2", ontology="tto:Rp02")
    return sdf


# ------------------------------------------------------------------ Attribute
def test_attribute_symbol_default_and_set():
    assert Attribute("a", 1.0).symbol == ""
    attr = Attribute("F", 1.0, unit="kN", symbol="F")
    assert attr.symbol == "F"
    assert attr.to_dict()["symbol"] == "F"
    attr.symbol = None
    assert attr.symbol == ""


def test_metadata_set_attr_and_dict_roundtrip():
    m = Metadata()
    m.set_attr("L_o", 20.0, unit="mm", symbol="L_o")
    m.set_attr("L_o", symbol="L_0")
    back = Metadata.from_dict(m.to_dict())
    assert back.get("L_o").symbol == "L_0"
    assert back.get("L_o").value == 20.0


def test_metadata_from_dict_without_symbol():
    m = Metadata.from_dict({"a": {"name": "a", "value": 1.0, "dtype": "float"}})
    assert m.get("a").symbol == ""


# -------------------------------------------------------------- Metadaten-CSV
def test_metadata_csv_roundtrip(tmp_path):
    m = Metadata()
    m.set_attr("R_p02", 952.1, unit="MPa", symbol="R_p0,2")   # Komma im Zeichen
    path = str(tmp_path / "m.csv")
    m.to_csv(path)
    assert Metadata.from_csv(path).get("R_p02").symbol == "R_p0,2"


def test_metadata_csv_reads_eight_column_files(tmp_path):
    path = tmp_path / "old.csv"
    path.write_text("a,1.5,mm,float,desc,lab,False,\n")
    m = Metadata.from_csv(str(path))
    assert m.get("a").value == 1.5
    assert m.get("a").symbol == ""


def test_to_dataframe_has_symbol_column():
    m = Metadata()
    m.set_attr("F", 1.0, symbol="F")
    df = m.to_dataframe()
    assert list(df.columns)[-1] == "symbol"
    assert df.loc["F", "symbol"] == "F"


# ------------------------------------------------------------------ DataFrame
def test_set_column_symbol_and_accessor():
    sdf = _sdf()
    assert sdf.col.R_p02.symbol == "R_p0,2"
    assert sdf.col.R_p02.label == "0,2-%-Dehngrenze"


def test_dataframe_dict_roundtrip():
    back = DataFrame.from_dict(_sdf().to_dict())
    assert back.get_column("R_p02").symbol == "R_p0,2"


def test_arrow_field_metadata_carries_symbol():
    pytest.importorskip("pyarrow")
    table = _sdf().to_arrow()
    assert table.schema.field("R_p02").metadata[b"symbol"] == "R_p0,2".encode()
    assert DataFrame.from_arrow(table).get_column("R_p02").symbol == "R_p0,2"


def test_hdf_roundtrip(tmp_path):
    pytest.importorskip("h5py")
    path = str(tmp_path / "r.h5")
    _sdf().to_hdf(filename=path)
    assert DataFrame.from_hdf(path).get_column("R_p02").symbol == "R_p0,2"


def test_datapackage_roundtrip(tmp_path):
    path = _sdf().to_datapackage(path=str(tmp_path))
    assert DataFrame.from_datapackage(path).get_column("R_p02").symbol == "R_p0,2"


# -------------------------------------------------------------------- JSON-LD
def test_context_has_quantity_symbol_term():
    assert vocab.build_context()["quantitySymbol"] == "sdata:quantitySymbol"
    hosted = os.path.join(os.path.dirname(__file__), "..", "ns", "context.jsonld")
    with open(hosted) as fh:
        assert json.load(fh)["@context"]["quantitySymbol"] == "sdata:quantitySymbol"


def test_column_node_separates_unit_and_quantity_symbol():
    node = semantic.column_node(_sdf().get_column("R_p02"))
    assert node["symbol"] == "MPa"
    assert node["quantitySymbol"] == "R_p0,2"


def test_attr_node_carries_quantity_symbol():
    m = Metadata()
    m.set_attr("L_o", 20.0, unit="mm", symbol="L_o")
    doc = semantic.to_jsonld(m)
    nodes = [v for v in doc.values() if isinstance(v, dict) and v.get("name") == "L_o"]
    assert nodes and nodes[0]["quantitySymbol"] == "L_o"


def test_csv_sidecar_roundtrip(tmp_path):
    path = str(tmp_path / "r.csv")
    _sdf().to_csv(filename=path, sidecar=True)
    assert DataFrame.from_csv(path).get_column("R_p02").symbol == "R_p0,2"


# ----------------------------------------------------------------------- HTML
def test_html_shows_symbol():
    attr = Attribute("F", 1.0, unit="kN", symbol="F_m")
    assert "<th>symbol</th>" in attribute_html(attr)
    assert "F_m" in attribute_html(attr)
    m = Metadata()
    m.add(attr)
    assert "F_m" in metadata_html(m)
