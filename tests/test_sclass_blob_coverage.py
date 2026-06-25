# -*- coding: utf-8 -*-
"""Vollständige Abdeckung von sdata/sclass/blob.py."""
import pytest

pytest.importorskip("fsspec")

import sdata.sclass.blob as blobmod
from sdata.sclass.blob import Blob


def test_invalid_content_type():
    with pytest.raises(ValueError):
        Blob(content_type="nope", name="b")


def test_bytes_content_and_hashes():
    b = Blob(content_type="bytes", value=b"hello", filetype="bin", name="b")
    assert b.filetype == "bin"
    assert b.content_bytes == b"hello"          # b64decode
    assert b.content_bytes == b"hello"          # Cache
    assert b.exists() is True
    assert len(b.sha1) == 40 and len(b.md5) == 32


def test_value_none_and_set_content():
    b = Blob(name="b")                          # bytes, value None
    assert b.exists() is False
    with pytest.raises(ValueError):
        _ = b.content_bytes                     # kein value
    b.set_content("bytes", b"data", filetype="x")
    assert b.content_bytes == b"data" and b.filetype == "x"


def test_uri_content(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"uri-bytes")
    b = Blob(content_type="uri", value=str(p), filetype="txt", name="u")
    assert b.content_bytes == b"uri-bytes"      # fsspec.open
    assert b.exists() is True
    # nicht existierende Datei -> exists False
    b2 = Blob(content_type="uri", value=str(tmp_path / "missing"), name="u2")
    assert b2.exists() is False


def test_set_value_type_errors():
    b = Blob(name="b")
    with pytest.raises(ValueError):
        b.set_content("bytes", "not-bytes")     # bytes erwartet
    with pytest.raises(ValueError):
        b.set_content("uri", b"not-str")        # str erwartet
    with pytest.raises(ValueError):
        b.set_content("weird", b"x")            # unbekannter content_type


def test_content_bytes_error_branches():
    b = Blob(content_type="bytes", value=b"x", name="b")
    # unbekannter ctype
    b.data["content"]["type"] = "weird"
    with pytest.raises(ValueError):
        _ = b.content_bytes
    # kein content
    b.data.pop("content")
    with pytest.raises(ValueError):
        _ = b.content_bytes


def test_exists_branches():
    b = Blob(name="b")
    assert b.exists() is False                  # value None
    b.data.pop("content")
    assert b.exists() is False                  # kein content
    b2 = Blob(content_type="bytes", value=b"x", name="b2")
    b2.data["content"]["type"] = "weird"
    assert b2.exists() is False                 # unbekannter ctype


def test_uri_fsspec_none(monkeypatch, tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"x")
    b = Blob(content_type="uri", value=str(p), name="u")
    monkeypatch.setattr(blobmod, "fsspec", None)
    with pytest.raises(ImportError):
        _ = b.content_bytes
    assert b.exists() is False


def test_uri_bad_value_raises_and_exists_exception():
    b = Blob(content_type="uri", value="://broken", name="u")
    with pytest.raises(ValueError):
        _ = b.content_bytes
    # unbekanntes Protokoll -> get_fs_token_paths wirft -> except-Zweig in exists()
    b2 = Blob(content_type="uri", value="weirdproto://x", name="u2")
    assert b2.exists() is False


def test_sha1_md5_none_on_error():
    b = Blob(name="b")                          # value None -> content_bytes wirft
    assert b.sha1 is None
    assert b.md5 is None


def test_to_from_dict():
    b = Blob(content_type="bytes", value=b"abc", filetype="bin", name="b")
    d = b.to_dict()
    assert "content" in d["data"]
    r = Blob.from_dict(d)
    assert r.data["content"]["type"] == "bytes"
    # from_dict ohne content -> Default ergänzt
    r2 = Blob.from_dict({"metadata": d["metadata"], "data": {}, "description": ""})
    assert r2.data["content"]["type"] == "bytes"
    # ungültige content-Struktur -> ValueError
    with pytest.raises(ValueError):
        Blob.from_dict({"metadata": d["metadata"], "data": {"content": {}}, "description": ""})
    # uri mit nicht-String value -> ValueError
    with pytest.raises(ValueError):
        Blob.from_dict({"metadata": d["metadata"],
                        "data": {"content": {"type": "uri", "filetype": "x", "value": 123}},
                        "description": ""})
