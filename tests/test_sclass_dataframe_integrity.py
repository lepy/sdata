# -*- coding: utf-8 -*-
"""DataFrame nutzt den gemeinsamen Integritäts-Mixin (RFC 0004, Option B):
sha1/md5/sha256/size + verify/update_checksum über content_bytes (Parquet)."""
import pandas as pd
import pytest

pytest.importorskip("pyarrow")

from sdata.sclass.content import ContentIntegrityMixin
from sdata.sclass.dataframe import DataFrame


def _df():
    return pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})


def test_dataframe_is_integrity_mixin():
    assert isinstance(DataFrame(df=_df(), name="x"), ContentIntegrityMixin)


def test_dataframe_hashes_and_size():
    sdf = DataFrame(df=_df(), name="x")
    assert len(sdf.sha256) == 64
    assert len(sdf.sha1) == 40
    assert len(sdf.md5) == 32
    assert sdf.size and sdf.size > 0
    assert sdf.content_bytes == sdf.df.to_parquet()   # reines Daten-Parquet (ohne _sdata)


def test_dataframe_verify_and_update_checksum():
    sdf = DataFrame(df=_df(), name="x")
    assert sdf.verify() is False                    # noch keine checksum gespeichert
    digest = sdf.update_checksum()
    assert digest == sdf.sha256 and len(digest) == 64
    assert sdf.verify() is True                     # passt (Parquet deterministisch je Objekt)
    sdf.df = pd.DataFrame({"weight": [9]})          # Daten ändern -> anderer Hash
    assert sdf.verify() is False
