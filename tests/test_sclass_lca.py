# -*- coding: utf-8 -*-
"""Kanonisches LCA-Systemformat: Schemas + :class:`LCASystem`-Container.

Prüft den Format-Vertrag aus ``sdata/sclass/lca.py``:

* die sechs Tabellen-Schemas tragen genau die spezifizierten Spalten (inkl. der
  getrennten Verteilungs-Parametrisierungs-Spalten der ``uncertainty``-Tabelle);
* die Zeilenordnung ist normativ — eine Zeilen-Permutation ergibt eine **andere**
  :meth:`LCASystem.content_checksum` (die Prüfsumme identifiziert die Quelle);
* Roundtrip über JSON (dict) und CSV ist verlustfrei (Ordnung und Werte);
* die Schema-Validierung schlägt bei einer fehlenden **Pflicht**spalte an, nicht
  bei einer fehlenden optionalen Spalte.
"""
import pandas as pd
import pytest

from sdata.sclass.lca import (
    ELEMENTARY_FLOWS_SCHEMA,
    EXCHANGES_A_SCHEMA,
    EXCHANGES_B_SCHEMA,
    FLOW_KINDS,
    FLOWS_SCHEMA,
    LCA_SCHEMAS,
    LCA_TABLE_ORDER,
    MATRICES,
    PROCESSES_SCHEMA,
    UNCERTAINTY_SCHEMA,
    LCASystem,
)


def _flows():
    return pd.DataFrame({
        "id": ["glass", "copper", "electricity"],
        "unit": ["kg", "kg", "MJ"],
        "kind": ["GOOD", "GOOD", "GOOD"],
        "name": ["Glass", "Copper", "Electricity"],
        "region": ["GLO", "GLO", "GLO"],
        "time_slice": ["2024", "2024", "2024"],
    })


def _processes():
    return pd.DataFrame({
        "id": ["prod_glass", "prod_copper"],
        "name": ["production of glass", "production of copper"],
        "reference_output": ["glass", "copper"],
    })


def _exchanges_a():
    return pd.DataFrame({
        "row_id": ["glass", "copper", "electricity"],
        "col_id": ["prod_glass", "prod_copper", "prod_glass"],
        "value": [1000.0, 100.0, -10.0],           # Output +, Input −
    })


def _system():
    s = LCASystem(name="demo")
    s.set_table("flows", _flows())
    s.set_table("processes", _processes())
    s.set_table("exchanges_a", _exchanges_a())
    return s


# --------------------------------------------------------------- Schema-Layout
def test_schema_columns_match_layout():
    """Die sechs Schemas tragen exakt die Spalten des Plan-Layouts."""
    assert [c.name for c in FLOWS_SCHEMA.columns] == \
        ["id", "unit", "kind", "name", "region", "time_slice"]
    assert [c.name for c in PROCESSES_SCHEMA.columns] == \
        ["id", "name", "reference_output"]
    assert [c.name for c in ELEMENTARY_FLOWS_SCHEMA.columns] == \
        ["id", "unit", "compartment", "name"]
    assert [c.name for c in EXCHANGES_A_SCHEMA.columns] == ["row_id", "col_id", "value"]
    assert [c.name for c in EXCHANGES_B_SCHEMA.columns] == ["row_id", "col_id", "value"]
    assert list(LCA_TABLE_ORDER) == list(LCA_SCHEMAS.keys())


def test_flow_kind_and_matrix_vocab():
    assert FLOW_KINDS == ["GOOD", "WASTE"]
    assert MATRICES == ["A", "B"]
    kind = FLOWS_SCHEMA._by_name["kind"]
    assert kind.required and kind.allowed == ["GOOD", "WASTE"]


def test_required_columns_are_the_mandatory_ones():
    def req(sch):
        return [c.name for c in sch.columns if c.required]
    assert req(FLOWS_SCHEMA) == ["id", "unit", "kind"]
    assert req(PROCESSES_SCHEMA) == ["id"]                 # name/reference_output optional
    assert req(ELEMENTARY_FLOWS_SCHEMA) == ["id", "unit", "compartment"]
    assert req(EXCHANGES_A_SCHEMA) == ["row_id", "col_id", "value"]
    assert req(EXCHANGES_B_SCHEMA) == ["row_id", "col_id", "value"]


def test_uncertainty_has_explicit_separate_parametrizations():
    """Getrennte Spaltensätze je Lognormal-Lesart — nie eine Sammelspalte."""
    cols = {c.name for c in UNCERTAINTY_SCHEMA.columns}
    assert {"matrix", "row_id", "col_id", "dist"} <= cols
    # Lognormal, beide Lesarten getrennt parametrisiert
    assert {"lognormal_underlying_mu", "lognormal_underlying_sigma"} <= cols
    assert {"lognormal_geometric_gmean", "lognormal_geometric_gsd"} <= cols
    # weitere Familien
    assert {"normal_mean", "normal_sd"} <= cols
    assert {"uniform_min", "uniform_max"} <= cols
    m = UNCERTAINTY_SCHEMA._by_name["matrix"]
    assert m.required and m.allowed == ["A", "B"]


