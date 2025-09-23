# ed25519_minimal.py
"""
Minimal-Implementierung von Ed25519 (reine Ed25519, nicht Ed25519ph),
nur für Lern- und Testzwecke. Nicht constant-time, nicht für Produktion.

Enthält:
- Schlüsselableitung aus 32-Byte-Seed (sk) -> publickey(sk)
- Signatur: signature(m, sk, pk)
- Verifikation: checkvalid(sig, m, pk) -> bool

Wichtige Hinweise:
- Diese Implementierung ist nicht constant-time und schützt nicht gegen
  Seitenkanäle. Für produktiven Einsatz NaCl/libsodium oder pynacl nutzen.
- Verifikation prüft S < l (Vermeidung einfacher Malleability).
"""

import hashlib
from typing import Tuple, List

b = 256
q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493  # Gruppenordnung

def H(m: bytes) -> bytes:
    """SHA-512-Hash als Bytes."""
    return hashlib.sha512(m).digest()

def inv(x: int) -> int:
    """Multiplikatives Inverses von x modulo q (Fermat)."""
    return pow(x, q - 2, q)

# Edwards-d-Konstante für Curve25519 in Edwards-Form
d = (-121665 * inv(121666)) % q

# sqrt(-1) mod q
I = pow(2, (q - 1) // 4, q)

def xrecover(y: int) -> int:
    """Aus y die x-Koordinate rekonstruieren (even/odd-Kanonisierung)."""
    xx = (y*y - 1) * inv(d*y*y + 1) % q
    x = pow(xx, (q + 3)//8, q)
    if (x*x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x

By = (4 * inv(5)) % q
Bx = xrecover(By)
B = [Bx, By]  # Basis-Punkt

def edwards(P: List[int], Q: List[int]) -> List[int]:
    """Edwards-Punktaddition."""
    x1, y1 = P
    x2, y2 = Q
    den = inv(1 + d*x1*x2*y1*y2 % q)
    x3 = (x1*y2 + x2*y1) * den % q
    den = inv(1 - d*x1*x2*y1*y2 % q)
    y3 = (y1*y2 + x1*x2) * den % q
    return [x3, y3]

def scalarmult(P: List[int], e: int) -> List[int]:
    """Skalarmultiplikation via Double-and-Add (iterativ)."""
    Q = [0, 1]          # Neutral-Element
    N = P[:]
    k = e
    while k > 0:
        if k & 1:
            Q = edwards(Q, N)
        N = edwards(N, N)
        k >>= 1
    return Q

def encodeint(y: int) -> bytes:
    """Little-Endian-Encoding von 256 Bit."""
    bits = [(y >> i) & 1 for i in range(b)]
    return bytes(sum(bits[8*i + j] << j for j in range(8)) for i in range(b//8))

def encodepoint(P: List[int]) -> bytes:
    """Komprimierte Punktdarstellung (y || sign(x))."""
    x, y = P
    bits = [(y >> i) & 1 for i in range(b-1)] + [x & 1]
    return bytes(sum(bits[8*i + j] << j for j in range(8)) for i in range(b//8))

def bit(h: bytes, i: int) -> int:
    """Lese Bit i aus Bytefolge (Little Endian pro Byte)."""
    return (h[i//8] >> (i % 8)) & 1

def publickey(sk: bytes) -> bytes:
    """
    Ableitung des Public Keys aus 32-Byte-Seed sk.
    Ed25519-„Clamping“: Bits 0..2 = 0, Bit 254 = 1, Bit 255 = 0.
    """
    h = H(sk)
    a = 2**(b-2) + sum(2**i * bit(h, i) for i in range(3, b-2))
    A = scalarmult(B, a)
    return encodepoint(A)

def Hint(m: bytes) -> int:
    """SHA-512(m) als 512-Bit little-endian Integer."""
    h = H(m)
    return sum(2**i * bit(h, i) for i in range(2*b))

def signature(m: bytes, sk: bytes, pk: bytes) -> bytes:
    """
    Signiere Nachricht m mit 32-Byte-Seed sk und passendem pk.
    Gibt 64-Byte-Signatur R(32) || S(32) zurück.
    """
    h = H(sk)
    a = 2**(b-2) + sum(2**i * bit(h, i) for i in range(3, b-2))
    inter = bytes(h[b//8 : b//4])          # h[32:64], korrekt für r
    r = Hint(inter + m) % l
    R = scalarmult(B, r)
    Rcompressed = encodepoint(R)
    hram = Hint(Rcompressed + pk + m) % l
    S = (r + hram * a) % l
    return Rcompressed + encodeint(S)

def isoncurve(P: List[int]) -> bool:
    """Prüfe, ob Punkt auf der Edwards-Kurve liegt."""
    x, y = P
    return (-x*x + y*y - 1 - d*x*x*y*y) % q == 0

def decodeint(s: bytes) -> int:
    """Little-Endian-Integer aus 32 Bytes (256 Bit)."""
    return sum(2**i * bit(s, i) for i in range(0, b))

def decodepoint(s: bytes) -> List[int]:
    """Dekodiere komprimierten Punkt und prüfe Kurvenzugehörigkeit."""
    if len(s) != 32:
        raise ValueError("Punktkodierung muss 32 Bytes haben")
    y = sum(2**i * bit(s, i) for i in range(0, b-1))
    x = xrecover(y)
    if (x & 1) != bit(s, b-1):
        x = q - x
    P = [x, y]
    if not isoncurve(P):
        raise ValueError("Punkt liegt nicht auf der Kurve")
    return P

def checkvalid(s: bytes, m: bytes, pk: bytes) -> bool:
    """
    Verifiziere Signatur s über Nachricht m mit Public Key pk.

    Rückgabe:
        True bei gültig, sonst False.

    Zusätzliche Checks:
    - Längenprüfung (64/32 Bytes)
    - S < l (Vermeidung einfacher Malleability)
    """
    if len(s) != b // 4:
        return False
    if len(pk) != b // 8:
        return False
    try:
        R = decodepoint(s[0 : b//8])      # 32 Bytes
        A = decodepoint(pk)
    except Exception:
        return False
    S = decodeint(s[b//8 : b//4])
    if S >= l:
        return False
    hram = Hint(encodepoint(R) + pk + m) % l
    # B*S == R + A*hram ?
    left = scalarmult(B, S)
    right = edwards(R, scalarmult(A, hram))
    return left == right

if __name__ == "__main__":
    import os, binascii

    # Rauchtest: Signieren & Verifizieren
    sk = os.urandom(32)
    pk = publickey(sk)
    message = b"Hallo, DIDComm!"
    sig = signature(message, sk, pk)
    print("Signatur:", sig.hex())
    print("Gueltig:", checkvalid(sig, message, pk))

    # RFC 8032 Testvektor (leere Nachricht)
    # Seed
    sk_tv = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc4"
        "4449c5697b326919703bac031cae7f60"
    )
    pk_tv = bytes.fromhex(
        "d75a980182b10ab7d54bfed3c964073a"
        "0ee172f3daa62325af021a68f707511a"
    )
    sig_tv = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a"
        "84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46b"
        "d25bf5f0595bbe24655141438e7a100b"
    )
    pk_calc = publickey(sk_tv)
    ok_pk = (pk_calc == pk_tv)
    ok_sig = checkvalid(sig_tv, b"", pk_tv)
    print("RFC8032 PK OK:", ok_pk)
    print("RFC8032 SIG OK:", ok_sig)
