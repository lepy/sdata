# -*- coding: utf-8 -*-
"""pint-Interop außerhalb der kuratierten Tabelle (RFC 0006).

Ohne installiertes pint bleibt das Verhalten unverändert (kuratierte Tabelle). Ist
pint vorhanden, werden nicht kuratierte Einheiten (imperial/abgeleitet) über pint auf
denselben 5-Achsen-Dimensionsvektor abgebildet und sind damit umrechenbar.

Getestet wird gegen ein **Fake-pint** (monkeypatch), damit die Zweige deterministisch
und ohne echte Abhängigkeit voll abgedeckt sind – dasselbe Muster wie bei
``validate_unit`` (siehe ``test_units.py``).
"""
import math

import pytest

from sdata import units


class _FakePint:
    """Minimaler pint-Ersatz: nur, was ``_pint_entry`` anfasst (Unit/Quantity/Fehler)."""

    class OffsetUnitCalculusError(Exception):
        pass

    #: name -> (dimensionality, factor_zu_SI, offset_zu_SI, is_offset)
    _REG = {
        "psi":  ({"[mass]": 1, "[length]": -1, "[time]": -2}, 6894.757293, 0.0, False),
        "inch": ({"[length]": 1}, 0.0254, 0.0, False),
        "lbf":  ({"[mass]": 1, "[length]": 1, "[time]": -2}, 4.4482216153, 0.0, False),
        "mm":   ({"[length]": 1}, 999.0, 0.0, False),   # bewusst falsch: Vorrang-Test
        "ampere": ({"[current]": 1}, 1.0, 0.0, False),  # Achse außerhalb -> nicht darstellbar
        "degF": ({"[temperature]": 1}, 5.0 / 9.0, 255.3722222, True),
    }

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

        def to_base_units(self):
            _dim, factor, _offset, is_offset = self._unit._spec
            if is_offset:
                raise _FakePint.OffsetUnitCalculusError()
            return _FakePint._Mag(self._value * factor)

        def to(self, _target):            # nur Kelvin-Pfad für Offset-Temperatur
            _dim, factor, offset, _is_offset = self._unit._spec
            return _FakePint._Mag(self._value * factor + offset)

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

def test_without_pint_unknown_stays_unknown():
    # Grundzustand: _pint is None -> nicht kuratierte Einheit bleibt unbekannt
    assert units._pint is None
    assert units.dimension_of("psi") is None
    with pytest.raises(units.UnitConversionError):
        units.convert(1.0, "psi", "MPa")


# ------------------------------------------------------------------ mit pint

def test_pint_dimension_of(fake_pint):
    assert units.dimension_of("psi") == (-1, 1, -2, 0, 0)     # Druck
    assert units.dimension_of("inch") == (1, 0, 0, 0, 0)      # Länge
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
    # elektrischer Strom liegt außerhalb (L, M, T, Θ, A)
    assert units.dimension_of("ampere") is None
    with pytest.raises(units.UnitConversionError):
        units.convert(1.0, "ampere", "psi")


def test_pint_unparseable_symbol_is_none(fake_pint):
    assert units.dimension_of("zonk") is None                 # Fake-pint wirft -> None


def test_curated_table_takes_precedence(fake_pint):
    # Fake-pint kennt "mm" mit falschem Faktor 999 – die kuratierte Tabelle gewinnt
    assert units.dimension_of("mm") == (1, 0, 0, 0, 0)
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
    assert vec == (Fraction(1, 2), 0, 0, 0, 0)
