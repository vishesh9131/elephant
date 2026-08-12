from __future__ import annotations

import re
from typing import Any, Mapping


_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]{12,}"),
    re.compile(r"\bgh[opusr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password)\b(\s*[:=]\s*)"
        r"(['\"]?)[^\s,'\"}]{8,}\3"
    ),
)
_SENSITIVE_KEY = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|auth(?:orization)?|client[_-]?secret|"
    r"password|private[_-]?key|refresh[_-]?token|secret)"
)


def redact_text(value: str) -> str:
    redacted = value
    for pattern in _PATTERNS:
        if pattern.groups >= 2:
            redacted = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", redacted)
        elif pattern.groups == 1:
            redacted = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return redact_text(str(value))
