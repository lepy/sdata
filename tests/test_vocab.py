# -*- coding: utf-8 -*-
"""Tests für sdata/vocab.py (Namespaces, @context, XSD/BFO, CURIE/Prädikat/Typ)."""
from sdata import vocab


def test_build_context_inline_and_url():
    ctx = vocab.build_context()
    assert ctx["sdata"] == vocab.SDATA_NS
    assert ctx["name"] == "schema:name"
    assert ctx["generatedAtTime"]["@type"] == "xsd:dateTime"
    # extra-Terme
    ctx2 = vocab.build_context(extra={"foo": "sdata:foo"})
    assert ctx2["foo"] == "sdata:foo"
    # url-Modus
    assert vocab.build_context(mode="url") == vocab.CONTEXT_URL


def test_xsd_for_dtype():
    assert vocab.xsd_for_dtype("int") == "xsd:integer"
    assert vocab.xsd_for_dtype(float) == "xsd:double"
    assert vocab.xsd_for_dtype("timestamp") == "xsd:dateTime"
    assert vocab.xsd_for_dtype("bytes") == "xsd:base64Binary"
    assert vocab.xsd_for_dtype("unknown") == "xsd:string"


def test_expand_curie():
    assert vocab.expand_curie("schema:name") == "https://schema.org/name"
    assert vocab.expand_curie("http://x.org/a") == "http://x.org/a"
    assert vocab.expand_curie("https://x.org/a") == "https://x.org/a"
    assert vocab.expand_curie("plainstring") == "plainstring"      # kein ':'
    assert vocab.expand_curie("nope:term") == "nope:term"          # unbek. Präfix
    assert vocab.expand_curie(123) == 123                          # nicht-str


def test_bfo_iri():
    assert vocab.bfo_iri("sdata.sclass:IndependentContinuant") == "bfo:BFO_0000004"
    assert vocab.bfo_iri("MaterialEntity") == "bfo:BFO_0000040"
    assert vocab.bfo_iri("sdata.sclass:Unknown") is None
    assert vocab.bfo_iri(None) is None
    assert vocab.bfo_iri("") is None


def test_safe_term_predicate_type():
    assert vocab.safe_term("force_x") == "force_x"
    assert vocab.safe_term("Gauge Length (mm)") == "Gauge_Length__mm"
    assert vocab.safe_term("!!!") == "attribute"
    assert vocab.predicate_for("force_x") == "sdata:force_x"
    assert vocab.type_iri("bfo:Quality") == "bfo:Quality"
    assert vocab.type_iri("") is None
    assert vocab.type_iri(None) is None
