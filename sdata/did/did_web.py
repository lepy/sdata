# -*- coding: utf-8 -*-
"""``did:web``: DID-Dokumente erzeugen und über HTTPS auflösen.

Zwei Schlüsseldarstellungen werden unterstützt:

* **JWK** (empfohlen für JWS/JWT): ``JsonWebKey2020`` + ``publicKeyJwk`` (jws-2020),
* **Multibase**: ``Ed25519VerificationKey2020`` + ``publicKeyMultibase`` (ed25519-2020).

``did:web:example.com`` wird zu ``https://example.com/.well-known/did.json``
aufgelöst; mit Pfadanteilen (``did:web:example.com:user:alice``) entsprechend zu
``https://example.com/user/alice/did.json``.

CLI::

    python -m sdata.did.did_web build --domain example.com \\
        --pub issuer_pub.json --out did.json --format jwk
    python -m sdata.did.did_web resolve --kid did:web:example.com#key-1

Referenzen:
    * `did:web Method <https://w3c-ccg.github.io/did-method-web/>`_
"""
from __future__ import annotations

import json
import logging
import argparse
from urllib.parse import quote
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
import base58

from .errors import EncodingError, ResolutionError
from .utils_didkey import pub_jwk_from_did_key, b64url_decode

logger = logging.getLogger(__name__)

__all__ = ["build_did_document", "did_web_to_url", "resolve_public_jwk_for_kid"]

JWS2020_CONTEXT = "https://w3id.org/security/suites/jws-2020/v1"
ED25519_2020_CONTEXT = "https://w3id.org/security/suites/ed25519-2020/v1"
DID_CORE_CONTEXT = "https://www.w3.org/ns/did/v1"

#: HTTP-Timeout (Sekunden) für die Auflösung.
HTTP_TIMEOUT = 15


def did_web(domain: str) -> str:
    """``'example.com'`` → ``'did:web:example.com'``."""
    return "did:web:{}".format(domain)


