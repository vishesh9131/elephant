from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from elephant.models import Event


@dataclass(frozen=True, slots=True)
class Capabilities:
    native_hooks: bool
    session_lifecycle: bool
    prompts: bool
    tool_calls: bool
    model_responses: bool
    transcript_path: bool
    context_usage: bool
    quota_usage: bool
    failure_reason: bool

    def to_dict(self) -> dict[str, bool]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }


class Adapter(Protocol):
    name: str
    capabilities: Capabilities

    def normalize(
        self,
        event_name: str,
        raw: Mapping[str, Any],
        *,
        project_id: str,
        cwd: str,
    ) -> list[Event]: ...


def event_context(raw: Mapping[str, Any], fallback_cwd: str) -> tuple[str, str]:
    session_id = str(
        raw.get("session_id")
        or raw.get("sessionId")
        or raw.get("conversation_id")
        or raw.get("conversationId")
        or "unknown-session"
    )
    cwd = str(raw.get("cwd") or raw.get("working_directory") or fallback_cwd)
    return session_id, cwd


def error_text(raw: Mapping[str, Any]) -> str:
    for key in ("error", "error_message", "message", "reason", "failure_reason"):
        value = raw.get(key)
        if isinstance(value, Mapping):
            return str(value.get("message") or value.get("type") or value)
        if value:
            return str(value)
    return "Unknown harness failure"


def is_quota_failure(raw: Mapping[str, Any]) -> bool:
    category = " ".join(
        str(raw.get(key, ""))
        for key in ("error", "error_type", "failure_type", "reason", "message")
    ).lower()
    markers = (
        "rate_limit",
        "rate limit",
        "quota",
        "billing_error",
        "billing error",
        "usage limit",
        "limit reached",
        "too many requests",
    )
    return any(marker in category for marker in markers)

