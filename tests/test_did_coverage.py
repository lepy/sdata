# -*- coding: utf-8 -*-
"""Ergänzende Abdeckung von sdata.did (CLIs + Fehler-/Edge-Branches)."""
import json
import uuid as _uuid

import pytest

import importlib

import sdata.did as did
# 'issue_vc' ist im Paket-Namespace als Funktion gecacht (Lazy-Export) und
# überschattet das gleichnamige Modul beim Attributzugriff -> via import_module holen.
issue_vc = importlib.import_module("sdata.did.issue_vc")
from sdata.did import (
    keys, did_web, verify_vp, utils_didkey, jose,
    did_peer4, ed25519, did_github, diddoc,
)
from sdata.did import EncodingError, ResolutionError, VerificationError

PUB_JWK = {"kty": "OKP", "crv": "Ed25519",
           "x": "qhqVmPevNBx1W-amRiTzOizsqtVHiOVGQMRMBM29cE0"}


# --- CLIs ---------------------------------------------------------------
def test_keys_cli(tmp_path):
    priv = tmp_path / "priv.json"
    pub = tmp_path / "pub.json"
    keys.main(["gen", "--out", str(priv)])
    keys.main(["pub", "--in", str(priv), "--out", str(pub)])
    keys.main(["thumb", "--in", str(pub)])
    assert priv.exists() and pub.exists()


def test_did_web_cli_build(tmp_path):
    pub = tmp_path / "pub.json"
    pub.write_text(json.dumps(PUB_JWK))
    out = tmp_path / "did.json"
    did_web.main(["build", "--domain", "example.com", "--pub", str(pub),
                  "--out", str(out), "--format", "multibase"])
    assert out.exists()


def test_did_web_cli_resolve(monkeypatch, capsys):
    doc = {"verificationMethod": [{"id": "did:web:example.com#key-1",
                                   "type": "JsonWebKey2020", "publicKeyJwk": PUB_JWK}]}

    monkeypatch.setattr(did_web, "http_get", lambda url, **k: (200, json.dumps(doc)))
    did_web.main(["resolve", "--kid", "did:web:example.com#key-1"])


def test_issue_vc_cli_vc_and_vp(tmp_path):
    keyfile = tmp_path / "issuer.json"
    keyfile.write_text(json.dumps(keys.gen_ed25519_jwk()))
    holderfile = tmp_path / "holder.json"
    holderfile.write_text(json.dumps(keys.gen_ed25519_jwk()))
    vc = tmp_path / "p.vc"
    issue_vc.main(["--issuer-domain", "i.example", "--issuer-key", str(keyfile),
                   "--gtin", "01", "--serial", "s", "--co2", "1", "--recycled", "2",
                   "--out", str(vc)])
    assert vc.exists()
    vp = tmp_path / "p.vp"
    issue_vc.main(["--issuer-domain", "i.example", "--issuer-key", str(keyfile),
                   "--gtin", "01", "--serial", "s", "--co2", "1", "--recycled", "2",
                   "--out", str(vp), "--make-vp", "--holder-key", str(holderfile)])
    assert vp.exists()
    # --make-vp ohne --holder-key -> SystemExit
    with pytest.raises(SystemExit):
        issue_vc.main(["--issuer-domain", "i.example", "--issuer-key", str(keyfile),
                       "--gtin", "01", "--serial", "s", "--co2", "1", "--recycled", "2",
                       "--out", str(tmp_path / "x"), "--make-vp"])


def test_verify_vp_cli(tmp_path, monkeypatch):
    issuer = keys.gen_ed25519_jwk()
    holder = keys.gen_ed25519_jwk()
    (tmp_path / "i.json").write_text(json.dumps(issuer))
    (tmp_path / "h.json").write_text(json.dumps(holder))
    vc = issue_vc.issue_vc("i.example", str(tmp_path / "i.json"),
                           gtin="01", serial="s", co2=1.0, recycled=2.0)
    holder_did = utils_didkey.did_key_from_jwk_ed25519(keys.pub_from_priv_jwk(holder))
    vp = issue_vc.make_vp(str(tmp_path / "h.json"), holder_did, vc, aud="a", nonce="n")
    vp_path = tmp_path / "p.vp"
    vp_path.write_text(vp)
    monkeypatch.setattr(verify_vp, "resolve_web_kid", lambda kid: keys.pub_from_priv_jwk(issuer))
    verify_vp.main(["--vp", str(vp_path)])
    # Fehlerfall -> SystemExit
    monkeypatch.setattr(verify_vp, "resolve_web_kid",
                        lambda kid: (_ for _ in ()).throw(ResolutionError("x")))
    with pytest.raises(SystemExit):
        verify_vp.main(["--vp", str(vp_path)])


