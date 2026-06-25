# -*- coding: utf-8 -*-
"""Ed25519-Schlüsselobjekte – drop-in-Teilmenge der ``python-ecdsa``-API.

Dieses Modul stellt genau die ``SigningKey``/``VerifyingKey``-Operationen
bereit, die ``jose`` und ``keys`` zuvor aus dem externen Paket ``ecdsa``
bezogen haben – jetzt jedoch ohne externe Abhängigkeit, gestützt auf die
RFC-8032-Primitive in :mod:`sdata.did.ed25519`.

.. warning::
   Die zugrunde liegende Ed25519-Implementierung ist **pure Python und nicht
   constant-time** (siehe Sicherheitshinweis in :mod:`sdata.did.ed25519`).
   Sie verhält sich darin wie ``python-ecdsa`` (ebenfalls pure Python, nicht
   seitenkanalresistent). Für Umgebungen mit Seitenkanal-Anforderungen ein
   libsodium-basiertes Backend (PyNaCl) oder ``cryptography`` verwenden.

Korrektheit wird gegen die offiziellen RFC-8032-Testvektoren abgesichert
(siehe ``tests/test_eddsa.py``).
"""
from __future__ import annotations

import os
from typing import Optional

from . import ed25519 as _ed

__all__ = ["Ed25519", "SigningKey", "VerifyingKey", "BadSignatureError"]


class BadSignatureError(Exception):
    """Signatur konnte nicht verifiziert werden (API-kompatibel zu ``ecdsa``)."""


class _Ed25519Curve:
    """Sentinel für den Kurvenparameter ``curve=Ed25519`` (API-Kompatibilität)."""

    name = "Ed25519"

    def __repr__(self) -> str:  # pragma: no cover - rein kosmetisch
        return "Ed25519"


#: Kurven-Sentinel, analog zu ``ecdsa.Ed25519``.
Ed25519 = _Ed25519Curve()


def _check_len(raw: bytes, expected: int, what: str) -> bytes:
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != expected:
        raise ValueError("{} muss {} Bytes sein".format(what, expected))
    return bytes(raw)


class VerifyingKey:
    """Öffentlicher Ed25519-Schlüssel (32-Byte, komprimiert)."""

    def __init__(self, pub: bytes):
        self._pub = pub

    @classmethod
    def from_string(cls, raw: bytes, curve=Ed25519) -> "VerifyingKey":
        """Erzeuge einen ``VerifyingKey`` aus 32 rohen Public-Key-Bytes."""
        return cls(_check_len(raw, 32, "Public Key"))

    def to_string(self) -> bytes:
        """Liefere den rohen 32-Byte Public Key."""
        return self._pub

    def verify(self, signature: bytes, data: bytes) -> bool:
        """Verifiziere ``signature`` über ``data``.

        Returns:
            ``True`` bei gültiger Signatur.
        Raises:
            BadSignatureError: wenn die Signatur ungültig ist.
        """
        if not _ed.verify(bytes(signature), bytes(data), self._pub):
            raise BadSignatureError("Signatur ungültig")
        return True


class SigningKey:
    """Privater Ed25519-Schlüssel (32-Byte-Seed)."""

    def __init__(self, seed: bytes):
        self._seed = seed
        self._pub = _ed.publickey(seed)

    @classmethod
    def generate(cls, curve=Ed25519) -> "SigningKey":
        """Erzeuge einen frischen Schlüssel aus 32 zufälligen Bytes (``os.urandom``)."""
        return cls(os.urandom(32))

    @classmethod
    def from_string(cls, raw: bytes, curve=Ed25519) -> "SigningKey":
        """Erzeuge einen ``SigningKey`` aus einem 32-Byte-Seed."""
        return cls(_check_len(raw, 32, "Seed"))

    def to_string(self) -> bytes:
        """Liefere den rohen 32-Byte-Seed (geheim halten!)."""
        return self._seed

    def get_verifying_key(self) -> VerifyingKey:
        """Leite den zugehörigen öffentlichen Schlüssel ab."""
        return VerifyingKey(self._pub)

    def sign(self, data: bytes) -> bytes:
        """Signiere ``data`` und gib die 64-Byte-Signatur zurück."""
        return _ed.sign(bytes(data), self._seed, self._pub)
