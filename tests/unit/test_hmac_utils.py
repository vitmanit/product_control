from src.utils.hmac_utils import generate_signature, verify_signature


def test_signature_is_deterministic():
    payload = {"event": "batch_created", "data": {"id": 1}}
    secret = "my-secret"

    sig1 = generate_signature(payload, secret)
    sig2 = generate_signature(payload, secret)

    assert sig1 == sig2
    assert len(sig1) == 64  # SHA-256 hex


def test_signature_changes_with_payload():
    secret = "my-secret"

    sig_a = generate_signature({"a": 1}, secret)
    sig_b = generate_signature({"a": 2}, secret)

    assert sig_a != sig_b


def test_signature_changes_with_secret():
    payload = {"a": 1}

    sig_a = generate_signature(payload, "secret-a")
    sig_b = generate_signature(payload, "secret-b")

    assert sig_a != sig_b


def test_signature_is_order_independent():
    secret = "my-secret"

    sig_a = generate_signature({"a": 1, "b": 2}, secret)
    sig_b = generate_signature({"b": 2, "a": 1}, secret)

    assert sig_a == sig_b


def test_verify_signature_accepts_valid():
    payload = {"event": "batch_closed", "id": 42}
    secret = "top-secret"

    sig = generate_signature(payload, secret)

    assert verify_signature(payload, secret, sig) is True


def test_verify_signature_rejects_invalid():
    payload = {"event": "batch_closed", "id": 42}
    secret = "top-secret"

    assert verify_signature(payload, secret, "0" * 64) is False


def test_verify_signature_rejects_wrong_secret():
    payload = {"event": "batch_closed", "id": 42}
    sig = generate_signature(payload, "secret-a")

    assert verify_signature(payload, "secret-b", sig) is False
