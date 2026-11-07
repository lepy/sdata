# -*- coding: utf-8 -*-
"""pint-Interop außerhalb der kuratierten Tabelle (RFC 0006).

Ohne installiertes pint bleibt das Verhalten unverändert (kuratierte Tabelle). Ist
pint vorhanden, werden nicht kuratierte Einheiten (imperial/abgeleitet) über pint auf
denselben 7-Achsen-Dimensionsvektor abgebildet und sind damit umrechenbar.

Getestet wird gegen ein **Fake-pint** (monkeypatch), damit die Zweige deterministisch
und ohne echte Abhängigkeit voll abgedeckt sind – dasselbe Muster wie bei
``validate_unit`` (siehe ``test_units.py``).
"""
import math

import pytest

from sdata import units


class _FakePint:
    """Minimaler pint-Ersatz: nur, was ``_pint_entry`` anfasst (Unit/Quantity).

    Verhält sich wie pint 0.25: ``degF`` lässt sich ohne Fehler in Basiseinheiten
    umrechnen (affin), Winkel tragen keine Dimension, aber die Root-Einheit ``radian``,
    logarithmische Einheiten sind nicht linear.
    """

    #: name -> (dimensionality, factor, offset, root_units, logarithmisch)
    _REG = {
        "psi":  ({"[mass]": 1, "[length]": -1, "[time]": -2}, 6894.757293, 0.0,
                 {"gram": 1, "meter": -1, "second": -2}, False),
        "inch": ({"[length]": 1}, 0.0254, 0.0, {"meter": 1}, False),
        "lbf":  ({"[mass]": 1, "[length]": 1, "[time]": -2}, 4.4482216153, 0.0,
                 {"gram": 1, "meter": 1, "second": -2}, False),
        "mm":   ({"[length]": 1}, 999.0, 0.0, {"meter": 1}, False),  # Vorrang-Test
        "ampere": ({"[current]": 1}, 1.0, 0.0, {"ampere": 1}, False),
        "mole": ({"[substance]": 1}, 1.0, 0.0, {"mole": 1}, False),
        "candela": ({"[luminosity]": 1}, 1.0, 0.0, {"candela": 1}, False),
        "degF": ({"[temperature]": 1}, 5.0 / 9.0, 255.3722222, {"kelvin": 1}, False),
        # pint: dimensionslos, aber Root-Einheit radian
        "grad": ({}, 0.015707963267948967, 0.0, {"radian": 1}, False),  # gesperrt
        "arcminute": ({}, 2.908882086657216e-4, 0.0, {"radian": 1}, False),
        "rpm":  ({"[time]": -1}, 0.10471975511965977, 0.0,
                 {"radian": 1, "second": -1}, False),
        "sr":   ({}, 1.0, 0.0, {"radian": 2}, False),
        # echt dimensionslos
        "ppm":  ({}, 1e-6, 0.0, {}, False),
        # pint: dimensionslos, aber eigene Root-Einheit
        "count": ({}, 1.0, 0.0, {"count": 1}, False),
        # logarithmisch: Wert -> factor ** Wert
        "dB":   ({}, 1.2589254117941673, 0.0, {}, True),
        "dBm":  ({"[mass]": 1, "[length]": 2, "[time]": -3}, 1.2589254117941673, 0.0,
                 {"gram": 1, "meter": 2, "second": -3}, True),
        # kaputte Einheit: Root-Einheiten nicht ermittelbar
        "broken": ({"[length]": 1}, 1.0, 0.0, None, False),
    }

    class _Units:
        def __init__(self, root):
            self._units = root

    class _Root:
        def __init__(self, root):
            self.units = _FakePint._Units(root)

    class _Unit:
        def __init__(self, spec):
            self.dimensionality = spec[0]
            self._spec = spec

    class _Mag:
        def __init__(self, magnitude):
            self.magnitude = magnitude

    class _Quantity:
        def __init__(self, value, unit):
            self._value = value
            self._unit = unit

        def _base(self):
            _dim, factor, offset, _root, log = self._unit._spec
            if log:
                return factor ** self._value
            return self._value * factor + offset

        def to_base_units(self):
            return _FakePint._Mag(self._base())

        def to(self, _target):            # nur Kelvin-Pfad für Temperatur
            return _FakePint._Mag(self._base())

        def to_root_units(self):
            root = self._unit._spec[3]
            if root is None:
                raise ValueError("no root units")
            return _FakePint._Root(root)

    @staticmethod
    def Unit(name):
        spec = _FakePint._REG.get(name)
        if spec is None:
            raise ValueError("unknown unit %r" % name)
        return _FakePint._Unit(spec)

    @staticmethod
    def Quantity(value, unit):
        return _FakePint._Quantity(value, unit)


