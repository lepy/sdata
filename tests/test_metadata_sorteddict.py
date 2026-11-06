# -*- coding: utf-8 -*-
"""Sortierte Attribut-Reihenfolge von Metadata (Ersatz für vendored sortedcontainers)."""
import copy
import json

from sdata.metadata import Metadata, SortedDict


def test_sorteddict_iterates_sorted():
    d = SortedDict()
    for k in ["c", "a", "b"]:
        d[k] = k.upper()
    assert list(d) == ["a", "b", "c"]
    assert list(d.keys()) == ["a", "b", "c"]
    assert list(d.values()) == ["A", "B", "C"]
    assert list(d.items()) == [("a", "A"), ("b", "B"), ("c", "C")]
    assert list(reversed(d)) == ["c", "b", "a"]


def test_sorteddict_is_a_dict_and_compares_like_one():
    d = SortedDict([("b", 2), ("a", 1)])
    assert isinstance(d, dict)
    assert d == {"a": 1, "b": 2}
    assert repr(d) == "SortedDict({'a': 1, 'b': 2})"
    assert json.loads(json.dumps(d)) == {"a": 1, "b": 2}


def test_sorteddict_copy_keeps_type():
    d = SortedDict(b=2, a=1)
    for c in (d.copy(), copy.copy(d), copy.deepcopy(d)):
        assert type(c) is SortedDict
        assert list(c) == ["a", "b"]


def test_sorteddict_mutation_after_iteration():
    d = SortedDict(b=2)
    assert list(d) == ["b"]
    d["a"] = 1
    d.pop("b")
    d.update(c=3)
    assert list(d) == ["a", "c"]


def test_metadata_attributes_sorted():
    m = Metadata(name="m")
    for name in ["zeta", "alpha", "mu"]:
        m.add(name, 1.0)
    assert m.keys() == ["alpha", "mu", "zeta"]
    assert list(m.user_attributes) == ["alpha", "mu", "zeta"]
    assert isinstance(m.attributes, SortedDict)
    assert type(m.user_attributes) is SortedDict
