# -*- coding: utf-8 -*-
"""base58btc-Kodierung (Bitcoin-Alphabet) – reine Standardbibliothek.

Ersetzt die externe ``base58``-Abhängigkeit im ``did``-Subpackage. Die
Funktionen sind bewusst klein und an die multibase-/``did:key``-Nutzung
angepasst (führende Nullbytes bleiben als ``1`` erhalten).

Referenz: https://datatracker.ietf.org/doc/html/draft-msporny-base58
"""
from __future__ import annotations

__all__ = ["b58encode", "b58decode"]

# Bitcoin-/IPFS-Alphabet (ohne 0, O, I, l)
_B58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {ch: i for i, ch in enumerate(_B58_ALPHABET)}


def b58encode(b: bytes) -> str:
    """Kodiere Bytes als base58btc (führende Nullbytes bleiben als ``1`` erhalten)."""
    n = int.from_bytes(b, "big", signed=False)
    out = bytearray()
    while n > 0:
        n, r = divmod(n, 58)
        out.append(_B58_ALPHABET[r])
    pad = 0
    for byte in b:
        if byte == 0:
            pad += 1
        else:
            break
    return ("1" * pad) + out[::-1].decode()


def b58decode(s: str) -> bytes:
    """Dekodiere einen base58btc-String zurück zu Bytes.

    Raises:
        ValueError: bei Zeichen ausserhalb des base58-Alphabets.
    """
    n = 0
    for ch in s.encode():
        try:
            n = n * 58 + _B58_INDEX[ch]
        except KeyError:
            raise ValueError("ungültiges base58-Zeichen: {!r}".format(chr(ch)))
    pad = len(s) - len(s.lstrip("1"))
    full = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * pad + full
