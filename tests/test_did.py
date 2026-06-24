# -*- coding: utf-8 -*-
"""Tests für das DID-/VC-Subpackage :mod:`sdata.did`.

Importiert über die öffentliche Paket-API. Die Tests laufen ohne Netzwerk
(HTTP wird via ``monkeypatch`` gemockt) und überspringen sich sauber, falls die
optionalen Abhängigkeiten (``ecdsa``/``base58``, via ``pip install sdata[did]``)
nicht installiert sind.
"""
import json
import base64
import hashlib

import pytest

# Optionale Abhängigkeiten / Paket – sonst die gesamte Datei überspringen.
pytest.importorskip("ecdsa")
pytest.importorskip("base58")
pytest.importorskip("sdata.did")

from sdata.did import (                                              # noqa: E402
    gen_ed25519_jwk, pub_from_priv_jwk, did_key_from_jwk_ed25519,
    pub_jwk_from_did_key, jwk_thumbprint_rfc7638,
    sign_compact, verify_compact, jws_header, jws_verify,
    issue_vc, make_vp, verify_presentation,
    build_did_document, did_web_to_url,
    did_peer4_from_payload, resolve_long_form,
    parse_did_github, resolve_did_github,
    EncodingError, ResolutionError, VerificationError,
)
from sdata.did import ed25519 as ed       # noqa: E402  (Lern-Referenz)
from sdata.did import did_peer4 as dp     # noqa: E402
from sdata.did import did_github as dgh   # noqa: E402
from sdata.did import did_web as dw       # noqa: E402
from sdata.did import verify_vp as vv     # noqa: E402
from sdata.did import diddoc              # noqa: E402

PUB_JWK = {"kty": "OKP", "crv": "Ed25519",
           "x": "qhqVmPevNBx1W-amRiTzOizsqtVHiOVGQMRMBM29cE0"}


def _b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ======================================================================
# ed25519.py  (reine Python-Referenzimplementierung)
# ======================================================================
class TestEd25519:
    SK = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc4"
                       "4449c5697b326919703bac031cae7f60")
    PK = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a"
                       "0ee172f3daa62325af021a68f707511a")
    SIG = bytes.fromhex("e5564300c360ac729086e2cc806e828a"
                        "84877f1eb8e5d974d873e06522490155"
                        "5fb8821590a33bacc61e39701cf9b46b"
                        "d25bf5f0595bbe24655141438e7a100b")

    def test_rfc8032_public_key(self):
        assert ed.publickey(self.SK) == self.PK
        assert ed.keypair_from_seed(self.SK).pk == self.PK

    def test_rfc8032_signature_matches_vector(self):
        assert ed.sign(b"", self.SK, self.PK) == self.SIG

    def test_rfc8032_verify(self):
        assert ed.verify(self.SIG, b"", self.PK) is True

    def test_sign_verify_roundtrip(self):
        seed = bytes(range(32))
        pk = ed.publickey(seed)
        sig = ed.sign(b"Hallo, DIDComm!", seed, pk)
        assert len(sig) == 64
        assert ed.verify(sig, b"Hallo, DIDComm!", pk) is True

    def test_rejects_tampered_message(self):
        seed = bytes(range(32))
        pk = ed.publickey(seed)
        sig = ed.sign(b"original", seed, pk)
        assert ed.verify(sig, b"tampered", pk) is False

    def test_rejects_tampered_signature(self):
        seed = bytes(range(32))
        pk = ed.publickey(seed)
        sig = bytearray(ed.sign(b"data", seed, pk))
        sig[0] ^= 0x01
        assert ed.verify(bytes(sig), b"data", pk) is False

    def test_rejects_bad_lengths(self):
        assert ed.verify(b"\x00" * 63, b"x", b"\x00" * 32) is False
        assert ed.verify(b"\x00" * 64, b"x", b"\x00" * 31) is False
        with pytest.raises(ValueError):
            ed.publickey(b"\x00" * 31)

    def test_high_S_rejected(self):
        seed = bytes(range(32))
        pk = ed.publickey(seed)
        sig = bytearray(ed.sign(b"m", seed, pk))
        sig[32:] = ed.encodeint(ed.l + 1)
        assert ed.verify(bytes(sig), b"m", pk) is False


