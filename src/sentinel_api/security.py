import hashlib
import hmac


def verify_github_signature(secret: str, body: bytes, signature: str | None) -> bool:
    """Validate GitHub's X-Hub-Signature-256 header against the exact raw body."""
    if not secret or not signature or not signature.startswith("sha256="):
        return False
    supplied = signature.removeprefix("sha256=")
    if len(supplied) != 64:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)
