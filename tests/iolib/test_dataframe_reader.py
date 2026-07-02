# -*- coding: utf-8 -*-
"""Reader-Interface für DataFrames (RFC 0009).

Deckt Protocol/ABC-Vertrag, den Eingangs-Metadaten-Vertrag (gemeinsame
``check_contract``-Funktion mit dem Writer) und die Roundtrip-Gesetze aus
RFC 0009 §6 für alle Writer/Reader-Paare ab (Parquet, Store, SQL —
Snapshot **und** ``fresh``)."""
import sqlite3

import pandas as pd
import pytest

pytest.importorskip("pyarrow")

from sdata.sclass.dataframe import DataFrame
from sdata.iolib.json1sqlitestore import JSON1SQLiteStore
from sdata.iolib.writer import ParquetWriter, StoreWriter, SqlWriter, check_contract
from sdata.iolib.reader import (
    DataFrameReader,
    BaseDataFrameReader,
    ParquetReader,
    StoreReader,
    SqlReader,
)


def _sdf(name="MeasureSet"):
    df = pd.DataFrame({"force": [5000.0, 6000.0], "stroke": [2.4, 2.5]})
    sdf = DataFrame(df=df, name=name, description="Beispieldaten")
    sdf.set_column("force", unit="N", label="Kraft")
    sdf.set_column("stroke", unit="mm")
    sdf.metadata.add("license", "CC-BY-4.0")
    return sdf


def _assert_roundtrip(back, sdf):
    """Identitätsbegriff aus RFC 0009 §6: Daten + Metadaten + Spaltensemantik."""
    pd.testing.assert_frame_equal(back.df.reset_index(drop=True),
                                  sdf.df.reset_index(drop=True))
    assert back.sname == sdf.sname
    assert str(back.suuid) == str(sdf.suuid)
    assert back.description == sdf.description
    assert back.metadata.get("license").value == "CC-BY-4.0"
    assert back.column_units == sdf.column_units
    assert back.get_column("force").label == "Kraft"


# ------------------------------------------------------------- Protocol / ABC

def test_reader_protocol_is_structural():
    assert isinstance(ParquetReader("x.spq"), DataFrameReader)


def test_base_reader_is_abstract():
    with pytest.raises(TypeError):
        BaseDataFrameReader()


# -------------------------------------------------- Parquet (fsspec, pyarrow)

def test_parquet_roundtrip(tmp_path):
    sdf = _sdf()
    uri = str(tmp_path / "run.spq")
    ParquetWriter(uri).write(sdf)
    with ParquetReader(uri) as r:
        back = r.read()
    _assert_roundtrip(back, sdf)


def test_parquet_reader_rejects_selector(tmp_path):
    uri = str(tmp_path / "run.spq")
    ParquetWriter(uri).write(_sdf())
    with pytest.raises(ValueError, match="selector"):
        ParquetReader(uri).read("something")


# --------------------------------------------------------- Eingangs-Vertrag

def test_reader_contract_ok_and_violated(tmp_path):
    sdf = _sdf()
    uri = str(tmp_path / "run.spq")
    ParquetWriter(uri).write(sdf)
    # erfüllt
    r = ParquetReader(uri, require_metadata=("license",), require_units=("force",))
    assert r.read().sname == sdf.sname
    # verletzt -> ValueError nennt die fehlenden Schlüssel, Rolle "reader"
    r2 = ParquetReader(uri, require_metadata=("doi",))
    with pytest.raises(ValueError, match=r"reader contract violated.*metadata=\['doi'\]"):
        r2.read()


def test_check_contract_shared_with_writer():
    # dieselbe Funktion trägt beide Rollen (RFC 0009: eine Vertragssemantik)
    with pytest.raises(ValueError, match="writer contract violated"):
        check_contract(_sdf(), require_columns=("nope",), role="writer")


# ------------------------------------------------------------- Store (JSON1)

