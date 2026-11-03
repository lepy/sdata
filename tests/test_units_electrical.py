# -*- coding: utf-8 -*-
"""Achsen für Stromstärke (I) und Stoffmenge (N) im Dimensionsvektor (RFC 0017)."""
import pandas as pd
import pytest

from sdata import units
from sdata.sclass.dataframe import DataFrame


def test_dim_names_have_seven_axes():
    assert units._DIM_NAMES == ("L", "M", "T", "Theta", "A", "I", "N")
    assert all(len(dim) == 7 for dim, _f, _o in units._UNITS.values())


@pytest.mark.parametrize("symbol, dim, quantity", [
    ("A", (0, 0, 0, 0, 0, 1, 0), "current"),
    ("mA", (0, 0, 0, 0, 0, 1, 0), "current"),
    ("kA", (0, 0, 0, 0, 0, 1, 0), "current"),
    ("V", (2, 1, -3, 0, 0, -1, 0), "voltage"),
    ("mV", (2, 1, -3, 0, 0, -1, 0), "voltage"),
    ("kV", (2, 1, -3, 0, 0, -1, 0), "voltage"),
    ("ohm", (2, 1, -3, 0, 0, -2, 0), "resistance"),
    ("mohm", (2, 1, -3, 0, 0, -2, 0), "resistance"),
    ("kohm", (2, 1, -3, 0, 0, -2, 0), "resistance"),
    ("Mohm", (2, 1, -3, 0, 0, -2, 0), "resistance"),
    ("C", (0, 0, 1, 0, 0, 1, 0), "charge"),
    ("Ah", (0, 0, 1, 0, 0, 1, 0), "charge"),
    ("mAh", (0, 0, 1, 0, 0, 1, 0), "charge"),
    ("mol", (0, 0, 0, 0, 0, 0, 1), "amount_of_substance"),
    ("mmol", (0, 0, 0, 0, 0, 0, 1), "amount_of_substance"),
])
def test_dimension_and_quantity(symbol, dim, quantity):
    assert units.dimension_of(symbol) == dim
    assert units.quantity_of(symbol) == quantity


def test_coulomb_is_charge():
    assert units.quantity_of("C") == "charge"
    assert units.qudt_iri("C") == "unit:C"


def test_milli_volt_to_volt():
    assert units.convert(1500, "mV", "V") == pytest.approx(1.5)
    assert units.convert_factor("kV", "V") == pytest.approx(1e3)


def test_ampere_hour_to_coulomb():
    assert units.convert(1, "Ah", "C") == pytest.approx(3600.0)
    assert units.convert(1000, "mAh", "Ah") == pytest.approx(1.0)
    assert units.convert(1, "mAh", "C") == pytest.approx(3.6)


def test_charge_and_temperature_are_incompatible():
    with pytest.raises(units.UnitConversionError):
        units.convert(1, "C", "K")


def test_pint_dimvector_maps_current_and_substance():
    # V/A -> pint: [mass][length]^2[time]^-3[current]^-2 == Dimension von ohm
    v_per_a = {"[mass]": 1, "[length]": 2, "[time]": -3, "[current]": -2}
    assert units._pint_dimvector(v_per_a) == units.dimension_of("ohm")
    # A/mol
    assert units._pint_dimvector({"[current]": 1, "[substance]": -1}) == \
        (0, 0, 0, 0, 0, 1, -1)
    # Lichtstärke bleibt nicht darstellbar
    assert units._pint_dimvector({"[luminosity]": 1}) is None


def test_pint_derived_units_resolve():
    pytest.importorskip("pint")
    assert units.dimension_of("V/A") == units.dimension_of("ohm")
    assert units.dimension_of("A/mol") == (0, 0, 0, 0, 0, 1, -1)
    assert units.dimension_of("V/m") == (1, 1, -3, 0, 0, -1, 0)


def test_unit_system_without_current_leaves_voltage_unchanged():
    df = pd.DataFrame({"force": [1000.0], "u": [3.3]})
    sdf = DataFrame(df=df, name="mix")
    sdf.set_column("force", unit="N")
    sdf.set_column("u", unit="V")            # Strom-Achse nicht im System
    conv = sdf.convert(["kN", "mm", "ms"])
    assert conv.column_units["force"] == "kN"
    assert conv.column_units["u"] == "V"      # unverändert
    assert list(conv.df["u"]) == [3.3]


def test_unit_system_with_current_basis_converts_voltage():
    system = units.UnitSystem(["kg", "m", "s", "A"])
    val, label = system.convert_value(1500.0, "mV")
    assert label == "V"                       # kanonisches SI-Symbol (RFC 0017)
    assert val == pytest.approx(1.5)


def test_unit_system_with_current_basis_names_electrical_symbols():
    system = units.UnitSystem(["kg", "m", "s", "A"])
    val, label = system.convert_value(2.0, "kohm")
    assert label == "ohm"
    assert val == pytest.approx(2000.0)
    val, label = system.convert_value(1.0, "mAh")
    assert label == "C"                       # Ladung SI-kohärent, nicht Ah
    assert val == pytest.approx(3.6)
    val, label = system.convert_value(250.0, "mA")
    assert label == "A"
    assert val == pytest.approx(0.25)


def test_unit_system_with_milliampere_basis_names_milliampere():
    system = units.UnitSystem(["kg", "m", "s", "mA"])
    val, label = system.convert_value(2.0, "A")
    assert label == "mA"
    assert val == pytest.approx(2000.0)


def test_unit_system_with_mol_basis_names_mol():
    system = units.UnitSystem(["kg", "m", "s", "mol"])
    val, label = system.convert_value(500.0, "mmol")
    assert label == "mol"
    assert val == pytest.approx(0.5)
