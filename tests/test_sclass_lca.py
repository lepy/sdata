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
    CSV_DIALECT,
    ELEMENTARY_FLOWS_SCHEMA,
    EXCHANGES_A_SCHEMA,
    EXCHANGES_B_SCHEMA,
    FLOW_KINDS,
    FLOWS_SCHEMA,
    LCA_SCHEMAS,
    LCA_TABLE_ORDER,
    MATRICES,
    PROCESSES_SCHEMA,
    RESULTS_DRAWS_SCHEMA,
    RESULTS_PROVENANCE_SCHEMA,
    RESULTS_SCHEMAS,
    RESULTS_SUMMARY_SCHEMA,
    RESULTS_TABLE_ORDER,
    UNCERTAINTY_SCHEMA,
    LCAResults,
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


# ----------------------------------------------------- CSV-Dialekt als Vertrag
def test_csv_dialect_contract_is_comma_dot_utf8():
    """Der gepinnte Dialekt ist Teil des öffentlichen Vertrags."""
    assert CSV_DIALECT == {"sep": ",", "decimal": ".", "encoding": "utf-8"}


def test_from_csv_dir_does_not_accept_dialect_override():
    """Keine Hintertür: ``sep``/``decimal``/``encoding`` sind nicht überschreibbar
    (``**read_csv_kwargs`` entfernt) — der Aufruf mit solchen kwargs schlägt fehl."""
    with pytest.raises(TypeError):
        LCASystem.from_csv_dir("irgendwo", sep=";")


def test_foreign_dialect_is_not_silently_misread(tmp_path):
    """Eine Datei in fremdem Dialekt (``;``-getrennt, Dezimalkomma) wird **nicht**
    still korrekt gelesen: unter dem gepinnten Komma-Dialekt landet die ganze
    Zeile in EINER Spalte — die Vertragsspalten fehlen, statt lautlos falsch zu
    erscheinen (kein stilles Fehllesen)."""
    (tmp_path / "exchanges_a.csv").write_text(
        "row_id;col_id;value\nglass;prod_glass;1000,0\n", encoding="utf-8")
    back = LCASystem.from_csv_dir(str(tmp_path))
    cols = list(back.table("exchanges_a").df.columns)
    assert cols != ["row_id", "col_id", "value"]        # nicht still in die Vertragsform gelesen
    assert len(cols) == 1                                # alles in einer (falschen) Spalte


def test_csv_roundtrip_stable_under_pinned_dialect(tmp_path):
    """Der gepinnte Dialekt hält den Roundtrip byte-/prüfsummenstabil (Regression)."""
    s = _system()
    s.to_csv_dir(str(tmp_path))
    assert LCASystem.from_csv_dir(str(tmp_path)).content_checksum() == s.content_checksum()


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


# ======================================================================
# RESULTS — Ergebnis-Rückrichtung (LCAResults), gleicher Vertragsstil
# ======================================================================
def _results_summary():
    return pd.DataFrame({
        "target": ["CO2", "CH4"],
        "nominal": [2.0, 0.1],
        "mean": [2.13, 0.11],
        "variance": [0.09, 0.001],
        "interpercentile_lower": [1.71, 0.05],
        "interpercentile_upper": [2.63, 0.18],
        "lower_percentile": [0.025, 0.025],
        "upper_percentile": [0.975, 0.975],
        "n": [1000, 1000],
        "n_failed": [0, 0],
        "n_guarded": [3, 3],
    })


def _results_draws():
    return pd.DataFrame({
        "target": ["CO2", "CO2", "CH4", "CH4"],
        "draw": [0, 1, 0, 1],
        "value": [2.05, 1.98, 0.10, 0.12],
    })


def _results_provenance():
    return pd.DataFrame({
        "key": ["seed", "generator", "content_hash"],
        "value": ["12345", "Philox", "abc123"],
    })


def _results():
    r = LCAResults(name="demo_results")
    r.set_table("results", _results_summary())
    r.set_table("draws", _results_draws())
    r.set_table("provenance", _results_provenance())
    return r


def test_results_schema_columns_match_layout():
    """Die drei Ergebnis-Schemas tragen exakt die spezifizierten Spalten."""
    assert [c.name for c in RESULTS_SUMMARY_SCHEMA.columns] == [
        "target", "nominal", "mean", "variance",
        "interpercentile_lower", "interpercentile_upper",
        "lower_percentile", "upper_percentile", "n", "n_failed", "n_guarded"]
    assert [c.name for c in RESULTS_DRAWS_SCHEMA.columns] == ["target", "draw", "value"]
    assert [c.name for c in RESULTS_PROVENANCE_SCHEMA.columns] == ["key", "value"]
    assert list(RESULTS_TABLE_ORDER) == list(RESULTS_SCHEMAS.keys())


def test_results_naming_is_interpercentile_not_confidence():
    """L6-Disziplin: das Streuungsband heißt Interperzentil, nie Konfidenz."""
    cols = {c.name for c in RESULTS_SUMMARY_SCHEMA.columns}
    assert {"interpercentile_lower", "interpercentile_upper"} <= cols
    assert not any("confidence" in c.lower() for c in cols)
    assert "nominal" in cols and "true_value" not in cols


def test_results_required_columns():
    def req(sch):
        return [c.name for c in sch.columns if c.required]
    # alle Kennzahl-Spalten sind Pflicht (das Ergebnis ist ohne sie unvollständig)
    assert req(RESULTS_SUMMARY_SCHEMA) == [c.name for c in RESULTS_SUMMARY_SCHEMA.columns]
    assert req(RESULTS_DRAWS_SCHEMA) == ["target", "draw", "value"]
    assert req(RESULTS_PROVENANCE_SCHEMA) == ["key", "value"]


def test_results_full_group_is_valid():
    assert _results().is_valid()


def test_results_row_order_is_normative():
    """Zeilen-Permutation ⇒ andere Content-Prüfsumme (Ordnung normativ)."""
    r = _results()
    before = r.content_checksum()
    r.set_table("results", _results_summary().iloc[[1, 0]].reset_index(drop=True))
    assert r.content_checksum() != before


def test_results_csv_dir_roundtrip_lossless(tmp_path):
    r = _results()
    written = r.to_csv_dir(str(tmp_path))
    assert [p.split("/")[-1] for p in written] == \
        ["results.csv", "draws.csv", "provenance.csv"]
    back = LCAResults.from_csv_dir(str(tmp_path))
    assert back.content_checksum() == r.content_checksum()
    for key in RESULTS_TABLE_ORDER:
        assert back.table(key).content_bytes == r.table(key).content_bytes


def test_results_uses_pinned_dialect_no_override():
    with pytest.raises(TypeError):
        LCAResults.from_csv_dir("irgendwo", sep=";")


def test_results_validation_flags_missing_required_column():
    r = LCAResults(name="x")
    r.set_table("results", _results_summary().drop(columns=["variance"]))
    rep = r.validate_tables()["results"]
    assert not rep.ok
    assert "variance" in rep.missing


def test_results_summary_only_is_valid_draws_optional():
    """Nur die Kennzahl-Tabelle (ohne draws/provenance) ist ein gültiges Ergebnis."""
    r = LCAResults(name="summary_only")
    r.set_table("results", _results_summary())
    assert r.is_valid()
    assert r.table("draws") is None
