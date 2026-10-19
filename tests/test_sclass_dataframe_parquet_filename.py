# -*- coding: utf-8 -*-
"""Tests: ``to_parquet(filename=...)`` schreibt die Datei (wie ``to_csv``)."""
import os

import pandas as pd
import pytest

from sdata.sclass.dataframe import DataFrame

pytest.importorskip("pyarrow")


def _sdf():
    sdf = DataFrame(pd.DataFrame({"F": [1.0, 2.0]}), name="curve")
    sdf.set_column("F", unit="kN", ontology="mto:AppliedForce")
    return sdf


def test_filename_only_writes_file(tmp_path):
    target = str(tmp_path / "BDJ1-Fz-S1L.spq")
    out = _sdf().to_parquet(filename=target)
    assert out == target
    assert os.path.isfile(target)
    back = DataFrame.from_parquet(target)
    assert back.get_column("F").unit == "kN"


def test_path_and_filename_writes_into_path(tmp_path):
    out = _sdf().to_parquet(path=str(tmp_path), filename="x.spq")
    assert out == os.path.join(str(tmp_path), "x.spq")
    assert os.path.isfile(out)


def test_path_only_uses_sname(tmp_path):
    sdf = _sdf()
    out = sdf.to_parquet(path=str(tmp_path))
    assert out == os.path.join(str(tmp_path), sdf.sname + ".spq")
    assert os.path.isfile(out)


def test_no_target_returns_bytes():
    assert isinstance(_sdf().to_parquet(), bytes)


def test_sidecar_next_to_custom_filename(tmp_path):
    sdf = _sdf()
    target = str(tmp_path / "x.spq")
    sdf.to_parquet(filename=target, sidecar=True)
    assert os.path.isfile(os.path.join(str(tmp_path), sdf.sname + ".meta.jsonld"))
