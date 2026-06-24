# -*- coding: utf-8 -*-
"""Ausstellung von Verifiable Credentials (VC) und Verifiable Presentations (VP).

Signaturformat: **JWT-VC** als Compact-JWS (EdDSA/Ed25519) über
:mod:`sdata.did.jose`. Der Issuer wird als ``did:web`` modelliert, der Holder
wahlweise als ``did:key`` (Multibase) oder als beliebige DID.

Das hier ausgestellte Credential ist ein einfacher **Digital Product Passport**
(``ProductPassport``) im Sinne von GS1/EU-DPP: GTIN, Seriennummer, GS1 Digital
Link sowie CO₂-Fußabdruck und Rezyklatanteil.

CLI::

    python -m sdata.did.issue_vc \\
        --issuer-domain issuer.example --issuer-key issuer_key.json \\
        --gtin 04012345678901 --serial SN-42 --co2 12.5 --recycled 80 \\
        --out product.vc

Referenzen:
    * `W3C VC Data Model <https://www.w3.org/TR/vc-data-model/>`_
    * `GS1 Digital Link <https://www.gs1.org/standards/gs1-digital-link>`_
"""
from __future__ import annotations

import json
import time
import uuid
import logging
import argparse
from typing import Any, Dict

from . import jose
from .keys import pub_from_priv_jwk
from .utils_didkey import did_key_from_jwk_ed25519

logger = logging.getLogger(__name__)

__all__ = ["issue_vc", "make_vp", "sign_compact_jws"]


def _now() -> int:
    return int(time.time())


def _in_days(days: int) -> int:
    return _now() + days * 24 * 3600


def _load_priv_jwk(path: str) -> Dict:
    with open(path, "r") as fh:
        return json.load(fh)


def sign_compact_jws(payload: Dict[str, Any], priv_jwk: Dict, kid: str, typ: str) -> str:
    """Signiere ``payload`` als Compact-JWS.

    Dünner Wrapper um :func:`sdata.did.jose.sign_compact`; aus Kompatibilität
    mit dem bisherigen API-Namen erhalten geblieben.
    """
    return jose.sign_compact(payload, priv_jwk, kid=kid, typ=typ)


def issue_vc(issuer_domain: str, issuer_key_path: str, gtin: str, serial: str,
             co2: float, recycled: float,
             subject_did: str = "did:example:product-xyz",
             validity_days: int = 365 * 3) -> str:
    """Stelle ein ``ProductPassport``-VC aus und gib es als Compact-JWS zurück.

    Args:
        issuer_domain: Domain des Issuers; ergibt ``did:web:<domain>``.
        issuer_key_path: Pfad zum **privaten** Issuer-JWK.
        gtin: GS1 GTIN (Global Trade Item Number).
        serial: Seriennummer des Produkts.
        co2: CO₂-Fußabdruck in kg CO₂e.
        recycled: Rezyklatanteil in Prozent.
        subject_did: DID des Credential-Subjects.
        validity_days: Gültigkeitsdauer ab jetzt (Default: 3 Jahre).

    Returns:
        Das signierte VC als Compact-JWS (``vc+ld+jwt``).
    """
    issuer_did = "did:web:{}".format(issuer_domain)
    kid = "{}#key-1".format(issuer_did)
    jwk_priv = _load_priv_jwk(issuer_key_path)
    payload = {
        "iss": issuer_did,
        "sub": subject_did,
        "nbf": _now(),
        "iat": _now(),
        "exp": _in_days(validity_days),
        "jti": "urn:uuid:{}".format(uuid.uuid4()),
        "vc": {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "ProductPassport"],
            "credentialSubject": {
                "gtin": gtin,
                "serialNumber": serial,
                "gs1DigitalLink": "https://id.gs1.org/01/{}/21/{}".format(gtin, serial),
                "co2Footprint": {"value": co2, "unitText": "kg CO2e"},
                "recycledContent": {"value": recycled, "unitText": "%"},
            },
            "credentialStatus": {
                "id": "https://{}/status/pp-2025#1".format(issuer_domain),
                "type": "StatusList2021Entry",
            },
        },
    }
    return sign_compact_jws(payload, jwk_priv, kid=kid, typ="vc+ld+jwt")


def make_vp(holder_key_path: str, holder_did: str, vc_jws: str,
            aud: str, nonce: str) -> str:
    """Baue eine Verifiable Presentation um ein VC und signiere sie (Holder).

    Für ``did:key``-Holder wird die konventionelle ``kid``
    ``did:key:<mb>#<mb>`` gesetzt, sonst ``<holder_did>#key-1``.
    """
    holder_jwk = _load_priv_jwk(holder_key_path)
    if holder_did.startswith("did:key:"):
        frag = did_key_from_jwk_ed25519(pub_from_priv_jwk(holder_jwk)).split(":", 2)[2]
        holder_kid = "{}#{}".format(holder_did, frag)
    else:
        holder_kid = "{}#key-1".format(holder_did)

    payload = {
        "holder": holder_did,
        "vp": {"type": ["VerifiablePresentation"], "verifiableCredential": [vc_jws]},
        "aud": aud,
        "nonce": nonce,
    }
    return sign_compact_jws(payload, holder_jwk, kid=holder_kid, typ="vp+jwt")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Verifiable Credential / Presentation ausstellen")
    ap.add_argument("--issuer-domain", required=True)
    ap.add_argument("--issuer-key", required=True)
    ap.add_argument("--gtin", required=True)
    ap.add_argument("--serial", required=True)
    ap.add_argument("--co2", type=float, required=True)
    ap.add_argument("--recycled", type=float, required=True)
    ap.add_argument("--subject", default="did:example:product-xyz")
    ap.add_argument("--out", required=True)

    ap.add_argument("--make-vp", action="store_true")
    ap.add_argument("--holder-key")
    ap.add_argument("--holder-did", default=None)
    ap.add_argument("--aud", default="https://verifier.example.org")
    ap.add_argument("--nonce", default=None)
    return ap


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args(argv)

    vc_jws = issue_vc(
        issuer_domain=args.issuer_domain,
        issuer_key_path=args.issuer_key,
        gtin=args.gtin,
        serial=args.serial,
        co2=args.co2,
        recycled=args.recycled,
        subject_did=args.subject,
    )

    if not args.make_vp:
        with open(args.out, "w") as fh:
            fh.write(vc_jws)
        logger.info("✔ VC geschrieben: %s", args.out)
        return

    if not args.holder_key:
        raise SystemExit("--make-vp benötigt --holder-key")

    if args.holder_did:
        holder_did = args.holder_did
    else:
        holder_jwk = _load_priv_jwk(args.holder_key)
        holder_did = did_key_from_jwk_ed25519(pub_from_priv_jwk(holder_jwk))

    nonce = args.nonce or str(uuid.uuid4())
    vp_jws = make_vp(args.holder_key, holder_did, vc_jws, aud=args.aud, nonce=nonce)
    with open(args.out, "w") as fh:
        fh.write(vp_jws)
    logger.info("✔ VP geschrieben: %s (enthält eingebettetes VC)", args.out)


if __name__ == "__main__":
    main()
