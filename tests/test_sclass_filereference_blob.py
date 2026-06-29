# -*- coding: utf-8 -*-
"""FileReference(Blob) — RFC 0003 Teil B (1. Schritt): FileReference auf Blob.

Verifiziert den Foundation-Gewinn: der Datei-Pfad bleibt als uri-Content erhalten
(ging zuvor verloren) und FileReference erbt die Blob-Content-API.
"""
import pytest

pytest.importorskip("fsspec")

from sdata.sclass.blob import Blob
from sdata.sclass.filereference import FileReference


def test_filereference_is_blob_and_retains_path(tmp_path):
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"hello pdf")
    fr = FileReference.from_file(str(p))
    assert isinstance(fr, Blob)
    # Pfad als uri-Content erhalten (zuvor ging er verloren)
    assert fr.data["content"]["type"] == "uri"
    assert fr.data["content"]["value"] == str(p)
    # geerbte Blob-Fähigkeiten
    assert fr.content_bytes == b"hello pdf"
    assert fr.exists() is True
    assert fr.size == len(b"hello pdf")
    with fr.open() as f:
        assert f.read() == b"hello pdf"


def test_filereference_missing_path_not_exists(tmp_path):
    fr = FileReference(name=str(tmp_path / "missing.txt"))
    assert fr.exists() is False
    assert fr.filetype == ".txt"          # robuste Property weiterhin korrekt
