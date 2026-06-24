# -*- coding: utf-8 -*-
"""Lern-/Demo-Modul: Signieren einer DIDComm-Nachricht als Flattened JWS.

.. warning::
   Nur zu Demonstrationszwecken. Es nutzt :mod:`sdata.did.ed25519`, eine
   **nicht** für den Produktiveinsatz geeignete (nicht constant-time)
   Referenzimplementierung. Für echte Anwendungen :mod:`sdata.did.jose`
   (python-ecdsa) bzw. ein libsodium-Backend verwenden.

Ausführen::

    python -m sdata.did.diddoc
"""
from __future__ import annotations

import base64
import json
import logging

from .ed25519 import sign, publickey

logger = logging.getLogger(__name__)

__all__ = ["base64url_encode", "base64url_decode", "build_didcomm_jws"]


def base64url_encode(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def base64url_decode(data: bytes) -> bytes:
    return base64.urlsafe_b64decode(data + b"=" * (4 - len(data) % 4))


def build_didcomm_jws(message: dict, seed: bytes, kid: str = "did:example:alice#key-1") -> dict:
    """Signiere eine DIDComm-Nachricht und gib die Flattened-JWS-Struktur zurück.

    Args:
        message: Die DIDComm-Nachricht (wird als JSON serialisiert).
        seed: 32-Byte-Ed25519-Seed (privater Schlüssel; nur Demo!).
        kid: Schlüssel-ID für den JWS-Header.
    """
    pk = publickey(seed)
    header = {"typ": "JWM", "alg": "EdDSA", "kid": kid}
    protected = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload = base64url_encode(json.dumps(message, separators=(",", ":")).encode())
    sig = sign(protected + b"." + payload, seed, pk)
    return {
        "payload": payload.decode("utf-8"),
        "signatures": [{
            "protected": protected.decode("utf-8"),
            "signature": base64url_encode(sig).decode("utf-8"),
            "header": {"kid": kid},
        }],
    }


def _demo() -> dict:
    import os
    message = {
        "id": "1234567890",
        "type": "http://example.com/protocols/lets_do_lunch/1.0/proposal",
        "from": "did:example:alice",
        "to": ["did:example:bob"],
        "created_time": 1516269022,
        "expires_time": 1516385931,
        "body": {"messagespecificattribute": "and its value"},
    }
    return build_didcomm_jws(message, seed=os.urandom(32))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Signierte DIDComm-Nachricht (JWS):")
    logger.info("%s", json.dumps(_demo(), indent=2))
