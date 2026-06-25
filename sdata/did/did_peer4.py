# -*- coding: utf-8 -*-
"""``did:peer:4``: statische, self-zertifizierende Peer-DIDs (Long-/Short-Form).

Diese Implementierung ist bewusst **abhängigkeitsfrei** (nur Standardbibliothek)
und bringt eine eigene base58btc- und varint-Kodierung mit – passend zum
pure-Python-Designziel des Subpackages.

Aufbau einer Long-Form::

    did:peer:4{hash}:{encoded_document}

* ``encoded_document`` = multibase(base58btc, multicodec(JSON) + kanonisches JSON),
* ``hash``             = multibase(base58btc, multihash(sha2-256, encoded_document)).

Die Short-Form ``did:peer:4{hash}`` ist self-zertifizierend: beim Auflösen der
Long-Form wird der Hash gegen das eingebettete Dokument validiert.

Referenzen:
    * `did:peer Method, Variante 4 <https://identity.foundation/peer-did-method-spec/>`_
"""
from __future__ import annotations

import json
import hashlib
from typing import Dict, Tuple

from .errors import EncodingError, VerificationError
# base58btc liegt jetzt zentral im eigenen Modul (frühere Inline-Variante);
# Re-Export aus Kompatibilitätsgründen.
from .base58btc import b58encode, b58decode

__all__ = ["did_peer4_from_payload", "resolve_long_form", "b58encode", "b58decode"]


# --- Varint (LEB128, wie in multicodec) -----------------------------------
def varint_encode(n: int) -> bytes:
    """Kodiere ``n`` als unsigned LEB128-varint."""
    out = bytearray()
    while True:
        to_write = n & 0x7F
        n >>= 7
        if n:
            out.append(to_write | 0x80)
        else:
            out.append(to_write)
            break
    return bytes(out)


def varint_decode(b: bytes) -> Tuple[int, int]:
    """Dekodiere einen unsigned LEB128-varint; gibt ``(wert, gelesene_bytes)`` zurück."""
    shift = 0
    value = 0
    for i, byte in enumerate(b):
        value |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return value, i + 1
        shift += 7
    raise EncodingError("ungültiger varint")


# --- Multicodec- & Multihash-Konstanten -----------------------------------
MULTICODEC_JSON = 0x0200   # multicodec-Code für JSON
MH_SHA256 = 0x12           # multihash: sha2-256
MH_SHA256_LEN = 32


def _canonical_json_bytes(payload: Dict) -> bytes:
    """Deterministische JSON-Serialisierung (Keys sortiert, ohne Whitespace)."""
    s = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return s.encode("utf-8")


def encode_document(payload: Dict) -> bytes:
    """Multicodec-Framing: ``varint(JSON-Code) + kanonisches JSON``."""
    return varint_encode(MULTICODEC_JSON) + _canonical_json_bytes(payload)


def multibase_b58btc(data: bytes) -> str:
    """Präfix ``z`` (base58btc) gemäß Multibase."""
    return "z" + b58encode(data)


def multihash_sha256(data: bytes) -> bytes:
    """``multihash(sha2-256, data)`` = ``0x12 0x20 || sha256(data)``."""
    return bytes([MH_SHA256, MH_SHA256_LEN]) + hashlib.sha256(data).digest()


# --- did:peer:4 Erzeugung & Auflösung -------------------------------------
def did_peer4_from_payload(payload: Dict) -> Tuple[str, str, Dict]:
    """Erzeuge Long-Form, Short-Form und kontextualisiertes DID-Dokument.

    Args:
        payload: DID-Dokument **ohne** ``id`` (relative Fragmente wie ``#key-0``
            sind erlaubt).

    Returns:
        ``(long_form, short_form, did_document)``.
    """
    encoded_doc_bytes = encode_document(payload)
    encoded_doc_mb = multibase_b58btc(encoded_doc_bytes)
    mh_mb = multibase_b58btc(multihash_sha256(encoded_doc_bytes))

    long_form = "did:peer:4{}:{}".format(mh_mb, encoded_doc_mb)
    short_form = "did:peer:4{}".format(mh_mb)
    did_doc = _contextualize_did_doc(payload, did_long=long_form, did_short=short_form)
    return long_form, short_form, did_doc


def resolve_long_form(did_long: str) -> Dict:
    """Löse eine Long-Form ``did:peer:4`` auf und validiere den Hash.

    Raises:
        EncodingError: bei strukturell ungültiger DID oder falschem multicodec/multihash.
        VerificationError: wenn der eingebettete Hash nicht zum Dokument passt.
    """
    if not did_long.startswith("did:peer:4"):
        raise EncodingError("keine did:peer:4")
    try:
        _, rest = did_long.split("did:peer:4", 1)
        hash_mb, doc_mb = rest.split(":", 1)
    except ValueError:
        raise EncodingError("erwarte Long-Form: did:peer:4{hash}:{doc}")

    if not (hash_mb.startswith("z") and doc_mb.startswith("z")):
        raise EncodingError("erwarte multibase base58btc ('z'-Präfix)")

    mh = b58decode(hash_mb[1:])
    encoded_doc_bytes = b58decode(doc_mb[1:])

    code, offset = varint_decode(encoded_doc_bytes)
    if code != MULTICODEC_JSON:
        raise EncodingError("multicodec-Code ist nicht JSON (0x0200)")
    json_bytes = encoded_doc_bytes[offset:]

    if len(mh) < 2 or mh[0] != MH_SHA256 or mh[1] != MH_SHA256_LEN:
        raise EncodingError("multihash ist nicht sha2-256/32")
    if mh[2:] != hashlib.sha256(encoded_doc_bytes).digest():
        raise VerificationError("Hash-Validierung fehlgeschlagen")

    payload = json.loads(json_bytes.decode("utf-8"))
    did_short = "did:peer:4{}".format(multibase_b58btc(mh))
    return _contextualize_did_doc(payload, did_long=did_long, did_short=did_short)


def _contextualize_did_doc(payload: Dict, *, did_long: str, did_short: str) -> Dict:
    """Setze ``id``/``alsoKnownAs`` und ergänze fehlende ``controller``-Felder."""
    doc = json.loads(json.dumps(payload))  # tiefe Kopie
    doc["id"] = did_long
    doc.setdefault("alsoKnownAs", [])
    if did_short not in doc["alsoKnownAs"]:
        doc["alsoKnownAs"].append(did_short)
    for vm in doc.get("verificationMethod", []):
        vm.setdefault("controller", did_long)
    return doc
