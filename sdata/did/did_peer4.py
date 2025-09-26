import json, hashlib
from typing import Dict, Tuple

# --- Base58 (BTC) ------------------------------------------------------------
_B58_ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, 'big', signed=False)
    out = bytearray()
    while n > 0:
        n, r = divmod(n, 58)
        out.append(_B58_ALPHABET[r])
    # führende Nullen beibehalten
    pad = 0
    for byte in b:
        if byte == 0:
            pad += 1
        else:
            break
    return ('1' * pad) + out[::-1].decode()

def b58decode(s: str) -> bytes:
    n = 0
    for ch in s.encode():
        n = n * 58 + _B58_ALPHABET.index(ch)
    # führende '1' -> führende 0x00
    pad = len(s) - len(s.lstrip('1'))
    full = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n else b''
    return b'\x00' * pad + full

# --- Varint (LEB128, wie in multicodec) -------------------------------------
def varint_encode(n: int) -> bytes:
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

# --- Multicodec & Multihash Konstanten ---------------------------------------
# multicodec für JSON = 0x0200 (siehe Spezifikation)
MULTICODEC_JSON = 0x0200
# multihash: sha2-256 = 0x12, Länge 32 Bytes = 0x20
MH_SHA256 = 0x12
MH_SHA256_LEN = 32

def _canonical_json_bytes(payload: Dict) -> bytes:
    # Stabil: Keys sortieren, keine Spaces (für deterministische Hashes)
    s = json.dumps(payload, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
    return s.encode('utf-8')

def encode_document(payload: Dict) -> bytes:
    """
    Multicodec-„Framing“: varint(code) + raw JSON bytes
    """
    return varint_encode(MULTICODEC_JSON) + _canonical_json_bytes(payload)

def multibase_b58btc(data: bytes) -> str:
    return 'z' + b58encode(data)

def multihash_sha256(data: bytes) -> bytes:
    digest = hashlib.sha256(data).digest()
    return bytes([MH_SHA256, MH_SHA256_LEN]) + digest

# ---------------- did:peer:4 Erzeugung & Auflösung ---------------------------
def did_peer4_from_payload(payload: Dict) -> Tuple[str, str, Dict]:
    """
    Erzeugt:
      - long_form: did:peer:4{hash_b58mb}:{doc_b58mb}
      - short_form: did:peer:4{hash_b58mb}
    und gibt zusätzlich das „kontextualisierte“ DID Document zurück.
    """
    # 1) Encoded Document (multicodec-framed JSON), dann multibase (b58btc)
    encoded_doc_bytes = encode_document(payload)
    encoded_doc_mb = multibase_b58btc(encoded_doc_bytes)   # 'z...'

    # 2) Hash über die *roh bytes* des encoded_doc (multicodec+json)
    #    (Hinweis: Einige Implementierungen hashen die selben Bytes; wenn du
    #    stattdessen die multibase-Zeichenkette hashen willst, tausche data=...)
    mh = multihash_sha256(encoded_doc_bytes)
    mh_mb = multibase_b58btc(mh)

    long_form = f"did:peer:4{mh_mb}:{encoded_doc_mb}"
    short_form = f"did:peer:4{mh_mb}"

    did_doc = _contextualize_did_doc(payload, did_long=long_form, did_short=short_form)
    return long_form, short_form, did_doc

def resolve_long_form(did_long: str) -> Dict:
    """
    Löst eine Long-Form did:peer:4 auf:
      - extrahiert hash & encoded document
      - validiert Hash
      - setzt id/controller/alsoKnownAs
    """
    if not did_long.startswith("did:peer:4"):
        raise ValueError("Kein did:peer:4")
    try:
        _, rest = did_long.split("did:peer:4", 1)
        hash_mb, doc_mb = rest.split(":", 1)
    except ValueError:
        raise ValueError("Erwarte Long-Form: did:peer:4{hash}:{doc}")

    if not (hash_mb.startswith('z') and doc_mb.startswith('z')):
        raise ValueError("Erwarte multibase base58-btc ('z'-Präfix)")

    mh = b58decode(hash_mb[1:])
    encoded_doc_bytes = b58decode(doc_mb[1:])

    # validate multicodec prefix
    # decode varint (einfaches Lesen)
    def varint_decode(b: bytes) -> Tuple[int, int]:
        shift = 0; value = 0
        for i, byte in enumerate(b):
            value |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                return value, i + 1
            shift += 7
        raise ValueError("Ungültige varint")

    code, offset = varint_decode(encoded_doc_bytes)
    if code != MULTICODEC_JSON:
        raise ValueError("Multicodec-Code ist nicht JSON (0x0200)")
    json_bytes = encoded_doc_bytes[offset:]

    # verify multihash (sha2-256, 32)
    if len(mh) < 2 or mh[0] != MH_SHA256 or mh[1] != MH_SHA256_LEN:
        raise ValueError("Multihash nicht sha2-256/32")
    expected = hashlib.sha256(encoded_doc_bytes).digest()
    if mh[2:] != expected:
        raise ValueError("Hash-Validierung fehlgeschlagen")

    payload = json.loads(json_bytes.decode('utf-8'))
    did_short = f"did:peer:4{'z'+b58encode(mh)}"
    did_doc = _contextualize_did_doc(payload, did_long=did_long, did_short=did_short)
    return did_doc

def _contextualize_did_doc(payload: Dict, *, did_long: str, did_short: str) -> Dict:
    """
    Setzt 'id', 'alsoKnownAs' und füllt fehlende 'controller' in verificationMethod.
    Relative Fragments (#key-0) bleiben gültig.
    """
    doc = json.loads(json.dumps(payload))  # flache Kopie
    doc['id'] = did_long
    doc.setdefault('alsoKnownAs', [])
    if did_short not in doc['alsoKnownAs']:
        doc['alsoKnownAs'].append(did_short)

    for vm in doc.get('verificationMethod', []):
        vm.setdefault('controller', did_long)

        # Falls relative IDs ohne DID: auf DID referenzierbar lassen; Resolver dürfen
        # „as-is“ belassen, viele Implementierungen lassen "#key-0" stehen.

    # Gleiches Schema für andere Beziehungen (authentication, assertionMethod, service ...)
    return doc

# --------------------------- Demo --------------------------------------------
if __name__ == "__main__":
    # Minimale Beispiel-Payload (ohne root 'id'!)
    payload = {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "verificationMethod": [{
            "id": "#key-0",
            "type": "JsonWebKey2020",
            "publicKeyJwk": {
                "kty": "OKP",
                "crv": "Ed25519",
                # Beispielwert; hier gehört dein Base64url-encodierter Ed25519 Public Key rein:
                "x": "qhqVmPevNBx1W-amRiTzOizsqtVHiOVGQMRMBM29cE0"
            }
            # 'controller' wird beim Kontextualisieren gesetzt
        }],
        "authentication": ["#key-0"],
        "assertionMethod": ["#key-0"],
        "service": [{
            "id": "#inbox",
            "type": "DIDCommMessaging",
            "serviceEndpoint": "https://example.org/inbox"
        }]
    }

    did_long, did_short, did_doc = did_peer4_from_payload(payload)
    print("LONG :", did_long)
    print("SHORT:", did_short)

    # Auflösung (inkl. Hash-Validierung)
    resolved = resolve_long_form(did_long)
    assert resolved['id'] == did_long
    assert did_short in resolved.get('alsoKnownAs', [])
    print("OK: resolve_long_form() validiert und kontextualisiert.")
    print(resolved)
