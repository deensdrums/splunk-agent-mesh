"""Short-lived signed access tokens for direct investigation SSE streams."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time


_TOKEN_SECRET = secrets.token_bytes(32)


def create_stream_token(investigation_id: str, ttl_seconds: int) -> str:
    expires = int(time.time()) + ttl_seconds
    payload = f"{investigation_id}:{expires}"
    signature = hmac.new(_TOKEN_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()


def is_valid_stream_token(investigation_id: str, token: str) -> bool:
    try:
        decoded = base64.b64decode(token.encode(), altchars=b"-_", validate=True).decode()
        token_investigation_id, expires_raw, signature = decoded.rsplit(":", 2)
        expires = int(expires_raw)
    except (ValueError, UnicodeDecodeError):
        return False
    if token_investigation_id != investigation_id or expires < int(time.time()):
        return False
    payload = f"{token_investigation_id}:{expires}"
    expected = hmac.new(_TOKEN_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
