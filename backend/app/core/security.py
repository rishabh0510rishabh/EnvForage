import hashlib
import hmac


def generate_hmac_signature(secret: str, payload: str) -> str:
    """Generate an HMAC-SHA256 signature for the given payload using the secret."""
    signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def verify_hmac_signature(secret: str, payload: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature against the payload."""
    expected_signature = generate_hmac_signature(secret, payload)
    return hmac.compare_digest(expected_signature, signature)
