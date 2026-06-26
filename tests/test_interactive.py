# -*- coding: utf-8 -*-
"""Tests für die interaktive Schicht: _repr_html_, .a-Accessor, get_prefixed."""
import pytest

from sdata.base import Base
from sdata.metadata import Attribute, Metadata


def test_attribute_repr_html():
    a = Attribute("force_x", 12.5, unit="kN", dtype="float", ontology="bfo:Quality")
    html = a._repr_html_()
    assert "force_x" in html and "kN" in html and "bfo:Quality" in html


def test_metadata_repr_html_bare_and_base():
    # bare Metadata: kein did/class
    m = Metadata()
    m.add("note", "<b>hi</b>")
    html = m._repr_html_()
    assert "note" in html
    assert "&lt;b&gt;hi&lt;/b&gt;" in html          # HTML-escaped
    assert "did:suuid" not in html
    # Base: mit did + class
    b = Base(name="specimen")
    b.metadata.add("force_x", 1.0, unit="kN", dtype="float")
    bh = b._repr_html_()
    assert "did:suuid:Base__specimen__" in bh
    assert "sdata.base:Base" in bh and "force_x" in bh


def test_attr_accessor():
    m = Metadata()
    m.add("force_x", 12.5, unit="kN", dtype="float")
    m.add("with space", 1)                          # kein Identifier -> nicht in dir()
    # get
    assert m.a.force_x.value == 12.5
    # set
    m.a.stress = 350.0
    assert m.get("stress").value == 350.0
    # dir -> nur identifier-fähige User-Attribute
    names = dir(m.a)
    assert "force_x" in names and "stress" in names and "with space" not in names
    # unbekannt -> AttributeError
    with pytest.raises(AttributeError):
        _ = m.a.does_not_exist
    # repr
    assert "AttrAccessor(" in repr(m.a)


def test_get_prefixed():
    m = Metadata()
    m.add("Load/Fx", 1.0, prefix="")                # key "Load/Fx"
    m.set_attr("Fy", 2.0, prefix="Load/")
    m.add("temp", 25.0)
    sub = m.get_prefixed("Load/")
    assert set(sub.keys()) == {"Load/Fx", "Load/Fy"}
    assert "temp" not in sub
    # reservierte via Prefix
    b = Base(name="x")
    assert all(k.startswith("_sdata") for k in b.metadata.get_prefixed("_sdata").keys())