# ======================================================================
# did_peer4.py  (abhängigkeitsfrei)
# ======================================================================
class TestDidPeer4:
    PAYLOAD = {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "verificationMethod": [{
            "id": "#key-0", "type": "JsonWebKey2020", "publicKeyJwk": PUB_JWK}],
        "authentication": ["#key-0"],
        "assertionMethod": ["#key-0"],
    }

    def test_long_and_short_form(self):
        long_form, short_form, doc = did_peer4_from_payload(self.PAYLOAD)
        assert short_form.startswith("did:peer:4z")
        assert long_form.startswith(short_form + ":")
        assert doc["id"] == long_form
        assert short_form in doc["alsoKnownAs"]

    def test_resolve_roundtrip(self):
        long_form, short_form, _ = did_peer4_from_payload(self.PAYLOAD)
        resolved = resolve_long_form(long_form)
        assert resolved["id"] == long_form
        assert short_form in resolved.get("alsoKnownAs", [])
        assert resolved["verificationMethod"][0]["controller"] == long_form

    def test_hash_tampering_raises_verification_error(self):
        long_form, _, _ = did_peer4_from_payload(self.PAYLOAD)
        hash_part = long_form[len("did:peer:4"):].split(":", 1)[0]
        other_long, _, _ = did_peer4_from_payload({**self.PAYLOAD, "authentication": []})
        other_doc_part = other_long[len("did:peer:4"):].split(":", 1)[1]
        forged = "did:peer:4{}:{}".format(hash_part, other_doc_part)
        with pytest.raises(VerificationError):
            resolve_long_form(forged)

    def test_rejects_non_peer4(self):
        with pytest.raises(EncodingError):
            resolve_long_form("did:web:example.com")

    def test_base58_roundtrip_with_leading_zeros(self):
        data = b"\x00\x00hello-\xff\x01"
        assert dp.b58decode(dp.b58encode(data)) == data


# ======================================================================
# diddoc.py  (Demo; Bugfix-Regression)
# ======================================================================
class TestDiddoc:
    def test_import_exposes_fixed_symbols(self):
        assert callable(diddoc.sign)
        assert callable(diddoc.publickey)

    def test_base64url_roundtrip(self):
        data = b"hello-world-\x00\xff"
        enc = diddoc.base64url_encode(data)
        assert b"=" not in enc
        assert diddoc.base64url_decode(enc) == data

    def test_build_didcomm_jws_is_verifiable(self):
        seed = bytes(range(1, 33))
        jws = diddoc.build_didcomm_jws({"id": "1"}, seed)
        pk = diddoc.publickey(seed)
        protected = jws["signatures"][0]["protected"].encode()
        payload = jws["payload"].encode()
        sig = diddoc.base64url_decode(jws["signatures"][0]["signature"].encode())
        assert ed.verify(sig, protected + b"." + payload, pk) is True


# ======================================================================
# utils_didkey.py
# ======================================================================
class TestUtilsDidKey:
    def test_didkey_jwk_roundtrip(self):
        did = did_key_from_jwk_ed25519(PUB_JWK)
        assert did.startswith("did:key:z")
        assert pub_jwk_from_did_key(did) == PUB_JWK
        assert pub_jwk_from_did_key(did.split(":", 2)[2]) == PUB_JWK

    def test_thumbprint_rfc7638_matches_reference(self):
        got = jwk_thumbprint_rfc7638(PUB_JWK)
        canon = json.dumps({"crv": "Ed25519", "kty": "OKP", "x": PUB_JWK["x"]},
                           separators=(",", ":"), sort_keys=True).encode()
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(canon).digest()).decode().rstrip("=")
        assert got == expected
        assert got == jwk_thumbprint_rfc7638(
            {"x": PUB_JWK["x"], "crv": "Ed25519", "kty": "OKP"})

    def test_validation_errors(self):
        with pytest.raises(EncodingError):
            did_key_from_jwk_ed25519({"kty": "RSA", "crv": "Ed25519", "x": "AA"})
        with pytest.raises(EncodingError):
            pub_jwk_from_did_key("did:key:Xnotmultibase")


