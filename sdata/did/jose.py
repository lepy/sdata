# -*- coding: utf-8 -*-
"""Kompakte JWS-Schicht (JOSE) für EdDSA/Ed25519 – gemeinsame Basis für VC & VP.

Diese Modul bündelt das Signieren/Verifizieren von **Compact-JWS**
(``header.payload.signature``, base64url), das zuvor doppelt in
``issue_vc`` und ``verify_vp`` implementiert war.

Krypto-Backend: ``python-ecdsa`` (reine Python-Implementierung von Ed25519).

.. warning::
   ``python-ecdsa`` ist nicht garantiert constant-time. Für hochsensible
   Produktivumgebungen mit Seitenkanal-Anforderungen sollte ein
   libsodium-basiertes Backend (PyNaCl) oder ``cryptography`` erwogen werden.
   Siehe auch das Paket-Docstring von :mod:`sdata.did`.

Referenzen:
    * `RFC 7515 <https://www.rfc-editor.org/rfc/rfc7515>`_ – JWS
    * `RFC 8037 <https://www.rfc-editor.org/rfc/rfc8037>`_ – EdDSA in JOSE
"""
from __future__ import annotations

import json
from typing import Any, Dict

from ecdsa import SigningKey, VerifyingKey, Ed25519, BadSignatureError

from .errors import EncodingError, VerificationError
from .utils_didkey import b64url, b64url_decode

__all__ = [
    "b64url_json",
    "protected_header",
    "signing_key_from_jwk",
    "verifying_key_from_jwk",
    "sign_compact",
    "decode_header",
    "verify_compact",
]


def b64url_json(obj: Any) -> str:
    """Serialisiere ``obj`` als kompaktes JSON und kodiere base64url (ohne Padding)."""
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    return b64url(raw)


def protected_header(kid: str, typ: str, alg: str = "EdDSA") -> Dict[str, str]:
    """Baue einen geschützten JWS-Header ``{alg, kid, typ}``."""
    return {"alg": alg, "kid": kid, "typ": typ}


def signing_key_from_jwk(jwk_priv: Dict) -> SigningKey:
    """Erzeuge einen Ed25519-``SigningKey`` aus einem privaten JWK (Feld ``d``).

    Raises:
        EncodingError: wenn das private JWK ungültig ist oder ``d`` fehlt.
    """
    if not isinstance(jwk_priv, dict) or "d" not in jwk_priv:
        raise EncodingError("privater JWK fehlt das Feld 'd'")
    if jwk_priv.get("kty") != "OKP" or jwk_priv.get("crv") != "Ed25519":
        raise EncodingError("nur OKP/Ed25519 wird unterstützt")
    raw = b64url_decode(jwk_priv["d"])  # 32 Byte Seed
    return SigningKey.from_string(raw, curve=Ed25519)


def verifying_key_from_jwk(jwk_pub: Dict) -> VerifyingKey:
    """Erzeuge einen Ed25519-``VerifyingKey`` aus einem öffentlichen JWK (Feld ``x``).

    Raises:
        EncodingError: wenn das öffentliche JWK ungültig ist oder ``x`` fehlt.
    """
    if not isinstance(jwk_pub, dict) or "x" not in jwk_pub:
        raise EncodingError("öffentlicher JWK fehlt das Feld 'x'")
    if jwk_pub.get("kty") != "OKP" or jwk_pub.get("crv") != "Ed25519":
        raise EncodingError("nur OKP/Ed25519 wird unterstützt")
    raw = b64url_decode(jwk_pub["x"])
    return VerifyingKey.from_string(raw, curve=Ed25519)


def sign_compact(payload: Dict[str, Any], priv_jwk: Dict, kid: str, typ: str,
                 alg: str = "EdDSA") -> str:
    """Signiere ``payload`` als Compact-JWS und gib ``header.payload.signature`` zurück."""
    header_b64 = b64url_json(protected_header(kid, typ, alg))
    payload_b64 = b64url_json(payload)
    signing_input = "{}.{}".format(header_b64, payload_b64).encode()
    sig = signing_key_from_jwk(priv_jwk).sign(signing_input)
    return "{}.{}.{}".format(header_b64, payload_b64, b64url(sig))


def decode_header(compact: str) -> Dict[str, Any]:
    """Dekodiere (ohne Verifikation) den geschützten Header eines Compact-JWS.

    Raises:
        EncodingError: wenn das JWS strukturell ungültig ist.
    """
    parts = compact.split(".")
    if len(parts) != 3:
        raise EncodingError("kein gültiges Compact-JWS (erwarte 3 Segmente)")
    try:
        return json.loads(b64url_decode(parts[0]).decode())
    except (ValueError, UnicodeDecodeError) as exc:
        raise EncodingError("JWS-Header nicht dekodierbar: {}".format(exc))


def verify_compact(compact: str, pub_jwk: Dict) -> Dict[str, Any]:
    """Verifiziere ein Compact-JWS gegen ``pub_jwk`` und gib das Payload zurück.

    Raises:
        EncodingError: bei strukturell ungültigem JWS.
        VerificationError: wenn die Signatur ungültig ist.
    """
    parts = compact.split(".")
    if len(parts) != 3:
        raise EncodingError("kein gültiges Compact-JWS (erwarte 3 Segmente)")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = "{}.{}".format(header_b64, payload_b64).encode()
    vk = verifying_key_from_jwk(pub_jwk)
    try:
        vk.verify(b64url_decode(sig_b64), signing_input)
    except BadSignatureError:
        raise VerificationError("Signatur ungültig")
    try:
        return json.loads(b64url_decode(payload_b64).decode())
    except (ValueError, UnicodeDecodeError) as exc:
        raise EncodingError("JWS-Payload nicht dekodierbar: {}".format(exc))
