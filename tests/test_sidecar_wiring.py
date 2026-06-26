# -*- coding: utf-8 -*-
"""Opt-in Sidecar-Verdrahtung in die Speicherpfade (to_json / to_parquet)."""
import pandas as pd
import pytest

from sdata.base import Base


def test_to_json_sidecar(tmp_path):
    b = Base(name="x")
    b.metadata.add("a", 1)
    fp = str(tmp_path / "x.sjson")
    assert b.to_json(fp, sidecar=True) is None
    side = tmp_path / (b.sname + ".meta.jsonld")
    assert side.exists()
    # Default: kein Sidecar
    Base(name="y").to_json(str(tmp_path / "y.sjson"))
    assert not list(tmp_path.glob("Base__y*.meta.jsonld"))
    # String-Modus unverändert
    assert isinstance(Base(name="z").to_json(), str)


def test_to_json_sidecar_no_dir(tmp_path, monkeypatch):
    # filepath ohne Verzeichnis -> dirname("") -> "." (cwd = tmp_path)
    monkeypatch.chdir(tmp_path)
    b = Base(name="here")
    b.to_json("here.sjson", sidecar=True)
    assert (tmp_path / (b.sname + ".meta.jsonld")).exists()


def test_to_parquet_sidecar(tmp_path):
    pytest.importorskip("pyarrow")
    from sdata.sclass.dataframe import DataFrame
    sdf = DataFrame(df=pd.DataFrame({"a": [1, 2, 3]}), name="d")
    sdf.metadata.add("temperature", 23.0, unit="degC", dtype="float")
    fp = sdf.to_parquet(path=str(tmp_path), sidecar=True)
    assert fp.endswith(".spq")
    assert (tmp_path / (sdf.sname + ".meta.jsonld")).exists()
    # Default: kein Sidecar
    sdf2 = DataFrame(df=pd.DataFrame({"a": [1]}), name="e")
    sdf2.to_parquet(path=str(tmp_path))
    assert not list(tmp_path.glob("*__e__*.meta.jsonld"))
