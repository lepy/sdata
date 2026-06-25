# -*- coding: utf-8 -*-
"""HTTP-GET mit optionalem ``requests``-Backend und ``urllib``-Fallback.

Wenn ``requests`` installiert ist, wird es genutzt (gewohntes Verhalten,
Connection-Pooling, certifi-CA-Bundle); andernfalls greift ein Fallback auf
``urllib.request`` aus der Standardbibliothek. **Die TLS-Zertifikatsprüfung
bleibt in beiden Fällen aktiv** (kein ``verify=False``).

Damit ist ``requests`` für ``sdata.did`` rein optional – das Subpackage bleibt
auch ohne die Abhängigkeit voll funktionsfähig.
"""
from __future__ import annotations

import ssl
import urllib.request
import urllib.error
from typing import Dict, Optional, Tuple

try:  # bevorzugtes Backend, falls installiert
    import requests as _requests
except ImportError:  # pragma: no cover - abhängig vom Environment
    _requests = None

__all__ = ["http_get", "HttpError"]


class HttpError(Exception):
    """Transportfehler (DNS/Timeout/Verbindung) beim HTTP-GET – backend-neutral.

    HTTP-Statuscodes (auch 4xx/5xx) sind *keine* ``HttpError`` – sie werden von
    :func:`http_get` als ``status_code`` zurückgegeben.
    """


def http_get(url: str, headers: Optional[Dict[str, str]] = None,
             timeout: float = 10.0) -> Tuple[int, str]:
    """GET ``url`` und liefere ``(status_code, body_text)``.

    Nutzt ``requests`` falls verfügbar, sonst ``urllib.request``.

    Raises:
        HttpError: bei Transportfehlern (DNS, Timeout, Verbindungsabbruch).
    """
    if _requests is not None:
        return _get_requests(url, headers, timeout)
    return _get_urllib(url, headers, timeout)


def _get_requests(url, headers, timeout):
    try:
        resp = _requests.get(url, headers=headers, timeout=timeout)
    except _requests.RequestException as exc:
        raise HttpError(str(exc)) from exc
    return resp.status_code, resp.text


def _get_urllib(url, headers, timeout):
    req = urllib.request.Request(url, headers=headers or {})
    ctx = ssl.create_default_context()  # Zertifikats-/Hostname-Prüfung aktiv
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.status, resp.read().decode(charset, "replace")
    except urllib.error.HTTPError as exc:  # 4xx/5xx: Status, kein Transportfehler
        return exc.code, exc.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:   # DNS/Timeout/Verbindung
        raise HttpError(str(exc)) from exc
