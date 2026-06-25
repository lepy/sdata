# -*- coding: utf-8 -*-
"""Erzeugung und Verwaltung von Ed25519-Schlüsseln im JWK-Format.

Schlüssel werden als JWK (RFC 8037, ``kty=OKP``, ``crv=Ed25519``) gehalten:

* öffentlich: Feld ``x`` (raw 32 Byte, base64url),
* privat:     zusätzlich Feld ``d`` (raw 32 Byte Seed, base64url – **geheim halten!**).

CLI (das ``did``-Modul ist als Subpackage organisiert, daher via ``-m``)::

    python -m sdata.did.keys gen   --out issuer_key.json
    python -m sdata.did.keys pub   --in  issuer_key.json --out issuer_pub.json
    python -m sdata.did.keys thumb --in  issuer_pub.json

.. note::
   ``gen`` schreibt einen **privaten** Schlüssel. Solche Dateien gehören nicht
   ins Versionskontrollsystem (siehe ``.gitignore``).
"""
from __future__ import annotations

import json
import logging
import argparse
from typing import Dict

from .eddsa import SigningKey, Ed25519

from .utils_didkey import b64url, jwk_thumbprint_rfc7638, did_key_from_jwk_ed25519

logger = logging.getLogger(__name__)

__all__ = ["gen_ed25519_jwk", "pub_from_priv_jwk"]


def gen_ed25519_jwk() -> Dict[str, str]:
    """Erzeuge ein frisches privates Ed25519-JWK (mit Feldern ``x`` und ``d``)."""
    sk = SigningKey.generate(curve=Ed25519)
    vk = sk.get_verifying_key()
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": b64url(vk.to_string()),   # Public Key (raw 32 Byte)
        "d": b64url(sk.to_string()),   # Private Key (raw 32 Byte – geheim halten!)
    }


def pub_from_priv_jwk(jwk_priv: Dict) -> Dict[str, str]:
    """Leite den öffentlichen JWK (ohne ``d``) aus einem privaten JWK ab."""
    return {"kty": jwk_priv["kty"], "crv": jwk_priv["crv"], "x": jwk_priv["x"]}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _cmd_gen(args: argparse.Namespace) -> None:
    with open(args.out, "w") as fh:
        json.dump(gen_ed25519_jwk(), fh, indent=2)
    logger.info("✔ Privates JWK gespeichert: %s", args.out)


def _cmd_pub(args: argparse.Namespace) -> None:
    with open(args.in_, "r") as fh:
        jwk = json.load(fh)
    with open(args.out, "w") as fh:
        json.dump(pub_from_priv_jwk(jwk), fh, indent=2)
    logger.info("✔ Öffentliches JWK gespeichert: %s", args.out)


def _cmd_thumb(args: argparse.Namespace) -> None:
    with open(args.in_, "r") as fh:
        jwk_pub = json.load(fh)
    logger.info("%s", json.dumps({
        "thumbprint_rfc7638": jwk_thumbprint_rfc7638(jwk_pub),
        "did_key": did_key_from_jwk_ed25519(jwk_pub),
    }, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Ed25519-JWK-Schlüsselverwaltung")
    sub = ap.add_subparsers(required=True)

    p = sub.add_parser("gen", help="Ed25519-Key erzeugen")
    p.add_argument("--out", required=True)
    p.set_defaults(func=_cmd_gen)

    p = sub.add_parser("pub", help="Public-Part aus privatem JWK ableiten")
    p.add_argument("--in", dest="in_", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=_cmd_pub)

    p = sub.add_parser("thumb", help="RFC-7638-Thumbprint + did:key aus Public-JWK")
    p.add_argument("--in", dest="in_", required=True)
    p.set_defaults(func=_cmd_thumb)
    return ap


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
