import random
import math
import hashlib
import base64

def is_prime(n, k=128):
    """Miller-Rabin primality test for n with k iterations."""
    if n <= 1 or n == 4:
        return False
    if n <= 3:
        return True
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def generate_prime(bits):
    """Generate a prime of approximately 'bits' length."""
    while True:
        p = random.getrandbits(bits)
        if p % 2 == 0:
            p += 1
        if is_prime(p):
            return p

def mod_inverse(a, m):
    """Extended Euclidean algorithm for modular inverse."""
    m0, x0, x1 = m, 0, 1
    if m == 1:
        return 0
    while a > 1:
        q = a // m
        m, a = a % m, m
        x0, x1 = x1 - q * x0, x0
    if x1 < 0:
        x1 += m0
    return x1

def generate_keys(bits=2048):
    """Generate RSA key pair: public and private as dicts with components."""
    half_bits = bits // 2
    p = generate_prime(half_bits)
    q = generate_prime(half_bits)
    while abs(p - q) < (1 << (half_bits - 100)):
        q = generate_prime(half_bits)
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    while math.gcd(e, phi) != 1:
        e += 2
    d = mod_inverse(e, phi)
    dp = d % (p - 1)
    dq = d % (q - 1)
    iq = mod_inverse(q, p)
    public_key = {
        'e': e,
        'n': n
    }
    private_key = {
        'version': 0,
        'n': n,
        'e': e,
        'd': d,
        'p': p,
        'q': q,
        'dp': dp,
        'dq': dq,
        'iq': iq
    }
    return public_key, private_key

def hash_message(message):
    """SHA-256 hash of message as int."""
    h = hashlib.sha256(message.encode() if isinstance(message, str) else message).digest()
    return int.from_bytes(h, 'big')

def sign(message, private_key):
    """Sign hashed message with private key (uses d, n from dict)."""
    d = private_key['d']
    n = private_key['n']
    m = hash_message(message)
    return pow(m, d, n)

def verify(message, signature, public_key):
    """Verify signature with public key (e, n from dict)."""
    e = public_key['e']
    n = public_key['n']
    m = hash_message(message)
    return pow(signature, e, n) == m

def _encrypt(message, public_key):
    """Encrypt message (bytes) with public key (e, n from dict). Raw RSA; ensure len(message) < log2(n)/8 - 1."""
    e = public_key['e']
    n = public_key['n']
    if isinstance(message, str):
        message = message.encode('utf-8')
    m = int.from_bytes(message, 'big')
    if m >= n:
        raise ValueError("Message too long for key size")
    return pow(m, e, n)

def _decrypt(ciphertext, private_key):
    """Decrypt ciphertext (int) with private key (uses d, n from dict). Returns bytes."""
    d = private_key['d']
    n = private_key['n']
    m = pow(ciphertext, d, n)
    byte_len = (m.bit_length() + 7) // 8
    return m.to_bytes(byte_len, 'big')

