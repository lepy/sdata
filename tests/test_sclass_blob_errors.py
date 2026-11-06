# -*- coding: utf-8 -*-
"""Einheitliche Fehlerbilder beim Zugriff auf Blob-Inhalte (RFC 0019)."""
import errno
import importlib.util
import os

import pytest

pytest.importorskip("fsspec")

import sdata.sclass.blob as blobmod
from sdata.sclass.blob import (
    Blob,
    ContentNotFoundError,
    ContentPermissionError,
    ContentUnavailableError,
)

IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
HAS_S3FS = importlib.util.find_spec("s3fs") is not None


def _uri_blob(uri):
    return Blob(content_type="uri", value=str(uri), filetype="bin", name="u")


# --- §2.1 Ausnahmeklassen -------------------------------------------------

def test_exception_hierarchy():
    assert issubclass(ContentUnavailableError, ValueError)
    assert issubclass(ContentNotFoundError, FileNotFoundError)
    assert issubclass(ContentNotFoundError, ContentUnavailableError)
    assert issubclass(ContentPermissionError, PermissionError)
    assert issubclass(ContentPermissionError, ContentUnavailableError)


def test_unavailable_translation_keeps_errno_filename_uri():
    err = blobmod._unavailable("/x", FileNotFoundError(2, "No such file", "/x"))
    assert type(err) is ContentNotFoundError
    assert (err.errno, err.filename, err.uri) == (2, "/x", "/x")
    err = blobmod._unavailable("/y", PermissionError(13, "denied", "/y"))
    assert type(err) is ContentPermissionError and err.errno == 13
    err = blobmod._unavailable("s3://b/k", ImportError("Install s3fs"))
    assert type(err) is ContentUnavailableError and err.uri == "s3://b/k"
    assert not isinstance(err, OSError)


def test_unavailable_without_errno_uses_default():
    err = blobmod._unavailable("memory://x", FileNotFoundError("/x"))
    assert err.errno == errno.ENOENT
    assert "Errno None" not in str(err)
    err = blobmod._unavailable("/y", PermissionError("denied"))
    assert err.errno == errno.EACCES


# --- §2.2 content_bytes ---------------------------------------------------

def test_content_bytes_missing_file(tmp_path):
    b = _uri_blob(tmp_path / "missing.bin")
    with pytest.raises(ContentNotFoundError) as info:
        _ = b.content_bytes
    assert isinstance(info.value, ValueError)              # Altaufrufer
    assert isinstance(info.value.__cause__, FileNotFoundError)
    assert info.value.uri == str(tmp_path / "missing.bin")


@pytest.mark.skipif(IS_ROOT, reason="root darf jede Datei lesen")
def test_content_bytes_no_permission(tmp_path):
    p = tmp_path / "noperm.bin"
    p.write_bytes(b"x")
    p.chmod(0)
    try:
        with pytest.raises(ContentPermissionError):
            _ = _uri_blob(p).content_bytes
    finally:
        p.chmod(0o600)


def test_content_bytes_directory(tmp_path):
    with pytest.raises(ContentUnavailableError) as info:
        _ = _uri_blob(tmp_path).content_bytes
    assert isinstance(info.value.__cause__, IsADirectoryError)


@pytest.mark.skipif(HAS_S3FS, reason="nur ohne s3fs")
def test_content_bytes_missing_backend():
    with pytest.raises(ContentUnavailableError) as info:
        _ = _uri_blob("s3://bucket/key.bin").content_bytes
    assert isinstance(info.value.__cause__, ImportError)


def test_content_bytes_unknown_protocol():
    with pytest.raises(ContentUnavailableError):
        _ = _uri_blob("foo://x/y").content_bytes


def test_content_bytes_memory_missing():
    with pytest.raises(ContentNotFoundError) as info:
        _ = _uri_blob("memory://rfc0019-missing.bin").content_bytes
    assert info.value.errno == errno.ENOENT


def test_programming_errors_stay_plain_valueerror():
    b = Blob(name="b")                                      # kein value
    with pytest.raises(ValueError) as info:
        _ = b.content_bytes
    assert not isinstance(info.value, ContentUnavailableError)


# --- §2.2 open ------------------------------------------------------------

def test_open_raises_at_call(tmp_path):
    b = _uri_blob(tmp_path / "missing.bin")
    with pytest.raises(ContentNotFoundError):
        b.open()                                            # nicht erst im with


def test_open_context_manager_still_works(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"data")
    with _uri_blob(p).open() as fh:
        assert fh.read() == b"data"
    with Blob(content_type="bytes", value=b"mem", name="m").open() as fh:
        assert fh.read() == b"mem"


# --- §2.2 exists ----------------------------------------------------------

def test_exists_false_only_when_missing(tmp_path):
    assert _uri_blob(tmp_path / "missing.bin").exists() is False
    assert _uri_blob(tmp_path).exists() is True             # gibt es, unlesbar


def test_exists_raises_when_it_cannot_check():
    with pytest.raises(ContentUnavailableError):
        _uri_blob("foo://x/y").exists()


def test_exists_without_fsspec_raises_importerror(monkeypatch, tmp_path):
    monkeypatch.setattr(blobmod, "fsspec", None)
    with pytest.raises(ImportError):
        _uri_blob(tmp_path / "f.bin").exists()


# --- §2.2 update_checksum / verify ----------------------------------------

def _cold_copy(blob):
    """Neue Instanz derselben Quelle mit gespeicherter Prüfsumme, aber leerem Cache."""
    cold = _uri_blob(blob.data["content"]["value"])
    cold.metadata.set_attr("checksum", blob.metadata.get("checksum").value)
    return cold


def _stored_then_deleted(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc")
    b = _uri_blob(p)
    b.update_checksum()
    cold = _cold_copy(b)
    p.unlink()
    return cold


def test_verify_raises_when_unreadable(tmp_path):
    cold = _stored_then_deleted(tmp_path)
    with pytest.raises(ContentNotFoundError):
        cold.verify()


def test_update_checksum_raises_when_unreadable(tmp_path):
    cold = _stored_then_deleted(tmp_path)
    before = cold.metadata.get("checksum").value
    with pytest.raises(ContentNotFoundError):
        cold.update_checksum()
    assert cold.metadata.get("checksum").value == before    # unverändert


def test_verify_false_means_mismatch_or_no_checksum(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc")
    b = _uri_blob(p)
    assert b.verify() is False                              # keine Prüfsumme
    b.update_checksum()
    cold = _cold_copy(b)
    p.write_bytes(b"manipuliert")
    assert cold.verify() is False                           # Abweichung


def test_verify_without_checksum_does_not_read(tmp_path):
    assert _uri_blob(tmp_path / "missing.bin").verify() is False


def test_update_checksum_without_content_raises():
    with pytest.raises(ValueError):
        Blob(name="leer").update_checksum()
