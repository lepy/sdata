# -*- coding: utf-8 -*-
"""Interop/Export (PR3) für sdata/sclass/dataframe.py:
CSV (pure pandas, immer verfügbar) sowie Arrow/Feather (pyarrow-guarded).
"""
import os

import pandas as pd
import pytest

from sdata.sclass.dataframe import DataFrame


def _df():
    return pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})


# ----------------------------------------------------------------- CSV (immer)
def test_to_csv_string_roundtrip(tmp_path):
    sdf = DataFrame(df=_df(), name="rt")
    text = sdf.to_csv()                       # ohne path/filename -> String
    assert isinstance(text, str) and "weight" in text
    fp = tmp_path / "data.csv"
    fp.write_text(text)
    back = DataFrame.from_csv(str(fp))
    assert list(back.df.columns) == ["weight", "height"]


def test_to_csv_file_and_sidecar(tmp_path):
    sdf = DataFrame(df=_df(), name="onfile", description="d")
    fp = sdf.to_csv(path=str(tmp_path), sidecar=True)
    assert fp.endswith(".csv") and os.path.exists(fp)
    # Sidecar liegt daneben
    sidecars = list(tmp_path.glob("*.meta.jsonld"))
    assert len(sidecars) == 1


def test_to_csv_explicit_filename_only(tmp_path):
    sdf = DataFrame(df=_df(), name="f")
    target = str(tmp_path / "explicit.csv")
    fp = sdf.to_csv(filename=target)          # filename ohne path -> else-Zweig
    assert fp == target and os.path.exists(target)
    loaded = DataFrame.from_csv(fp)
    assert list(loaded.df.columns) == ["weight", "height"]


def test_from_csv_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataFrame.from_csv(str(tmp_path / "nope.csv"))


# ------------------------------------- CSV-Sidecar-Roundtrip (RFC 0008, A3/B6)
def test_csv_sidecar_roundtrip(tmp_path):
    sdf = DataFrame(df=_df(), name="specimen", description="d")
    sdf.metadata.add("max_force", 12.5, unit="kN", dtype="float",
                     ontology="bfo:Quality")
    sdf.set_column("weight", unit="kg", label="Gewicht", description="w")
    fp = sdf.to_csv(path=str(tmp_path), sidecar=True)
    back = DataFrame.from_csv(fp)                    # Sidecar-Konsum ist Default
    assert back.name == "specimen"
    assert back.sname == sdf.sname
    assert str(back.suuid) == str(sdf.suuid)
    attr = back.metadata.get("max_force")
    assert attr.value == 12.5 and attr.unit == "kN"
    assert back.column_units["weight"] == "kg"
    assert back.col["weight"].label == "Gewicht"
    assert back.col["weight"].description == "w"
    pd.testing.assert_frame_equal(back.df, sdf.df)


def test_csv_sidecar_opt_out(tmp_path):
    sdf = DataFrame(df=_df(), name="specimen")
    sdf.metadata.add("max_force", 12.5, unit="kN", dtype="float")
    fp = sdf.to_csv(path=str(tmp_path), sidecar=True)
    back = DataFrame.from_csv(fp, sidecar=False)     # Schalter: nur Daten
    assert back.metadata.get("max_force") is None
    assert back.name != "specimen"


def test_csv_sidecar_custom_filename_next_to_file(tmp_path):
    sdf = DataFrame(df=_df(), name="specimen")
    sdf.metadata.add("license", "CC-BY-4.0", dtype="str")
    target = str(tmp_path / "explicit.csv")
    sdf.to_csv(filename=target, sidecar=True)
    # Sidecar liegt neben der CSV (<stem>.meta.jsonld), nicht im CWD
    assert os.path.exists(str(tmp_path / "explicit.meta.jsonld"))
    back = DataFrame.from_csv(target)
    assert back.metadata.get("license").value == "CC-BY-4.0"


def test_csv_sidecar_broken_is_ignored(tmp_path):
    sdf = DataFrame(df=_df(), name="specimen")
    fp = sdf.to_csv(path=str(tmp_path), sidecar=True)
    sidecar = os.path.splitext(fp)[0] + ".meta.jsonld"
    with open(sidecar, "w") as fh:
        fh.write("{ kaputt")                          # unparsebar -> nur Daten
    back = DataFrame.from_csv(fp)
    assert list(back.df.columns) == ["weight", "height"]


# ------------------------------------------------------------ Arrow (pyarrow)
def test_to_arrow_embeds_metadata():
    pytest.importorskip("pyarrow")
    sdf = DataFrame(df=_df(), name="a", description="d")
    sdf.set_column("weight", unit="kg")
    table = sdf.to_arrow()
    assert b"_sdata" in (table.schema.metadata or {})


def test_arrow_roundtrip_preserves_annotations():
    pytest.importorskip("pyarrow")
    sdf = DataFrame(df=_df(), name="a", description="desc")
    sdf.set_column("weight", unit="kg")
    back = DataFrame.from_arrow(sdf.to_arrow())
    assert list(back.df.columns) == ["weight", "height"]
    assert back.description == "desc"
    assert back.get_column("weight").unit == "kg"


def test_from_arrow_plain_table_without_sdata():
    pa = pytest.importorskip("pyarrow")
    table = pa.Table.from_pandas(_df())       # kein _sdata -> raw None
    back = DataFrame.from_arrow(table)
    assert list(back.df.columns) == ["weight", "height"]


# ---------------------------------------------------------- Feather (pyarrow)
def test_feather_file_roundtrip(tmp_path):
    pytest.importorskip("pyarrow")
    sdf = DataFrame(df=_df(), name="feat", description="fd")
    sdf.set_column("height", unit="m")
    fp = sdf.to_feather(path=str(tmp_path), sidecar=True)
    assert fp.endswith(".feather") and os.path.exists(fp)
    assert list(tmp_path.glob("*.meta.jsonld"))   # Sidecar geschrieben
    back = DataFrame.from_feather(fp)
    assert back.description == "fd"
    assert back.get_column("height").unit == "m"


def test_feather_bytes_and_explicit_filename(tmp_path):
    pytest.importorskip("pyarrow")
    sdf = DataFrame(df=_df(), name="feat")
    raw = sdf.to_feather()                     # ohne path -> bytes
    assert isinstance(raw, (bytes, bytearray))
    target = str(tmp_path / "explicit.feather")
    fp = sdf.to_feather(filename=target)       # filename ohne path -> else-Zweig
    assert fp == target and os.path.exists(target)


def test_from_feather_missing_file_raises(tmp_path):
    pytest.importorskip("pyarrow")
    with pytest.raises(FileNotFoundError):
        DataFrame.from_feather(str(tmp_path / "nope.feather"))