@pytest.fixture
def fake_pint(monkeypatch):
    monkeypatch.setattr(units, "_pint", _FakePint)
    return _FakePint


# ------------------------------------------------------------------ ohne pint

def test_without_pint_unknown_stays_unknown(monkeypatch):
    # Grundzustand ohne pint -> nicht kuratierte Einheit bleibt unbekannt
    monkeypatch.setattr(units, "_pint", None)
    assert units.dimension_of("psi") is None
    with pytest.raises(units.UnitConversionError):
        units.convert(1.0, "psi", "MPa")


# ------------------------------------------------------------------ mit pint

def test_pint_dimension_of(fake_pint):
    assert units.dimension_of("psi") == (-1, 1, -2, 0, 0, 0, 0)     # Druck
    assert units.dimension_of("inch") == (1, 0, 0, 0, 0, 0, 0)      # Länge
    assert units.quantity_of("psi") == "pressure"
    assert units.quantity_of("lbf") == "force"


def test_pint_convert_pressure_and_length(fake_pint):
    assert units.convert(1.0, "psi", "MPa") == pytest.approx(0.006894757, rel=1e-6)
    assert units.convert(1.0, "inch", "mm") == pytest.approx(25.4)
    assert units.convert_factor("inch", "mm") == pytest.approx(25.4)


def test_pint_offset_unit_degF(fake_pint):
    # affine Einheit über zwei Kelvin-Stützpunkte
    assert units.convert(32.0, "degF", "degC") == pytest.approx(0.0, abs=1e-6)
    assert units.convert(212.0, "degF", "degC") == pytest.approx(100.0, abs=1e-6)
    # Offset-Einheit hat keinen reinen Faktor
    with pytest.raises(units.UnitConversionError, match="offset units need convert"):
        units.convert_factor("degF", "K")


def test_pint_unrepresentable_axis_is_none(fake_pint):
    # Lichtstärke liegt außerhalb (L, M, T, Θ, A, I, N)
    assert units.dimension_of("candela") is None
    with pytest.raises(units.UnitConversionError):
        units.convert(1.0, "candela", "psi")


def test_pint_current_and_substance_axes(fake_pint):
    assert units.dimension_of("ampere") == (0, 0, 0, 0, 0, 1, 0)
    assert units.dimension_of("mole") == (0, 0, 0, 0, 0, 0, 1)


def test_pint_unparseable_symbol_is_none(fake_pint):
    assert units.dimension_of("zonk") is None                 # Fake-pint wirft -> None


def test_curated_table_takes_precedence(fake_pint):
    # Fake-pint kennt "mm" mit falschem Faktor 999 – die kuratierte Tabelle gewinnt
    assert units.dimension_of("mm") == (1, 0, 0, 0, 0, 0, 0)
    assert units.convert_factor("m", "mm") == pytest.approx(1000.0)


def test_pint_unit_in_unit_system(fake_pint):
    # imperiales System: Länge löst auf "inch", Kraft auf "lbf"
    sysimp = units.UnitSystem(["lbf", "inch", "s"])
    assert sysimp.unit_for("length") == "inch"
    val, label = sysimp.convert_value(25.4, "mm")             # mm kuratiert -> Länge
    assert val == pytest.approx(1.0)                          # 25.4 mm == 1 inch
    assert label == "inch"


def test_pint_dimvector_fractional_exponent(fake_pint):
    # nicht ganzzahliger Exponent bleibt erhalten (kein int-Cast)
    from fractions import Fraction
    vec = units._pint_dimvector({"[length]": Fraction(1, 2)})
    assert vec == (Fraction(1, 2), 0, 0, 0, 0, 0, 0)


@pytest.mark.parametrize("symbol", ["dB", "dBm", "count", "broken"])
def test_pint_nonlinear_or_unknown_root_is_not_taken_over(fake_pint, symbol):
    # logarithmisch (dB, dBm), fremde Root-Einheit (count) oder keine Root-Einheiten
    assert units.dimension_of(symbol) is None
    with pytest.raises(units.UnitConversionError):
        units.convert(1.0, symbol, "-")


