# -*- coding: utf-8 -*-
"""Abdeckung für sdata.doe.DOE."""
import pandas as pd

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
    assert "sheet_thickness" in data.metadata.keys()