# --- make_vp Nicht-did:key-Holder --------------------------------------
def test_make_vp_non_didkey_holder(tmp_path):
    holder = keys.gen_ed25519_jwk()
    (tmp_path / "h.json").write_text(json.dumps(holder))
    vp = issue_vc.make_vp(str(tmp_path / "h.json"), "did:web:holder.example", "vc.jws",
                          aud="a", nonce="n")
    assert jose.decode_header(vp)["kid"] == "did:web:holder.example#key-1"


# --- did_web _load_pub_input Varianten ---------------------------------
def test_did_web_load_variants(tmp_path):
    did_str = utils_didkey.did_key_from_jwk_ed25519(PUB_JWK)
    mb = did_str.split(":", 2)[2]
    # JSON mit multibase
    p1 = tmp_path / "m.json"
    p1.write_text(json.dumps({"multibase": mb}))
    doc = did_web.build_did_document("example.com", str(p1), variant="jwk")
    assert doc["verificationMethod"][0]["publicKeyJwk"] == PUB_JWK
    # reiner Multibase-Text
    p2 = tmp_path / "m.txt"
    p2.write_text(mb)
    assert did_web.build_did_document("example.com", str(p2), variant="multibase")
    # ungültige Eingabe
    p3 = tmp_path / "bad.txt"
    p3.write_text("not-valid")
    with pytest.raises(EncodingError):
        did_web.build_did_document("example.com", str(p3))
    with pytest.raises(EncodingError):
        did_web.build_did_document("example.com", str(p1), variant="invalid")
    # resolve: multibase-VM + Fehlerfälle
    with pytest.raises(EncodingError):
        did_web.did_web_to_url("did:key:z1")


def test_did_web_resolve_branches(monkeypatch):
    mb = utils_didkey.did_key_from_jwk_ed25519(PUB_JWK).split(":", 2)[2]
    doc = {"verificationMethod": [{"id": "did:web:e.com#key-1",
                                   "type": "Ed25519VerificationKey2020",
                                   "publicKeyMultibase": mb}]}

    monkeypatch.setattr(did_web, "http_get", lambda url, **k: (200, json.dumps(doc)))
    assert did_web.resolve_public_jwk_for_kid("did:web:e.com#key-1") == PUB_JWK
    # kid nicht gefunden
    with pytest.raises(ResolutionError):
        did_web.resolve_public_jwk_for_kid("did:web:e.com#missing")
    # HTTP-Fehlerstatus -> ResolutionError
    monkeypatch.setattr(did_web, "http_get", lambda url, **k: (404, ""))
    with pytest.raises(ResolutionError):
        did_web.resolve_public_jwk_for_kid("did:web:e.com#key-1")


# --- utils_didkey Edge -------------------------------------------------
def test_utils_didkey_edge():
    assert utils_didkey.did_key_fragment_from_jwk(PUB_JWK).startswith("z")
    assert utils_didkey.kid_for_did_web("did:web:x") == "did:web:x#key-1"
    did_str = utils_didkey.did_key_from_jwk_ed25519(PUB_JWK)
    assert utils_didkey.kid_for_did_key(did_str).count("#") == 1
    assert utils_didkey.kid_for_did_key(did_str, PUB_JWK).count("#") == 1
    with pytest.raises(EncodingError):
        utils_didkey.jwk_thumbprint_rfc7638({"kty": "RSA"})
    with pytest.raises(EncodingError):
        utils_didkey.pub_jwk_from_did_key("z" + "1" * 10)   # falsches multicodec


# --- jose Fehler-Branches ----------------------------------------------
def test_jose_errors():
    with pytest.raises(EncodingError):
        jose.signing_key_from_jwk({"kty": "OKP", "crv": "Ed25519"})   # kein 'd'
    with pytest.raises(EncodingError):
        jose.verifying_key_from_jwk({"crv": "Ed25519"})               # kein 'x'
    with pytest.raises(EncodingError):
        jose.decode_header("nur.zwei")
    with pytest.raises(EncodingError):
        jose.verify_compact("nur.zwei", PUB_JWK)


# --- did_peer4 Branches ------------------------------------------------
def test_did_peer4_branches():
    assert did_peer4.b58encode(b"") == ""
    assert did_peer4.varint_decode(did_peer4.varint_encode(300)) == (300, 2)
    with pytest.raises(EncodingError):
        did_peer4.varint_decode(b"\x80\x80")        # unvollständiger varint
    with pytest.raises(EncodingError):
        did_peer4.resolve_long_form("did:peer:4znohash")   # keine 2 Teile


