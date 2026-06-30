# -*- coding: utf-8 -*-
"""Tests für DataFrame.convert (Umrechnung in ein Einheitensystem)."""
import logging

import pandas as pd
import pytest

from sdata import units
from sdata.sclass.dataframe import DataFrame


def _tensile():
    """Ein vollständig annotierter Zugversuch-DataFrame (force[N]/time[s]/disp[mm])."""
    df = pd.DataFrame({
        "force": [0.0, 2500.0, 5000.0],
        "time": [0.0, 0.25, 0.5],
        "displacement": [0.0, 1.2, 2.4],
    })
    sdf = DataFrame(df=df, name="tensile_test", description="a tension test")
    sdf.set_column("force", unit="N", label="Force", ontology="bfo:Quality")
    sdf.set_column("time", unit="s", label="Time", ontology="bfo:Quality")
    sdf.set_column("displacement", unit="mm", label="Displacement",
                   ontology="bfo:Quality")
    return sdf


def test_convert_to_unit_system_copy():
    sdf = _tensile()
    conv = sdf.convert(["kN", "mm", "ms"])

    # umgerechnete Kopie
    assert conv.column_units == {"force": "kN", "time": "ms", "displacement": "mm"}
    assert list(conv.df["force"]) == [0.0, 2.5, 5.0]
    assert list(conv.df["time"]) == [0.0, 250.0, 500.0]
    assert list(conv.df["displacement"]) == [0.0, 1.2, 2.4]   # mm -> mm unverändert

    # Original bleibt unangetastet
    assert sdf.column_units == {"force": "N", "time": "s", "displacement": "mm"}
    assert list(sdf.df["force"]) == [0.0, 2500.0, 5000.0]
    assert conv is not sdf


def test_convert_preserves_other_column_metadata():
    sdf = _tensile()
    conv = sdf.convert(["kN", "mm", "ms"])
    assert conv.get_column("force").label == "Force"
    assert conv.get_column("force").ontology == "bfo:Quality"
    assert conv.description == "a tension test"


def test_convert_inplace():
    sdf = _tensile()
    ret = sdf.convert(["kN", "mm", "ms"], inplace=True)
    assert ret is sdf
    assert list(sdf.df["force"]) == [0.0, 2.5, 5.0]
    assert sdf.column_units["time"] == "ms"


def test_convert_accepts_unit_system_object():
    sdf = _tensile()
    system = units.UnitSystem(["kN", "mm", "ms"])
    conv = sdf.convert(system)
    assert conv.column_units["force"] == "kN"


def test_convert_leaves_unaddressed_quantity_unchanged():
    df = pd.DataFrame({"force": [1000.0], "stress": [200.0]})
    sdf = DataFrame(df=df, name="mix")
    sdf.set_column("force", unit="N")
    sdf.set_column("stress", unit="MPa")
    conv = sdf.convert(["kN", "mm", "ms"])   # kein Druck im System
    assert conv.column_units["force"] == "kN"
    assert conv.column_units["stress"] == "MPa"     # unverändert
    assert list(conv.df["stress"]) == [200.0]


def test_convert_dict_mapping():
    df = pd.DataFrame({"stress": [1000.0]})
    sdf = DataFrame(df=df, name="d")
    sdf.set_column("stress", unit="MPa")
    conv = sdf.convert({"stress": "GPa"})
    assert conv.column_units["stress"] == "GPa"
    assert list(conv.df["stress"]) == [1.0]          # 1000 MPa -> 1 GPa


def test_convert_dict_column_without_unit_warns(caplog):
    df = pd.DataFrame({"x": [1.0, 2.0]})
    sdf = DataFrame(df=df, name="d")                 # x hat keine Einheit ("-")
    with caplog.at_level(logging.WARNING):
        conv = sdf.convert({"x": "kN"})
    assert "has no unit" in caplog.text
    assert list(conv.df["x"]) == [1.0, 2.0]          # unverändert


def test_convert_dict_unknown_column_warns(caplog):
    sdf = _tensile()
    with caplog.at_level(logging.WARNING):
        sdf.convert({"ghost": "kN"})           # Spalte existiert nicht
    assert "has no unit" in caplog.text


def test_convert_dict_incompatible_raises():
    sdf = _tensile()
    with pytest.raises(units.UnitConversionError, match="incompatible"):
        sdf.convert({"force": "mm"})           # Kraft -> Länge
