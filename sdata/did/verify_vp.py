# -*- coding: utf-8 -*-
"""Verifikation von Verifiable Presentations (VP) und der eingebetteten VC.

Geprüft werden:

1. die Holder-Signatur der VP,
2. optional ``aud`` und ``nonce`` (Replay-Schutz),
3. die Issuer-Signatur des eingebetteten VC,
4. der Gültigkeitszeitraum des VC (``nbf``/``exp``).

Unterstützte DID-Methoden für die Schlüsselauflösung:

* **Issuer** ``did:web`` – Auflösung via HTTPS (:mod:`sdata.did.did_web`),
* **Holder** ``did:key`` – lokale Rückgewinnung des Public-JWK (kein Netzwerk).

Die Bibliotheksfunktionen werfen :class:`sdata.did.VerificationError` /
:class:`sdata.did.ResolutionError` (nie ``SystemExit``).

CLI::

    python -m sdata.did.verify_vp --vp product.vp \\
        --expected-aud https://verifier.example.org --expected-nonce <nonce>
"""
from __future__ import annotations

import time
import logging
import argparse
from typing import Any, Dict, Optional

from . import jose
from .errors import ResolutionError, VerificationError
from .utils_didkey import pub_jwk_from_did_key
from .did_web import resolve_public_jwk_for_kid as resolve_web_kid

logger = logging.getLogger(__name__)

__all__ = [
    "resolve_public_jwk_for_kid",
    "verify_presentation",
    "jws_header",
    "jws_verify",
]


def jws_header(compact: str) -> Dict[str, Any]:
    """Dekodiere den (ungeprüften) Header eines Compact-JWS."""
    return jose.decode_header(compact)


def jws_verify(compact: str, public_jwk: Dict) -> Dict[str, Any]:
    """Verifiziere ein Compact-JWS gegen ``public_jwk`` und gib das Payload zurück."""
    return jose.verify_compact(compact, public_jwk)


def resolve_public_jwk_for_kid(kid: str) -> Dict[str, str]:
    """Löse die ``kid`` zu einem öffentlichen JWK auf (``did:web`` oder ``did:key``).

    Raises:
        ResolutionError: bei nicht unterstützter DID-Methode oder Auflösefehler.
    """
    did = kid.split("#")[0]
    if did.startswith("did:web:"):
        return resolve_web_kid(kid)
    if did.startswith("did:key:"):
        return pub_jwk_from_did_key(did)
    raise ResolutionError("nicht unterstützte DID-Methode in kid: {}".format(kid))


def verify_presentation(vp_jws: str, *, expected_aud: Optional[str] = None,
                        expected_nonce: Optional[str] = None,
                        now: Optional[int] = None) -> Dict[str, Any]:
    """Verifiziere eine VP samt eingebettetem VC vollständig.

    Args:
        vp_jws: Die Verifiable Presentation als Compact-JWS.
        expected_aud: Falls gesetzt, muss ``vp.aud`` exakt übereinstimmen.
        expected_nonce: Falls gesetzt, muss ``vp.nonce`` exakt übereinstimmen.
        now: Referenzzeit (Unix-Sekunden) für die ``nbf``/``exp``-Prüfung;
            Default ist die aktuelle Zeit. Nützlich für Tests.

    Returns:
        Ein Dict mit ``issuer``, ``holder``, ``credentialSubject``, ``vc`` und ``vp``.

    Raises:
        VerificationError: bei ungültiger Signatur, ``aud``/``nonce``-Mismatch,
            fehlendem VC oder abgelaufenem/ noch nicht gültigem VC.
        ResolutionError: wenn ein Schlüssel nicht aufgelöst werden kann.
    """
    now = int(time.time()) if now is None else int(now)

    # 1) VP-Signatur (Holder)
    vp_pub = resolve_public_jwk_for_kid(jws_header(vp_jws)["kid"])
    vp = jws_verify(vp_jws, vp_pub)

    # 2) aud / nonce
    if expected_aud is not None and vp.get("aud") != expected_aud:
        raise VerificationError("aud stimmt nicht überein")
    if expected_nonce is not None and vp.get("nonce") != expected_nonce:
        raise VerificationError("nonce stimmt nicht überein")

    # 3) eingebettetes VC extrahieren & prüfen (Issuer)
    creds = vp.get("vp", {}).get("verifiableCredential", [])
    if not creds:
        raise VerificationError("VP enthält keine verifiableCredential")
    vc_jws = creds[0]
    vc_pub = resolve_public_jwk_for_kid(jws_header(vc_jws)["kid"])
    vc = jws_verify(vc_jws, vc_pub)

    # 4) Gültigkeitszeitraum
    nbf, exp = vc.get("nbf"), vc.get("exp")
    if nbf is not None and now < nbf:
        raise VerificationError("VC ist noch nicht gültig (nbf)")
    if exp is not None and now > exp:
        raise VerificationError("VC ist abgelaufen (exp)")

    return {
        "issuer": vc.get("iss"),
        "holder": vp.get("holder"),
        "credentialSubject": vc.get("vc", {}).get("credentialSubject", {}),
        "vc": vc,
        "vp": vp,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="Verifiable Presentation verifizieren")
    ap.add_argument("--vp", required=True)
    ap.add_argument("--expected-aud")
    ap.add_argument("--expected-nonce")
    args = ap.parse_args(argv)

    with open(args.vp, "r") as fh:
        vp_jws = fh.read().strip()

    try:
        result = verify_presentation(
            vp_jws,
            expected_aud=args.expected_aud,
            expected_nonce=args.expected_nonce,
        )
    except (VerificationError, ResolutionError) as exc:
        raise SystemExit("✘ Verifikation fehlgeschlagen: {}".format(exc))

    subj = result["credentialSubject"]
    logger.info("✔ VP + VC verifiziert")
    logger.info("Issuer: %s", result["issuer"])
    logger.info("Holder: %s", result["holder"])
    logger.info("GTIN: %s  SN: %s", subj.get("gtin"), subj.get("serialNumber"))
    logger.info("CO2: %s  Recycled: %s", subj.get("co2Footprint"), subj.get("recycledContent"))


if __name__ == "__main__":
    main()
