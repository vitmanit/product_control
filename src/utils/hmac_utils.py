import hashlib
import hmac
import json


def generate_signature(payload: dict, secret_key: str) -> str:
    payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hmac.new(
        secret_key.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload: dict, secret_key: str, signature: str) -> bool:
    expected = generate_signature(payload, secret_key)
    return hmac.compare_digest(expected, signature)
