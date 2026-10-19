# -*- coding: utf-8 -*-
"""Tests: deklarierter Spalten-dtype korrumpiert die Spalten-Annotation nicht.

Der Wert eines Spalten-Attributs ist der pandas-dtype-Name (``"float64"``); das
Attribut selbst bleibt deshalb vom dtype ``str``.
"""
import logging

import pandas as pd

from sdata.sclass.dataframe import DataFrame


def _sdf():
    return DataFrame(pd.DataFrame({"F": [1.0, 2.0], "n": [1, 2]}), name="t")


def test_set_column_matching_dtype_logs_no_error(caplog):
    sdf = _sdf()
    with caplog.at_level(logging.WARNING):
        attr = sdf.set_column("F", unit="kN", dtype="float")
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert attr.value == "float64"
    assert attr.dtype == "str"
    assert attr.unit == "kN"


def test_set_column_mismatching_dtype_warns(caplog):
    sdf = _sdf()
    with caplog.at_level(logging.WARNING):
        attr = sdf.set_column("n", dtype="float")
    assert any("dtype" in r.getMessage() for r in caplog.records)
    assert attr.value == "int64"


def test_df_reassignment_keeps_column_value(caplog):
    sdf = _sdf()
    sdf.set_column("F", unit="kN", dtype="float")
    with caplog.at_level(logging.ERROR):
        sdf.df = pd.DataFrame({"F": [3.0]})
    assert not caplog.records
    assert sdf.get_column("F").value == "float64"
    assert sdf.get_column("F").unit == "kN"


def test_legacy_column_metadata_with_declared_dtype_loads(caplog):
    """Ältere Serialisierungen tragen ``dtype='float'`` an der Spalte."""
    cm = {"F": {"name": "F", "value": "float64", "dtype": "float", "unit": "kN"}}
    with caplog.at_level(logging.ERROR):
        sdf = DataFrame(pd.DataFrame({"F": [1.0]}), column_metadata=cm, name="t")
    assert not caplog.records
    assert sdf.get_column("F").value == "float64"
    assert sdf.get_column("F").unit == "kN"


def test_to_dict_roundtrip_keeps_column_value():
    sdf = _sdf()
    sdf.set_column("F", unit="kN", dtype="float")
    back = DataFrame.from_dict(sdf.to_dict())
    assert back.get_column("F").value == "float64"
    assert back.get_column("F").unit == "kN"
