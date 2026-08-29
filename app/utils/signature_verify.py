import hashlib
import hmac


def verify_whatsapp_signature(
    payload: bytes, signature_header: str, app_secret: str
) -> bool:
    if not signature_header or not app_secret:
        return False

    expected = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


def verify_paystack_signature(
    payload: bytes, signature_header: str, secret_key: str
) -> bool:
    if not signature_header or not secret_key:
        return False

    expected = hmac.new(
        secret_key.encode("utf-8"),
        payload,
        hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)
