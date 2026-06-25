# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/sclass/lazy_namespace.py."""
import sys
import types

import pytest

from sdata.base import Base
from sdata.sclass.lazy_namespace import (
    LazyRegistry, ExportItem, _split_spec, _resolve_attr,
    resolve_by_string, to_json, from_json, TYPE_FIELD, SPEC_FIELD,
)


def test_split_spec_and_resolve_attr():
    assert _split_spec("a.b:C.D") == ("a.b", "C.D")
    with pytest.raises(ValueError):
        _split_spec("nocolon")
    with pytest.raises(ValueError):
        _split_spec(":x")
    import sdata.base as m
    assert _resolve_attr(m, "Base") is Base


def test_export_item():
    assert ExportItem(name="X", spec="m:X").name == "X"


def _temp_pkg(name):
    pkg = types.ModuleType(name)
    sys.modules[name] = pkg
    return pkg


def test_registry_lifecycle():
    name = "sdata._test_lazy_pkg"
    pkg = _temp_pkg(name)
    try:
        reg = LazyRegistry(name)
        reg.register("Base", "sdata.base:Base")
        reg.register_many({"SUUID": "sdata.suuid:SUUID"})
        assert "Base" in reg.exports()
        reg.attach()
        reg.attach()                          # idempotent
        assert pkg.__getattr__("Base") is Base
        with pytest.raises(AttributeError):
            pkg.__getattr__("Missing")
        assert "Base" in pkg.__dir__()
        reg.register("X", "sdata.base:Base")          # nach attach -> __all__ update
        reg.register_many({"Y": "sdata.base:Base"})
        assert "X" in pkg.__all__ and "Y" in pkg.__all__
        assert resolve_by_string("Base", reg) is Base  # Kurzname via Registry
    finally:
        del sys.modules[name]


def test_get_pkg_missing():
    with pytest.raises(RuntimeError):
        LazyRegistry("nonexistent.package.xyz")._get_pkg()


def test_resolve_by_string_requires_registry():
    assert resolve_by_string("sdata.base:Base") is Base
    with pytest.raises(ValueError):
        resolve_by_string("Base")             # Kurzname ohne Registry


def test_to_json_and_from_json():
    b = Base(name="x")
    d = to_json(b, include_spec=True)
    assert SPEC_FIELD in d and TYPE_FIELD in d
    assert isinstance(from_json(d), Base)     # via __spec__ + from_dict

    # via __type__ + Registry
    name = "sdata._test_lazy_pkg3"
    _temp_pkg(name)
    try:
        reg = LazyRegistry(name)
        reg.register("Base", "sdata.base:Base")
        reg.attach()
        assert isinstance(from_json(to_json(b, type_name="Base"), reg), Base)
    finally:
        del sys.modules[name]

    # Klasse ohne from_dict -> init-Pfad
    obj = from_json({SPEC_FIELD: "builtins:dict", "a": 1})
    assert obj == {"a": 1}

    # weder __type__ noch __spec__ -> ValueError
    with pytest.raises(ValueError):
        from_json({"foo": 1})
