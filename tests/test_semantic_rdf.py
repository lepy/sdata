# -*- coding: utf-8 -*-
"""Tests für die RDF/Turtle-Serialisierung (rdflib optional, JSON-LD-Fallback)."""
import json

import pytest

from sdata.base import Base
from sdata import semantic


def _md():
    b = Base(name="specimen_rdf")
    b.metadata.add("force_x", 12.5, unit="kN", dtype="float")
    return b.metadata


def test_to_rdf_fallback_is_jsonld(monkeypatch):
    monkeypatch.setattr(semantic, "_rdflib", None)
    out = _md().to_rdf()
    doc = json.loads(out)                      # Fallback = gültiges JSON-LD
    assert "@context" in doc and doc["name"] == "specimen_rdf"
    # Base-Delegator liefert dasselbe (Fallback-JSON-LD)
    b = Base(name="specimen_rdf")
    b.metadata.add("force_x", 12.5, unit="kN", dtype="float")
    assert json.loads(b.to_turtle())["name"] == "specimen_rdf"


def test_to_rdf_with_fake_rdflib(monkeypatch):
    class _FakeGraph:
        def parse(self, data=None, format=None):
            self.data = data
            return self
        def serialize(self, format=None):
            return "@FAKE-RDF@ format={}".format(format)

    class _FakeRdflib:
        Graph = _FakeGraph

    monkeypatch.setattr(semantic, "_rdflib", _FakeRdflib)
    assert "@FAKE-RDF@ format=turtle" in _md().to_turtle()
    assert "format=nt" in _md().to_rdf(fmt="nt")


def test_to_turtle_real_rdflib():
    rdflib = pytest.importorskip("rdflib")
    ttl = _md().to_turtle()
    graph = rdflib.Graph()
    graph.parse(data=ttl, format="turtle")
    assert len(graph) > 0                       # Tripel wurden erzeugt