def _load_pub_input(path: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Lade die ``--pub``-Eingabe.

    Returns:
        ``("jwk", jwk_dict)`` oder ``("multibase", {"mb": "z…"})``.

    Akzeptiert ein JWK-JSON (``kty=OKP``/``crv=Ed25519``/``x``), ein
    ``{"multibase": "z…"}``-JSON oder eine Textdatei mit einem ``z…``-String.

    Raises:
        EncodingError: wenn die Eingabe weder JWK noch gültige Multibase ist.
    """
    text = Path(path).read_text().strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        obj = None

    if isinstance(obj, dict):
        if obj.get("kty") == "OKP" and obj.get("crv") == "Ed25519" and "x" in obj:
            return "jwk", obj
        if "multibase" in obj and str(obj["multibase"]).startswith("z"):
            return "multibase", {"mb": str(obj["multibase"])}

    if text.startswith("z"):
        return "multibase", {"mb": text}

    raise EncodingError(
        "--pub '{}' ist weder JWK-JSON noch eine gültige Multibase (z…)".format(path))


def _did_context(add_security: str, variant: str):
    """Stelle die ``@context``-Liste zusammen (``add_security``: 'auto'|'on'|'off')."""
    ctx = [DID_CORE_CONTEXT]
    if add_security == "off":
        return ctx
    security = JWS2020_CONTEXT if variant == "jwk" else ED25519_2020_CONTEXT
    ctx.append(security)
    return ctx


def build_did_document(domain: str, public_input_path: str,
                       key_id_suffix: str = "key-1", variant: str = "jwk",
                       add_security_context: str = "auto") -> Dict[str, Any]:
    """Erzeuge ein DID-Dokument (``did.json``) für ``did:web:<domain>``.

    Args:
        domain: Domain des Issuers.
        public_input_path: Pfad zu Public-JWK-JSON **oder** Multibase-Datei.
        key_id_suffix: Fragment der ``verificationMethod``-ID (Default ``key-1``).
        variant: ``'jwk'`` (JsonWebKey2020) oder ``'multibase'`` (Ed25519VerificationKey2020).
        add_security_context: ``'auto'`` | ``'on'`` | ``'off'``.

    Raises:
        EncodingError: bei ungültiger ``variant`` oder Eingabe.
    """
    if variant not in ("jwk", "multibase"):
        raise EncodingError("variant muss 'jwk' oder 'multibase' sein")

    kind, data = _load_pub_input(public_input_path)
    did = did_web(domain)
    vm_id = "{}#{}".format(did, key_id_suffix)
    ctx = _did_context(add_security_context, variant)

    if variant == "jwk":
        jwk_pub = pub_jwk_from_did_key(data["mb"]) if kind == "multibase" else data
        vm = {"id": vm_id, "type": "JsonWebKey2020", "controller": did,
              "publicKeyJwk": jwk_pub}
    else:
        if kind == "jwk":
            raw = b64url_decode(data["x"])
            mb = "z" + base58.b58encode(bytes([0xED, 0x01]) + raw).decode()
        else:
            mb = data["mb"]
        vm = {"id": vm_id, "type": "Ed25519VerificationKey2020", "controller": did,
              "publicKeyMultibase": mb}

    return {
        "@context": ctx,
        "id": did,
        "verificationMethod": [vm],
        "assertionMethod": [vm_id],
        "authentication": [vm_id],
    }


def did_web_to_url(did: str) -> str:
    """Bilde die HTTPS-URL des ``did.json`` für eine ``did:web``-DID.

    Raises:
        EncodingError: wenn ``did`` keine ``did:web``-DID ist.
    """
    if not did.startswith("did:web:"):
        raise EncodingError("keine did:web-DID: {}".format(did))
    segments = ":".join(did.split(":")[2:]).split(":")
    host = segments[0]
    path = "/".join(map(quote, segments[1:]))
    if path:
        return "https://{}/{}/did.json".format(host, path)
    return "https://{}/.well-known/did.json".format(host)


def resolve_public_jwk_for_kid(kid: str) -> Dict[str, str]:
    """Lade das ``did.json`` und liefere immer einen Public-**JWK** zur ``kid``.

    Unterstützt sowohl ``publicKeyJwk`` als auch ``publicKeyMultibase``
    (Letzteres wird zu JWK konvertiert).

    Raises:
        ResolutionError: bei Netzwerkfehlern oder wenn die ``kid`` nicht gefunden
            bzw. kein Schlüsselmaterial vorhanden ist.
    """
    did = kid.split("#")[0]
    url = did_web_to_url(did)
    try:
        resp = requests.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        doc = resp.json()
    except requests.RequestException as exc:
        raise ResolutionError("did:web-Auflösung fehlgeschlagen ({}): {}".format(url, exc))

    by_id = {vm.get("id"): vm for vm in doc.get("verificationMethod", [])}
    vm = by_id.get(kid)
    if not vm:
        raise ResolutionError("Schlüssel {} nicht im did.json gefunden".format(kid))

    if "publicKeyJwk" in vm:
        return vm["publicKeyJwk"]
    mb = vm.get("publicKeyMultibase")
    if isinstance(mb, str) and mb.startswith("z"):
        return pub_jwk_from_did_key(mb)
    raise ResolutionError("weder publicKeyJwk noch publicKeyMultibase gefunden")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="did:web-Dokumente erzeugen/auflösen")
    sub = ap.add_subparsers(required=True)

    p = sub.add_parser("build", help="did.json erzeugen")
    p.add_argument("--domain", required=True)
    p.add_argument("--pub", required=True, help="Public-JWK-JSON ODER Datei mit Multibase (z…)")
    p.add_argument("--out", required=True)
    p.add_argument("--key-id", default="key-1")
    p.add_argument("--format", choices=["jwk", "multibase"], default="jwk")
    p.add_argument("--context", choices=["auto", "on", "off"], default="auto")
    p.set_defaults(cmd="build")

    p = sub.add_parser("resolve", help="Public-JWK per kid auflösen")
    p.add_argument("--kid", required=True)
    p.set_defaults(cmd="resolve")

    args = ap.parse_args(argv)
    if args.cmd == "build":
        doc = build_did_document(args.domain, args.pub, key_id_suffix=args.key_id,
                                 variant=args.format, add_security_context=args.context)
        with open(args.out, "w") as fh:
            json.dump(doc, fh, indent=2)
        logger.info("✔ did.json erzeugt: %s", args.out)
    else:
        logger.info("%s", json.dumps(resolve_public_jwk_for_kid(args.kid), indent=2))


if __name__ == "__main__":
    main()
