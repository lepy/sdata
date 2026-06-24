# sdata.did — Decentralized Identifiers & Verifiable Credentials

Schlanke, **pure-Python** Bausteine für Self-Sovereign Identity (SSI) rund um
Ed25519: Schlüssel als JWK, Compact-JWS (JOSE/EdDSA), Verifiable Credentials &
Presentations sowie mehrere DID-Methoden.

## Installation

Die DID-Funktionen brauchen zwei optionale Abhängigkeiten:

```bash
pip install "sdata[did]"     # zieht ecdsa + base58
```

## Unterstützte Standards

| Bereich | Standard |
|---|---|
| DID-Dokumente | [W3C DID Core](https://www.w3.org/TR/did-core/) |
| DID-Methoden | [did:web](https://w3c-ccg.github.io/did-method-web/), [did:key](https://w3c-ccg.github.io/did-method-key/), [did:peer:4](https://identity.foundation/peer-did-method-spec/), `did:github` (projektspezifisch) |
| Credentials | [W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model/) (JWT-VC) |
| Signatur | [JOSE/JWS RFC 7515](https://www.rfc-editor.org/rfc/rfc7515), [EdDSA RFC 8037](https://www.rfc-editor.org/rfc/rfc8037) |
| Thumbprint | [JWK Thumbprint RFC 7638](https://www.rfc-editor.org/rfc/rfc7638) |

## ⚠️ Sicherheitshinweis

Der produktive Krypto-Pfad nutzt `python-ecdsa` (reine Python-Implementierung).
Sie ist dependency-arm, aber **nicht garantiert constant-time** (Timing-
Seitenkanal-Risiko). Für hochsensible Umgebungen ein libsodium-Backend (PyNaCl)
oder `cryptography` (OpenSSL) erwägen.

Das Modul `ed25519.py` ist eine reine **Lern-Referenz** (RFC 8032) und wird vom
Funktionspfad **nicht** verwendet.

## Modulübersicht

| Modul | Inhalt |
|---|---|
| `errors.py` | Ausnahmehierarchie (`DidError`, `EncodingError`, `ResolutionError`, `VerificationError`) |
| `keys.py` | Ed25519-JWK erzeugen/ableiten (CLI) |
| `utils_didkey.py` | JWK ↔ `did:key`, RFC-7638-Thumbprint, `kid`-Helfer |
| `jose.py` | Compact-JWS signieren/verifizieren (EdDSA) |
| `issue_vc.py` | VC/VP ausstellen (ProductPassport, CLI) |
| `verify_vp.py` | VP+VC verifizieren (`verify_presentation`, CLI) |
| `did_web.py` | `did:web`-Dokumente bauen/auflösen (CLI) |
| `did_peer4.py` | `did:peer:4` (abhängigkeitsfrei) |
| `did_github.py` | `did:github`-Auflösung über GitHub-Rohinhalte |
| `ed25519.py` | Lern-Referenz Ed25519 (nicht für Produktion) |
| `diddoc.py` | Demo: DIDComm-JWS |

## Schnellstart (Bibliothek)

```python
from sdata.did import (
    gen_ed25519_jwk, pub_from_priv_jwk, did_key_from_jwk_ed25519,
    sign_compact, verify_compact,
)

jwk = gen_ed25519_jwk()                       # privates JWK (x + d)
pub = pub_from_priv_jwk(jwk)                   # nur x
did = did_key_from_jwk_ed25519(pub)           # did:key:z…
kid = f"{did}#{did.split(':', 2)[2]}"

jws = sign_compact({"hello": "world"}, jwk, kid=kid, typ="JWT")
assert verify_compact(jws, pub)["hello"] == "world"
```

### VC ausstellen & Presentation verifizieren

```python
from sdata.did import verify_presentation, VerificationError

result = verify_presentation(vp_jws, expected_aud="https://verifier.example.org",
                             expected_nonce=nonce)
print(result["issuer"], result["credentialSubject"]["gtin"])
```

## CLI (als Modul, `-m`)

```bash
# Schlüssel
python -m sdata.did.keys gen   --out issuer_key.json
python -m sdata.did.keys pub   --in  issuer_key.json --out issuer_pub.json
python -m sdata.did.keys thumb --in  issuer_pub.json

# did:web-Dokument
python -m sdata.did.did_web build --domain example.com \
    --pub issuer_pub.json --out did.json --format jwk
python -m sdata.did.did_web resolve --kid did:web:example.com#key-1

# VC ausstellen / VP verifizieren
python -m sdata.did.issue_vc --issuer-domain issuer.example \
    --issuer-key issuer_key.json --gtin 04012345678901 --serial SN-42 \
    --co2 12.5 --recycled 80 --out product.vc
python -m sdata.did.verify_vp --vp product.vp \
    --expected-aud https://verifier.example.org
```

## Tests

```bash
pytest tests/test_did.py
```

Die Tests laufen ohne Netzwerk (HTTP wird gemockt) und überspringen sich
sauber (`skip`), falls optionale Abhängigkeiten fehlen.
