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
    assert "parquet" in d["data"]["dataframes"]["d"]
    r = DataFrameGroup.from_dict(d)
    assert r.data["dataframes"]["d"]["df"] is not None
