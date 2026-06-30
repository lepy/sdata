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


def test_unit_system():
    sys = units.UnitSystem(["kN", "mm", "ms"])
    assert sys.unit_for("force") == "kN"
    assert sys.unit_for("length") == "mm"
    assert sys.unit_for("time") == "ms"
    assert sys.unit_for("pressure") is None
    assert sys.target_for("N") == "kN"
    assert sys.target_for("s") == "ms"
    assert sys.target_for("mm") == "mm"
    assert sys.target_for("MPa") is None              # Größe nicht im System
    assert sys.target_for("-") is None                # dimensionslos
    assert repr(sys) == "UnitSystem(['kN', 'mm', 'ms'])"


def test_unit_system_last_unit_wins():
    sys = units.UnitSystem(["N", "kN"])               # beide force
    assert sys.unit_for("force") == "kN"


def test_unit_system_unknown_unit_raises():
    with pytest.raises(units.UnitConversionError, match="unknown unit in system"):
        units.UnitSystem(["kN", "furlong"])
