# -*- coding: utf-8 -*-
"""Spalten-Ergonomie (PR2) für sdata/sclass/dataframe.py:
``set_column``/``get_column``, ``col``-Accessor, ``column_units`` und das
Synchronisieren/Prunen der column_metadata bei df-Neuzuweisung.
"""
import logging

import pandas as pd
import pytest

from sdata.metadata import Attribute
from sdata.sclass.dataframe import DataFrame


def _df():
    return pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})


def test_set_and_get_column():
    sdf = DataFrame(df=_df(), name="x")
    attr = sdf.set_column("weight", unit="kg", label="Gewicht")
    assert isinstance(attr, Attribute)
    got = sdf.get_column("weight")
    assert got.unit == "kg"
    assert got.label == "Gewicht"
    # unbekannte Spalte -> None
    assert sdf.get_column("nope") is None


def test_set_column_preserves_other_fields():
    sdf = DataFrame(df=_df(), name="x")
    sdf.set_column("weight", unit="kg")
    sdf.set_column("weight", label="Gewicht")        # nur label setzen
    attr = sdf.get_column("weight")
    assert attr.unit == "kg" and attr.label == "Gewicht"


def test_set_column_orphan_warns(caplog):
    sdf = DataFrame(df=_df(), name="x")
    with caplog.at_level(logging.WARNING):
        sdf.set_column("nope", unit="x")
    assert any("not a df column" in r.getMessage() for r in caplog.records)
    # Annotation wird dennoch angelegt
    assert sdf.get_column("nope") is not None


def test_col_accessor_get():
    sdf = DataFrame(df=_df(), name="x")
    assert isinstance(sdf.col.weight, Attribute)
    assert isinstance(sdf.col["weight"], Attribute)
    with pytest.raises(AttributeError):
        sdf.col.unknown
    with pytest.raises(KeyError):
        sdf.col["unknown"]


def test_col_accessor_setattr_raises():
    sdf = DataFrame(df=_df(), name="x")
    with pytest.raises(AttributeError):
        sdf.col.weight = 1


def test_col_accessor_dir_and_repr():
    sdf = DataFrame(df=_df(), name="x")
    assert "weight" in dir(sdf.col) and "height" in dir(sdf.col)
    assert "ColumnAccessor" in repr(sdf.col)


def test_col_mutate_in_place_persists():
    sdf = DataFrame(df=_df(), name="x")
    sdf.col["weight"].unit = "kg"
    sdf.col.weight.label = "Gewicht"
    attr = sdf.get_column("weight")
    assert attr.unit == "kg" and attr.label == "Gewicht"


def test_column_units_view():
    sdf = DataFrame(df=_df(), name="x")
    sdf.set_column("weight", unit="kg")
    cu = sdf.column_units
    assert cu == {"weight": "kg", "height": "-"}
    assert list(cu) == ["weight", "height"]          # df-Spaltenreihenfolge


def test_sync_prunes_removed_columns_on_reassign():
    sdf = DataFrame(df=_df(), name="x")
    sdf.set_column("weight", unit="kg")
    # height entfällt -> Annotation wird geprunt, weight bleibt erhalten
    sdf.df = pd.DataFrame({"weight": [3, 4]})
    assert sdf.get_column("height") is None
    assert sdf.get_column("weight").unit == "kg"
    # neue Spalte -> Annotation wird ergänzt
    sdf.df = pd.DataFrame({"weight": [5], "depth": [6]})
    assert sdf.get_column("depth") is not None
    assert sdf.get_column("weight").unit == "kg"


def test_init_keeps_user_orphan_without_pruning():
    # Bei der Konstruktion gelieferte column_metadata bleibt erhalten (kein Prune)
    sdf = DataFrame(df=_df(), column_metadata={"zzz": {"unit": "x"}}, name="x")
    assert sdf.get_column("zzz") is not None
