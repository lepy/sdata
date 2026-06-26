# -*- coding: utf-8 -*-
"""Regressions für die PR1-Korrekturen an sdata/sclass/dataframe.py.

Deckt die behobenen Bugs ab (mutable Default, ``!sdata``→``_sdata``, getypte
Restore-Pfade, Waisen-Spalten-Warnung, klare pyarrow-Fehlermeldung) sowie die
neuen Convenience-Durchreichen.
"""
import logging

import pandas as pd
import pytest

pytest.importorskip("pyarrow")  # Parquet-Backend

from sdata.metadata import Metadata
from sdata.sclass import dataframe as dfm
from sdata.sclass.dataframe import DataFrame


def _df():
    return pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})


def test_no_shared_mutable_default():
    """Zwei ohne ``df`` erzeugte Instanzen teilen NICHT dasselbe DataFrame-Objekt."""
    a = DataFrame(name="a")
    b = DataFrame(name="b")
    assert a.df is not b.df
    a.df = pd.DataFrame({"x": [1]})
    assert "x" not in b.df.columns


def test_orphan_column_metadata_warns(caplog):
    """column_metadata-Keys ohne passende Spalte werden (nicht-brechend) gewarnt."""
    with caplog.at_level(logging.WARNING):
        sdf = DataFrame(df=_df(), column_metadata={"zzz": {"unit": "x"}}, name="o")
    assert any("zzz" in r.getMessage() for r in caplog.records)
    # nicht-brechend: Instanz ist nutzbar, Key bleibt erhalten
    assert sdf.column_metadata.get("zzz") is not None


def test_to_dataframe_uses_underscore_key():
    """``to_dataframe`` bettet unter ``_sdata`` (nicht ``!sdata``) inkl. column_metadata ein."""
    sdf = DataFrame(df=_df(), name="att", description="d")
    out = sdf.to_dataframe()
    assert "!sdata" not in out.attrs
    sd = out.attrs["_sdata"]
    assert sd["description"] == "d"
    assert "metadata" in sd and "column_metadata" in sd


def test_restore_from_attrs_variants():
    """``_restore_from_attrs`` ist robust gegen None/leer und füllt Teil-/Voll-Dicts."""
    src = DataFrame(df=_df(), name="r", description="rdesc")
    # None / leer -> No-Op
    sdf = DataFrame(name="empty", description="keep")
    sdf._restore_from_attrs(None)
    sdf._restore_from_attrs({})
    assert sdf.description == "keep"
    # Voll-Dict
    full = src.to_dataframe().attrs["_sdata"]
    target = DataFrame(name="t")
    target._restore_from_attrs(full)
    assert target.description == "rdesc"
    assert isinstance(target.column_metadata, Metadata)
    # Teil-Dict (nur description)
    only = DataFrame(name="only")
    only._restore_from_attrs({"description": "partial"})
    assert only.description == "partial"


def test_parquet_bytes_restore_roundtrip():
    """Bytes-Round-Trip stellt Beschreibung über die getypten Restore-Pfade wieder her."""
    sdf = DataFrame(df=_df(), name="b", description="bd")
    raw = sdf.to_parquet()  # ohne path -> bytes, bettet _sdata ein
    back = DataFrame.from_parquet_bytes(raw)
    assert back.description == "bd"
    assert list(back.df.columns) == ["weight", "height"]


def test_from_parquet_missing_file_raises(tmp_path):
    """Fehlende Datei -> klares ``FileNotFoundError`` (kein nacktes ``Exception``)."""
    with pytest.raises(FileNotFoundError):
        DataFrame.from_parquet(str(tmp_path / "nope.spq"))


def test_to_from_dict_engine_kwarg():
    """``engine`` ist in to_dict/from_dict ein durchgereichtes kwarg (Default pyarrow)."""
    sdf = DataFrame(df=_df(), name="e")
    d = sdf.to_dict(engine="pyarrow")
    r = DataFrame.from_dict(d, engine="pyarrow")
    assert list(r.df.columns) == ["weight", "height"]


def test_require_parquet_missing_engine():
    """Fehlende Engine -> sprechende ImportError mit Installationshinweis."""
    with pytest.raises(ImportError, match=r"sdata\[parquet\]"):
        dfm._require_parquet("definitely_not_a_real_engine_xyz")


def test_require_parquet_ok():
    """Vorhandene Engine -> kein Fehler."""
    dfm._require_parquet("pyarrow")


def test_dict_roundtrip_preserves_description_and_annotations():
    """to_dict/from_dict erhält description UND Spalten-Annotationen (Regression)."""
    sdf = DataFrame(df=_df(), name="rt", description="a tension test")
    sdf.set_column("weight", unit="kg", label="Gewicht", ontology="bfo:Quality")
    r = DataFrame.from_dict(sdf.to_dict())
    assert r.description == "a tension test"     # zuvor verloren (nur to_dict schrieb sie)
    w = r.get_column("weight")
    assert w.unit == "kg" and w.label == "Gewicht" and w.ontology == "bfo:Quality"


def test_convenience_passthroughs():
    """Dünne Delegationen an das innere pandas-DataFrame."""
    sdf = DataFrame(df=_df(), name="c")
    assert len(sdf) == 3
    assert sdf.shape == (3, 2)
    assert list(sdf.columns) == ["weight", "height"]
    assert sdf.dtypes["weight"] == sdf.df.dtypes["weight"]
    assert len(sdf.head(2)) == 2
    assert "weight" in sdf.describe().columns
    r = repr(sdf)
    assert "DataFrame" in r and "shape=(3, 2)" in r