# --- ed25519 Branches --------------------------------------------------
def test_ed25519_branches():
    with pytest.raises(ValueError):
        ed25519.decodeint(b"\x00" * 31)           # falsche Länge
    with pytest.raises(ValueError):
        ed25519.decodepoint(b"\x00" * 31)
    seed = bytes(range(32))
    pk = ed25519.publickey(seed)
    # decodepoint eines gültigen Punktes
    assert isinstance(ed25519.decodepoint(pk), ed25519.Point)


# --- diddoc Demo -------------------------------------------------------
def test_diddoc_demo():
    out = diddoc._demo()
    assert "payload" in out and out["signatures"]


# --- did_github resolve (gemockt) --------------------------------------
def test_did_github_resolve(monkeypatch):
    doc = {"@context": ["https://www.w3.org/ns/did/v1"], "id": "did:github:u:r"}
    monkeypatch.setattr(did_github, "fetch_json",
                        lambda url: doc if url.endswith("did.json") else None)
    assert did_github.resolve_did_github("did:github:u:r:main:sub")["id"] == "did:github:u:r"


def _didkey_kid(jwk_pub):
    d = utils_didkey.did_key_from_jwk_ed25519(jwk_pub)
    return d, "{}#{}".format(d, d.split(":", 2)[2])


def test_error_branches(tmp_path):
    assert isinstance(dir(did), list)                       # __init__ __dir__

    # issue_vc CLI --holder-did
    keyfile = tmp_path / "i.json"
    keyfile.write_text(json.dumps(keys.gen_ed25519_jwk()))
    holderfile = tmp_path / "h.json"
    holderfile.write_text(json.dumps(keys.gen_ed25519_jwk()))
    issue_vc.main(["--issuer-domain", "i.example", "--issuer-key", str(keyfile),
                   "--gtin", "01", "--serial", "s", "--co2", "1", "--recycled", "2",
                   "--out", str(tmp_path / "x.vp"), "--make-vp",
                   "--holder-key", str(holderfile), "--holder-did", "did:web:h.example"])

    # did_web: --context off + resolve ohne Schlüsselmaterial
    pub = tmp_path / "pub.json"
    pub.write_text(json.dumps(PUB_JWK))
    out = tmp_path / "d.json"
    did_web.main(["build", "--domain", "e.com", "--pub", str(pub), "--out", str(out),
                  "--context", "off"])

    # jose key-Validierung
    with pytest.raises(EncodingError):
        jose.signing_key_from_jwk({"kty": "RSA", "crv": "Ed25519", "d": "AA"})
    with pytest.raises(EncodingError):
        jose.verifying_key_from_jwk({"kty": "RSA", "crv": "Ed25519", "x": "AA"})

    # utils_didkey-Validierung
    with pytest.raises(EncodingError):
        utils_didkey.jwk_thumbprint_rfc7638("notdict")
    with pytest.raises(EncodingError):
        utils_didkey.did_key_from_jwk_ed25519({"kty": "OKP", "crv": "Ed25519"})
    with pytest.raises(EncodingError):
        utils_didkey.did_key_from_jwk_ed25519({"kty": "OKP", "crv": "Ed25519", "x": "AA"})
    did_str = utils_didkey.did_key_from_jwk_ed25519(PUB_JWK)
    frag = did_str.split(":", 2)[2]
    assert utils_didkey.pub_jwk_from_did_key("#" + frag) == PUB_JWK    # '#'-Strip

    # verify_vp Fehlerzweige
    with pytest.raises(ResolutionError):
        verify_vp.resolve_public_jwk_for_kid("did:foo:x#k")

    holder = keys.gen_ed25519_jwk()
    hdid, hkid = _didkey_kid(keys.pub_from_priv_jwk(holder))
    vp_empty = jose.sign_compact({"holder": hdid, "vp": {"verifiableCredential": []}},
                                 holder, kid=hkid, typ="vp+jwt")
    with pytest.raises(VerificationError):
        verify_vp.verify_presentation(vp_empty)               # keine VC

    issuer = keys.gen_ed25519_jwk()
    idid, ikid = _didkey_kid(keys.pub_from_priv_jwk(issuer))
    vc_future = jose.sign_compact(
        {"iss": idid, "nbf": 9999999999, "exp": 99999999999,
         "vc": {"credentialSubject": {}}}, issuer, kid=ikid, typ="vc+ld+jwt")
    vp_future = jose.sign_compact(
        {"holder": hdid, "vp": {"verifiableCredential": [vc_future]}},
        holder, kid=hkid, typ="vp+jwt")
    with pytest.raises(VerificationError):
        verify_vp.verify_presentation(vp_future)              # VC nbf in der Zukunft

    # ed25519: falsche Längen
    with pytest.raises(ValueError):
        ed25519.sign(b"m", b"\x00" * 31, b"\x00" * 32)