def test_store_roundtrip_by_suuid_sname_and_id(tmp_path):
    sdf = _sdf()
    db = str(tmp_path / "runs.db")
    with StoreWriter(db) as w:
        rcpt = w.write(sdf)
    with StoreReader(db) as r:
        _assert_roundtrip(r.read(str(sdf.suuid)), sdf)        # suuid-str
        _assert_roundtrip(r.read(sdf.suuid), sdf)             # suuid-Objekt/str-Property
        _assert_roundtrip(r.read(sdf.sname), sdf)             # sname-Fallback
        _assert_roundtrip(r.read(rcpt.detail["record_id"]), sdf)  # int-Record-ID


def test_store_reader_unknown_selector(tmp_path):
    db = str(tmp_path / "runs.db")
    with StoreWriter(db) as w:
        w.write(_sdf())
    with StoreReader(db) as r:
        with pytest.raises(KeyError):
            r.read("does-not-exist")


def test_store_reader_borrowed_store_stays_open(tmp_path):
    store = JSON1SQLiteStore(str(tmp_path / "runs.db"))
    with StoreWriter(store) as w:
        w.write(_sdf())
    with StoreReader(store) as r:                     # übergebener Store: not owned
        assert r.read(_sdf().sname).sname == _sdf().sname
    assert store.count() == 1                         # Verbindung ist noch offen
    store.conn.close()


def test_store_iter_skips_foreign_records(tmp_path):
    sdf_a, sdf_b = _sdf("a"), _sdf("b")
    db = str(tmp_path / "runs.db")
    with StoreWriter(db) as w:
        w.write(sdf_a)
        w.write(sdf_b)
        w._store.insert({"_sdata_name": "fremd", "note": "kein DataFrame"})
    with StoreReader(db) as r:
        names = sorted(x.name for x in r.iter())
    assert names == ["a", "b"]                        # Fremd-Record übersprungen


# ------------------------------------------------------------------ SQL (DBAPI)

def test_sql_roundtrip_snapshot(tmp_path):
    sdf = _sdf()
    conn = sqlite3.connect(str(tmp_path / "runs.sqlite"))
    with SqlWriter(conn, table="runs") as w:
        w.write(sdf)
    with SqlReader(conn) as r:
        back = r.read(str(sdf.suuid))
    _assert_roundtrip(back, sdf)
    # Selektor über sname funktioniert ebenfalls
    with SqlReader(conn) as r:
        assert r.read(sdf.sname).sname == sdf.sname
    conn.close()


def test_sql_reader_unknown_selector(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "runs.sqlite"))
    with SqlWriter(conn, table="runs") as w:
        w.write(_sdf())
    with pytest.raises(KeyError, match="sdata_dataframe_meta"):
        SqlReader(conn).read("unknown")
    conn.close()


def test_sql_reader_fresh_reads_cumulative_table(tmp_path):
    sdf = _sdf()
    conn = sqlite3.connect(str(tmp_path / "runs.sqlite"))
    with SqlWriter(conn, table="runs") as w:          # zweimal append: 2 + 2 Zeilen
        w.write(sdf)
        w.write(sdf)
    with SqlReader(conn, fresh=True) as r:
        back = r.read(str(sdf.suuid))
    assert len(back.df) == 4                          # aktueller Tabellenstand
    assert back.column_units == sdf.column_units      # Metadaten aus dem Snapshot
    # Snapshot-Sicht bleibt unverändert beim Schreibstand
    with SqlReader(conn) as r:
        assert len(r.read(str(sdf.suuid)).df) == 2
    conn.close()


# ------------------------------------------------ Batch: write_group/read_group

def test_write_group_and_read_group_store(tmp_path):
    from sdata.sclass.dataframegroup import DataFrameGroup
    from sdata.iolib.writer import write_group
    from sdata.iolib.reader import read_group

    a, b = _sdf("A"), _sdf("B")
    group = DataFrameGroup(name="batch")
    group.add(a, key="A")
    group.add(b, key="B")

    db = str(tmp_path / "group.db")
    receipts = write_group(StoreWriter(db), group)       # eine Senke, eine Transaktion
    assert len(receipts) == 2
    assert {r.sname for r in receipts} == {a.sname, b.sname}

    back = read_group(StoreReader(db), [a.sname, b.sname])
    assert sorted(back.list_dataframes()) == [a.sname, b.sname]
    assert back.get(a.sname).column_units == a.column_units
