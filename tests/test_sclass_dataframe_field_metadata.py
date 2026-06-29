# -*- coding: utf-8 -*-
"""Native Per-Spalten-Field-Metadata in Arrow/Feather (zusätzlich zum _sdata-Blob)."""
import pandas as pd
import pytest

pa = pytest.importorskip("pyarrow")

from sdata.sclass.dataframe import DataFrame


def _df():
    return pd.DataFrame({"weight": [10, 20, 30], "height": [1.5, 1.6, 1.7]})


def test_to_arrow_attaches_per_field_metadata():
    sdf = DataFrame(df=_df(), name="x")
    sdf.set_column("weight", unit="kg", label="Gewicht", ontology="bfo:Quality")
    # height bleibt un-annotiert
    schema = sdf.to_arrow().schema
    wmeta = schema.field("weight").metadata
    assert wmeta[b"unit"] == b"kg"
    assert wmeta[b"label"] == b"Gewicht"
    assert wmeta[b"ontology"] == b"bfo:Quality"
    assert schema.field("height").metadata is None       # keine Default-Annotation
    assert b"_sdata" in (schema.metadata or {})           # Blob weiterhin vorhanden


def test_field_metadata_for_none_cases():
    sdf = DataFrame(df=_df(), name="x")
    assert sdf._field_metadata_for("height") is None      # nur dtype-Default ("-"/"")
    assert sdf._field_metadata_for("missing") is None     # keine solche Spalte


def test_from_arrow_merges_field_metadata_without_blob():
    # externe Arrow-Tabelle: nur Per-Field-Metadata, KEIN _sdata-Blob
    t = pa.Table.from_pandas(_df())
    fields = []
    for f in t.schema:
        if f.name == "weight":
            f = f.with_metadata({b"unit": b"kg", b"label": b"Gewicht"})
        fields.append(f)
    table = pa.Table.from_arrays(list(t.columns), schema=pa.schema(fields))
    assert b"_sdata" not in (table.schema.metadata or {})  # kein Blob
    back = DataFrame.from_arrow(table)
    assert back.get_column("weight").unit == "kg"
    assert back.get_column("weight").label == "Gewicht"


def test_arrow_roundtrip_preserves_field_metadata():
    sdf = DataFrame(df=_df(), name="x")
    sdf.set_column("weight", unit="kg")
    back = DataFrame.from_arrow(sdf.to_arrow())
    assert back.get_column("weight").unit == "kg"


def test_feather_carries_field_metadata(tmp_path):
    import pyarrow.feather as feather
    sdf = DataFrame(df=_df(), name="x")
    sdf.set_column("height", unit="m", ontology="bfo:Quality")
    fp = sdf.to_feather(path=str(tmp_path))
    table = feather.read_table(fp)                         # nativ lesbar
    assert table.schema.field("height").metadata[b"unit"] == b"m"
    back = DataFrame.from_feather(fp)
    assert back.get_column("height").unit == "m"
