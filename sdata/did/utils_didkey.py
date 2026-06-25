# -*- coding: utf-8 -*-
"""Hilfsfunktionen rund um ``did:key``, JWK und RFC-7638-Thumbprints (Ed25519).

Funktionsumfang:

* Base64url-Kodierung ohne Padding (RFC 7515 §2),
* RFC-7638-Thumbprint: kanonisches JSON ``{crv,kty,x}`` → SHA-256 → base64url,
* ``did:key`` für Ed25519 erzeugen (multicodec ``0xED 0x01`` + multibase ``z``-base58btc),
* ``did:key`` (bzw. nackte Multibase) zurück zu einem Public-JWK auflösen,
* konventionelle ``kid``-Bildung für ``did:web`` und ``did:key``.

Es werden ausschließlich **öffentliche** Schlüssel verarbeitet; private Schlüssel
tauchen hier nicht auf. Abhängigkeitsfrei (nur Standardbibliothek + die eigene
base58btc-Kodierung in :mod:`sdata.did.base58btc`).

Referenzen:
    * `RFC 7638 <https://www.rfc-editor.org/rfc/rfc7638>`_ – JWK Thumbprint
    * `did:key Method <https://w3c-ccg.github.io/did-method-key/>`_
    * `Multicodec <https://github.com/multiformats/multicodec>`_ (ed25519-pub = 0xED)
"""
from __future__ import annotations

import json
import base64
import hashlib
from typing import Dict

from .base58btc import b58encode, b58decode
from .errors import EncodingError

__all__ = [
    "b64url",
    "b64url_decode",
    "jwk_thumbprint_rfc7638",
    "did_key_from_jwk_ed25519",
    "did_key_fragment_from_jwk",
    "pub_jwk_from_did_key",
    "kid_for_did_web",
    "kid_for_did_key",
]

# multicodec-Präfix (unsigned varint) für einen öffentlichen Ed25519-Schlüssel.
_ED25519_PUB_PREFIX = bytes([0xED, 0x01])


# --------------------------------------------------------------------------
# Base64url-Helfer (ohne Padding, RFC 7515)
# --------------------------------------------------------------------------
def b64url(data: bytes) -> str:
    """Kodiere ``data`` als base64url ohne ``=``-Padding."""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def b64url_decode(s: str) -> bytes:
    """Dekodiere einen base64url-String; fehlendes Padding wird ergänzt."""
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


# --------------------------------------------------------------------------
# Validierung
# --------------------------------------------------------------------------
def _assert_ed25519_jwk_pub(jwk_pub: Dict) -> None:
    """Stelle sicher, dass ``jwk_pub`` ein gültiger öffentlicher Ed25519-JWK ist.

    Raises:
        EncodingError: bei falschem Typ, ``kty``/``crv`` oder Schlüssellänge.
    """
    if not isinstance(jwk_pub, dict):
        raise EncodingError("jwk_pub muss ein dict sein")
    if jwk_pub.get("kty") != "OKP" or jwk_pub.get("crv") != "Ed25519":
        raise EncodingError("nur OKP/Ed25519 wird unterstützt")
    if "x" not in jwk_pub:
        raise EncodingError("JWK fehlt das Feld 'x' (Public Key)")
    raw = b64url_decode(jwk_pub["x"])
    if len(raw) != 32:
        raise EncodingError(
            "Ed25519 Public Key muss 32 Byte sein (war {})".format(len(raw)))


def _strip_didkey_multibase(did_or_mb: str) -> str:
    """Normalisiere ``did:key:z…``, ``#z…`` oder ``z…`` auf die nackte Multibase ``z…``."""
    s = did_or_mb
    if s.startswith("did:key:"):
        s = s.split(":", 2)[2]
    if s.startswith("#"):
        s = s[1:]
    return s


# --------------------------------------------------------------------------
# RFC-7638-Thumbprint
# --------------------------------------------------------------------------
def jwk_thumbprint_rfc7638(jwk_pub: Dict) -> str:
    """Berechne den RFC-7638-Thumbprint eines öffentlichen Ed25519-JWK.

    Kanonisiert wird über die Pflichtfelder ``{crv, kty, x}`` (lexikografisch
    sortiert, ohne Whitespace); davon der SHA-256, base64url-kodiert.

    Returns:
        Der Thumbprint als base64url-String (ohne Padding).
    """
    _assert_ed25519_jwk_pub(jwk_pub)
    data = {"crv": jwk_pub["crv"], "kty": jwk_pub["kty"], "x": jwk_pub["x"]}
    canon = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    return b64url(hashlib.sha256(canon).digest())


# --------------------------------------------------------------------------
# did:key  <->  JWK
# --------------------------------------------------------------------------
def did_key_from_jwk_ed25519(jwk_pub: Dict) -> str:
    """Erzeuge eine ``did:key``-DID aus einem öffentlichen Ed25519-JWK."""
    _assert_ed25519_jwk_pub(jwk_pub)
    raw = b64url_decode(jwk_pub["x"])  # 32 Byte
    mb = "z" + b58encode(_ED25519_PUB_PREFIX + raw)
    return "did:key:{}".format(mb)


def did_key_fragment_from_jwk(jwk_pub: Dict) -> str:
    """Liefere den Multibase-Teil (``z…``) – praktisch als ``kid``-Fragment."""
    _assert_ed25519_jwk_pub(jwk_pub)
    raw = b64url_decode(jwk_pub["x"])
    return "z" + b58encode(_ED25519_PUB_PREFIX + raw)


def pub_jwk_from_did_key(did_key_or_mb: str) -> Dict[str, str]:
    """Gewinne den öffentlichen JWK aus einer ``did:key``-DID oder Multibase zurück.

    Akzeptiert ``did:key:z…``, ``#z…`` oder die nackte Multibase ``z…``.

    Raises:
        EncodingError: bei fehlendem ``z``-Präfix oder falschem multicodec.
    """
    mb = _strip_didkey_multibase(did_key_or_mb)
    if not mb.startswith("z"):
        raise EncodingError("did:key erwartet base58btc (z-Codec)")
    raw = b58decode(mb[1:])  # 'z' entfernen
    if not (len(raw) >= 34 and raw[0] == 0xED and raw[1] == 0x01):
        raise EncodingError("unerwartetes multicodec-Präfix für ed25519-pub")
    pubkey = raw[2:34]
    return {"kty": "OKP", "crv": "Ed25519", "x": b64url(pubkey)}


# --------------------------------------------------------------------------
# kid-Helfer (konventionell)
# --------------------------------------------------------------------------
def kid_for_did_web(did_web: str, key_id: str = "key-1") -> str:
    """``kid_for_did_web('did:web:example.com')`` → ``'did:web:example.com#key-1'``."""
    return "{}#{}".format(did_web, key_id)


def kid_for_did_key(did_key: str, jwk_pub: Dict = None) -> str:
    """Bilde die konventionelle ``kid`` ``did:key:<mb>#<mb>``.

    Wird ``jwk_pub`` übergeben, wird das Fragment aus dem JWK abgeleitet,
    andernfalls die Multibase aus ``did_key`` wiederverwendet.
    """
    mb = _strip_didkey_multibase(did_key)
    frag = mb if not jwk_pub else did_key_fragment_from_jwk(jwk_pub)
    return "did:key:{}#{}".format(mb, frag)