# --------------------------------------------------- Zeilenordnung ist normativ
def test_row_permutation_changes_content_checksum():
    """Eine Zeilen-Permutation ⇒ **andere** Content-Prüfsumme (Ordnung normativ)."""
    s = _system()
    before = s.content_checksum()
    permuted = _flows().iloc[[2, 0, 1]].reset_index(drop=True)   # gleiche Menge, andere Ordnung
    s.set_table("flows", permuted)
    after = s.content_checksum()
    assert before != after


def test_column_permutation_changes_content_checksum():
    """Auch die Spaltenordnung geht in die Prüfsumme ein."""
    s = _system()
    before = s.content_checksum()
    s.set_table("flows", _flows()[["unit", "id", "kind", "name", "region", "time_slice"]])
    assert s.content_checksum() != before


def test_content_checksum_is_stable_and_data_only():
    """Gleiche Daten ⇒ gleiche Prüfsumme (objektunabhängig); Metadaten zählen nicht."""
    assert _system().content_checksum() == _system().content_checksum()
    assert len(_system().content_checksum()) == 64
    s = _system()
    before = s.content_checksum()
    s.table("flows").set_column("id", unit="-", label="annotiert")   # nur Metadaten
    assert s.content_checksum() == before


def test_content_checksum_depends_on_all_subtables():
    s = _system()
    before = s.content_checksum()
    s.set_table("exchanges_a", _exchanges_a().iloc[[2, 1, 0]].reset_index(drop=True))
    assert s.content_checksum() != before


# ------------------------------------------------------------- JSON-Roundtrip
def test_json_roundtrip_lossless_order_and_values():
    pytest.importorskip("pyarrow")                    # dict/JSON bettet Parquet ein
    s = _system()
    back = LCASystem.from_dict(s.to_dict())
    assert back.content_checksum() == s.content_checksum()
    for key in ("flows", "processes", "exchanges_a"):
        assert list(back.table(key).df.columns) == list(s.table(key).df.columns)
        assert back.table(key).content_bytes == s.table(key).content_bytes


def test_json_string_roundtrip():
    pytest.importorskip("pyarrow")
    s = _system()
    back = LCASystem.from_json(s.to_json())
    assert back.content_checksum() == s.content_checksum()


# -------------------------------------------------------------- CSV-Roundtrip
def test_csv_dir_roundtrip_lossless_order_and_values(tmp_path):
    s = _system()
    written = s.to_csv_dir(str(tmp_path))
    assert [p.split("/")[-1] for p in written] == \
        ["flows.csv", "processes.csv", "exchanges_a.csv"]
    back = LCASystem.from_csv_dir(str(tmp_path))
    assert back.content_checksum() == s.content_checksum()
    for key in ("flows", "processes", "exchanges_a"):
        assert list(back.table(key).df.columns) == list(s.table(key).df.columns)
        assert back.table(key).content_bytes == s.table(key).content_bytes


# ----------------------------------------------------------- Schema-Validierung
def test_validation_flags_missing_required_column():
    """Fehlende **Pflicht**spalte (``id``) ⇒ Tabelle ungültig."""
    s = LCASystem(name="x")
    s.set_table("flows", _flows().drop(columns=["id"]))
    rep = s.validate_tables()["flows"]
    assert not rep.ok
    assert "id" in rep.missing


def test_validation_tolerates_missing_optional_column():
    """Fehlende **optionale** Spalte (``region``) ⇒ Tabelle bleibt gültig."""
    s = LCASystem(name="x")
    s.set_table("flows", _flows().drop(columns=["region"]))
    rep = s.validate_tables()["flows"]
    assert rep.ok
    assert s.is_valid()


def test_full_system_is_valid():
    assert _system().is_valid()


def test_validate_tables_absent_with_only_present_false():
    s = LCASystem(name="x")           # leeres System
    reports = s.validate_tables(only_present=False)
    assert set(reports) == set(LCA_SCHEMAS)
    assert not reports["flows"].ok    # Pflichtspalten fehlen komplett
    assert reports == s.validate_tables(only_present=False)


# ---------------------------------------------------------------- set_table API
def test_set_table_rejects_unknown_key():
    s = LCASystem(name="x")
    with pytest.raises(ValueError):
        s.set_table("not_a_table", _flows())


def test_set_table_applies_schema_metadata():
    s = LCASystem(name="x")
    s.set_table("flows", _flows())
    # das Schema hat die Spalten-Metadaten vervollständigt (Beschreibung gesetzt)
    assert s.table("flows").get_column("kind").description
