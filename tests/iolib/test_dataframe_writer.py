# -*- coding: utf-8 -*-
"""Writer-Interface für DataFrames (RFC 0007).

Deckt Protocol/ABC-Vertrag, die ``ensure_sdata``-Bridge und die konkreten Writer
(Parquet, Store, SQL, Graph) ab — inkl. der im Review behobenen Punkte:
F1 (Store-Auffindbarkeit trotz ``to_dict``-Shape), F2 (Graph schreibt die Datei
wirklich), F3/F4 (atomarer SQL-Write, ``str(suuid)``), F6 (einheitliches
``WriteReceipt``)."""
import json
import os
import sqlite3

import pandas as pd
import pytest

pytest.importorskip("pyarrow")

from sdata.sclass.dataframe import DataFrame
from sdata.iolib.json1sqlitestore import JSON1SQLiteStore
from sdata.iolib.writer import (
    WriteReceipt,
    DataFrameWriter,
    BaseDataFrameWriter,
    ParquetWriter,
    StoreWriter,
    SqlWriter,
    GraphWriter,
    ensure_sdata,
    write_with_provenance,
)


def _sdf(name="MeasureSet"):
    df = pd.DataFrame({"force": [5000.0, 6000.0], "stroke": [2.4, 2.5]})
    sdf = DataFrame(df=df, name=name, description="Beispieldaten")
    sdf.set_column("force", unit="N", label="Kraft")
    sdf.set_column("stroke", unit="mm")
    sdf.metadata.add("license", "CC-BY-4.0")
    return sdf


# --------------------------------------------------------------- Bridge / ABC

def test_ensure_sdata_passthrough():
    sdf = _sdf()
    assert ensure_sdata(sdf) is sdf


def test_ensure_sdata_wraps_plain_pandas_and_restores_attrs():
    sdf = _sdf()
    plain = sdf.df.copy()
    plain.attrs["_sdata"] = {"metadata": sdf.metadata.to_dict(),
                             "column_metadata": sdf.column_metadata.to_dict(),
                             "description": sdf.description}
    wrapped = ensure_sdata(plain)
    assert isinstance(wrapped, DataFrame)
    assert wrapped.description == "Beispieldaten"
    assert wrapped.column_units["force"] == "N"


def test_ensure_sdata_plain_pandas_without_attrs():
    wrapped = ensure_sdata(pd.DataFrame({"a": [1, 2]}))
    assert isinstance(wrapped, DataFrame)
    assert list(wrapped.df.columns) == ["a"]


def test_ensure_sdata_typeerror():
    with pytest.raises(TypeError):
        ensure_sdata(42)


def test_writer_protocol_is_structural():
    assert isinstance(ParquetWriter("x.spq"), DataFrameWriter)


def test_contract_ok_and_violations():
    w = ParquetWriter("x.spq", require_metadata=("license",),
                      require_columns=("force",), require_units=("force",))
    w._check_contract(_sdf())  # erfüllt -> kein Fehler

    bad = ParquetWriter("x.spq", require_metadata=("doi",))
    with pytest.raises(ValueError, match="metadata=\\['doi'\\]"):
        bad._check_contract(_sdf())

    bad_c = ParquetWriter("x.spq", require_columns=("nope",))
    with pytest.raises(ValueError, match="columns=\\['nope'\\]"):
        bad_c._check_contract(_sdf())

    bad_u = ParquetWriter("x.spq", require_units=("stroke_missing",))
    with pytest.raises(ValueError, match="units="):
        bad_u._check_contract(_sdf())


def test_base_is_abstract():
    with pytest.raises(TypeError):
        BaseDataFrameWriter()  # abstrakte _write_impl


# ------------------------------------------------------------------- Parquet

def test_parquet_writer_roundtrip(tmp_path):
    sdf = _sdf()
    out = str(tmp_path / "run.spq")
    with ParquetWriter(out) as w:
        rcpt = w.write(sdf)
    assert isinstance(rcpt, WriteReceipt)
    assert rcpt.backend == "parquet" and rcpt.target == out
    assert rcpt.suuid == str(sdf.suuid) and rcpt.detail["bytes"] > 0

    with open(out, "rb") as fh:
        back = DataFrame.from_parquet_bytes(fh.read())
    pd.testing.assert_frame_equal(back.df, sdf.df)
    assert back.column_units["force"] == "N"          # Einheiten überleben (RFC 0006)
    assert back.description == "Beispieldaten"


def test_parquet_writer_accepts_plain_pandas(tmp_path):
    out = str(tmp_path / "plain.spq")
    ParquetWriter(out).write(pd.DataFrame({"a": [1, 2, 3]}))
    assert os.path.exists(out)


# --------------------------------------------------------------------- Store

def test_store_writer_roundtrip_and_findable():
    """F1: trotz genesteter ``to_dict``-Struktur ist das Objekt per suuid/sname auffindbar."""
    sdf = _sdf()
    store = JSON1SQLiteStore(":memory:")
    w = StoreWriter(store)              # übergebener Store -> wird nicht geschlossen
    rcpt = w.write(sdf)

    got = store.get(rcpt.target)
    assert got["_sdata_sname"] == sdf.sname          # top-level, indiziert
    assert got["_sdata_suuid"] == str(sdf.suuid)
    back = DataFrame.from_dict(got["sdata"])          # verlustfrei unter "sdata"
    pd.testing.assert_frame_equal(back.df, sdf.df)

    # der eigentliche F1-Beweis: Store-Query über die generierten Spalten trifft
    assert store.get_id_by_key("_sdata_suuid", str(sdf.suuid)) == rcpt.target
    assert store.get_id_by_key("_sdata_sname", sdf.sname) == rcpt.target