# ======================================================================
# did_web.py
# ======================================================================
class TestDidWeb:
    def test_url_well_known(self):
        assert did_web_to_url("did:web:example.com") == \
            "https://example.com/.well-known/did.json"

    def test_url_with_path(self):
        assert did_web_to_url("did:web:example.com:user:alice") == \
            "https://example.com/user/alice/did.json"

    def test_url_rejects_non_web(self):
        with pytest.raises(EncodingError):
            did_web_to_url("did:key:z123")

    def test_build_did_document_jwk(self, tmp_path):
        pub = tmp_path / "pub.json"
        pub.write_text(json.dumps(PUB_JWK))
        doc = build_did_document("example.com", str(pub), variant="jwk")
        assert doc["id"] == "did:web:example.com"
        vm = doc["verificationMethod"][0]
        assert vm["type"] == "JsonWebKey2020"
        assert vm["id"] == "did:web:example.com#key-1"
        assert vm["publicKeyJwk"] == PUB_JWK
        assert "did:web:example.com#key-1" in doc["assertionMethod"]

    def test_build_did_document_multibase(self, tmp_path):
        pub = tmp_path / "pub.json"
        pub.write_text(json.dumps(PUB_JWK))
        doc = build_did_document("example.com", str(pub), variant="multibase")
        vm = doc["verificationMethod"][0]
        assert vm["type"] == "Ed25519VerificationKey2020"
        assert vm["publicKeyMultibase"].startswith("z")

    def test_resolve_public_jwk_mocked(self, monkeypatch):
        doc = {"verificationMethod": [{
            "id": "did:web:example.com#key-1", "type": "JsonWebKey2020",
            "publicKeyJwk": PUB_JWK}]}

        class FakeResp:
            def raise_for_status(self):
                pass

            def json(self):
                return doc

        monkeypatch.setattr(dw.requests, "get", lambda *a, **k: FakeResp())
        assert dw.resolve_public_jwk_for_kid("did:web:example.com#key-1") == PUB_JWK

    def test_resolve_network_error_raises_resolution_error(self, monkeypatch):
        def boom(*a, **k):
            raise dw.requests.RequestException("boom")
        monkeypatch.setattr(dw.requests, "get", boom)
        with pytest.raises(ResolutionError):
            dw.resolve_public_jwk_for_kid("did:web:example.com#key-1")


# ======================================================================
# did_github.py
# ======================================================================
class TestDidGithub:
    def test_parse_full(self):
        p = parse_did_github("did:github:lepy:cudi2:main:sub__dir")
        assert (p.user, p.repo, p.ref, p.subpath) == ("lepy", "cudi2", "main", "sub/dir")
        assert p.did == "did:github:lepy:cudi2:main:sub/dir"

    def test_parse_minimal(self):
        p = parse_did_github("did:github:alice:repo")
        assert (p.user, p.repo, p.ref, p.subpath) == ("alice", "repo", None, None)

    def test_parse_invalid(self):
        with pytest.raises(EncodingError):
            parse_did_github("did:web:example.com")
        with pytest.raises(EncodingError):
            parse_did_github("did:github:onlyuser")

    def test_raw_url(self):
        assert dgh._raw_url("u", "r", "main", "did.json") == \
            "https://raw.githubusercontent.com/u/r/main/did.json"

    def test_candidate_paths_order(self):
        cands = dgh.candidate_paths(parse_did_github("did:github:u:r"))
        assert cands[0] == ("main", ".well-known/did.json")
        assert ("master", "did.json") in cands

    def test_resolve_picks_first_hit(self, monkeypatch):
        doc = {"@context": ["https://www.w3.org/ns/did/v1"], "id": "did:github:u:r"}
        monkeypatch.setattr(
            dgh, "fetch_json",
            lambda url: doc if url.endswith(".well-known/did.json") else None)
        assert resolve_did_github("did:github:u:r")["id"] == "did:github:u:r"

    def test_resolve_requires_context(self, monkeypatch):
        monkeypatch.setattr(dgh, "fetch_json", lambda url: {"id": "x"})
        with pytest.raises(EncodingError):
            resolve_did_github("did:github:u:r")

    def test_resolve_not_found(self, monkeypatch):
        monkeypatch.setattr(dgh, "fetch_json", lambda url: None)
        with pytest.raises(ResolutionError):
            resolve_did_github("did:github:u:r")


