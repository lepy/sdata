# -*- coding: utf-8 -*-
"""Abdeckung für sdata.doe.DOE."""
import pandas as pd

import sdata
from sdata.doe import DOE


def _doe():
    return DOE({"sheet_thickness": [0.8, 1.8], "slant_depth": [10.0, 50.0]}, name="t")


def test_init_and_ranges():
    doe = DOE()
    assert doe.dim_num == 0
    doe = _doe()
    assert doe.dim_num == 2
    assert set(doe.ranges.keys()) == {"sheet_thickness", "slant_depth"}


def test_add_range():
    doe = DOE()
    doe.add_range("x", [3.0, 1.0])   # min/max werden normalisiert
    assert doe.ranges["x"].min == 1.0
    assert doe.ranges["x"].max == 3.0


def test_gen_sobol01_unit_interval():
    df = _doe().gen_sobol01(n=5)
    assert list(df.columns) == ["sheet_thickness", "slant_depth"]
    assert df.index.name == "doe_id"
    assert ((df >= 0) & (df <= 1)).all().all()


def test_gen_sobol_scaled_to_ranges():
    df = _doe().gen_sobol(n=8)
    assert df["sheet_thickness"].min() >= 0.8
    assert df["sheet_thickness"].max() <= 1.8
    assert df["slant_depth"].min() >= 10.0
    assert df["slant_depth"].max() <= 50.0


def test_to_data():
    doe = _doe()
    df = doe.gen_sobol(n=4)
    data = doe.to_data("mydoe", df, uid=None)
    assert data.name == "mydoe"
    assert data.df.shape[0] == 4
    # doe_id ist Spalte (nicht Index), damit sie die Serialisierung überlebt
    assert list(data.df["doe_id"]) == [1, 2, 3, 4]
    assert list(df.index) == [1, 2, 3, 4]  # Eingabe bleibt unverändert
    assert "sheet_thickness" in data.metadata.keys()


def test_to_data_uid_hex_string():
    doe = _doe()
    hexuid = "48b26864e7794f5182d38459bab8584d"
    data = doe.to_data("mydoe", doe.gen_sobol(n=2), uid=hexuid)
    assert data.suuid.huuid == hexuid
    # Bindestrich-Form ergibt dieselbe Identität
    dashed = "48b26864-e779-4f51-82d3-8459bab8584d"
    assert doe.to_data("mydoe", doe.gen_sobol(n=2), uid=dashed).suuid.huuid == hexuid


def test_to_data_uid_suuid_passthrough():
    doe = _doe()
    sid = sdata.SUUID.random("DataFrame", "mydoe")
    data = doe.to_data("mydoe", doe.gen_sobol(n=2), uid=sid)
    assert data.suuid.sname == sid.sname


def test_to_data_uid_default_is_deterministic():
    doe = _doe()
    a = doe.to_data("mydoe", doe.gen_sobol(n=2))
    b = doe.to_data("mydoe", doe.gen_sobol(n=2))
    assert a.suuid.sname == b.suuid.sname
