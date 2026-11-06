# -*- coding: utf-8 -*-
"""Nicht-native dtype-Werte (timestamp, date, bytes …) überleben jede
JSON-basierte Serialisierung: ``to_json``, Parquet, Data Package, HDF5."""
import datetime
import json
import zipfile
from decimal import Decimal

import pandas as pd
import pytest

from sdata import dtypes
from sdata.base import Base
from sdata.sclass.dataframe import DataFrame

# dtype -> (Eingabewert, erwarteter Wert nach dem Rücklesen)
CASES = {
    "timestamp": ("2026-11-06T09:00:00+01:00", None),
    "date": (datetime.date(2026, 11, 6), datetime.date(2026, 11, 6)),
    "time": (datetime.time(9, 30, 15), datetime.time(9, 30, 15)),
    "duration": (datetime.timedelta(hours=1, seconds=5),
                 datetime.timedelta(hours=1, seconds=5)),
    "decimal": (Decimal("1.2345"), Decimal("1.2345")),
    "bytes": (b"\x00\x01sdata", b"\x00\x01sdata"),
    "complex": (complex(1, -2), complex(1, -2)),
    "langstring": (dtypes.LangString("Temperatur", "de"),
                   dtypes.LangString("Temperatur", "de")),
    "json": ({"a": [1, 2]}, {"a": [1, 2]}),
    "uri": ("https://example.org/x", "https://example.org/x"),
    "floatlist": ([1.0, 2.5], [1.0, 2.5]),
    "list": (["a", "b"], ["a", "b"]),
}
DTYPES = sorted(CASES)


def _expected(dtype):
    value, expected = CASES[dtype]
    return dtypes.get(dtype).coerce(value) if expected is None else expected


def _frame(dtype):
    sdf = DataFrame(df=pd.DataFrame({"time": [1.0, 2.0], "temperature": [2.4, 5.2]}),
                    name="dtype-probe")
    sdf.metadata.add("probe", CASES[dtype][0], dtype=dtype)
    return sdf


def _check(restored, dtype):
    attr = restored.metadata.get("probe")
    assert attr.dtype == dtype
    if dtype == "timestamp":                # JSON-Form ist UTC: gleicher Zeitpunkt
        assert attr.value.utc == _expected(dtype).utc
    else:
        assert attr.value == _expected(dtype)


def test_cases_cover_all_registered_dtypes():
    natives = {"str", "int", "float", "bool"}
    assert set(dtypes.names()) - natives == set(CASES)


@pytest.mark.parametrize("dtype", DTYPES)
def test_base_to_json_roundtrip(dtype):
    b = Base(name="probe")
    b.metadata.add("probe", CASES[dtype][0], dtype=dtype)
    s = b.to_json()
    json.loads(s)
    _check(Base.from_json(s), dtype)


@pytest.mark.parametrize("dtype", DTYPES)
def test_base_to_json_file(dtype, tmp_path):
    b = Base(name="probe")
    b.metadata.add("probe", CASES[dtype][0], dtype=dtype)
    p = tmp_path / "b.json"
    b.to_json(filepath=str(p))
    _check(Base.from_json(p.read_text()), dtype)


@pytest.mark.parametrize("dtype", DTYPES)
def test_dataframe_to_json_roundtrip(dtype):
    sdf = _frame(dtype)
    _check(DataFrame.from_json(sdf.to_json()), dtype)


@pytest.mark.parametrize("dtype", DTYPES)
def test_parquet_roundtrip(dtype, tmp_path):
    pytest.importorskip("pyarrow")
    sdf = _frame(dtype)
    _check(DataFrame.from_parquet_bytes(sdf.to_parquet()), dtype)
    sdf.to_parquet(path=str(tmp_path))
    _check(DataFrame.from_parquet(str(tmp_path / f"{sdf.sname}.spq")), dtype)


@pytest.mark.parametrize("fmt", ["csv", "parquet"])
@pytest.mark.parametrize("dtype", DTYPES)
def test_datapackage_roundtrip(dtype, fmt, tmp_path):
    if fmt == "parquet":
        pytest.importorskip("pyarrow")
    sdf = _frame(dtype)
    filepath = sdf.to_datapackage(path=str(tmp_path), fmt=fmt)
    with zipfile.ZipFile(filepath) as zf:
        json.loads(zf.read("datapackage.json"))
        json.loads(zf.read(f"{sdf.sname}.meta.jsonld"))
    _check(DataFrame.from_datapackage(filepath), dtype)


@pytest.mark.parametrize("dtype", DTYPES)
def test_hdf_roundtrip(dtype, tmp_path):
    pytest.importorskip("h5py")
    sdf = _frame(dtype)
    filepath = str(tmp_path / "probe.h5")
    sdf.to_hdf(filename=filepath)
    _check(DataFrame.from_hdf(filepath), dtype)


@pytest.mark.parametrize("dtype", DTYPES)
def test_arrow_roundtrip(dtype):
    pytest.importorskip("pyarrow")
    sdf = _frame(dtype)
    _check(DataFrame.from_arrow(sdf.to_arrow()), dtype)


@pytest.mark.parametrize("dtype", DTYPES)
def test_store_writer_roundtrip(dtype, tmp_path):
    from sdata.iolib.reader import StoreReader
    from sdata.iolib.writer import StoreWriter
    sdf = _frame(dtype)
    db = str(tmp_path / "store.db")
    writer = StoreWriter(db)
    writer.write(sdf)
    writer.close()
    reader = StoreReader(db)
    try:
        _check(reader.read(sdf.sname), dtype)
    finally:
        reader.close()


@pytest.mark.parametrize("dtype", DTYPES)
def test_sql_writer_roundtrip(dtype):
    import sqlite3
    from sdata.iolib.reader import SqlReader
    from sdata.iolib.writer import SqlWriter
    sdf = _frame(dtype)
    conn = sqlite3.connect(":memory:")
    writer = SqlWriter(conn, table="probe")
    writer.write(sdf)
    writer.flush()
    _check(SqlReader(conn).read(sdf.sname), dtype)


def test_json1_store_accepts_dtype_values(tmp_path):
    from sdata.iolib.json1sqlitestore import JSON1SQLiteStore
    with JSON1SQLiteStore(str(tmp_path / "s.db")) as store:
        rid = store.insert({"d": datetime.date(2026, 11, 6)})
        store.set_path(rid, "$.b", b"\x00\x01")
        store.insert_path(rid, "$.t", datetime.time(9, 30))
        store.replace_path(rid, "$.d", Decimal("1.5"))
        assert store.get(rid) == {"d": "1.5", "b": "AAE=", "t": "09:30:00"}
