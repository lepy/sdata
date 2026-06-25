# -*- coding: utf-8 -*-
"""Abdeckung für das HTTP-Backend mit requests-Bevorzugung und urllib-Fallback."""
import io
import urllib.error

import pytest

from sdata.did import _http
from sdata.did._http import http_get, HttpError


# --- requests-Backend (über injiziertes Fake-Modul, real nicht nötig) -------
class _FakeRequests:
    class RequestException(Exception):
        pass

    @staticmethod
    def get(url, headers=None, timeout=None):
        class R:
            status_code = 200
            text = "ok"
        return R()


def test_requests_backend_success(monkeypatch):
    monkeypatch.setattr(_http, "_requests", _FakeRequests)
    assert http_get("http://x", headers={"A": "b"}, timeout=1) == (200, "ok")


def test_requests_backend_transport_error(monkeypatch):
    class FR:
        class RequestException(Exception):
            pass

        @staticmethod
        def get(url, headers=None, timeout=None):
            raise FR.RequestException("boom")

    monkeypatch.setattr(_http, "_requests", FR)
    with pytest.raises(HttpError):
        http_get("http://x")


# --- urllib-Fallback (requests "nicht installiert") -------------------------
class _FakeURLResp:
    status = 200

    class headers:
        @staticmethod
        def get_content_charset():
            return None  # -> Default utf-8

    def read(self):
        return b"hello"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_urllib_backend_success(monkeypatch):
    monkeypatch.setattr(_http, "_requests", None)
    monkeypatch.setattr(_http.urllib.request, "urlopen",
                        lambda req, timeout=None, context=None: _FakeURLResp())
    assert http_get("http://x", headers={"A": "b"}) == (200, "hello")


def test_urllib_backend_http_status(monkeypatch):
    monkeypatch.setattr(_http, "_requests", None)

    def raise_http(req, timeout=None, context=None):
        raise urllib.error.HTTPError("http://x", 404, "NF", {}, io.BytesIO(b"nope"))

    monkeypatch.setattr(_http.urllib.request, "urlopen", raise_http)
    assert http_get("http://x") == (404, "nope")


def test_urllib_backend_transport_error(monkeypatch):
    monkeypatch.setattr(_http, "_requests", None)

    def raise_url(req, timeout=None, context=None):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(_http.urllib.request, "urlopen", raise_url)
    with pytest.raises(HttpError):
        http_get("http://x")
