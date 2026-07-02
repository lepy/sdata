# -*- coding: utf-8 -*-
"""HDF5-Serialisierung (RFC 0002): to_hdf / from_hdf (h5py, Extra sdata[hdf]).

h5py ist nicht in der kanonischen CI -> die Suite skippt hier; die Methoden
sind in dataframe.py ``# pragma: no cover``. Diese Tests verifizieren das Verhalten
in Umgebungen mit installiertem h5py (z. B. Scratchpad / ``sdata[hdf]``).
"""
import datetime

import pandas as pd
import pytest

h5py = pytest.importorskip("h5py")

from sdata.sclass.dataframe import DataFrame


def _annotated():
    df = pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})
    sdf = DataFrame(df=df, name="specimen", description="a tension test")
    sdf.set_column("weight", unit="kg", label="Gewicht", ontology="bfo:Quality")
    return sdf


def test_hdf_roundtrip_default_key(tmp_path):
    sdf = _annotated()
    fp = sdf.to_hdf(path=str(tmp_path), sidecar=True)
    assert fp.endswith(".h5")
    assert list(tmp_path.glob("*.meta.jsonld"))          # Sidecar geschrieben
    back = DataFrame.from_hdf(fp)                          # Default-Key
    assert list(back.df.columns) == ["weight", "height"]
    assert back.description == "a tension test"
    assert back.get_column("weight").unit == "kg"
    assert back.get_column("weight").ontology == "bfo:Quality"
    # Werte bleiben erhalten (native Per-Spalten-Datasets)
    assert back.df["weight"].tolist() == [10, 20, 30]
    assert back.df["height"].tolist() == [1.5, 1.6, 1.7]


def test_hdf_explicit_key_and_multiple_in_one_file(tmp_path):
    a = _annotated()
    b = DataFrame(df=pd.DataFrame({"x": [1, 2]}), name="bbb", description="second")
    shared = str(tmp_path / "both.h5")
    a.to_hdf(filename=shared, key="a")
    b.to_hdf(filename=shared, key="b")                     # mode="a" -> beide Keys
    ra = DataFrame.from_hdf(shared, key="a")
    rb = DataFrame.from_hdf(shared, key="b")
    assert ra.get_column("weight").unit == "kg"
    assert list(rb.df.columns) == ["x"] and rb.description == "second"


def test_hdf_rewrites_same_key(tmp_path):
    fp = str(tmp_path / "one.h5")
    _annotated().to_hdf(filename=fp, key="k")
    # zweites Schreiben auf denselben Key ersetzt (kein Fehler durch Kollision)
    DataFrame(df=pd.DataFrame({"z": [9]}), name="zz").to_hdf(filename=fp, key="k")
    back = DataFrame.from_hdf(fp, key="k")
    assert list(back.df.columns) == ["z"] and back.df["z"].tolist() == [9]


def test_hdf_legacy_pytables_kwargs_ignored(tmp_path):
    # format/complevel/complib (PyTables) werden vom h5py-Backend ignoriert
    fp = _annotated().to_hdf(path=str(tmp_path), format="table", complevel=5)
    back = DataFrame.from_hdf(fp)
    assert back.get_column("weight").unit == "kg"


def test_hdf_string_and_datetime_columns(tmp_path):
    df = pd.DataFrame({
        "label": ["a", "b", "c"],
        "t": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
    })
    sdf = DataFrame(df=df, name="mixed")
    fp = sdf.to_hdf(path=str(tmp_path))
    back = DataFrame.from_hdf(fp)
    assert back.df["label"].tolist() == ["a", "b", "c"]
    assert list(back.df["t"]) == list(df["t"])


def test_hdf_preserves_non_default_index(tmp_path):
    df = pd.DataFrame({"v": [1, 2, 3]}, index=["r1", "r2", "r3"])
    df.index.name = "row"
    fp = DataFrame(df=df, name="idx").to_hdf(path=str(tmp_path))
    back = DataFrame.from_hdf(fp)
    assert list(back.df.index) == ["r1", "r2", "r3"]
    assert back.df.index.name == "row"


def test_hdf_compression(tmp_path):
    fp = _annotated().to_hdf(path=str(tmp_path), compression="gzip")
    back = DataFrame.from_hdf(fp)
    assert back.df["weight"].tolist() == [10, 20, 30]


def test_to_hdf_requires_path_or_filename():
    with pytest.raises(ValueError):
        _annotated().to_hdf()                              # kein path/filename


def test_from_hdf_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataFrame.from_hdf(str(tmp_path / "nope.h5"))


def test_from_hdf_without_sdata_attr(tmp_path):
    # unser Layout, aber ohne _sdata-Attribut -> Restore-None-Pfad (description="")
    fp = _annotated().to_hdf(path=str(tmp_path), key="data")
    with h5py.File(fp, "a") as f:
        del f["data"].attrs["_sdata"]
    back = DataFrame.from_hdf(fp, key="data")
    assert list(back.df.columns) == ["weight", "height"]
    assert back.description == ""


def test_from_hdf_empty_file_raises(tmp_path):
    fp = str(tmp_path / "empty.h5")
    with h5py.File(fp, "w"):
        pass
    with pytest.raises(ValueError):
        DataFrame.from_hdf(fp)
