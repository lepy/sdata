#!/usr/bin/env python3
__version__ = "0.2.0"

import os
from random import SystemRandom
from hashlib import sha256
import json
import base64

"""
# https://github.com/soreatu/Cryptography/blob/f79810f0477b6474dd6b9cd865ba0a2e6eb2ebf8/ElGamalSignatrue.py

Parameters chosen from RFC3526 (https://www.ietf.org/rfc/rfc3526.txt

2048-bit MODP Group

This group is assigned id 14.

This prime is: 2^2048 - 2^1984 - 1 + 2^64 * { [2^1918 pi] + 124476 }

Its hexadecimal value is:

    FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
    29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
    EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
    E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
    EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE45B3D
    C2007CB8 A163BF05 98DA4836 1C55D39A 69163FA8 FD24CF5F
    83655D23 DCA3AD96 1C62F356 208552BB 9ED52907 7096966D
    670C354E 4ABC9804 F1746C08 CA18217C 32905E46 2E36CE3B
    E39E772C 180E8603 9B2783A2 EC07A28F B5C55DF0 6F4C52C9
    DE2BCBF6 95581718 3995497C EA956AE5 15D22618 98FA0510
    15728E5A 8AACAA68 FFFFFFFF FFFFFFFF

The generator is: 2.
"""
import base64
import os
import sys
import math


def bytes2int(raw_bytes: bytes) -> int:
    r"""Converts a list of bytes or an 8-bit string to an integer.

    When using unicode strings, encode it to some encoding like UTF8 first.

    >>> (((128 * 256) + 64) * 256) + 15
    8405007
    >>> bytes2int(b'\x80@\x0f')
    8405007

    """
    return int.from_bytes(raw_bytes, "big", signed=False)


def int2bytes(number: int, fill_size: int = 0) -> bytes:
    """
    Convert an unsigned integer to bytes (big-endian)::

    Does not preserve leading zeros if you don't specify a fill size.

    :param number:
        Integer value
    :param fill_size:
        If the optional fill size is given the length of the resulting
        byte string is expected to be the fill size and will be padded
        with prefix zero bytes to satisfy that length.
    :returns:
        Raw bytes (base-256 representation).
    :raises:
        ``OverflowError`` when fill_size is given and the number takes up more
        bytes than fit into the block. This requires the ``overflow``
        argument to this function to be set to ``False`` otherwise, no
        error will be raised.
    """

    if number < 0:
        raise ValueError("Number must be an unsigned integer: %d" % number)

    bytes_required = max(1, math.ceil(number.bit_length() / 8))

    if fill_size > 0:
        return number.to_bytes(fill_size, "big")

    return number.to_bytes(bytes_required, "big")


class Key:
    def __init__(self, *args, **kwargs):
        if kwargs.get("p") is not None:
            self.p = kwargs.get("p")
        else:
            self.p = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF
        self.g = 2

    @classmethod
    def from_bytes(cls, bytes):
        key = cls(0, 0)
        key.load_pkcs1(bytes)
        return key

    def save_pkcs1(self):
        raise NotImplementedError

    def load_pkcs1(self):
        raise NotImplementedError


class PublicKey(Key):
    """Represents a private RSA key."""

    def __init__(self, pub, *args, **kwargs):
        Key.__init__(self, *args, **kwargs)
        self.pub = pub

    def __str__(self):
        return f"PublicKey({self.pub})"

    __repr__ = __str__

    def save_pkcs1(self):
        """Saves the key in PKCS#1 DER or PEM format.

        :param format: the format to save; 'PEM' or 'DER'
        :type format: str
        :returns: the DER- or PEM-encoded key.
        :rtype: bytes"""

        n = base64.b64encode(f"{self.pub}".encode("ascii")).decode("ascii")
        s = ''.join(["-----BEGIN PUBLIC KEY-----\n",
                     "{0}\n".format(n),
                     "-----END PUBLIC KEY-----\n"])
        return s.encode("ascii")

    def load_pkcs1(self, key, *args, **kwargs):
        """Loads a key in PKCS#1 DER or PEM format.

        :param keyfile: contents of a DER- or PEM-encoded file that contains
            the key.
        :type keyfile: bytes
        :param format: the format of the file to load; 'PEM' or 'DER'
        :type format: str

        :return: the loaded key
        """
        x = key.decode("ascii").replace("-----BEGIN PUBLIC KEY-----\n", "").replace(
            "\n-----END PUBLIC KEY-----\n", "")
        self.pub = int(base64.b64decode(x).decode("ascii"))
        # self.pub = bytes2int(base64.b64decode(x))
        return self.pub


