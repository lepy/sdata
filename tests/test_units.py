# -*- coding: utf-8 -*-
"""Tests für sdata/units.py (Einheiten→QUDT/UCUM, unit_node, pint-Validierung)."""
from sdata import units


def test_normalize_symbol():
    assert units.normalize_symbol(None) == "-"
    assert units.normalize_symbol(" mm ") == "mm"
    assert units.normalize_symbol("°C") == "degC"
    assert units.normalize_symbol("mpa") == "MPa"        # lower-Alias
    assert units.normalize_symbol("furlong") == "furlong"  # unbekannt -> passthrough


def test_qudt_and_ucum():
    assert units.qudt_iri("kN") == "unit:KiloN"
    assert units.qudt_iri("-") is None
    assert units.qudt_iri("furlong") is None
    assert units.ucum_code("degC") == "Cel"
    assert units.ucum_code("furlong") == "furlong"
    assert units.ucum_code(None) == "1"


def test_unit_node():
    n = units.unit_node("kN")
    assert n == {"unitRef": "unit:KiloN", "symbol": "kN"}
    assert units.unit_node("-") == {"symbol": "-"}         # keine IRI
    assert units.unit_node(None) == {"symbol": ""}


def test_validate_unit_pure():
    assert units.validate_unit("mm") is True
    assert units.validate_unit("furlong") is False         # ohne pint


def test_validate_unit_with_pint(monkeypatch):
    class _FakePint:
        @staticmethod
        def Unit(symbol):
            if symbol == "furlong":
                return object()
            raise ValueError("bad unit")

    monkeypatch.setattr(units, "_pint", _FakePint)
    assert units.has_pint() is True
    assert units.validate_unit("furlong") is True          # via pint
    assert units.validate_unit("zonk") is False            # pint wirft


def test_has_pint_is_bool():
    assert isinstance(units.has_pint(), bool)
