# -*- coding: utf-8 -*-
"""DataFrame nutzt den gemeinsamen Integritäts-Mixin (RFC 0004, Option B):
sha1/md5/sha256/size + verify/update_checksum über ``content_bytes``.

Die Hash-Basis ist die **kanonische CSV-Form** (nicht Parquet): sie ist byte-stabil
und damit portabel — derselbe Datensatz ergibt umgebungsunabhängig denselben Hash
(RFC 0004). Deshalb braucht die Integritäts-Schicht auch kein pyarrow.
"""
import pandas as pd


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
    # kanonische CSV-Form (Header + Werte, ohne Index), kein Parquet
    assert sdf.content_bytes == sdf.df.to_csv(index=False).encode("utf-8")


def test_dataframe_verify_and_update_checksum():
    sdf = DataFrame(df=_df(), name="x")
    assert sdf.verify() is False                    # noch keine checksum gespeichert
    digest = sdf.update_checksum()
    assert digest == sdf.sha256 and len(digest) == 64
    assert sdf.verify() is True                     # kanonische CSV -> deterministisch
    sdf.df = pd.DataFrame({"weight": [9]})          # Daten ändern -> anderer Hash
    assert sdf.verify() is False


def test_content_hash_is_portable_across_objects():
    """Kern von RFC 0004: gleiche Daten -> gleicher Hash, unabhängig vom Objekt/Parquet.

    Eine auf einer Maschine gespeicherte Prüfsumme verifiziert auf einer anderen —
    hier modelliert durch zwei unabhängig erzeugte DataFrames mit identischen Daten.
    """
    a = DataFrame(df=_df(), name="a")
    b = DataFrame(df=_df(), name="b")               # anderes Objekt/Name, gleiche Daten
    digest = a.update_checksum()
    assert b.sha256 == digest                       # datenidentisch -> hash-identisch


def test_content_hash_ignores_metadata():
    """Der Hash liegt auf den Daten, nicht auf den Metadaten (RFC 0004, Option B)."""
    sdf = DataFrame(df=_df(), name="x")
    before = sdf.sha256
    sdf.update_checksum()                           # schreibt checksum in die Metadaten
    sdf.metadata.set_attr("label", "annotated")     # weitere Metadaten-Änderung
    sdf.set_column("weight", unit="kg")             # Spalten-Metadaten
    assert sdf.sha256 == before                     # Daten unverändert -> Hash unverändert
    assert sdf.verify() is True


def test_content_hash_needs_no_pyarrow(monkeypatch):
    """Die Integritäts-Schicht kommt ohne pyarrow aus (CSV statt Parquet)."""
    import sdata.sclass.dataframe as dfmod
    sdf = DataFrame(df=_df(), name="x")

    def _boom(*_a, **_k):
        raise AssertionError("content_bytes darf to_parquet nicht aufrufen")

    monkeypatch.setattr(dfmod.pd.DataFrame, "to_parquet", _boom)
    assert len(sdf.sha256) == 64                     # kein to_parquet im Hash-Pfad
    assert sdf.content_bytes.startswith(b"weight,height")