class PrivateKey(Key):
    """Represents a private RSA key."""

    def __init__(self, pub, priv, *args, **kwargs):
        Key.__init__(self, *args, **kwargs)
        self.pub = pub
        self.priv = priv

    def __str__(self):
        return f"PrivateKey({self.pub}|{self.priv})"

    __repr__ = __str__

    def save_pkcs1(self):
        """Saves the key in PKCS#1 DER or PEM format.

        :param format: the format to save; 'PEM' or 'DER'
        :type format: str
        :returns: the DER- or PEM-encoded key.
        :rtype: bytes"""

        n = base64.b64encode(f"{self.pub}|{self.priv}".encode("ascii")).decode("ascii")
        s = ''.join(["-----BEGIN PRIVATE KEY-----\n",
                     "{0}\n".format(n),
                     "-----END PRIVATE KEY-----\n"])
        return s.encode("ascii")

    def load_pkcs1(self, key, *args, **kwargs):
        """Loads a key in PKCS#1 DER or PEM format.

        :param keyfile: contents of a DER- or PEM-encoded file that contains
            the key.
        :type keyfile: bytes
        :param format: the format of the file to load; 'PEM' or 'DER'
        :type format: str

        :return: the loaded key
        """
        x = key.decode("ascii").replace("-----BEGIN PRIVATE KEY-----\n", "").replace(
            "\n-----END PRIVATE KEY-----\n", "")
        a = base64.b64decode(x).decode("ascii").split("|")
        self.pub = int(a[0])
        self.priv = int(a[1])
        return self.pub, self.priv


class Signature(Key):
    """Represents a signature."""

    def __init__(self, r, s, *args, **kwargs):
        Key.__init__(self, *args, **kwargs)
        self.r = r
        self.s = s

    def __str__(self):
        return f"Signature({self.r}|{self.s})"

    __repr__ = __str__

    def save_pkcs1(self):
        """Saves the key in PKCS#1 DER or PEM format.

        :param format: the format to save; 'PEM' or 'DER'
        :type format: str
        :returns: the DER- or PEM-encoded key.
        :rtype: bytes"""

        n = base64.b64encode(f"{self.r}|{self.s}".encode("ascii")).decode("ascii")
        s = ''.join(["-----BEGIN SIGNATURE KEY-----\n",
                     "{0}\n".format(n),
                     "-----END SIGNATURE KEY-----\n"])
        return s.encode("ascii")

    def load_pkcs1(self, key, *args, **kwargs):
        """Loads a key in PKCS#1 DER or PEM format.

        :param keyfile: contents of a DER- or PEM-encoded file that contains
            the key.
        :type keyfile: bytes
        :param format: the format of the file to load; 'PEM' or 'DER'
        :type format: str

        :return: the loaded key
        """
        x = key.decode("ascii").replace("-----BEGIN SIGNATURE KEY-----\n", "").replace(
            "\n-----END SIGNATURE KEY-----\n", "")
        a = base64.b64decode(x).decode("ascii").split("|")
        self.r = int(a[0])
        self.s = int(a[1])
        return self.r, self.s


class SignedMessage:
    MESSAGE = "message"
    SIGNATURE = "signature"

    def __init__(self, message=None, privkey=None):
        # self._license_data = kwargs.get("license_data")
        self._data = {}
        self._data[self.MESSAGE] = message or ""
        self._data[self.SIGNATURE] = None
        if privkey is not None:
            self.sign(privkey)

    def _get_message(self):
        return self._data[self.MESSAGE]

    def _set_message(self, value):
        assert isinstance(value, str)
        self._data[self.MESSAGE] = value

    message = property(fget=_get_message, fset=_set_message, doc="message utf8 encoded (str)")

    @property
    def signature(self):
        return self._data.get(self.SIGNATURE)

    @property
    def data(self):
        return self._data

    def __str__(self):
        return f"{self.data}"

    def __repr__(self):
        return f"{self.__class__.__name__}({len(self.data[self.MESSAGE])})"

    def dumps(self):
        return json.dumps(self.data)
        # return json.dumps(self.data, skipkeys=False, ensure_ascii=True, check_circular=True,
        #                   allow_nan=True, cls=None, indent=False, separators=None,
        #                   default=None, sort_keys=False)

    def loads(self, s):
        """update data from json string

        """
        d = json.loads(s)
        self._data.update(d)

    @classmethod
    def from_str(cls, s):
        sm = cls()
        sm.loads(s)
        return sm

    def get_signature_bytes(self, privkey):
        signature = sign(self._data[self.MESSAGE].encode("utf-8"), privkey)
        return signature.save_pkcs1()

    def sign(self, privkey):
        signature_bytes = self.get_signature_bytes(privkey)
        # license_bytes = self.get_license_bytes()
        # self.data[self.LICENSE_KEY] = license_bytes
        self.data[self.SIGNATURE] = signature_bytes.decode("utf-8")

    def verify(self, pubkey):
        if self.data[self.SIGNATURE] is None:
            return False
        signature = Signature.from_bytes(self.data[self.SIGNATURE].encode("utf-8"))
        license_bytes = self.data[self.MESSAGE].encode("utf-8")
        is_valid = verify(license_bytes, signature, pubkey)
        return is_valid


