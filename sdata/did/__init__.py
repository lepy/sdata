# -*- coding: utf-8 -*-
"""``sdata.did`` – Decentralized Identifiers (DID) & Verifiable Credentials (VC).

Dieses Subpackage bündelt eine schlanke, **pure-Python** Umsetzung gängiger
SSI-Bausteine (Self-Sovereign Identity) rund um Ed25519:

============================  ====================================================
Bereich                       Modul / Funktionen
============================  ====================================================
Schlüssel (Ed25519/JWK)       :mod:`~sdata.did.keys` – :func:`gen_ed25519_jwk`, :func:`pub_from_priv_jwk`
JWK / did:key / Thumbprint    :mod:`~sdata.did.utils_didkey`
JOSE / Compact-JWS (EdDSA)    :mod:`~sdata.did.jose` – :func:`sign_compact`, :func:`verify_compact`
VC / VP ausstellen            :mod:`~sdata.did.issue_vc` – :func:`issue_vc`, :func:`make_vp`
VC / VP verifizieren          :mod:`~sdata.did.verify_vp` – :func:`verify_presentation`
did:web                       :mod:`~sdata.did.did_web` – :func:`build_did_document`, :func:`resolve_did_web`
did:key                       :mod:`~sdata.did.utils_didkey` – :func:`did_key_from_jwk_ed25519`, :func:`pub_jwk_from_did_key`
did:peer:4                    :mod:`~sdata.did.did_peer4` – :func:`did_peer4_from_payload`, :func:`resolve_long_form`
did:github                    :mod:`~sdata.did.did_github` – :func:`resolve_did_github`
============================  ====================================================

Unterstützte Standards: W3C DID Core, did:web, did:key, did:peer:4,
W3C Verifiable Credentials (JWT-VC), JOSE/JWS (RFC 7515), EdDSA (RFC 8037),
JWK-Thumbprint (RFC 7638).

Installation
------------
Krypto (Ed25519) und base58btc sind **abhängigkeitsfrei** (reine
Standardbibliothek) – siehe :mod:`~sdata.did.eddsa` und
:mod:`~sdata.did.base58btc`. Auch die HTTP-Auflösung von ``did:web`` /
``did:github`` läuft ohne externe Abhängigkeit: :mod:`~sdata.did._http` nutzt
``requests`` falls installiert, sonst ``urllib`` (Standardbibliothek)::

    pip install "sdata"          # voll funktionsfähig (urllib-HTTP-Backend)
    pip install "sdata[http]"    # optional: 'requests' als HTTP-Backend

.. warning::
   **Sicherheit / SOTA-Hinweis.** Der produktive Krypto-Pfad nutzt die
   pure-Python-Ed25519-Implementierung in :mod:`sdata.did.ed25519` (über den
   Adapter :mod:`sdata.did.eddsa`). Sie ist abhängigkeitsfrei, aber **nicht
   garantiert constant-time** und damit potenziell anfällig für
   Timing-Seitenkanäle – genau wie das zuvor genutzte ``python-ecdsa``
   (ebenfalls pure Python). Für hochsensible Umgebungen ein libsodium-Backend
   (PyNaCl) oder ``cryptography`` (OpenSSL) erwägen. Korrektheit ist gegen die
   offiziellen RFC-8032-Testvektoren abgesichert.

Beispiel
--------
::

    from sdata.did import (gen_ed25519_jwk, pub_from_priv_jwk,
                           did_key_from_jwk_ed25519, sign_compact, verify_compact)

    jwk = gen_ed25519_jwk()
    did = did_key_from_jwk_ed25519(pub_from_priv_jwk(jwk))
    kid = f"{did}#{did.split(':', 2)[2]}"
    jws = sign_compact({"hello": "world"}, jwk, kid=kid, typ="JWT")
    assert verify_compact(jws, pub_from_priv_jwk(jwk))["hello"] == "world"
"""
from __future__ import annotations

import importlib

# Lazy-Loading (PEP 562): Submodule werden erst beim Zugriff importiert. Vorteile:
#   * ``python -m sdata.did.<modul>`` löst keine runpy-Doppelimport-Warnung aus,
#   * ``import sdata.did`` ist leichtgewichtig – schwerere Submodule (z. B.
#     ``did_web`` mit dem HTTP-Backend) werden erst geladen, wenn eine sie
#     nutzende Funktion tatsächlich angefasst wird.
# Mapping: exportierter Name -> "submodul"  oder  ("submodul", "originalname").
_EXPORTS = {
    # Fehler
    "DidError": "errors", "EncodingError": "errors",
    "ResolutionError": "errors", "VerificationError": "errors",
    # Schlüssel / JWK / did:key
    "gen_ed25519_jwk": "keys", "pub_from_priv_jwk": "keys",
    "b64url": "utils_didkey", "b64url_decode": "utils_didkey",
    "jwk_thumbprint_rfc7638": "utils_didkey",
    "did_key_from_jwk_ed25519": "utils_didkey",
    "did_key_fragment_from_jwk": "utils_didkey",
    "pub_jwk_from_did_key": "utils_didkey",
    "kid_for_did_web": "utils_didkey", "kid_for_did_key": "utils_didkey",
    # JOSE / JWS
    "sign_compact": "jose", "verify_compact": "jose", "decode_header": "jose",
    # VC / VP
    "issue_vc": "issue_vc", "make_vp": "issue_vc", "sign_compact_jws": "issue_vc",
    "verify_presentation": "verify_vp", "jws_header": "verify_vp",
    "jws_verify": "verify_vp", "resolve_public_jwk_for_kid": "verify_vp",
    # DID-Methoden
    "build_did_document": "did_web", "did_web_to_url": "did_web",
    "resolve_did_web": ("did_web", "resolve_public_jwk_for_kid"),
    "did_peer4_from_payload": "did_peer4", "resolve_long_form": "did_peer4",
    "resolve_did_github": "did_github", "parse_did_github": "did_github",
}


def __getattr__(name):
    """Importiere das zugehörige Submodul beim ersten Zugriff (PEP 562)."""
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(
            "module {!r} has no attribute {!r}".format(__name__, name))
    modname, attrname = target if isinstance(target, tuple) else (target, name)
    mod = importlib.import_module("." + modname, __name__)
    value = getattr(mod, attrname)
    globals()[name] = value  # cachen, damit __getattr__ nur einmal feuert
    return value


def __dir__():
    return sorted(__all__)


__all__ = [
    # Fehler
    "DidError", "EncodingError", "ResolutionError", "VerificationError",
    # Schlüssel / JWK / did:key
    "gen_ed25519_jwk", "pub_from_priv_jwk",
    "b64url", "b64url_decode", "jwk_thumbprint_rfc7638",
    "did_key_from_jwk_ed25519", "did_key_fragment_from_jwk", "pub_jwk_from_did_key",
    "kid_for_did_web", "kid_for_did_key",
    # JOSE / JWS
    "sign_compact", "verify_compact", "decode_header",
    # VC / VP
    "issue_vc", "make_vp", "sign_compact_jws",
    "verify_presentation", "resolve_public_jwk_for_kid", "jws_header", "jws_verify",
    # DID-Methoden
    "build_did_document", "did_web_to_url", "resolve_did_web",
    "did_peer4_from_payload", "resolve_long_form",
    "resolve_did_github", "parse_did_github",
]
