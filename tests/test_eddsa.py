# -*- coding: utf-8 -*-
"""Korrektheits- und API-Tests für das abhängigkeitsfreie Ed25519-Backend.

Die offiziellen RFC-8032-Testvektoren (§7.1) sichern ab, dass die pure-Python-
Implementierung bitgenau das gleiche Ergebnis liefert wie eine etablierte
Bibliothek – Grundlage dafür, ``python-ecdsa`` als Abhängigkeit abzulösen.
"""
import pytest

from sdata.did import ed25519
from sdata.did.eddsa import (
    Ed25519, SigningKey, VerifyingKey, BadSignatureError,
)
from sdata.did.base58btc import b58encode, b58decode


def _h(s):
    return bytes.fromhex(s)


# RFC 8032 §7.1 – (secret, public, message, signature)
RFC8032_VECTORS = [
    (  # TEST 1 – leere Nachricht
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e0652249015"
        "55fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
    ),
    (  # TEST 2 – 1 Byte
        "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "72",
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    ),
    (  # TEST 3 – 2 Byte
        "c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
        "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
        "af82",
        "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac"
        "18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a",
    ),
    (  # TEST – SHA-512("abc") als Nachricht
        "833fe62409237b9d62ec77587520911e9a759cec1d19755b7da901b96dca3d42",
        "ec172b93ad5e563bf4932c70e1245034c35467ef2efd4d64ebf819683467e2bf",
        "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
        "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f",
        "dc2a4459e7369633a52b1bf277839a00201009a3efbf3ecb69bea2186c26b589"
        "09351fc9ac90b3ecfdfbc7c66431e0303dca179c138ac17ad9bef1177331a704",
    ),
]


@pytest.mark.parametrize("sk_hex,pk_hex,msg_hex,sig_hex", RFC8032_VECTORS)
def test_rfc8032_primitives(sk_hex, pk_hex, msg_hex, sig_hex):
    sk, pk, msg, sig = _h(sk_hex), _h(pk_hex), _h(msg_hex), _h(sig_hex)
    assert ed25519.publickey(sk) == pk
    assert ed25519.sign(msg, sk, pk) == sig
    assert ed25519.verify(sig, msg, pk) is True
    # manipulierte Nachricht -> ungültig
    assert ed25519.verify(sig, msg + b"\x00", pk) is False


@pytest.mark.parametrize("sk_hex,pk_hex,msg_hex,sig_hex", RFC8032_VECTORS)
def test_rfc8032_adapter(sk_hex, pk_hex, msg_hex, sig_hex):
    sk, pk, msg, sig = _h(sk_hex), _h(pk_hex), _h(msg_hex), _h(sig_hex)
    signer = SigningKey.from_string(sk, curve=Ed25519)
    assert signer.to_string() == sk
    assert signer.get_verifying_key().to_string() == pk
    assert signer.sign(msg) == sig
    verifier = VerifyingKey.from_string(pk, curve=Ed25519)
    assert verifier.verify(sig, msg) is True


def test_adapter_bad_signature_raises():
    sk = _h(RFC8032_VECTORS[0][0])
    pk = _h(RFC8032_VECTORS[0][1])
    sig = _h(RFC8032_VECTORS[0][3])
    vk = VerifyingKey.from_string(pk)
    with pytest.raises(BadSignatureError):
        vk.verify(sig, b"andere nachricht")


def test_adapter_generate_roundtrip():
    sk = SigningKey.generate(curve=Ed25519)
    vk = sk.get_verifying_key()
    msg = b"hallo welt"
    sig = sk.sign(msg)
    assert vk.verify(sig, msg) is True
    # zwei frische Schlüssel unterscheiden sich
    assert sk.to_string() != SigningKey.generate().to_string()


def test_adapter_wrong_length():
    with pytest.raises(ValueError):
        SigningKey.from_string(b"\x00" * 31)
    with pytest.raises(ValueError):
        VerifyingKey.from_string(b"\x00" * 33)


def test_ed25519_sentinel():
    assert Ed25519.name == "Ed25519"


# --- base58btc --------------------------------------------------------------
def test_base58_roundtrip_and_prefix():
    # multicodec ed25519-pub Präfix + 32 Byte
    raw = bytes([0xED, 0x01]) + b"\x11" * 32
    enc = b58encode(raw)
    assert isinstance(enc, str)
    assert b58decode(enc) == raw


def test_base58_leading_zero_and_empty():
    assert b58encode(b"\x00\x00\x05") == "11" + b58encode(b"\x05")
    assert b58encode(b"") == ""
    assert b58decode("") == b""
    assert b58decode("11") == b"\x00\x00"


def test_base58_invalid_char():
    with pytest.raises(ValueError):
        b58decode("0OIl")  # nicht im Alphabet
