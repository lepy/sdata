# -*- coding: utf-8 -*-
"""Blob-Härtung (RFC 0003, Teil A): sha256/verify/update_checksum, size,
nicht-serialisierter Cache und Standard-Vokabular statt undefiniertem saf:-Prefix.
"""
import json

from sdata.sclass.blob import Blob


def test_sha256_and_size():
    b = Blob(content_type="bytes", value=b"hello", filetype="bin", name="b")
    assert len(b.sha256) == 64
    assert b.size == 5


def test_sha256_size_none_on_error():
    b = Blob(name="b")                              # value None -> content_bytes wirft
    assert b.sha256 is None
    assert b.size is None


def test_update_checksum_and_verify():
    b = Blob(content_type="bytes", value=b"data", name="b")
    assert b.verify() is False                      # noch keine checksum gespeichert
    digest = b.update_checksum()
    assert digest == b.sha256 and len(digest) == 64
    assert b.verify() is True                       # Inhalt passt zur checksum
    b.set_content("bytes", b"tampered")             # Inhalt ändern (Cache wird geleert)
    assert b.verify() is False                      # stimmt nicht mehr


def test_ontology_uses_standard_vocab():
    b = Blob(content_type="bytes", value=b"x", name="b")
    assert b.metadata.get("checksum").ontology == "schema:sha256"
    assert b.metadata.get("mime_type").ontology == "dcat:mediaType"
    assert b.metadata.get("source_uri").ontology == "dcterms:source"
    assert b.metadata.get("creation_date").ontology == "dcterms:created"
    assert b.metadata.get("modified_date").ontology == "dcterms:modified"
    assert b.metadata.get("publisher").ontology == "dcterms:publisher"
    assert b.metadata.get("license").ontology == "dcterms:license"
    # JSON-LD enthält keinen undefinierten saf:-Prefix mehr
    assert "saf:" not in json.dumps(b.to_jsonld())


def test_cache_is_not_serialized():
    b = Blob(content_type="bytes", value=b"hello", name="b")
    assert b.content_bytes == b"hello"              # füllt den Lazy-Cache
    assert b._content_cache == b"hello"             # Instanzattribut ...
    d = b.to_dict()
    assert "content_cached" not in d["data"]        # ... nicht im serialisierten data
    assert "content" in d["data"]