def encrypt(message, public_key):
    chunk_size = (public_key['n'].bit_length() // 8) - 1
    chunks = [message[i:i+chunk_size] for i in range(0, len(message), chunk_size)]
    return [_encrypt(chunk, public_key) for chunk in chunks]

def decrypt(cipher_chunks, private_key):
    return b''.join(_decrypt(c, private_key) for c in cipher_chunks)

def export_key(key):
    """Export key dict to bytes: len(exp_bytes) (4B) + exp_bytes + mod_bytes. For public: exp=e, mod=n; for private: exp=d, mod=n (simplified)."""
    if 'e' in key:  # Public key
        exp = key['e']
        mod = key['n']
    elif 'd' in key:  # Private key (simplified, without full components)
        exp = key['d']
        mod = key['n']
    else:
        raise ValueError("Invalid key dict")
    exp_bytes = exp.to_bytes((exp.bit_length() + 7) // 8, 'big')
    mod_bytes = mod.to_bytes((mod.bit_length() + 7) // 8, 'big')
    len_exp = len(exp_bytes).to_bytes(4, 'big')
    return len_exp + exp_bytes + mod_bytes

def import_key(key_bytes, is_public=True):
    """Import key from bytes to dict: Parse len_exp (4B), exp_bytes, then mod_bytes. Returns {'e': exp, 'n': mod} if public, {'d': exp, 'n': mod} if private."""
    len_exp = int.from_bytes(key_bytes[:4], 'big')
    exp_bytes = key_bytes[4:4 + len_exp]
    mod_bytes = key_bytes[4 + len_exp:]
    exp = int.from_bytes(exp_bytes, 'big')
    mod = int.from_bytes(mod_bytes, 'big')
    if is_public:
        return {'e': exp, 'n': mod}
    else:
        return {'d': exp, 'n': mod}

def save_key_to_file(key, filename):
    """Save exported key bytes to file."""
    with open(filename, 'wb') as f:
        f.write(export_key(key))

def load_key_from_file(filename, is_public=True):
    """Load key bytes from file and import to dict."""
    with open(filename, 'rb') as f:
        return import_key(f.read(), is_public=is_public)

def encode_mpint(x):
    """Encode integer as SSH mpint: uint32 len + big-endian bytes (leading zero if MSB set)."""
    if x < 0:
        raise ValueError("Negative mpint not supported")
    if x == 0:
        return b'\x00\x00\x00\x00'
    b = x.to_bytes((x.bit_length() + 7) // 8, 'big')
    if b[0] >= 128:
        b = b'\x00' + b
    return len(b).to_bytes(4, 'big') + b

def export_to_ssh(public_key, comment=''):
    """Export public key dict to OpenSSH format: 'ssh-rsa base64_data [comment]'."""
    e = public_key['e']
    n = public_key['n']
    algo = b'ssh-rsa'
    algo_str = len(algo).to_bytes(4, 'big') + algo
    e_mp = encode_mpint(e)
    n_mp = encode_mpint(n)
    data = algo_str + e_mp + n_mp
    b64 = base64.b64encode(data).decode('ascii')
    return f"ssh-rsa {b64}" + (f" {comment}" if comment else "")

def decode_mpint(data, offset):
    """Decode SSH mpint from bytes at offset; returns (value, new_offset)."""
    length = int.from_bytes(data[offset:offset+4], 'big')
    offset += 4
    value = int.from_bytes(data[offset:offset+length], 'big')
    return value, offset + length

def import_from_ssh(ssh_string):
    """Import public key from OpenSSH format string; returns dict {'e': e, 'n': n}."""
    parts = ssh_string.split()
    if parts[0] != 'ssh-rsa':
        raise ValueError("Unsupported key type")
    data = base64.b64decode(parts[1])
    offset = 0
    algo_len = int.from_bytes(data[offset:offset+4], 'big')
    offset += 4
    algo = data[offset:offset+algo_len]
    if algo != b'ssh-rsa':
        raise ValueError("Unsupported algorithm")
    offset += algo_len
    e, offset = decode_mpint(data, offset)
    n, offset = decode_mpint(data, offset)
    return {'e': e, 'n': n}

# ASN.1/DER-Encoding-Funktionen für PEM-Export

def der_encode_length(length):
    """Encode DER length: short form if <128, else long."""
    if length < 128:
        return length.to_bytes(1, 'big')
    len_bytes = length.to_bytes((length.bit_length() + 7) // 8, 'big')
    return (0x80 | len(len_bytes)).to_bytes(1, 'big') + len_bytes

def der_encode_integer(i):
    """Encode positive INTEGER (for keys): tag 0x02, length, big-endian bytes with leading 0x00 if MSB set."""
    if i < 0:
        raise ValueError("Negative integers not supported for keys")
    if i == 0:
        return b'\x02\x01\x00'
    b = i.to_bytes((i.bit_length() + 7) // 8, 'big')
    if b[0] & 0x80:
        b = b'\x00' + b  # Ensure positive (no sign bit)
    return b'\x02' + der_encode_length(len(b)) + b

def der_encode_sequence(fields):
    """Encode SEQUENCE: tag 0x30, length, concatenated encoded fields."""
    content = b''.join(fields)
    return b'\x30' + der_encode_length(len(content)) + content

def export_private_to_pem(private_key):
    """Export private key dict to PEM format: ASN.1 DER encoded, then Base64."""
    fields = [
        der_encode_integer(private_key['version']),
        der_encode_integer(private_key['n']),
        der_encode_integer(private_key['e']),
        der_encode_integer(private_key['d']),
        der_encode_integer(private_key['p']),
        der_encode_integer(private_key['q']),
        der_encode_integer(private_key['dp']),
        der_encode_integer(private_key['dq']),
        der_encode_integer(private_key['iq'])
    ]
    der_bytes = der_encode_sequence(fields)
    b64 = base64.b64encode(der_bytes).decode('ascii')
    # Wrap Base64 to 64 chars per line
    wrapped = '\n'.join(b64[i:i+64] for i in range(0, len(b64), 64))
    return f"-----BEGIN RSA PRIVATE KEY-----\n{wrapped}\n-----END RSA PRIVATE KEY-----"

def export_public_to_pem(public_key):
    """Export public key dict to PEM format (PKCS#1): ASN.1 DER encoded, then Base64."""
    fields = [
        der_encode_integer(public_key['n']),
        der_encode_integer(public_key['e'])
    ]
    der_bytes = der_encode_sequence(fields)
    b64 = base64.b64encode(der_bytes).decode('ascii')
    # Wrap Base64 to 64 chars per line
    wrapped = '\n'.join(b64[i:i+64] for i in range(0, len(b64), 64))
    return f"-----BEGIN RSA PUBLIC KEY-----\n{wrapped}\n-----END RSA PUBLIC KEY-----"

# ASN.1/DER-Decoding-Funktionen für PEM-Import

def der_decode_length(data, offset):
    """Decode DER length at offset; returns (length, new_offset)."""
    first = data[offset]
    offset += 1
    if first < 128:
        return first, offset
    num_bytes = first & 0x7F
    length = int.from_bytes(data[offset:offset + num_bytes], 'big')
    return length, offset + num_bytes

def der_decode_integer(data, offset):
    """Decode INTEGER at offset; returns (value, new_offset)."""
    tag = data[offset]
    if tag != 0x02:
        raise ValueError("Expected INTEGER tag 0x02")
    offset += 1
    length, offset = der_decode_length(data, offset)
    value_bytes = data[offset:offset + length]
    # Remove leading 0x00 if present (for positive interpretation)
    if value_bytes[0] == 0 and len(value_bytes) > 1:
        value_bytes = value_bytes[1:]
    value = int.from_bytes(value_bytes, 'big')
    return value, offset + length

def der_decode_sequence(data, offset):
    """Decode SEQUENCE at offset; returns (fields list, new_offset)."""
    tag = data[offset]
    if tag != 0x30:
        raise ValueError("Expected SEQUENCE tag 0x30")
    offset += 1
    length, offset = der_decode_length(data, offset)
    end = offset + length
    fields = []
    while offset < end:
        # Assume all fields are INTEGERs for RSA private key
        value, offset = der_decode_integer(data, offset)
        fields.append(value)
    if offset != end:
        raise ValueError("SEQUENCE parsing mismatch")
    return fields, offset

def import_private_from_pem(pem_str):
    """Import private key from PEM string: Parse to DER, then ASN.1 decode to dict."""
    lines = pem_str.strip().splitlines()
    if lines[0] != "-----BEGIN RSA PRIVATE KEY-----" or lines[-1] != "-----END RSA PRIVATE KEY-----":
        raise ValueError("Invalid PEM format")
    b64 = ''.join(lines[1:-1])
    der_bytes = base64.b64decode(b64)
    fields, _ = der_decode_sequence(der_bytes, 0)
    if len(fields) != 9:
        raise ValueError("Invalid RSA private key structure")
    return {
        'version': fields[0],
        'n': fields[1],
        'e': fields[2],
        'd': fields[3],
        'p': fields[4],
        'q': fields[5],
        'dp': fields[6],
        'dq': fields[7],
        'iq': fields[8]
    }

def import_public_from_pem(pem_str):
    """Import public key from PEM string (PKCS#1): Parse to DER, then ASN.1 decode to dict."""
    lines = pem_str.strip().splitlines()
    if lines[0] != "-----BEGIN RSA PUBLIC KEY-----" or lines[-1] != "-----END RSA PUBLIC KEY-----":
        raise ValueError("Invalid PEM format")
    b64 = ''.join(lines[1:-1])
    der_bytes = base64.b64decode(b64)
    fields, _ = der_decode_sequence(der_bytes, 0)
    if len(fields) != 2:
        raise ValueError("Invalid RSA public key structure")
    return {
        'n': fields[0],
        'e': fields[1]
    }

def encrypt_dict(d, public_key):
    """Encrypt a dictionary using JSON serialization and raw RSA."""
    message = json.dumps(d).encode('utf-8')
    return encrypt(message, public_key)

def decrypt_dict(ciphertext, private_key):
    """Decrypt ciphertext to a dictionary using JSON deserialization."""
    message_bytes = decrypt(ciphertext, private_key)
    return json.loads(message_bytes.decode('utf-8'))

def get_public_key(private_key):
    """Get private key from JSON serialization and raw RSA."""
    return {"n": private_key["n"], "e": private_key["e"]}

if __name__ == '__main__':
    # Generiere Schlüsselpaar (für Test: kleine Bitlänge, Produktion: >=2048)
    # Generiere Schlüsselpaar (für Test: kleine Bitlänge, Produktion: >=2048)
    public_key, private_key = generate_keys(bits=1024)

    private_key_pem = '-----BEGIN RSA PRIVATE KEY-----\nMIICWQIBAAKBgAq06GZ85TN3wSL22Z8M2S10NmNA9FiUdpZ2tSSJv3GAbd4PFbaz\n+nNjA2KIKAQLFAix7YoXFNijFWegMrSmZO+7EHCwW+z3TDhgFMMkNS7XxS0xFXN+\nEeOWBaIh6GrsyQDvA10Iq/VYFAgm/T3y6cvkqh7lND2qdmrizjde1G4xAgMBAAEC\ngYAKTRrZGMuxZEQn7tddJxCBojF9943g+B7ND7OjTwEqJEYRA/SBT9LlV9t23seZ\ndEs3PnHsjd6ZvPcoN8LxerLcHxMU19PwAAKzVWnOYSrb/9SqlkLEE8KirMIYb6Zi\ndj03J+tiD9thDCuEPmt5Kgu8RV+YiIVbQoHdD/hpjDDEzQJBAKiI59lAbJWo7XBm\nhZbL7oA2Gi5ZfSPk9oWXkBc//W7BQn6lDxaTQbpJP3ufykyl7X/ThySqXSffi2jM\nN1nOvfsCQBBDXkvjfsYcUHYc8JeVmwfEGoWZ5Nf3TOwIkSKg6pW6vtHtPj2nhdm0\n3+zO+UCLJNVjf2mIyzuD8XNeLM53qMMCQHegJaFJX0mjjFW6D5yHyBRtUowPrQmr\nXWhZukcmfob82mv2UQ1fHMpTb6IaO4fIRxnyVPyriE/jFpseSTOP0b0CQA1GgN3f\nyWd8S23u97I1TETNnny6f+SPGXp/D8I9quAofYWtbKY1bnylOjj7RtmZ+6o4uxPx\ntzxQ2zK6iEbNxLMCQHr1RanjbQdU599V0IIS6nvUonUEir5S1v26chyy5TeND1Yi\npzCHYxLDDqoQ/exDkAACu6KxmVYoj4Wj59PHgIo=\n-----END RSA PRIVATE KEY-----'

    public_key_pem = '-----BEGIN RSA PUBLIC KEY-----\nMIGIAoGACrToZnzlM3fBIvbZnwzZLXQ2Y0D0WJR2lna1JIm/cYBt3g8VtrP6c2MD\nYogoBAsUCLHtihcU2KMVZ6AytKZk77sQcLBb7PdMOGAUwyQ1LtfFLTEVc34R45YF\noiHoauzJAO8DXQir9VgUCCb9PfLpy+SqHuU0Pap2auLON17UbjECAwEAAQ==\n-----END RSA PUBLIC KEY-----'

    public_key = import_public_from_pem(public_key_pem)

    private_key = import_private_from_pem(private_key_pem)

    # Nachricht signieren
    message = "sdata message"
    signature = sign(message, private_key)

    # Signatur verifizieren
    is_valid = verify(message, signature, public_key)

    print(f"Public Key: {public_key}")
    print(f"Private Key: {private_key}")  # Nur zu Demo-Zwecken; nie teilen!
    print(f"Signature: {signature}")
    print(f"Verifikation: {'Erfolgreich' if is_valid else 'Fehlgeschlagen'}")

    m0 = b"hello spencer"
    print(m0)
    c = encrypt(m0, public_key)
    m = decrypt(c, private_key)
    print(m)
    print(m0==m)
