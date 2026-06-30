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


def test_convert_derives_units():
    """v2: abgeleitete Einheiten (Spannung/Energie/Geschwindigkeit) werden mitgeführt."""
    df = pd.DataFrame({"force": [5000.0], "stress": [200.0], "v": [3.0],
                       "energy": [12.0]})
    sdf = DataFrame(df=df, name="mix")
    sdf.set_column("force", unit="N");   sdf.set_column("stress", unit="MPa")
    sdf.set_column("v", unit="m/s");     sdf.set_column("energy", unit="J")
    conv = sdf.convert(["kN", "mm", "ms"])
    assert conv.column_units == {"force": "kN", "stress": "GPa",
                                 "v": "m/s", "energy": "J"}
    assert list(conv.df["force"]) == [5.0]            # N -> kN
    assert list(conv.df["stress"]) == [0.2]           # MPa -> GPa (kN/mm²)
    assert list(conv.df["energy"]) == [12.0]          # J -> kN·mm = J


def test_convert_leaves_unspanned_dimension_unchanged():
    df = pd.DataFrame({"force": [1000.0], "temp": [25.0], "ratio": [0.5],
                       "raw": [7.0]})
    sdf = DataFrame(df=df, name="mix")
    sdf.set_column("force", unit="N")
    sdf.set_column("temp", unit="degC")      # Temperatur-Dimension nicht im System
    sdf.set_column("ratio", unit="%")        # dimensionslos
    # "raw" behält die Default-Einheit "-" (keine Einheit gesetzt)
    conv = sdf.convert(["kN", "mm", "ms"])
    assert conv.column_units["force"] == "kN"
    assert conv.column_units["temp"] == "degC"        # unverändert
    assert list(conv.df["temp"]) == [25.0]
    assert conv.column_units["ratio"] == "%"          # unverändert
    assert list(conv.df["raw"]) == [7.0]              # einheitenlos -> unverändert


def test_convert_dict_target_equals_current_noop():
    sdf = _tensile()                                  # force in "N"
    conv = sdf.convert({"force": "N"})                # Ziel == aktuell
    assert conv.column_units["force"] == "N"
    assert list(conv.df["force"]) == [0.0, 2500.0, 5000.0]


def test_convert_dict_mapping():
    df = pd.DataFrame({"stress": [1000.0]})
    sdf = DataFrame(df=df, name="d")
    sdf.set_column("stress", unit="MPa")
    conv = sdf.convert({"stress": "GPa"})
    assert conv.column_units["stress"] == "GPa"
    assert list(conv.df["stress"]) == [1.0]          # 1000 MPa -> 1 GPa
    assert conv.unit_system is None                   # dict path records no system


# ---------------------------------------------------------- settable unit_system
def test_unit_system_default_none():
    assert DataFrame(df=pd.DataFrame({"a": [1]}), name="d").unit_system is None


def test_set_unit_system_object_and_convert_without_args():
    sdf = _tensile()
    sdf.unit_system = units.UnitSystem(["kN", "mm", "ms"])
    assert isinstance(sdf.unit_system, units.UnitSystem)

    si = sdf.convert()                               # uses the recorded system
    assert si.column_units == {"force": "kN", "time": "ms", "displacement": "mm"}
    assert list(si.df["force"]) == [0.0, 2.5, 5.0]
    assert repr(si.unit_system) == "UnitSystem(['kN', 'mm', 'ms'])"
    # setting only records intent — the data is untouched until convert()
    assert sdf.column_units["force"] == "N"


def test_set_unit_system_from_list_is_wrapped():
    sdf = _tensile()
    sdf.unit_system = ["kN", "mm", "ms"]             # list -> UnitSystem
    assert isinstance(sdf.unit_system, units.UnitSystem)
    assert sdf.unit_system.unit_for("force") == "kN"


def test_unit_system_constructor_kwarg():
    sdf = DataFrame(df=pd.DataFrame({"force": [1000.0]}), name="d",
                    unit_system=["kN", "mm", "ms"])
    sdf.set_column("force", unit="N")
    assert isinstance(sdf.unit_system, units.UnitSystem)
    assert list(sdf.convert().df["force"]) == [1.0]


def test_unit_system_clear():
    sdf = _tensile()
    sdf.unit_system = ["kN", "mm", "ms"]
    sdf.unit_system = None
    assert sdf.unit_system is None


def test_convert_without_units_or_system_raises():
    sdf = _tensile()
    with pytest.raises(ValueError, match="no unit system"):
        sdf.convert()


def test_convert_copy_preserves_unit_system():
    sdf = _tensile()
    sdf.unit_system = ["kN", "mm", "ms"]
    copy = sdf.convert(inplace=False)               # converted copy keeps the system
    assert isinstance(copy.unit_system, units.UnitSystem)


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


# ------------------------------------------------------------- relabel_units
def test_relabel_units_same_dimension(caplog):
    """Werte sind faktisch schon kN, aber als N gelabelt -> nur Label korrigieren."""
    sdf = _tensile()                                  # force in "N"
    with caplog.at_level(logging.WARNING):
        report = sdf.relabel_units({"force": "kN"})
    assert sdf.column_units["force"] == "kN"
    assert list(sdf.df["force"]) == [0.0, 2500.0, 5000.0]   # Werte unverändert!
    assert report == [{"column": "force", "old": "N", "new": "kN",
                       "dimension_changed": False}]


def test_relabel_units_missing_unit():
    df = pd.DataFrame({"x": [1.0, 2.0]})
    sdf = DataFrame(df=df, name="d")                  # x ohne Einheit
    report = sdf.relabel_units({"x": "kN"})
    assert sdf.column_units["x"] == "kN"
    assert list(sdf.df["x"]) == [1.0, 2.0]
    assert report[0]["dimension_changed"] is False    # alte Dimension unbekannt


def test_relabel_units_dimension_change_requires_force():
    sdf = _tensile()                                  # force in "N"
    with pytest.raises(units.UnitConversionError, match="changes dimension"):
        sdf.relabel_units({"force": "mm"})            # Kraft -> Länge ohne force
    assert sdf.column_units["force"] == "N"           # nichts geändert


def test_relabel_units_dimension_change_forced(caplog):
    sdf = _tensile()
    with caplog.at_level(logging.WARNING):
        report = sdf.relabel_units({"force": "mm"}, force=True)
    assert sdf.column_units["force"] == "mm"
    assert list(sdf.df["force"]) == [0.0, 2500.0, 5000.0]   # Werte unverändert
    assert report[0]["dimension_changed"] is True
    assert "dimension changed" in caplog.text
