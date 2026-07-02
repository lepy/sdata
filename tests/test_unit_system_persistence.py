# -*- coding: utf-8 -*-
"""Persistenz des Ziel-Einheitensystems (RFC 0014).

`DataFrame.unit_system` liegt als reserviertes Metadaten-Feld `_sdata_unit_system`
und reist dadurch durch alle Serialisierungspfade (dict/parquet/hdf/JSON-LD) mit.
"""
import pandas as pd
import pytest

from sdata.sclass.dataframe import DataFrame
from sdata.units import UnitSystem


def _sdf():
    return DataFrame(df=pd.DataFrame({"f": [1.0, 2.0]}), name="t",
                     unit_system=["kN", "mm", "ms"])


def test_set_via_constructor_and_getter_returns_unitsystem():
    sdf = _sdf()
    assert isinstance(sdf.unit_system, UnitSystem)
    assert sdf.unit_system == UnitSystem(["kN", "mm", "ms"])
    assert sdf.unit_system.units == ["kN", "mm", "ms"]


def test_setter_accepts_list_and_unitsystem():
    sdf = DataFrame(df=pd.DataFrame({"f": [1.0]}), name="t")
    assert sdf.unit_system is None                      # Default: None (Getter-None-Zweig)
    sdf.unit_system = ["m", "s", "kg"]
    assert sdf.unit_system == UnitSystem(["m", "s", "kg"])
    sdf.unit_system = UnitSystem(["kN", "mm", "ms"])
    assert sdf.unit_system == UnitSystem(["kN", "mm", "ms"])


def test_clear_removes_reserved_attr():
    sdf = _sdf()
    assert DataFrame.SDATA_UNIT_SYSTEM in sdf.metadata
    sdf.unit_system = None
    assert sdf.unit_system is None
    assert DataFrame.SDATA_UNIT_SYSTEM not in sdf.metadata


def test_reserved_attr_not_a_user_attribute():
    sdf = _sdf()
    assert DataFrame.SDATA_UNIT_SYSTEM not in sdf.metadata.user_attributes
    assert DataFrame.SDATA_UNIT_SYSTEM in sdf.metadata.sdata_attributes


def test_roundtrip_dict():
    back = DataFrame.from_dict(_sdf().to_dict())
    assert back.unit_system == UnitSystem(["kN", "mm", "ms"])


def test_roundtrip_parquet(tmp_path):
    fp = _sdf().to_parquet(path=str(tmp_path))
    back = DataFrame.from_parquet(fp)
    assert back.unit_system == UnitSystem(["kN", "mm", "ms"])


def test_roundtrip_no_unit_system_stays_none():
    sdf = DataFrame(df=pd.DataFrame({"f": [1.0]}), name="t")
    back = DataFrame.from_dict(sdf.to_dict())
    assert back.unit_system is None


def test_jsonld_emits_unit_system():
    doc = _sdf().to_jsonld()
    assert doc.get("sdata:unitSystem") == ["kN", "mm", "ms"]


def test_convert_uses_persisted_unit_system():
    sdf = DataFrame(df=pd.DataFrame({"f": [1000.0]}), name="c",
                    unit_system=["kN", "mm", "ms"])
    sdf.set_column("f", unit="N")
    out = sdf.convert()                                  # kein Argument -> nutzt persistiertes System
    assert out.get_column("f").unit == "kN"
    assert out.df["f"].tolist() == [1.0]
    assert out.unit_system == UnitSystem(["kN", "mm", "ms"])


def test_convert_sets_unit_system_on_result():
    sdf = DataFrame(df=pd.DataFrame({"f": [1000.0]}), name="c")
    sdf.set_column("f", unit="N")
    assert sdf.unit_system is None
    out = sdf.convert(["kN", "mm", "ms"])
    assert out.unit_system == UnitSystem(["kN", "mm", "ms"])


def test_unitsystem_equality_and_hash():
    a, b = UnitSystem(["kN", "mm", "ms"]), UnitSystem(["kN", "mm", "ms"])
    assert a == b and hash(a) == hash(b)
    assert a != UnitSystem(["m", "s", "kg"])
    assert a != "not a system"
    assert len({a, b}) == 1


@pytest.mark.parametrize("_", [0])
def test_roundtrip_hdf(tmp_path, _):
    pytest.importorskip("h5py")
    fp = _sdf().to_hdf(path=str(tmp_path))
    back = DataFrame.from_hdf(fp)
    assert back.unit_system == UnitSystem(["kN", "mm", "ms"])
