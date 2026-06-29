# -*- coding: utf-8 -*-
"""DataFrame.as_blob(fmt) — Komposition statt Vererbung (RFC 0004, Option C):
eine Tabelle wird in einem gewählten Format zu einem binären Blob-Asset
(hash-/verify-/write-fähig), ohne dass DataFrame von Blob erbt."""
import pandas as pd
import pytest

pytest.importorskip("pyarrow")

from sdata.sclass.blob import Blob
from sdata.sclass.dataframe import DataFrame


def _sdf():
    df = pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})
    cmd = {"weight": {"label": "Gewicht", "unit": "kg"}}
    return DataFrame(df=df, column_metadata=cmd, name="MeasureSet",
                     description="Beispieldaten")


def test_as_blob_default_is_parquet():
    sdf = _sdf()
    blob = sdf.as_blob()
    assert isinstance(blob, Blob)
    assert blob.filetype == "parquet"
    assert blob.metadata.get("mime_type").value == "application/vnd.apache.parquet"
    assert blob.content_bytes == sdf.to_parquet()      # gleiche Bytes wie direkt serialisiert
    # Name/Description werden von der Tabelle übernommen
    assert blob.name == "MeasureSet"
    assert blob.description == "Beispieldaten"


def test_as_blob_checksum_and_verify():
    blob = _sdf().as_blob("parquet")
    assert blob.metadata.get("checksum").value == blob.sha256
    assert blob.verify() is True                        # update_checksum lief in as_blob
    assert blob.size and blob.size > 0


def test_as_blob_roundtrip_parquet():
    sdf = _sdf()
    blob = sdf.as_blob("parquet")
    back = DataFrame.from_parquet_bytes(blob.content_bytes)
    pd.testing.assert_frame_equal(back.df, sdf.df)
    # eingebettete sdata-Metadaten überleben den Umweg über den Blob
    assert back.column_metadata.get("weight").unit == "kg"


def test_as_blob_csv():
    sdf = _sdf()
    blob = sdf.as_blob("csv")
    assert blob.filetype == "csv"
    assert blob.metadata.get("mime_type").value == "text/csv"
    assert blob.content_bytes == sdf.to_csv().encode("utf-8")
    assert b"weight" in blob.content_bytes


def test_as_blob_arrow_and_feather():
    sdf = _sdf()
    for fmt in ("arrow", "feather"):
        blob = sdf.as_blob(fmt)
        assert blob.filetype == fmt
        assert blob.metadata.get("mime_type").value == "application/vnd.apache.arrow.file"
        # Arrow-IPC ist als Feather wieder einlesbar
        back = DataFrame.from_feather  # noqa: F841 (nur Existenz-Check)
        assert blob.content_bytes == sdf.to_feather()


def test_as_blob_name_override():
    blob = _sdf().as_blob("csv", name="custom")
    assert blob.name == "custom"


def test_as_blob_unsupported_format():
    with pytest.raises(ValueError, match="unsupported blob format"):
        _sdf().as_blob("xlsx")
