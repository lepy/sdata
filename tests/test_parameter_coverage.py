# -*- coding: utf-8 -*-
"""Vollständige Abdeckung für sdata.parameter."""
import pytest

from sdata.parameter import (
    Distribution, Parameter, Variable, DiscreteVariable,
    VariableInt, VariableFloat, VariableStr,
    DiscreteVariableInt, DiscreteVariableFloat, DiscreteVariableStr,
    DiscreteVariableBool, ParameterSet,
)


# --- Distribution -----------------------------------------------------------
def test_distribution_roundtrip_and_generate():
    d = Distribution("uniform", a=1)
    assert Distribution.from_dict(d.to_dict()).name == "uniform"
    assert 0.0 <= d.generate_value((0.0, 1.0)) <= 1.0
    with pytest.raises(ValueError):
        Distribution("weibull").generate_value((0.0, 1.0))


# --- _validate_and_cast_value ----------------------------------------------
def test_validate_and_cast_value_paths():
    # erfolgreiche Konvertierung "5" -> 5
    v = Variable("x", "5", int, bounds=[0, 10])
    assert v.value == 5
    # fehlgeschlagene Konvertierung -> Warnung, Originalwert bleibt
    with pytest.warns(UserWarning):
        v2 = Variable("y", "notanumber", int, bounds=[0, 10])
    assert v2.value == "notanumber"


# --- Parameter.from_dict ----------------------------------------------------
def test_parameter_from_dict_unknown():
    with pytest.raises(ValueError):
        Parameter.from_dict({"class_name": "DoesNotExist"})


# --- Variable ---------------------------------------------------------------
def test_variable_sample_value_fixed_and_random():
    fixed = VariableFloat("a", 2.0, bounds=[1.0, 3.0], fix=True)
    assert fixed.sample_value() == 2.0
    rnd = VariableFloat("b", 2.0, bounds=[1.0, 3.0])
    val = rnd.sample_value()
    assert 1.0 <= val <= 3.0


def test_variable_sample_values():
    fixed = VariableFloat("a", 2.0, bounds=[1.0, 3.0], fix=True)
    assert fixed.sample_values(3) == [2.0, 2.0, 2.0]
    rnd = VariableFloat("b", 2.0, bounds=[1.0, 3.0])
    assert len(rnd.sample_values(4)) == 4


def test_variable_repr_with_and_without_minmax():
    # VariableFloat hat min/max -> try-Zweig
    vf = VariableFloat("a", 2.0, bounds=[1.0, 3.0])
    assert "a" in repr(vf) and str(vf) == repr(vf)
    # Basis-Variable ohne min/max-Property -> except-Zweig
    base = Variable("b", 2.0, float, bounds=[1.0, 3.0])
    assert "b" in repr(base)


# --- DiscreteVariable -------------------------------------------------------
def test_discrete_variable_sample_and_dict():
    fixed = DiscreteVariableInt("d", 1, [1, 2, 3], fix=True)
    assert fixed.sample_value() == 1
    assert fixed.sample_values(2) == [1, 1]
    rnd = DiscreteVariableInt("d", 1, [1, 2, 3])
    assert rnd.sample_value() in [1, 2, 3]
    assert len(rnd.sample_values(5)) == 5
    data = rnd.to_dict()
    assert data["discrete_values"] == [1, 2, 3]


def test_discrete_variable_repr_branches():
    # > 4 Werte -> gekürzt mit "..."
    many = DiscreteVariableInt("d", 1, [1, 2, 3, 4, 5, 6])
    assert "..." in repr(many)
    # 1..4 Werte -> direkte Liste
    few = DiscreteVariableInt("d", 1, [1, 2])
    assert "1, 2" in repr(few) or "[1, 2]" in repr(few)
    # leere Werte -> "None"
    empty = DiscreteVariableInt("d", 1, [])
    assert "None" in repr(empty)
    # Ausnahme im try -> "!"
    broken = DiscreteVariableInt("d", 1, [1, 2])
    broken.discrete_values = 123  # len(int) -> TypeError
    assert "!" in repr(broken)
    assert str(few) == repr(few)


# --- VariableInt / VariableFloat min/max ------------------------------------
def test_variable_int_min_max():
    vi = VariableInt("i", 5, bounds=[1, 10])
    assert vi.min == 1 and vi.max == 10
    no_bounds = VariableInt("i", 5)
    with pytest.raises(ValueError):
        _ = no_bounds.min
    with pytest.raises(ValueError):
        _ = no_bounds.max


def test_variable_float_min_max_and_default_bounds():
    vf = VariableFloat("f", 2.5)            # bounds=None -> [2.5, 2.5]
    assert vf.min == 2.5 and vf.max == 2.5
    vf.bounds = None
    with pytest.raises(ValueError):
        _ = vf.min
    with pytest.raises(ValueError):
        _ = vf.max


def test_variable_str_sample_values():
    vs = VariableStr("s", "hello")
    assert vs.sample_values(3) == ["hello", "hello", "hello"]


def test_discrete_variable_specialized():
    b = DiscreteVariableBool("flag", True)
    assert set(b.discrete_values) == {True, False}
    f = DiscreteVariableFloat("f", 1.0, [1.0, 2.0, 3.0])
    assert f.value == 1.0
    s = DiscreteVariableStr("s", "a", ["a", "b"])
    assert s.value == "a"


# --- ParameterSet -----------------------------------------------------------
def _pset():
    ps = ParameterSet("set1")
    ps.add_parameters([
        VariableFloat("a", 1.0, bounds=[0.0, 2.0]),
        VariableInt("b", 3, bounds=[1, 5]),
    ])
    return ps


def test_parameterset_views_and_access():
    ps = _pset()
    assert ps.name == "set1"
    assert set(ps.parameters.keys()) == {"a", "b"}
    assert "a" in ps
    assert ps["a"].name == "a"
    assert set(ps.keys()) == {"a", "b"}
    assert len(list(ps.values())) == 2
    assert len(list(ps.items())) == 2
    assert len(list(iter(ps))) == 2
    assert ps.get("missing", "dflt") == "dflt"
    assert ps.get("a") is not None


def test_parameterset_update_pop():
    ps = _pset()
    ps.update([VariableFloat("c", 9.0, bounds=[0.0, 10.0])])
    assert "c" in ps
    popped = ps.pop("c")
    assert popped.name == "c"
    assert ps.pop("nope") is None


def test_parameterset_json_roundtrip_and_print(caplog):
    ps = _pset()
    js = ps.to_json()
    restored = ParameterSet.from_json(js)
    assert set(restored.keys()) == {"a", "b"}
    assert ParameterSet.from_dict(ps.to_dict()).name == "set1"
    import logging
    with caplog.at_level(logging.INFO):
        ps.print()
    assert repr(ps).startswith("ParameterSet(set1")
    assert str(ps) == repr(ps)
