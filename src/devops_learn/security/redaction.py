"""Structural redaction for security evidence.

This is deliberately applied before evidence is normalized, audited, rendered,
or written to an artifact.  It is not an instruction for an LLM to follow.
"""

from __future__ import annotations

import re
from typing import Any

REDACTED_SECRET = "[REDACTED SECRET]"
_ASSIGNMENT = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|API[_-]?KEY)[A-Z0-9_]*)\s*[=:]\s*([^\s,]+)"
)
_BEARER = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+")


def redact_text(value: str) -> str:
    """Remove common credential-shaped values while retaining useful context."""
    value = _ASSIGNMENT.sub(lambda match: f"{match.group(1)}={REDACTED_SECRET}", value)
    return _BEARER.sub(lambda match: f"{match.group(1)}{REDACTED_SECRET}", value)


def redact_data(value: Any, *, secret_context: bool = False) -> Any:
    """Return a recursively safe copy of scanner data.

    Scanner fields named Match, Secret, Value, or Code are evidence-bearing
    secret contexts even when their values do not look like a conventional key.
    """
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_is_secret = key.lower() in {"match", "secret", "value", "code", "lines"}
            result[str(key)] = redact_data(item, secret_context=secret_context or key_is_secret)
        return result
    if isinstance(value, list):
        return [redact_data(item, secret_context=secret_context) for item in value]
    if isinstance(value, str):
        return REDACTED_SECRET if secret_context else redact_text(value)
    return value