def test_store_writer_owns_and_closes_path_target(tmp_path):
    db = str(tmp_path / "runs.db")
    with StoreWriter(db) as w:                          # Pfad-Ziel -> Store gehört dem Writer
        ra = w.write(_sdf("Alpha"))
        rb = w.write(_sdf("Beta"))
    # nach close ist die DB persistiert und über eine NEUE Verbindung lesbar
    store = JSON1SQLiteStore(db)
    assert store.get_id_by_key("_sdata_suuid", ra.suuid) is not None
    assert store.get_id_by_key("_sdata_sname", rb.sname) is not None
    store.conn.close()


# ----------------------------------------------------------------------- SQL

def test_sql_writer_relational_roundtrip_and_meta():
    sdf = _sdf()
    conn = sqlite3.connect(":memory:")
    with SqlWriter(conn, table="runs") as w:
        rcpt = w.write(sdf)
    assert rcpt.backend == "sql" and rcpt.target == "runs"

    data = pd.read_sql("SELECT * FROM runs", conn)
    pd.testing.assert_frame_equal(data.reset_index(drop=True), sdf.df.reset_index(drop=True))

    row = conn.execute(
        "SELECT suuid, sname, sdata FROM runs__sdata").fetchone()
    assert row[0] == str(sdf.suuid) and row[1] == sdf.sname
    back = DataFrame.from_dict(json.loads(row[2]))
    pd.testing.assert_frame_equal(back.df, sdf.df)
    conn.close()


def test_sql_writer_via_sqlalchemy_raw_connection():
    """Interop-Beleg (RFC 0007 §10): SqlWriter läuft auf einer DBAPI-Verbindung aus
    ``engine.raw_connection()`` — nicht auf einem SQLAlchemy-Engine/Connection direkt."""
    sa = pytest.importorskip("sqlalchemy")
    import warnings

    sdf = _sdf()
    raw = sa.create_engine("sqlite://").raw_connection()   # in-memory, gepoolt
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                    # pandas: "Other DBAPI2 objects…"
        with SqlWriter(raw, table="runs") as w:
            rcpt = w.write(sdf)
    assert rcpt.backend == "sql"
    assert raw.execute("SELECT count(*) FROM runs").fetchone()[0] == len(sdf.df)
    row = raw.execute("SELECT suuid, sname FROM runs__sdata").fetchone()
    assert row[0] == str(sdf.suuid) and row[1] == sdf.sname
    raw.close()


def test_sql_writer_atomicity_rolls_back_pending_meta():
    """F3: scheitert ``to_sql`` bei bereits geschriebener (pending) Metazeile,
    wird diese zurückgerollt — keine verwaiste Metadatenzeile."""
    sdf = _sdf()
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE runs(force REAL)")     # existiert -> if_exists='fail' wirft
    w = SqlWriter(conn, table="runs", if_exists="fail")
    with pytest.raises(ValueError):
        w.write(sdf)                                   # Metazeile pending, dann to_sql-Fehler
    # das rollback im Writer hat die pending Metazeile verworfen
    assert conn.execute("SELECT count(*) FROM runs__sdata").fetchone()[0] == 0
    conn.close()


# --------------------------------------------------------------------- Graph

def test_graph_writer_writes_jsonld_file(tmp_path):
    """F2: der Einzeldatei-Modus schreibt die Datei wirklich."""
    sdf = _sdf()
    out = str(tmp_path / "run.jsonld")
    rcpt = GraphWriter(out, fmt="json-ld").write(sdf)
    assert os.path.exists(out)
    doc = json.loads(open(out, encoding="utf-8").read())
    assert doc  # nicht leer
    assert rcpt.backend == "graph" and rcpt.target == out


def test_graph_writer_turtle_string_when_no_target():
    rcpt = GraphWriter(fmt="turtle").write(_sdf())
    assert rcpt.target is None
    assert isinstance(rcpt.detail["text"], str) and rcpt.detail["text"]


def test_graph_writer_named_graphs_guarded_without_rdflib():
    import sdata.semantic as sem
    if sem._rdflib is not None:  # pragma: no cover
        pytest.skip("rdflib installed — Guard nicht auslösbar")
    with pytest.raises(ImportError, match="sdata\\[rdf\\]"):
        GraphWriter("x.nq", named_graphs=True)


# --------------------------------------------------------------- Provenance

def test_write_with_provenance_injects_into_metadata(tmp_path):
    sdf = _sdf()
    out = str(tmp_path / "prov.spq")
    write_with_provenance(ParquetWriter(out), sdf,
                          {"wasDerivedFrom": "raw://batch-42"})
    assert sdf.metadata.get("wasDerivedFrom").value == "raw://batch-42"
    with open(out, "rb") as fh:
        back = DataFrame.from_parquet_bytes(fh.read())
    assert back.metadata.get("wasDerivedFrom").value == "raw://batch-42"
