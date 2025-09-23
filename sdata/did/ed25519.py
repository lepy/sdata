# ed25519_typed.py
"""
Lern-/Test-Implementierung von Ed25519 (pure), nicht constant-time.
Verwendet:
- Point: typing.NamedTuple (x, y)
- KeyPair: @dataclass (sk, pk)
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import NamedTuple

# --- Konstanten ---
b = 256
q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493  # Gruppenordnung

class Point(NamedTuple):
    x: int
    y: int

@dataclass(frozen=True)
class KeyPair:
    sk: bytes  # 32-Byte-Seed
    pk: bytes  # 32-Byte Public Key (compressed)

# --- Basisfunktionen ---
def H(m: bytes) -> bytes:
    """SHA-512-Hash m -> 64 Bytes."""
    return hashlib.sha512(m).digest()

def inv(x: int) -> int:
    """Multiplikatives Inverses in F_q (q prim)."""
    return pow(x, q - 2, q)

# Edwards-d und sqrt(-1)
d = (-121665 * inv(121666)) % q
I = pow(2, (q - 1) // 4, q)

def xrecover(y: int) -> int:
    """Rekonstruiere x aus y gemäß Edwards-Kurvengleichung; even x."""
    xx = (y*y - 1) * inv(d*y*y + 1) % q
    x = pow(xx, (q + 3)//8, q)
    if (x*x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x

By = (4 * inv(5)) % q
Bx = xrecover(By)
B = Point(Bx, By)
O = Point(0, 1)  # neutrales Element

def edwards(P: Point, Q: Point) -> Point:
    """Edwards-Punktaddition."""
    x1, y1 = P
    x2, y2 = Q
    den_x = inv(1 + (d * x1 * x2 * y1 * y2) % q)
    x3 = (x1*y2 + x2*y1) * den_x % q
    den_y = inv(1 - (d * x1 * x2 * y1 * y2) % q)
    y3 = (y1*y2 + x1*x2) * den_y % q
    return Point(x3, y3)

def scalarmult(P: Point, e: int) -> Point:
    """Double-and-Add, iterativ (nicht constant-time)."""
    Q = O
    N = P
    k = e
    while k > 0:
        if k & 1:
            Q = edwards(Q, N)
        N = edwards(N, N)
        k >>= 1
    return Q

# --- Kodierung ---
def encodeint(y: int) -> bytes:
    """Little-Endian-Encoding von 256 Bit."""
    bits = [(y >> i) & 1 for i in range(b)]
    return bytes(sum(bits[8*i + j] << j for j in range(8)) for i in range(b//8))

def bit(h: bytes, i: int) -> int:
    """Lese Bit i aus Bytes (LE pro Byte)."""
    return (h[i//8] >> (i % 8)) & 1

def encodepoint(P: Point) -> bytes:
    """Komprimierte Punktdarstellung: y (255 Bit) || sign(x) (1 Bit)."""
    x, y = P
    bits = [(y >> i) & 1 for i in range(b-1)] + [x & 1]
    return bytes(sum(bits[8*i + j] << j for j in range(8)) for i in range(b//8))

def isoncurve(P: Point) -> bool:
    """Prüfe Kurvengleichung -x^2 + y^2 = 1 + d x^2 y^2 (mod q)."""
    x, y = P
    return (-x*x + y*y - 1 - d*x*x*y*y) % q == 0

def decodeint(s: bytes) -> int:
    """Little-Endian-Integer aus 32 Bytes (256 Bit)."""
    if len(s) != 32:
        raise ValueError("Integer-Kodierung muss 32 Bytes haben")
    return sum(2**i * bit(s, i) for i in range(b))

def decodepoint(s: bytes) -> Point:
    """Dekodiere komprimierten Punkt und prüfe Kurvenzugehörigkeit."""
    if len(s) != 32:
        raise ValueError("Punktkodierung muss 32 Bytes haben")
    y = sum(2**i * bit(s, i) for i in range(b-1))
    x = xrecover(y)
    if (x & 1) != bit(s, b-1):
        x = q - x
    P = Point(x, y)
    if not isoncurve(P):
        raise ValueError("Punkt liegt nicht auf der Kurve")
    return P

# --- Ed25519 API ---
def publickey(sk: bytes) -> bytes:
    """
    Ableitung des Public Keys aus 32-Byte-Seed.
    Clamping: Bits 0..2 = 0, Bit 254 = 1, Bit 255 = 0.
    """
    if len(sk) != 32:
        raise ValueError("sk muss 32 Bytes (Seed) sein")
    h = H(sk)
    a = 2**(b-2) + sum(2**i * bit(h, i) for i in range(3, b-2))
    A = scalarmult(B, a)
    return encodepoint(A)

def Hint(m: bytes) -> int:
    """SHA-512(m) als 512-Bit little-endian Integer."""
    h = H(m)
    return sum(2**i * bit(h, i) for i in range(2*b))

def sign(m: bytes, sk: bytes, pk: bytes) -> bytes:
    """
    Signiere Nachricht m mit Seed sk und zugehörigem pk.
    Ergebnis: 64 Byte = R(32) || S(32).
    """
    if len(sk) != 32 or len(pk) != 32:
        raise ValueError("sk/pk müssen 32 Bytes sein")
    h = H(sk)
    a = 2**(b-2) + sum(2**i * bit(h, i) for i in range(3, b-2))
    inter = bytes(h[b//8 : b//4])          # h[32:64]
    r = Hint(inter + m) % l
    R = scalarmult(B, r)
    Rcomp = encodepoint(R)
    hram = Hint(Rcomp + pk + m) % l
    S = (r + hram * a) % l
    return Rcomp + encodeint(S)

def verify(sig: bytes, m: bytes, pk: bytes) -> bool:
    """
    Verifiziere Signatur (R||S) über Nachricht m mit Public Key pk.
    Zusätzliche Checks: Längen, S < l.
    """
    if len(sig) != 64 or len(pk) != 32:
        return False
    try:
        R = decodepoint(sig[:32])
        A = decodepoint(pk)
        S = decodeint(sig[32:])
    except Exception:
        return False
    if S >= l:
        return False
    hram = Hint(encodepoint(R) + pk + m) % l
    # Prüfe B*S == R + A*hram
    left = scalarmult(B, S)
    right = edwards(R, scalarmult(A, hram))
    return left == right

def keypair_from_seed(seed32: bytes) -> KeyPair:
    """Erzeuge KeyPair aus 32-Byte-Seed."""
    pk = publickey(seed32)
    return KeyPair(sk=seed32, pk=pk)

# --- Demo & Testvektor ---
if __name__ == "__main__":
    import os

    # Demo
    kp = keypair_from_seed(os.urandom(32))
    msg = b"Hallo, DIDComm!"
    sig = sign(msg, kp.sk, kp.pk)
    print("Sig OK?:", verify(sig, msg, kp.pk))

    # RFC 8032 Testvektor (leere Nachricht)
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
    kp_tv = keypair_from_seed(sk_tv)
    print("RFC PK OK:", kp_tv.pk == pk_tv)
    print("RFC SIG OK:", verify(sig_tv, b"", kp_tv.pk))
