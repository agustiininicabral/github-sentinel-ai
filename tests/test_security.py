import hashlib
import hmac

from sentinel_api.security import verify_github_signature


def test_valid_signature():
    body = b'{"action":"opened"}'
    digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert verify_github_signature("secret", body, f"sha256={digest}")


def test_invalid_signature_and_empty_secret():
    assert not verify_github_signature("secret", b"{}", "sha256=" + "0" * 64)
    assert not verify_github_signature("", b"{}", "sha256=" + "0" * 64)


def test_signature_is_bound_to_exact_bytes():
    body = b'{"a":1}'
    digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert not verify_github_signature("secret", b'{ "a": 1 }', f"sha256={digest}")
