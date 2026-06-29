# -*- coding: utf-8 -*-
"""Blob Teil A — Rest (RFC 0003): mime_type/creation_date-Autofill (B2) und
write()/open() über fsspec (B5)."""
import pytest

pytest.importorskip("fsspec")

import sdata.sclass.blob as blobmod
from sdata.sclass.blob import Blob


def test_mime_and_creation_autofill():
    b = Blob(content_type="bytes", value=b"x", filetype="pdf", name="b")
    assert b.metadata.get("mime_type").value == "application/pdf"
    ctime = b.metadata.get("_sdata_ctime").value
    assert ctime and b.metadata.get("creation_date").value == ctime   # aus _sdata_ctime
    # Default-Filetype 'binary' -> kein MIME ableitbar -> bleibt None
    b2 = Blob(content_type="bytes", value=b"x", name="b2")
    assert b2.metadata.get("mime_type").value is None


def test_write_and_open_bytes(tmp_path):
    b = Blob(content_type="bytes", value=b"hello", filetype="bin", name="b")
    dest = str(tmp_path / "out.bin")
    assert b.write(dest) == dest
    assert (tmp_path / "out.bin").read_bytes() == b"hello"
    with b.open() as f:                          # bytes -> io.BytesIO
        assert f.read() == b"hello"


def test_open_uri(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"uri-bytes")
    b = Blob(content_type="uri", value=str(p), filetype="txt", name="u")
    with b.open() as f:                          # uri -> streamendes fsspec-Handle
        assert f.read() == b"uri-bytes"


def test_open_errors():
    with pytest.raises(ValueError):
        Blob(name="b").open()                    # kein value
    b = Blob(content_type="bytes", value=b"x", name="b2")
    b.data["content"]["type"] = "weird"
    with pytest.raises(ValueError):
        b.open()                                 # unbekannter content_type


def test_write_open_fsspec_none(monkeypatch, tmp_path):
    b = Blob(content_type="bytes", value=b"x", name="b")
    bu = Blob(content_type="uri", value=str(tmp_path / "f"), name="u")
    monkeypatch.setattr(blobmod, "fsspec", None)
    with pytest.raises(ImportError):
        b.write(str(tmp_path / "x.bin"))
    with pytest.raises(ImportError):
        bu.open()