# ======================================================================
# jose.py / issue_vc.py / verify_vp.py
# ======================================================================
class TestJoseAndCredentials:
    def _keypair_did(self):
        jwk = gen_ed25519_jwk()
        pub = pub_from_priv_jwk(jwk)
        did = did_key_from_jwk_ed25519(pub)
        kid = "{}#{}".format(did, did.split(":", 2)[2])
        return jwk, pub, kid

    def test_keygen_shape(self):
        jwk = gen_ed25519_jwk()
        assert jwk["kty"] == "OKP" and jwk["crv"] == "Ed25519"
        assert "x" in jwk and "d" in jwk
        assert "d" not in pub_from_priv_jwk(jwk)

    def test_sign_and_verify_compact(self):
        jwk, pub, kid = self._keypair_did()
        jws = sign_compact({"iss": "x", "hello": "world"}, jwk, kid=kid, typ="JWT")
        assert jws_header(jws)["alg"] == "EdDSA"
        assert jws_header(jws)["kid"] == kid
        assert verify_compact(jws, pub)["hello"] == "world"

    def test_verify_via_didkey_resolution(self):
        jwk, _, kid = self._keypair_did()
        jws = sign_compact({"hello": "world"}, jwk, kid=kid, typ="JWT")
        pub = vv.resolve_public_jwk_for_kid(kid)     # did:key -> lokal, kein Netz
        assert jws_verify(jws, pub)["hello"] == "world"

    def test_tampered_payload_raises_verification_error(self):
        jwk, pub, kid = self._keypair_did()
        h, _, s = sign_compact({"a": 1}, jwk, kid=kid, typ="x").split(".")
        bad = base64.urlsafe_b64encode(json.dumps({"a": 2}).encode()).decode().rstrip("=")
        with pytest.raises(VerificationError):
            verify_compact("{}.{}.{}".format(h, bad, s), pub)

    def test_malformed_jws_raises_encoding_error(self):
        _, pub, _ = self._keypair_did()
        with pytest.raises(EncodingError):
            verify_compact("not-a-jws", pub)

    def test_issue_vc_product_passport_schema(self, tmp_path):
        keyfile = tmp_path / "issuer.json"
        keyfile.write_text(json.dumps(gen_ed25519_jwk()))
        jws = issue_vc(issuer_domain="issuer.example", issuer_key_path=str(keyfile),
                       gtin="04012345678901", serial="SN-42", co2=12.5, recycled=80.0)
        payload = json.loads(_b64url_decode(jws.split(".")[1]))
        assert payload["iss"] == "did:web:issuer.example"
        subj = payload["vc"]["credentialSubject"]
        assert subj["gtin"] == "04012345678901"
        assert subj["serialNumber"] == "SN-42"
        assert subj["co2Footprint"] == {"value": 12.5, "unitText": "kg CO2e"}
        assert subj["recycledContent"] == {"value": 80.0, "unitText": "%"}
        assert subj["gs1DigitalLink"] == "https://id.gs1.org/01/04012345678901/21/SN-42"
        assert {"VerifiableCredential", "ProductPassport"} <= set(payload["vc"]["type"])

    # --- vollständiger Fluss: Issuer (did:web, gemockt) + Holder (did:key) ---
    def _make_vp(self, tmp_path, monkeypatch, aud="aud1", nonce="n1"):
        issuer = gen_ed25519_jwk()
        holder = gen_ed25519_jwk()
        (tmp_path / "i.json").write_text(json.dumps(issuer))
        (tmp_path / "h.json").write_text(json.dumps(holder))
        vc = issue_vc("issuer.example", str(tmp_path / "i.json"),
                      gtin="01", serial="s", co2=1.0, recycled=2.0)
        holder_did = did_key_from_jwk_ed25519(pub_from_priv_jwk(holder))
        vp = make_vp(str(tmp_path / "h.json"), holder_did, vc, aud=aud, nonce=nonce)
        # did:web-Auflösung des Issuers durch den Public-Key ersetzen
        monkeypatch.setattr(vv, "resolve_web_kid",
                            lambda kid: pub_from_priv_jwk(issuer))
        return vp

    def test_end_to_end_verify_presentation(self, tmp_path, monkeypatch):
        vp = self._make_vp(tmp_path, monkeypatch)
        result = verify_presentation(vp, expected_aud="aud1", expected_nonce="n1")
        assert result["issuer"] == "did:web:issuer.example"
        assert result["holder"].startswith("did:key:z")
        assert result["credentialSubject"]["gtin"] == "01"

    def test_verify_presentation_aud_mismatch(self, tmp_path, monkeypatch):
        vp = self._make_vp(tmp_path, monkeypatch)
        with pytest.raises(VerificationError):
            verify_presentation(vp, expected_aud="WRONG")

    def test_verify_presentation_nonce_mismatch(self, tmp_path, monkeypatch):
        vp = self._make_vp(tmp_path, monkeypatch)
        with pytest.raises(VerificationError):
            verify_presentation(vp, expected_nonce="WRONG")

    def test_verify_presentation_expired(self, tmp_path, monkeypatch):
        vp = self._make_vp(tmp_path, monkeypatch)
        # Referenzzeit weit in der Zukunft -> exp überschritten
        with pytest.raises(VerificationError):
            verify_presentation(vp, now=99999999999)
