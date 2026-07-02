# -*- coding: utf-8 -*-
"""ParquetWriter/-Reader Verzeichnis-Modus (RFC 0007 F5 / RFC 0011 §5.3).

Mehrere ``write`` in ein Verzeichnis (`<sname>.spq` je Mitglied) statt Überschreiben
derselben URI; symmetrisch über ``keys()``/``read_group`` zurücklesbar.
"""
import pandas as pd
import pytest

pytest.importorskip("pyarrow")
pytest.importorskip("fsspec")

from sdata.sclass.dataframe import DataFrame
from sdata.sclass.dataframegroup import DataFrameGroup
from sdata.iolib.writer import ParquetWriter, write_group
from sdata.iolib.reader import ParquetReader, read_group


def _group():
    a = DataFrame(df=pd.DataFrame({"x": [1, 2]}), name="aaa")
    b = DataFrame(df=pd.DataFrame({"y": [3, 4]}), name="bbb",
                  unit_system=["kN", "mm", "ms"])
    g = DataFrameGroup(name="g")
    g.add(a)
    g.add(b)
    return g, a, b


def test_write_group_directory_one_file_per_member(tmp_path):
    g, a, b = _group()
    d = str(tmp_path / "run")
    receipts = write_group(ParquetWriter(d, directory=True), g)
    assert {r.target.rsplit("/", 1)[-1] for r in receipts} == {
        a.sname + ".spq", b.sname + ".spq"}
    assert sorted(p.name for p in (tmp_path / "run").glob("*.spq")) == sorted(
        [a.sname + ".spq", b.sname + ".spq"])


def test_directory_roundtrip_via_keys_and_read_group(tmp_path):
    g, a, b = _group()
    d = str(tmp_path / "run")
    write_group(ParquetWriter(d, directory=True), g)
    reader = ParquetReader(d, directory=True)
    assert reader.keys() == sorted([a.sname, b.sname])
    back = read_group(reader, reader.keys())
    assert back.get(a.sname).df["x"].tolist() == [1, 2]
    # unit_system reist mit (RFC 0014)
    from sdata.units import UnitSystem
    assert back.get(b.sname).unit_system == UnitSystem(["kN", "mm", "ms"])


def test_directory_read_single_member_by_sname(tmp_path):
    g, a, b = _group()
    d = str(tmp_path / "run")
    write_group(ParquetWriter(d, directory=True), g)
    got = ParquetReader(d, directory=True).read(b.sname)
    assert got.df["y"].tolist() == [3, 4]


def test_single_file_mode_overwrites(tmp_path):
    # Default-Modus unverändert: mehrere write auf dieselbe URI überschreiben
    _, a, b = _group()
    fp = str(tmp_path / "one.spq")
    with ParquetWriter(fp) as w:
        w.write(a)
        w.write(b)
    back = ParquetReader(fp).read()
    assert back.df["y"].tolist() == [3, 4]                # zuletzt geschrieben: b
    assert list((tmp_path).glob("*.spq")) == [tmp_path / "one.spq"]


def test_directory_reader_requires_key(tmp_path):
    g, _, _ = _group()
    d = str(tmp_path / "run")
    write_group(ParquetWriter(d, directory=True), g)
    with pytest.raises(ValueError):
        ParquetReader(d, directory=True).read()          # ohne Key


def test_single_file_reader_rejects_selector(tmp_path):
    _, a, _ = _group()
    fp = str(tmp_path / "one.spq")
    ParquetWriter(fp).write(a)
    with pytest.raises(ValueError):
        ParquetReader(fp).read("something")              # Einzeldatei nimmt keinen Selektor


def test_keys_requires_directory_mode(tmp_path):
    with pytest.raises(ValueError):
        ParquetReader(str(tmp_path / "x.spq")).keys()
