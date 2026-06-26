# -*- coding: utf-8 -*-
"""Tabellen-Schema-Validierung (PR4): sdata.schema.TableSchema sowie
DataFrame.validate_table / der DataFrame.TABLE_SCHEMA-Hook.
"""
import pandas as pd

from sdata.schema import TableSchema, AttrSpec
from sdata.sclass.dataframe import DataFrame


def _df():
    return pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})


# ----------------------------------------------------------------- validate
def test_validate_ok():
    sdf = DataFrame(df=_df(), name="x")
    sdf.set_column("weight", unit="kg")
    schema = TableSchema("t", [AttrSpec("weight", dtype="int", unit="kg")])
    rep = sdf.validate_table(schema)
    assert rep.ok
    assert rep.extra == ["height"]                 # nicht spezifiziert, aber kein Fehler


def test_validate_missing_column():
    sdf = DataFrame(df=_df(), name="x")
    schema = TableSchema("t", [AttrSpec("zzz", dtype="float")])
    rep = sdf.validate_table(schema)
    assert not rep.ok and "zzz" in rep.missing


def test_validate_dtype_mismatch():
    sdf = DataFrame(df=_df(), name="x")
    schema = TableSchema("t", [AttrSpec("weight", dtype="float")])  # ist int
    rep = sdf.validate_table(schema)
    assert not rep.ok and rep.type_errors and rep.type_errors[0][0] == "weight"


def test_validate_unit_mismatch_and_match():
    sdf = DataFrame(df=_df(), name="x")
    schema = TableSchema("t", [AttrSpec("weight", dtype="int", unit="kg")])
    assert "weight" in sdf.validate_table(schema).unit_errors   # Spalte hat "-"
    sdf.set_column("weight", unit="kg")
    assert sdf.validate_table(schema).ok                        # jetzt passend


# -------------------------------------------------------------------- apply
def test_apply_fills_annotations():
    sdf = DataFrame(df=_df(), name="x")
    schema = TableSchema("t", [AttrSpec("weight", unit="kg",
                                        ontology="bfo:Quality",
                                        description="the weight")])
    schema.apply(sdf)
    attr = sdf.get_column("weight")
    assert attr.unit == "kg"
    assert attr.ontology == "bfo:Quality"
    assert attr.description == "the weight"


def test_apply_recreates_missing_attr():
    sdf = DataFrame(df=_df(), name="x")
    sdf.column_metadata.pop("weight")              # Annotation entfernen, Spalte bleibt
    assert sdf.get_column("weight") is None
    schema = TableSchema("t", [AttrSpec("weight", dtype="int", unit="kg")])
    schema.apply(sdf)
    assert sdf.get_column("weight").unit == "kg"


def test_apply_skips_absent_column():
    sdf = DataFrame(df=_df(), name="x")
    schema = TableSchema("t", [AttrSpec("zzz", unit="kg")])     # nicht im df
    schema.apply(sdf)
    assert sdf.get_column("zzz") is None           # nichts angelegt


# ---------------------------------------------------------------- to/from dict
def test_tableschema_to_from_dict_roundtrip():
    schema = TableSchema("t", [AttrSpec("weight", dtype="int", unit="kg"),
                               AttrSpec("height", dtype="float", unit="m")])
    d = schema.to_dict()
    back = TableSchema.from_dict(d)
    assert back.name == "t"
    assert [c.name for c in back.columns] == ["weight", "height"]
    assert back._by_name["weight"].unit == "kg"


# ----------------------------------------------------- validate_table method
def test_validate_table_default_without_schema():
    sdf = DataFrame(df=_df(), name="x")
    assert sdf.validate_table().ok                 # kein Schema -> trivial gültig


def test_validate_table_explicit_schema():
    sdf = DataFrame(df=_df(), name="x")
    rep = sdf.validate_table(TableSchema("s", [AttrSpec("weight", dtype="float")]))
    assert not rep.ok


# --------------------------------------------------------- TABLE_SCHEMA hook
class _TblDataFrame(DataFrame):
    TABLE_SCHEMA = TableSchema("auto", [
        AttrSpec("weight", dtype="int", unit="kg", ontology="bfo:Quality"),
    ])


def test_table_schema_hook_applied_at_init():
    sdf = _TblDataFrame(df=_df())
    # Annotationen wurden beim Init aus dem Schema vervollständigt
    assert sdf.get_column("weight").unit == "kg"
    assert sdf.get_column("weight").ontology == "bfo:Quality"
    # validate_table() ohne Argument nutzt den Hook
    assert sdf.validate_table().ok