def test_did_peer4_invalid_multibase():
    with pytest.raises(EncodingError):
        did_peer4.resolve_long_form("did:peer:4xnohash:ydoc")   # kein 'z'-Präfix


def test_did_web_resolve_no_key(monkeypatch):
    doc = {"verificationMethod": [{"id": "did:web:e.com#key-1", "type": "X"}]}

    monkeypatch.setattr(did_web, "http_get", lambda url, **k: (200, json.dumps(doc)))
    with pytest.raises(ResolutionError):
        did_web.resolve_public_jwk_for_kid("did:web:e.com#key-1")


def test_did_github_fetch_json(monkeypatch):
    did_github.fetch_json.cache_clear()
    monkeypatch.setenv("GITHUB_TOKEN", "tok")               # _headers Token-Zweig

    def fake_get(url, **kw):
        if url.endswith(".well-known/did.json"):
            return (404, "")
        return (200, '{"@context":["x"],"id":"did:github:u:r"}')
    monkeypatch.setattr(did_github, "http_get", fake_get)
    assert did_github.resolve_did_github("did:github:u:r")["id"] == "did:github:u:r"


def test_did_github_comments_and_not_found(monkeypatch):
    did_github.fetch_json.cache_clear()

    comments = '// c\n{"@context":["x"],"id":"did:github:a:b"} /* x */'
    monkeypatch.setattr(did_github, "http_get", lambda url, **k: (200, comments))
    assert did_github.resolve_did_github("did:github:a:b")["id"] == "did:github:a:b"

    did_github.fetch_json.cache_clear()

    monkeypatch.setattr(did_github, "http_get", lambda url, **k: (404, ""))
    with pytest.raises(ResolutionError):
        did_github.resolve_did_github("did:github:none:none")


def test_jose_malformed_json():
    import base64
    bad = base64.urlsafe_b64encode(b"not json").decode().rstrip("=")
    with pytest.raises(EncodingError):
        jose.decode_header("{}.a.b".format(bad))
    holder = keys.gen_ed25519_jwk()
    _, hkid = _didkey_kid(keys.pub_from_priv_jwk(holder))
    sk = jose.signing_key_from_jwk(holder)
    h = jose.b64url_json({"alg": "EdDSA", "kid": hkid, "typ": "x"})
    p = base64.urlsafe_b64encode(b"not json").decode().rstrip("=")
    sig = sk.sign("{}.{}".format(h, p).encode())
    jws = "{}.{}.{}".format(h, p, utils_didkey.b64url(sig))
    with pytest.raises(EncodingError):
        jose.verify_compact(jws, keys.pub_from_priv_jwk(holder))   # Sig ok, Payload kein JSON


def test_did_peer4_invalid_codec_and_hash():
    import hashlib
    bad_doc = did_peer4.varint_encode(0x99) + b'{"a":1}'        # falscher multicodec
    doc_mb = did_peer4.multibase_b58btc(bad_doc)
    mh_mb = did_peer4.multibase_b58btc(did_peer4.multihash_sha256(bad_doc))
    with pytest.raises(EncodingError):
        did_peer4.resolve_long_form("did:peer:4{}:{}".format(mh_mb, doc_mb))
    good_doc = did_peer4.encode_document({"a": 1})
    doc_mb2 = did_peer4.multibase_b58btc(good_doc)
    bad_mh = did_peer4.multibase_b58btc(bytes([0x99, 0x20]) + hashlib.sha256(good_doc).digest())
    with pytest.raises(EncodingError):
        did_peer4.resolve_long_form("did:peer:4{}:{}".format(bad_mh, doc_mb2))


def test_did_github_missing_id(monkeypatch):
    monkeypatch.setattr(did_github, "fetch_json", lambda url: {"@context": ["x"]})
    with pytest.raises(EncodingError):
        did_github.resolve_did_github("did:github:u:r")


# --- Paket __getattr__ -------------------------------------------------
def test_package_getattr_unknown():
    with pytest.raises(AttributeError):
        did.this_does_not_exist
