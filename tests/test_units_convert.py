# -*- coding: utf-8 -*-
"""Tests für die Einheiten-Konvertierung (sdata/units.py): convert / convert_factor /
quantity_of / UnitSystem."""
import numpy as np
import pandas as pd
import pytest

from sdata import units


def test_quantity_of():
    assert units.quantity_of("kN") == "force"
    assert units.quantity_of("mm") == "length"
    assert units.quantity_of("ms") == "time"
    assert units.quantity_of("MPa") == "pressure"
    assert units.quantity_of("degC") == "temperature"
    assert units.quantity_of("-") is None          # dimensionslos
    assert units.quantity_of(None) is None          # _norm_convert(None) -> "-"
    assert units.quantity_of("furlong") is None      # unbekannt


def test_convert_scalar():
    assert units.convert(5000, "N", "kN") == 5.0
    assert units.convert(0.5, "s", "ms") == 500.0
    assert units.convert(1.2, "mm", "mm") == 1.2     # Identität
    assert units.convert(2, "m", "mm") == 2000.0


def test_convert_list_and_tuple():
    assert units.convert([1000, 2000], "N", "kN") == [1.0, 2.0]
    assert units.convert((0.1, 0.2), "s", "ms") == [100.0, 200.0]


def test_convert_numpy_and_series():
    out = units.convert(np.array([1000.0, 2000.0]), "N", "kN")
    assert isinstance(out, np.ndarray)
    assert list(out) == [1.0, 2.0]
    ser = units.convert(pd.Series([1000.0, 2000.0]), "N", "kN")
    assert isinstance(ser, pd.Series)
    assert list(ser) == [1.0, 2.0]


def test_convert_temperature_offset():
    assert units.convert(25, "degC", "K") == 298.15
    assert round(units.convert(300, "K", "degC"), 2) == 26.85
    assert units.convert(20, "degC", "degC") == 20      # Offset hebt sich auf


def test_convert_aliases():
    assert units.convert(1, "µm", "nm") == pytest.approx(1000.0)  # Mikrometer (nicht mm!)
    assert units.quantity_of("CELSIUS") == "temperature"  # .lower()-Alias
    assert units.convert(2, "sec", "ms") == 2000.0


def test_convert_unknown_units_raise():
    with pytest.raises(units.UnitConversionError, match="source"):
        units.convert(1, "furlong", "mm")
    with pytest.raises(units.UnitConversionError, match="target"):
        units.convert(1, "mm", "furlong")


def test_convert_incompatible_raises():
    with pytest.raises(units.UnitConversionError, match="incompatible"):
        units.convert(1, "mm", "kN")


def test_convert_factor():
    assert units.convert_factor("N", "kN") == 0.001
    assert units.convert_factor("s", "ms") == 1000.0


def test_convert_factor_incompatible_raises():
    with pytest.raises(units.UnitConversionError, match="incompatible"):
        units.convert_factor("mm", "kN")


def test_convert_factor_offset_raises():
    with pytest.raises(units.UnitConversionError, match="offset"):
        units.convert_factor("degC", "K")


def test_unit_system_base_units():
    sys = units.UnitSystem(["kN", "mm", "ms"])
    assert sys.unit_for("force") == "kN"
    assert sys.unit_for("length") == "mm"
    assert sys.unit_for("time") == "ms"
    assert sys.target_for("N") == "kN"
    assert sys.target_for("s") == "ms"
    assert sys.target_for("mm") == "mm"
    assert sys.target_for("-") is None                # dimensionslos
    assert sys.target_for("furlong") is None          # unbekannt
    assert repr(sys) == "UnitSystem(['kN', 'mm', 'ms'])"


def test_unit_system_derives_units():
    """v2: abgeleitete Einheiten werden aus der Dimensions-Algebra hergeleitet."""
    sys = units.UnitSystem(["kN", "mm", "ms"])
    # Spannung kN/mm² = GPa, Energie kN·mm = J, Geschwindigkeit mm/ms = m/s, Masse kg
    assert sys.unit_for("pressure") == "GPa"
    assert sys.unit_for("energy") == "J"
    assert sys.unit_for("velocity") == "m/s"
    assert sys.target_for("MPa") == "GPa"
    assert sys.target_for("kg") == "kg"
    assert sys.target_for("g") == "kg"
    assert sys.target_for("1/s") == "1/ms"
    # exakte numerische Umrechnung der abgeleiteten Größen
    assert sys.convert_value(200.0, "MPa") == (0.2, "GPa")
    assert sys.convert_value(12.0, "J") == (12.0, "J")
    assert sys.convert_value(5000.0, "N") == (5.0, "kN")
    assert sys.convert_value([1000.0, 2000.0], "N") == ([1.0, 2.0], "kN")