def newkeys(p=None, **kwargs):
    """Generates public and private keys, and returns them as (pub, priv).

    The public key is also known as the 'encryption key', and is a
    :py:class:`rsa.PublicKey` object. The private key is also known as the
    'decryption key' and is a :py:class:`rsa.PrivateKey` object.
    """

    if p is None:
        p = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF

    g = 2
    random_ = SystemRandom()
    x = random_.randint(1, p - 2)
    y = pow(g, x, p)

    pubkey = PublicKey(y, p=p)
    privkey = PrivateKey(y, x, p=p)

    return (pubkey, privkey)


def GCD(x, y):
    """GCD(x:long, y:long): long
    Return the GCD of x and y.
    """
    x = abs(x);
    y = abs(y)
    while x > 0:
        x, y = y % x, x
    return y


def inverse(u, v):
    """inverse(u:long, v:long):long
    Return the inverse of u mod v.
    """
    u3, v3 = int(u), int(v)
    u1, v1 = 1, 0
    while v3 > 0:
        q = divmod(u3, v3)[0]
        u1, v1 = v1, u1 - v1 * q
        u3, v3 = v3, u3 - v3 * q
    while u1 < 0:
        u1 = u1 + v
    return u1


def sign(message: bytes, privkey: PrivateKey, *args, **kwargs) -> bytes:
    """Signs the message with the private key.

    Hashes the message, then signs the hash with the given key. This is known
    as a "detached signature", because the message itself isn't altered.

    :param message: the message to sign. Can be an 8-bit string or a file-like
        object. If ``message`` has a ``read()`` method, it is assumed to be a
        file-like object.
    :param priv_key: the :py:class:`rsa.PrivateKey` to sign with
    :param hash_method: the hash method used on the message. default 'SHA-256' (planned to implement  'MD5', 'SHA-1',
        'SHA-224', 'SHA-256', 'SHA-384' or 'SHA-512'.(
    :return: a message signature block.
    :raise OverflowError: if the private key is too small to contain the
        requested hash.

    """
    # def sign(m, params, prikey):
    p = privkey.p
    g = privkey.g
    x = privkey.priv
    random_ = SystemRandom()
    k = random_.randint(1, p - 1)

    while GCD(k, p - 1) != 1:
        k = random_.randint(1, p - 1)

    Hm = int.from_bytes(sha256(message).digest(), 'big')

    r = pow(g, k, p)
    s = (inverse(k, p - 1) * (Hm - x * r)) % (p - 1)
    sig = Signature(r, s)
    return sig


def verify(message: bytes, signature: Signature, pubkey: PublicKey) -> str:
    """Verifies that the signature matches the message.

    The hash method is detected automatically from the signature.

    :param message: the signed message. Can be an 8-bit string or a file-like
        object. If ``message`` has a ``read()`` method, it is assumed to be a
        file-like object.
    :param signature: the signature block, as created with :py:func:`rsa.sign`.
    :param pub_key: the :py:class:`rsa.PublicKey` of the person signing the message.
    :raise VerificationError: when the signature doesn't match the message.
    :returns: the name of the used hash.

    """

    r = signature.r
    s = signature.s
    p = pubkey.p
    g = pubkey.g
    y = pubkey.pub

    if not (0 < r < p) or not (0 < s < p):
        return False

    Hm = int.from_bytes(sha256(message).digest(), 'big')
    l = pow(g, Hm, p)
    r = (pow(y, r, p) * pow(r, s, p)) % p

    return l == r


if __name__ == '__main__':
    (pubkey, privkey) = newkeys()
    print(pubkey)
    s = pubkey.save_pkcs1()
    print(s)
    k = pubkey.load_pkcs1(s)
    print(k)

    print(privkey)
    print(privkey.save_pkcs1())

    s = privkey.save_pkcs1()
    # k = privkey.load_pkcs1(s)
    # print(k)
