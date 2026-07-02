# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/sclass/dataframegroup.py."""
import pandas as pd
import pytest

pytest.importorskip("pyarrow")

from sdata.sclass.dataframegroup import DataFrameGroup


def _df():
    return pd.DataFrame({"a": [1, 2], "b": [3, 4]})


def test_add_get_list_remove():
    g = DataFrameGroup(name="g")
    g.add_dataframe("d1", _df())
    assert g.get_dataframe("d1") is not None
    assert g.get_dataframe("missing") is None
    assert g.get_column_metadata("d1") is not None
    assert g.get_column_metadata("missing") is None
    assert g.list_dataframes() == ["d1"]
    g.add_dataframe("d1", _df(), overwrite=True)          # overwrite
    with pytest.raises(ValueError):                       # existiert ohne overwrite
        g.add_dataframe("d1", _df())
    g.remove_dataframe("d1")
    with pytest.raises(KeyError):                         # nicht vorhanden
        g.remove_dataframe("d1")


def test_column_metadata_validation():
    g = DataFrameGroup(name="g")
    cm = {"a": {"label": "A", "unit": "-"}, "b": {"label": "B", "unit": "-"}}
    g.add_dataframe("d", _df(), column_metadata=cm)
    assert g.get_column_metadata("d") == cm
    with pytest.raises(ValueError):                       # Spalten passen nicht
        g.add_dataframe("x", _df(), column_metadata={"a": {"label": "", "unit": ""}})
    with pytest.raises(ValueError):                       # label/unit fehlt
        g.add_dataframe("y", _df(),
                        column_metadata={"a": {"label": ""}, "b": {"label": ""}})


def test_to_from_dict():
    g = DataFrameGroup(name="g")
    g.add_dataframe("d", _df())
    d = g.to_dict()
    assert "sdata" in d["data"]["dataframes"]["d"]        # neues Layout (RFC 0011)
    r = DataFrameGroup.from_dict(d)
    assert r.get_dataframe("d") is not None


def test_roundtrip_preserves_units_and_ontology():
    from sdata.sclass.dataframe import DataFrame
    g = DataFrameGroup(name="g")
    sdf = DataFrame(df=_df(), name="m")
    sdf.set_column("a", unit="kg", label="Masse", ontology="bfo:Quality")
    g.add(sdf, key="m")
    back = DataFrameGroup.from_dict(g.to_dict())
    member = back.get("m")
    assert member.column_units["a"] == "kg"              # Einheit überlebt (nicht nur label/unit)
    assert member.get_column("a").ontology == "bfo:Quality"
    assert member.get_column("a").label == "Masse"


def test_from_dict_reads_legacy_layout():
    import base64
    import io
    # altes Serialisierungs-Layout: {parquet, column_metadata:{label,unit}}
    g = DataFrameGroup(name="g")
    d = g.to_dict()
    bio = io.BytesIO()
    _df().to_parquet(bio, engine="pyarrow")
    d["data"]["dataframes"] = {
        "old": {
            "parquet": base64.b64encode(bio.getvalue()).decode("utf-8"),
            "column_metadata": {"a": {"label": "A", "unit": "kg"},
                                "b": {"label": "B", "unit": "-"}},
        }
    }
    r = DataFrameGroup.from_dict(d)
    assert r.get_dataframe("old") is not None
    assert r.get("old").column_units["a"] == "kg"        # {label,unit} auf Metadata gehoben
    assert r.get_column_metadata("old")["a"] == {"label": "A", "unit": "kg"}


def test_add_and_items():
    from sdata.sclass.dataframe import DataFrame
    g = DataFrameGroup(name="g")
    g.add(DataFrame(df=_df(), name="x"), key="x")
    g.add(_df(), key="y")                                 # pandas -> gewrappt
    assert sorted(k for k, _ in g.items()) == ["x", "y"]
    assert g.get("x") is not None


def test_add_duplicate_key_raises():
    g = DataFrameGroup(name="g")
    g.add(_df(), key="x")
    with pytest.raises(ValueError):                       # ohne overwrite
        g.add(_df(), key="x")
    g.add(_df(), key="x", overwrite=True)                 # mit overwrite ok


def test_from_dict_passes_through_dataframe_entry():
    from sdata.sclass.dataframe import DataFrame
    # Fallback-Zweig: Eintrag ist bereits ein DataFrame (weder 'sdata' noch 'parquet')
    g = DataFrameGroup(name="g")
    d = g.to_dict()
    d["data"]["dataframes"] = {"m": DataFrame(df=_df(), name="m")}
    r = DataFrameGroup.from_dict(d)
    assert r.get_dataframe("m") is not None
