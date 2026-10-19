# -*- coding: utf-8 -*-
"""Tests: QUDT-/UCUM-Abdeckung aller konvertierbaren Einheiten und Mikrometer-Alias."""
import pytest

from sdata import units


@pytest.mark.parametrize("symbol", ["µm", "μm", "um"])
def test_micrometre_is_not_millimetre(symbol):
    assert units.normalize_symbol(symbol) == "um"
    assert units.qudt_iri(symbol) == "unit:MicroM"
    assert units.ucum_code(symbol) == "um"


@pytest.mark.parametrize("symbol,iri,ucum", [
    ("mm2", "unit:MilliM2", "mm2"),
    ("mm²", "unit:MilliM2", "mm2"),
    ("m2", "unit:M2", "m2"),
    ("mm3", "unit:MilliM3", "mm3"),
    ("mm/s", "unit:MilliM-PER-SEC", "mm.s-1"),
    ("m/s", "unit:M-PER-SEC", "m.s-1"),
    ("m/s2", "unit:M-PER-SEC2", "m.s-2"),
    ("ms", "unit:MilliSEC", "ms"),
    ("1/ms", "unit:PER-MilliSEC", "ms-1"),
    ("kPa", "unit:KiloPA", "kPa"),
    ("J", "unit:J", "J"),
    ("t", "unit:TONNE", "t"),
])
def test_qudt_for_derived_units(symbol, iri, ucum):
    assert units.qudt_iri(symbol) == iri
    assert units.ucum_code(symbol) == ucum


def test_every_convertible_unit_has_qudt_iri():
    """Jede Einheit der Umrechnungstabelle ist auch im QUDT-Vokabular bekannt
    (ausgenommen dimensionslos)."""
    missing = [s for s in units._UNITS
               if s not in ("-", "") and units.qudt_iri(s) is None]
    assert missing == []


def test_unit_node_area():
    assert units.unit_node("mm2") == {"unitRef": "unit:MilliM2", "symbol": "mm2"}
