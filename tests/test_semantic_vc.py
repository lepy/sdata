# -*- coding: utf-8 -*-
"""Tests für signierte Metadaten als W3C Verifiable Credential (pure-Python EdDSA)."""
import pytest

from sdata.base import Base
from sdata.metadata import Metadata
from sdata import semantic
from sdata.did import keys, pub_from_priv_jwk
from sdata.did.errors import VerificationError


def _signed():
    priv = keys.gen_ed25519_jwk()
    pub = pub_from_priv_jwk(priv)
    b = Base(name="specimen_vc")
    b.metadata.add("force_x", 12.5, unit="kN", dtype="float")
    jws = b.metadata.to_verifiable_credential("did:example:issuer", priv)
    return jws, pub, b


def test_vc_roundtrip_and_verify():
    jws, pub, b = _signed()
    assert jws.count(".") == 2                      # Compact-JWS
    subject = semantic.verify_credential(jws, pub)
    assert subject["@id"] == b.to_jsonld()["@id"]
    # Rekonstruktion zu Metadata
    m = Metadata.from_verifiable_credential(jws, pub)
    assert m.get("force_x").value == 12.5
    assert m.name == "specimen_vc"


def test_vc_tampered_fails():
    jws, pub, _ = _signed()
    header, payload, sig = jws.split(".")
    # Signatur unverändert, Payload manipulieren -> Verifikation muss scheitern
    tampered = header + "." + payload[:-4] + "AAAA" + "." + sig
    with pytest.raises((VerificationError, Exception)):
        semantic.verify_credential(tampered, pub)


def test_vc_extra_claims_and_no_id():
    priv = keys.gen_ed25519_jwk()
    pub = pub_from_priv_jwk(priv)
    # bare Metadata ohne _sdata_sname -> kein 'sub'/@id, aber extra_claims greifen
    m = Metadata()
    m.add("note", "frei")
    jws = m.to_verifiable_credential("did:example:issuer", priv,
                                     extra_claims={"nonce": "abc"})
    import sdata.did.jose as jose
    payload = jose.verify_compact(jws, pub)
    assert payload["nonce"] == "abc"
    assert "sub" not in payload                      # kein @id -> kein sub
    assert payload["vc"]["credentialSubject"]["sdata:note"] == {"@value": "frei", "@type": "xsd:string"}
