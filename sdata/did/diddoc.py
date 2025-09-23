import base64
import json
def base64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=')

def base64url_decode(data):
    return base64.urlsafe_b64decode(data + b'=' * (4 - len(data) % 4))

from sdata.did.ed25519 import signature

if __name__ == '__main__':

    # DIDComm-Nachricht als JSON
    didcomm_message = {
        "id": "1234567890",
        "type": "http://example.com/protocols/lets_do_lunch/1.0/proposal",
        "from": "did:example:alice",
        "to": ["did:example:bob"],
        "created_time": 1516269022,
        "expires_time": 1516385931,
        "body": {"messagespecificattribute": "and its value"}
    }
    message_json = json.dumps(didcomm_message, separators=(',', ':')).encode('utf-8')

    # JWS Header
    header = {
        "typ": "JWM",
        "alg": "EdDSA",
        "kid": "did:example:alice#key-1"
    }
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')

    protected = base64url_encode(header_json)
    payload = base64url_encode(message_json)
    signing_string = protected + b'.' + payload

    # Signiere mit Ed25519 (beachte: DIDComm verwendet die raw Signatur)
    sig = signature(signing_string, sk, pk)
    signature_base64 = base64url_encode(sig)

    # Finale JWS-Struktur (Flattened JSON)
    jws = {
        "payload": payload.decode('utf-8'),
        "signatures": [{
            "protected": protected.decode('utf-8'),
            "signature": signature_base64.decode('utf-8'),
            "header": {"kid": header["kid"]}
        }]
    }

    print("Signierte DIDComm-Nachricht (JWS):")
    print(json.dumps(jws, indent=2))