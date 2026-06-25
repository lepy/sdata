# -*- coding: utf-8 -*-
"""Abdeckung von sdata/sclass/dependency_graph.py und sdata/sclass/__init__.py."""
import pytest

from sdata.base import Base
from sdata.sclass.dependency_graph import (
    toposort, toposort_flatten, CircularDependencyError,
)
from sdata.sclass import (
    register, register_many, get_specs, class_to_spec, obj_to_spec,
    spec_to_class, is_importable_by_spec, make_module_alias,
)


# --- dependency_graph ---------------------------------------------------
def test_toposort_empty():
    assert list(toposort({})) == []


def test_toposort_dag_and_flatten():
    g = {"a": {"b"}, "b": set(), "c": {"a"}}
    levels = list(toposort(g))
    assert levels[0] == {"b"}
    flat = toposort_flatten(g)
    assert flat.index("b") < flat.index("a") < flat.index("c")
    assert "y" in toposort_flatten({"x": {"y"}})   # extra_nodes
    assert isinstance(toposort_flatten(g, sort=False), list)


def test_toposort_cycle():
    with pytest.raises(CircularDependencyError):
        list(toposort({"a": {"b"}, "b": {"a"}}))


# --- sclass/__init__ ----------------------------------------------------
def test_registry_and_specs():
    register("MyAlias", "sdata.base:Base")
    register_many({"MyAlias2": "sdata.base:Base"})
    assert "MyAlias" in get_specs()
    assert class_to_spec(Base) == "sdata.base:Base"
    assert obj_to_spec(Base(name="x")) == "sdata.base:Base"
    assert spec_to_class("sdata.base:Base") is Base
    assert spec_to_class("nope.mod:Thing", on_error="ignore") is Base
    with pytest.raises(ModuleNotFoundError):
        spec_to_class("nope.mod:Thing", on_error="strict")


def test_is_importable_and_make_module_alias():
    assert is_importable_by_spec(Base) is True

    class Local:           # lokal/nested -> nicht per Spec importierbar
        pass
    assert is_importable_by_spec(Local) is False
    spec = make_module_alias(Local, alias="LocalAlias_xyz")
    assert spec.endswith(":LocalAlias_xyz")
    assert spec_to_class(spec) is Local
