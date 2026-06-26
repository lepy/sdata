# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/sclass/dataframe.py."""
import pandas as pd
import pytest

pytest.importorskip("pyarrow")          # Parquet-Backend

from sdata.metadata import Metadata
from sdata.sclass.dataframe import DataFrame


def _df():
    return pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})


def test_init_variants():
    cm = {"weight": {"label": "Gewicht", "unit": "kg"}}
    a = DataFrame(df=_df(), column_metadata=cm, name="A")
    assert isinstance(a.cmd, Metadata)
    assert not a.cmdf.empty
    # column_metadata als Metadata
    b = DataFrame(df=_df(), column_metadata=a.cmd, name="B")
    assert isinstance(b.column_metadata, Metadata)
    # ungültiges column_metadata -> Warnung
    c = DataFrame(df=_df(), column_metadata=123, name="C")
    assert isinstance(c.column_metadata, Metadata)
    # df=None
    d = DataFrame(df=None, name="D")
    assert d.df.empty


def test_df_setter_index_name_and_columns():
    sdf = DataFrame(name="x")
    sdf.df = _df()
    assert sdf.df.index.name == "index"
    assert sdf.column_metadata.get("weight") is not None


def test_to_from_dict_roundtrip():
    sdf = DataFrame(df=_df(), name="rt", description="desc")
    d = sdf.to_dict()
    assert "parquet_bytes" in d["data"] and "column_metadata" in d["data"]
    r = DataFrame.from_dict(d)
    assert list(r.df.columns) == ["weight", "height"]


def test_to_dataframe_attrs():
    sdf = DataFrame(df=_df(), name="att", description="d")
    out = sdf.to_dataframe()
    assert "!sdata" not in out.attrs            # alter Tippfehler-Bug behoben
    assert "_sdata" in out.attrs
    sd = out.attrs["_sdata"]
    assert sd["description"] == "d"
    assert "metadata" in sd and "column_metadata" in sd


def test_to_parquet_bytes_and_from_bytes():
    sdf = DataFrame(df=_df(), name="pq")
    raw = sdf.to_parquet()                      # ohne path -> bytes
    assert isinstance(raw, (bytes, bytearray))
    back = DataFrame.from_parquet_bytes(raw)    # attrs nicht erhalten -> except-Zweige
    assert list(back.df.columns) == ["weight", "height"]


def test_to_parquet_file_and_from_parquet(tmp_path):
    sdf = DataFrame(df=_df(), name="onfile")
    fp = sdf.to_parquet(path=str(tmp_path))     # schreibt <sname>.spq
    assert fp.endswith(".spq")
    loaded = DataFrame.from_parquet(fp)
    assert list(loaded.df.columns) == ["weight", "height"]
    # nicht existierende Datei -> Exception
    with pytest.raises(Exception):
        DataFrame.from_parquet(str(tmp_path / "nope.spq"))


def test_from_parquet_bytes_without_sdata_attrs():
    raw = _df().to_parquet()                    # plain, keine _sdata-attrs
    back = DataFrame.from_parquet_bytes(raw)    # attrs None -> except-Zweige
    assert list(back.df.columns) == ["weight", "height"]


def test_from_parquet_without_sdata_attrs(tmp_path):
    fp = str(tmp_path / "plain.spq")
    _df().to_parquet(fp)
    loaded = DataFrame.from_parquet(fp)         # attrs None -> except-Zweige
    assert list(loaded.df.columns) == ["weight", "height"]