def test_pint_angle_goes_to_angle_axis(fake_pint):
    assert units.dimension_of("arcminute") == (0, 0, 0, 0, 1, 0, 0)
    assert units.convert(60.0, "arcminute", "deg") == pytest.approx(1.0)
    with pytest.raises(units.UnitConversionError, match="different dimension"):
        units.convert(1.0, "arcminute", "%")


@pytest.mark.parametrize("symbol", ["grad", "Grad", " grad "])
def test_pint_ambiguous_grad_stays_unmapped(fake_pint, symbol):
    # pint kennt grad (= gon); dt. „Grad" meint aber deg -> bewusst gesperrt
    assert units.dimension_of(symbol) is None


def test_pint_rpm_keeps_angle_and_is_not_hz(fake_pint):
    # rpm ist eine Winkelgeschwindigkeit: A·T⁻¹, nicht in Hz umrechenbar
    assert units.dimension_of("rpm") == (0, 0, -1, 0, 1, 0, 0)
    with pytest.raises(units.UnitConversionError, match="different dimension"):
        units.convert(1.0, "rpm", "Hz")


def test_pint_steradian_is_angle_squared(fake_pint):
    assert units.dimension_of("sr") == (0, 0, 0, 0, 2, 0, 0)


def test_pint_ppm_is_dimensionless(fake_pint):
    assert units.dimension_of("ppm") == (0, 0, 0, 0, 0, 0, 0)
    assert units.convert(1e4, "ppm", "%") == pytest.approx(1.0)


def test_pint_zero_factor_is_rejected(fake_pint, monkeypatch):
    monkeypatch.setitem(_FakePint._REG, "nil", ({"[length]": 1}, 0.0, 0.0, {"meter": 1}, False))
    assert units.dimension_of("nil") is None


def test_pint_offset_outside_temperature_is_rejected(fake_pint, monkeypatch):
    monkeypatch.setitem(_FakePint._REG, "shifted", ({"[length]": 1}, 1.0, 5.0, {"meter": 1}, False))
    assert units.dimension_of("shifted") is None


def test_pint_fractional_angle_exponent(fake_pint, monkeypatch):
    from fractions import Fraction
    monkeypatch.setitem(_FakePint._REG, "sqrad", ({}, 1.0, 0.0, {"radian": Fraction(1, 2)}, False))
    assert units.dimension_of("sqrad") == (0, 0, 0, 0, Fraction(1, 2), 0, 0)


def test_pint_quantity_error_is_rejected(fake_pint, monkeypatch):
    class _Boom(_FakePint._Quantity):
        def to_base_units(self):
            raise RuntimeError("boom")
    monkeypatch.setattr(_FakePint, "Quantity", staticmethod(lambda v, u: _Boom(v, u)))
    assert units.dimension_of("inch") is None


@pytest.mark.parametrize("a, b, value, expected", [
    ("degF", "degC", 212.0, 100.0),
    ("degF", "degC", 32.0, 0.0),
    ("arcminute", "deg", 60.0, 1.0),
    ("turn", "deg", 1.0, 360.0),
    ("ppm", "%", 1e4, 1.0),
    ("psi", "MPa", 1.0, 0.006894757293),
])
def test_real_pint_converts(a, b, value, expected):
    pytest.importorskip("pint")
    if units._pint is None:
        pytest.skip("pint-Registry nicht geladen")
    assert units.convert(value, a, b) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("a, b", [("rpm", "Hz"), ("dBm", "W"), ("count", "-"),
                                  ("grad", "deg")])
def test_real_pint_rejects(a, b):
    pytest.importorskip("pint")
    if units._pint is None:
        pytest.skip("pint-Registry nicht geladen")
    with pytest.raises(units.UnitConversionError):
        units.convert(1.0, a, b)


@pytest.mark.parametrize("a, b", [("dB", "-"), ("grad", "%"), ("arcminute", "-")])
def test_real_pint_does_not_convert_angle_or_log_to_dimensionless(a, b):
    pytest.importorskip("pint")
    if units._pint is None:
        pytest.skip("pint-Registry nicht geladen")
    with pytest.raises(units.UnitConversionError):
        units.convert(1.0, a, b)
