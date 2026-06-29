# -*- coding: utf-8 -*-
"""HDF5-Serialisierung (RFC 0002): to_hdf / from_hdf (PyTables, Extra sdata[hdf]).

PyTables ist nicht in der kanonischen CI -> die Suite skippt hier; die Methoden
sind in dataframe.py ``# pragma: no cover``. Diese Tests verifizieren das Verhalten
in Umgebungen mit installiertem PyTables (z. B. Scratchpad / ``sdata[hdf]``).
"""
import pandas as pd
import pytest

pytest.importorskip("tables")

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


def test_hdf_table_format(tmp_path):
    fp = _annotated().to_hdf(path=str(tmp_path), format="table")
    back = DataFrame.from_hdf(fp)
    assert back.get_column("weight").unit == "kg"


def test_to_hdf_requires_path_or_filename():
    with pytest.raises(ValueError):
        _annotated().to_hdf()                              # kein path/filename


def test_from_hdf_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataFrame.from_hdf(str(tmp_path / "nope.h5"))


def test_from_hdf_plain_without_sdata_attr(tmp_path):
    # einfaches pandas-HDF ohne _sdata-Attribut -> Restore-None-Pfad
    fp = str(tmp_path / "plain.h5")
    pd.DataFrame({"weight": [1, 2]}).to_hdf(fp, key="data", format="fixed")
    back = DataFrame.from_hdf(fp, key="data")
    assert list(back.df.columns) == ["weight"]
    assert back.description == ""