def test_unit_system_factor_for():
    sys = units.UnitSystem(["kN", "mm", "ms"])
    assert sys.factor_for((1, 1, -2, 0)) == 1000.0    # Kraft -> kN
    assert sys.factor_for((-1, 1, -2, 0)) == 1e9      # Druck -> GPa


def test_unit_system_uncovered_and_unknown():
    sys = units.UnitSystem(["kN", "mm", "ms"])        # keine Temperatur-Dimension
    assert sys.target_for("degC") is None             # Dimension nicht aufgespannt
    assert sys.convert_value(25.0, "degC") is None
    assert sys.convert_value(1.0, "furlong") is None  # unbekannte Quell-Einheit
    assert sys.unit_for("nonsense") is None            # unbekannte Größe


def test_unit_system_mlt_and_temperature():
    mlt = units.UnitSystem(["t", "mm", "s"])          # Masse-Länge-Zeit
    assert mlt.target_for("N") == "N"                  # t·mm/s² = N
    assert mlt.target_for("kg") == "t"
    withT = units.UnitSystem(["mm", "kg", "s", "K"])
    assert withT.convert_value(25.0, "degC") == (298.15, "K")   # Offset


def test_unit_system_redundant_consistent_and_inconsistent():
    ok = units.UnitSystem(["kN", "mm", "ms", "GPa"])  # GPa folgt bereits -> konsistent
    assert ok.unit_for("pressure") == "GPa"
    with pytest.raises(units.UnitConversionError, match="inconsistent"):
        units.UnitSystem(["N", "kN"])                  # beide Kraft, widersprüchlich


def test_unit_system_fractional_exponent():
    """Solver liefert rationale Exponenten (Fläche-Basis -> Länge über 1/2)."""
    sys = units.UnitSystem(["mm2", "s"])
    assert sys.target_for("m") == "mm"
    assert sys.convert_value(1.0, "m") == (1000.0, "mm")


def test_unit_system_offset_base_rejected():
    with pytest.raises(units.UnitConversionError, match="offset unit not allowed"):
        units.UnitSystem(["degC", "mm"])


def test_unit_system_unknown_unit_raises():
    with pytest.raises(units.UnitConversionError, match="unknown unit in system"):
        units.UnitSystem(["kN", "furlong"])


def test_compose_and_canonical_helpers():
    from fractions import Fraction
    # kanonischer Treffer
    assert units._canonical((1, 1, -2, 0), 1e3) == "kN"
    assert units._canonical((-1, 1, -2, 0), 1e9) == "GPa"
    assert units._canonical((1, 1, -2, 0), 1.234) is None   # kein Faktor-Treffer
    # Komposition aus Basis-Symbolen
    assert units._compose(["kN", "mm"], [Fraction(1), Fraction(-2)]) == "kN/mm^2"
    assert units._compose(["kN", "mm"], [Fraction(1), Fraction(1)]) == "kN*mm"
    assert units._compose(["mm"], [Fraction(-4)]) == "1/mm^4"          # nur Nenner
    assert units._compose(["mm"], [Fraction(0)]) == "1"               # leer


def test_dimension_of():
    assert units.dimension_of("MPa") == (-1, 1, -2, 0)
    assert units.dimension_of("kN") == (1, 1, -2, 0)
    assert units.dimension_of("furlong") is None
    assert units.dimension_of(None) == (0, 0, 0, 0)   # -> "-"


def test_solve_linear_helper():
    from fractions import Fraction
    # eindeutig lösbar
    assert units._solve_linear([[2, 0], [0, 3]], [4, 9]) == [Fraction(2), Fraction(3)]
    # freie Variable (Spalte ohne Pivot) -> partikuläre Lösung mit 0
    assert units._solve_linear([[1, 0], [0, 0]], [5, 0]) == [Fraction(5), Fraction(0)]
    # widersprüchlich -> None
    assert units._solve_linear([[1], [0]], [1, 7]) is None
