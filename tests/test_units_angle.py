# -*- coding: utf-8 -*-
"""Winkel-Einheiten (RFC 0006): eigene Dimensions-Achse „A" (ebener Winkel).

rad/deg/gon konvertieren untereinander, sind aber gegen dimensionslose Einheiten
(``-``/``%``/``""``) abgegrenzt. dB (logarithmisch) bleibt bewusst außen vor.
"""
import math

import pytest

from sdata import units
from sdata.units import (convert, convert_factor, dimension_of, quantity_of,
                         qudt_iri, ucum_code, validate_unit, UnitSystem,
                         UnitConversionError)


def test_angle_is_own_axis():
    assert dimension_of("rad") == (0, 0, 0, 0, 1)
    assert dimension_of("deg") == (0, 0, 0, 0, 1)
    assert dimension_of("gon") == (0, 0, 0, 0, 1)
    assert dimension_of("mrad") == (0, 0, 0, 0, 1)
    assert quantity_of("rad") == "angle"
    # dimensionslos bleibt eine andere Achse
    assert dimension_of("%") == (0, 0, 0, 0, 0)
    assert quantity_of("%") is None


@pytest.mark.parametrize("val,frm,to,exp", [
    (180.0, "deg", "rad", math.pi),
    (math.pi, "rad", "deg", 180.0),
    (200.0, "gon", "deg", 180.0),
    (1.0, "rad", "mrad", 1000.0),
    (90.0, "deg", "gon", 100.0),
])
def test_angle_conversions(val, frm, to, exp):
    assert convert(val, frm, to) == pytest.approx(exp)


def test_angle_convert_factor():
    assert convert_factor("deg", "rad") == pytest.approx(math.pi / 180.0)
    assert convert_factor("gon", "rad") == pytest.approx(math.pi / 200.0)


def test_angle_not_convertible_to_dimensionless():
    # Kern der eigenen Achse: rad ist KEIN Prozent und keine blanke Zahl
    for other in ("-", "%", ""):
        with pytest.raises(UnitConversionError, match="different dimension"):
            convert(1.0, "rad", other)
    with pytest.raises(UnitConversionError, match="different dimension"):
        convert(50.0, "%", "deg")


def test_angle_aliases_and_vocabulary():
    assert dimension_of("°") == (0, 0, 0, 0, 1)          # ° -> deg
    assert dimension_of("degrees") == (0, 0, 0, 0, 1)
    assert dimension_of("radians") == (0, 0, 0, 0, 1)
    assert dimension_of("gradian") == (0, 0, 0, 0, 1)    # gradian -> gon
    assert qudt_iri("deg") == "unit:DEG"
    assert qudt_iri("rad") == "unit:RAD"
    assert qudt_iri("gon") == "unit:GON"
    assert ucum_code("gon") == "gon"
    assert validate_unit("rad") and validate_unit("deg") and validate_unit("gon")


def test_grad_is_deliberately_not_mapped():
    # „grad" ist mehrdeutig (engl. gradian vs. dt. „Grad" = deg) -> nicht gemappt
    assert dimension_of("grad") is None
    assert "grad" not in units._CONVERT_ALIASES


def test_unit_system_with_angle_basis():
    rad_sys = UnitSystem(["rad"])
    assert rad_sys.target_for("deg") == "rad"
    assert rad_sys.unit_for("angle") == "rad"
    val, label = rad_sys.convert_value(180.0, "deg")
    assert val == pytest.approx(math.pi)
    assert label == "rad"


def test_mechanical_system_leaves_angle_untouched():
    mech = UnitSystem(["kN", "mm", "ms"])       # spannt die Winkel-Achse nicht auf
    assert mech.target_for("deg") is None
    assert mech.convert_value(90.0, "deg") is None


def test_inconsistent_angle_basis_rejected():
    with pytest.raises(UnitConversionError, match="inconsistent"):
        UnitSystem(["rad", "deg"])              # zwei Winkel-Skalen -> widersprüchlich


def test_db_stays_out():
    # logarithmische „Einheit" passt nicht ins lineare Faktor-Modell
    assert dimension_of("dB") is None
    with pytest.raises(UnitConversionError):
        convert(3.0, "dB", "rad")
