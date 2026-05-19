"""Credential redaction and security helpers."""

import re

_REDACT_PATTERNS = [
    re.compile(r'(api[-_]?key\s*[:=]\s*)[^\s,\'"]+', re.IGNORECASE),
    re.compile(r'(Bearer\s+)[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE),
    re.compile(r'(sk-)[A-Za-z0-9]{20,}'),
    re.compile(r'(ant-[a-z0-9]{4}-)[A-Za-z0-9\-]{20,}'),
]


def redact_key(key: str | None) -> str:
    """Return a safe display string: first 4 chars + ****."""
    if not key:
        return "<not set>"
    visible = key[:4] if len(key) >= 4 else key
    return f"{visible}****"


def redact_log_message(message: str) -> str:
    """Scrub known secret patterns from a log string."""
    for pattern in _REDACT_PATTERNS:
        message = pattern.sub(r'\g<1>****', message)
    return message


def is_safe_model_name(name: str) -> bool:
    """Validate model name is a safe alphanumeric/dash/dot/slash string (no path traversal)."""
    if '..' in name or name.startswith('/') or name.startswith('.'):
        return False
    return bool(re.match(r'^[A-Za-z0-9][A-Za-z0-9._/:\-]{0,99}$', name))


def is_safe_url(url: str) -> bool:
    """Validate base URL looks like an HTTP(S) origin."""
    return bool(re.match(r'^https?://[A-Za-z0-9._:\-/]+$', url))
