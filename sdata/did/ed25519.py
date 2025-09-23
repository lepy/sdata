import hashlib

b = 256
q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493

def H(m):
  return hashlib.sha512(m).digest()

def expmod(b,e,m):
  if e == 0: return 1
  t = expmod(b,e//2,m)**2 % m
  if e & 1: t = (t*b) % m
  return t

def inv(x):
  return expmod(x,q-2,q)

d = -121665 * inv(121666)
I = expmod(2,(q-1)//4,q)

def xrecover(y):
  xx = (y*y-1) * inv(d*y*y+1)
  x = expmod(xx,(q+3)//8,q)
  if (x*x - xx) % q != 0: x = (x*I) % q
  if x % 2 != 0: x = q-x
  return x

By = 4 * inv(5)
Bx = xrecover(By)
B = [Bx % q,By % q]

def edwards(P,Q):
  x1 = P[0]
  y1 = P[1]
  x2 = Q[0]
  y2 = Q[1]
  x3 = (x1*y2+x2*y1) * inv(1+d*x1*x2*y1*y2)
  y3 = (y1*y2+x1*x2) * inv(1-d*x1*x2*y1*y2)
  return [x3 % q,y3 % q]

def scalarmult(P,e):
  if e == 0: return [0,1]
  Q = scalarmult(P,e//2)
  Q = edwards(Q,Q)
  if e & 1: Q = edwards(Q,P)
  return Q

def encodeint(y):
  bits = [(y >> i) & 1 for i in range(b)]
  return b''.join([bytes([(bits[8*i+0]) + (bits[8*i+1]<<1) + (bits[8*i+2]<<2) + (bits[8*i+3]<<3) + (bits[8*i+4]<<4) + (bits[8*i+5]<<5) + (bits[8*i+6]<<6) + (bits[8*i+7]<<7)]) for i in range(b//8)])

def encodepoint(P):
  x = P[0]
  y = P[1]
  bits = [(y >> i) & 1 for i in range(b-1)] + [x & 1]
  return b''.join([bytes([(bits[8*i+0]) + (bits[8*i+1]<<1) + (bits[8*i+2]<<2) + (bits[8*i+3]<<3) + (bits[8*i+4]<<4) + (bits[8*i+5]<<5) + (bits[8*i+6]<<6) + (bits[8*i+7]<<7)]) for i in range(b//8)])

def bit(h,i):
  return (h[i//8] >> (i%8)) & 1

def publickey(sk):
  h = H(sk)
  a = 2**(b-2) + sum(2**i * bit(h,i) for i in range(3,b-2))
  A = scalarmult(B,a)
  return encodepoint(A)

def Hint(m):
  h = H(m)
  return sum(2**i * bit(h,i) for i in range(2*b))

def signature(m,sk,pk):
  h = H(sk)
  a = 2**(b-2) + sum(2**i * bit(h,i) for i in range(3,b-2))
  inter = bytes([h[j] for j in range(b//8, b//4)])  # KORREKTUR HIER: b//4 statt b
  r = Hint(inter + m)
  R = scalarmult(B,r)
  Rcompressed = encodepoint(R)
  h = Hint(Rcompressed + pk + m)
  S = r + h * a
  return Rcompressed + encodeint(S % l)

def isoncurve(P):
  x = P[0]
  y = P[1]
  return (-x*x + y*y - 1 - d*x*x*y*y) % q == 0

def decodeint(s):
  return sum(2**i * bit(s,i) for i in range(0,b))

def decodepoint(s):
  y = sum(2**i * bit(s,i) for i in range(0,b-1))
  x = xrecover(y)
  if x & 1 != bit(s,b-1): x = q-x
  P = [x,y]
  if not isoncurve(P): raise Exception("decoding point that is not on curve")
  return P

def checkvalid(s,m,pk):
  if len(s) != b//4: raise Exception("signature length is wrong")
  if len(pk) != b//8: raise Exception("public-key length is wrong")
  R = decodepoint(s[0:b//8])
  A = decodepoint(pk)
  S = decodeint(s[b//8:b//4])
  h = Hint(encodepoint(R) + pk + m)
  return scalarmult(B,S) == edwards(R,scalarmult(A,h))


if __name__ == '__main__':
    import os

    sk = os.urandom(32)  # Privater Schlüssel (Seed)
    pk = publickey(sk)  # Öffentlicher Schlüssel
    message = b"Hallo, DIDComm!"

    sig = signature(message, sk, pk)
    print("Signatur:", sig.hex())

    # Verifizieren
    try:
        checkvalid(sig, message, pk)
        print("Signatur gültig!")
    except Exception as e:
        print("Signatur ungültig:", e)