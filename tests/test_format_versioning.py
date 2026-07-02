# -*- coding: utf-8 -*-
"""Format-Versionierung (RFC 0010).

Deckt das neue Feld ``_sdata_format_version``, die Toleranzregeln (fehlend=v1 /
gleich / älter->migrieren / neuer->Warnung bzw. strict->Fehler) und den einen
Choke-Point (``Base.from_dict``, ``DataFrame.from_dict``, ``_restore_from_attrs``)
ab."""
import warnings

import pandas as pd
import pytest

from sdata.base import Base
from sdata.sclass.dataframe import DataFrame
import sdata.format as fmt
from sdata.format import (
    CURRENT_FORMAT_VERSION,
    SDATA_FORMAT_VERSION_KEY,
    FormatVersionWarning,
    IncompatibleFormatError,
    read_format_version,
    ensure_compatible,
    register_migration,
)


@pytest.fixture(autouse=True)
def _clean_migrations():
    """Migrations-Registry pro Test isolieren (Tests registrieren Wegwerf-Stufen)."""
    saved = dict(fmt._MIGRATIONS)
    fmt._MIGRATIONS.clear()
    yield
    fmt._MIGRATIONS.clear()
    fmt._MIGRATIONS.update(saved)


def _base():
    return Base(name="obj")


# ------------------------------------------------------------------- Feld

def test_field_is_set_and_int():
    b = _base()
    attr = b.metadata.get(SDATA_FORMAT_VERSION_KEY)
    assert attr is not None
    assert attr.value == CURRENT_FORMAT_VERSION
    assert attr.dtype == "int"
    # bleibt getrennt von der Paketversion
    assert b.metadata.get("_sdata_version").value != CURRENT_FORMAT_VERSION


def test_field_survives_roundtrip():
    b = _base()
    back = Base.from_dict(b.to_dict())
    assert back.metadata.get(SDATA_FORMAT_VERSION_KEY).value == CURRENT_FORMAT_VERSION


# ------------------------------------------------------- read_format_version

def test_read_format_version_variants():
    assert read_format_version(None) == 1
    assert read_format_version("nope") == 1
    assert read_format_version({}) == 1                       # fehlend
    assert read_format_version({"metadata": "x"}) == 1        # meta nicht dict
    assert read_format_version({"metadata": {}}) == 1
    assert read_format_version(
        {"metadata": {SDATA_FORMAT_VERSION_KEY: {"value": 3}}}) == 3
    assert read_format_version({SDATA_FORMAT_VERSION_KEY: 2}) == 2   # flache Shape
    assert read_format_version(
        {"metadata": {SDATA_FORMAT_VERSION_KEY: {"value": "bad"}}}) == 1


# ----------------------------------------------------------- Toleranzregeln

def test_missing_field_reads_as_v1_without_warning():
    b = _base()
    d = b.to_dict()
    del d["metadata"][SDATA_FORMAT_VERSION_KEY]
    with warnings.catch_warnings():
        warnings.simplefilter("error")               # jede Warnung wäre ein Fehler
        back = Base.from_dict(d)
    assert back.name == "obj"


def test_equal_version_passes_through_unchanged():
    d = _base().to_dict()
    assert ensure_compatible(d) is d                 # keine Kopie, keine Migration


def test_newer_version_warns_and_best_effort():
    d = _base().to_dict()
    d["metadata"][SDATA_FORMAT_VERSION_KEY]["value"] = CURRENT_FORMAT_VERSION + 5
    with pytest.warns(FormatVersionWarning, match="newer than supported"):
        back = Base.from_dict(d)
    assert back.name == "obj"


def test_newer_version_strict_raises():
    d = _base().to_dict()
    d["metadata"][SDATA_FORMAT_VERSION_KEY]["value"] = CURRENT_FORMAT_VERSION + 5
    with pytest.raises(IncompatibleFormatError, match="newer than supported"):
        Base.from_dict(d, strict=True)


def test_ensure_compatible_non_dict_passthrough():
    assert ensure_compatible(None) is None


# --------------------------------------------------------- Migrations-Treppe

def test_single_step_migration_applied():
    @register_migration(1)
    def _v1_to_v2(payload):
        payload["metadata"][SDATA_FORMAT_VERSION_KEY]["value"] = 2
        payload["migrated"] = True
        return payload

    d = _base().to_dict()                            # v1 geschrieben
    out = ensure_compatible(d, current=2)
    assert out["migrated"] is True
    assert read_format_version(out) == 2


def test_multi_step_migration_runs_in_order():
    calls = []

    @register_migration(1)
    def _v1_to_v2(payload):
        calls.append(1)
        payload["metadata"][SDATA_FORMAT_VERSION_KEY]["value"] = 2
        return payload

    @register_migration(2)
    def _v2_to_v3(payload):
        calls.append(2)
        payload["metadata"][SDATA_FORMAT_VERSION_KEY]["value"] = 3
        return payload

    d = _base().to_dict()
    out = ensure_compatible(d, current=3)
    assert calls == [1, 2]
    assert read_format_version(out) == 3


def test_missing_migration_step_raises():
    d = _base().to_dict()                            # v1, aber keine Stufe registriert
    with pytest.raises(IncompatibleFormatError, match=r"v1 -> v2"):
        ensure_compatible(d, current=2)


# ------------------------------------------------- Choke-Point deckt Parquet

def test_restore_from_attrs_checks_version():
    pytest.importorskip("pyarrow")
    sdf = DataFrame(df=pd.DataFrame({"f": [1.0, 2.0]}), name="d")
    sdf.set_column("f", unit="N")
    df = sdf.to_dataframe()                           # attrs['_sdata'] gesetzt
    df.attrs["_sdata"]["metadata"][SDATA_FORMAT_VERSION_KEY]["value"] = 99
    target = DataFrame()
    with pytest.warns(FormatVersionWarning):
        target._restore_from_attrs(df.attrs["_sdata"])


def test_dataframe_from_dict_roundtrip_keeps_units():
    pytest.importorskip("pyarrow")
    sdf = DataFrame(df=pd.DataFrame({"f": [1.0]}), name="d")
    sdf.set_column("f", unit="N")
    back = DataFrame.from_dict(sdf.to_dict())
    assert back.column_units["f"] == "N"
    assert back.metadata.get(SDATA_FORMAT_VERSION_KEY).value == CURRENT_FORMAT_VERSION
