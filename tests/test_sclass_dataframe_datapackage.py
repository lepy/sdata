# -*- coding: utf-8 -*-
"""Frictionless Data Package (.zip) Bündel: to_datapackage / from_datapackage."""
import io
import json
import zipfile

import pandas as pd
import pytest

from sdata.sclass.dataframe import DataFrame


def _annotated():
    df = pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})
    sdf = DataFrame(df=df, name="specimen", description="a tension test")
    sdf.set_column("weight", unit="kg", label="Gewicht",
                   description="mass", ontology="bfo:Quality")
    # height bleibt un-annotiert
    return sdf


# ------------------------------------------------------------------- CSV
def test_datapackage_csv_roundtrip(tmp_path):
    sdf = _annotated()
    fp = sdf.to_datapackage(path=str(tmp_path))
    assert fp.endswith(".zip")
    back = DataFrame.from_datapackage(fp)
    assert list(back.df.columns) == ["weight", "height"]
    assert back.description == "a tension test"
    assert back.get_column("weight").unit == "kg"
    assert back.get_column("weight").ontology == "bfo:Quality"


def test_datapackage_descriptor_is_frictionless(tmp_path):
    fp = _annotated().to_datapackage(path=str(tmp_path))
    with zipfile.ZipFile(fp) as zf:
        names = zf.namelist()
        dp = json.loads(zf.read("datapackage.json"))
    assert dp["profile"] == "tabular-data-package"
    res = dp["resources"][0]
    assert res["profile"] == "tabular-data-resource"
    assert res["path"].startswith("data/") and res["format"] == "csv"
    fields = {f["name"]: f for f in res["schema"]["fields"]}
    assert fields["weight"]["type"] == "integer"
    assert fields["weight"]["title"] == "Gewicht"
    assert fields["weight"]["unit"] == "kg"
    assert fields["weight"]["rdfType"] == "bfo:Quality"
    assert fields["height"]["type"] == "number"
    assert "title" not in fields["height"]          # un-annotiert
    # verlustfreier sdata-Block + Daten + Sidecar im Zip
    assert "metadata" in dp["sdata"] and "column_metadata" in dp["sdata"]
    assert any(n.endswith(".meta.jsonld") for n in names)
    assert res["path"] in names


def test_datapackage_returns_bytes_without_path():
    raw = _annotated().to_datapackage()
    assert isinstance(raw, (bytes, bytearray))
    assert zipfile.is_zipfile(io.BytesIO(raw))


def test_datapackage_no_sidecar(tmp_path):
    fp = _annotated().to_datapackage(path=str(tmp_path), sidecar=False)
    with zipfile.ZipFile(fp) as zf:
        names = zf.namelist()
    assert not any(n.endswith(".meta.jsonld") for n in names)


def test_datapackage_explicit_filename(tmp_path):
    target = str(tmp_path / "pkg.zip")
    fp = _annotated().to_datapackage(filename=target)   # filename ohne path
    assert fp == target
    assert DataFrame.from_datapackage(fp).get_column("weight").unit == "kg"


def test_datapackage_column_without_metadata(tmp_path):
    sdf = _annotated()
    sdf.column_metadata.pop("weight")                   # Annotation entfernen, Spalte bleibt
    fp = sdf.to_datapackage(path=str(tmp_path))
    with zipfile.ZipFile(fp) as zf:
        dp = json.loads(zf.read("datapackage.json"))
    weight = {f["name"]: f for f in dp["resources"][0]["schema"]["fields"]}["weight"]
    assert weight["type"] == "integer" and "title" not in weight


def test_datapackage_bad_format_raises():
    with pytest.raises(ValueError, match="csv|parquet"):
        _annotated().to_datapackage(fmt="orc")


def test_from_datapackage_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataFrame.from_datapackage(str(tmp_path / "nope.zip"))


# --------------------------------------------------------------- Parquet
def test_datapackage_parquet_roundtrip(tmp_path):
    pytest.importorskip("pyarrow")
    sdf = _annotated()
    fp = sdf.to_datapackage(path=str(tmp_path), fmt="parquet")
    with zipfile.ZipFile(fp) as zf:
        assert any(n.endswith(".spq") for n in zf.namelist())
    back = DataFrame.from_datapackage(fp)
    assert list(back.df.columns) == ["weight", "height"]
    assert back.get_column("weight").unit == "kg"
