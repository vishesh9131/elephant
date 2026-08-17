from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Confidence(str, Enum):
    EXACT = "exact"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class EventKind(str, Enum):
    SESSION_STARTED = "session.started"
    SESSION_RESUMED = "session.resumed"
    SESSION_INTERRUPTED = "session.interrupted"
    SESSION_COMPLETED = "session.completed"
    SESSION_ENDED = "session.ended"
    USER_PROMPTED = "user.prompted"
    USER_NOTED = "user.noted"
    MODEL_REQUESTED = "model.requested"
    MODEL_RESPONDED = "model.responded"
    MODEL_FAILED = "model.failed"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    FILE_READ = "file.read"
    FILE_CHANGED = "file.changed"
    COMMAND_COMPLETED = "command.completed"
    VERIFICATION_COMPLETED = "verification.completed"
    CONTEXT_USAGE = "context.usage"
    CONTEXT_COMPACTING = "context.compacting"
    QUOTA_WARNING = "quota.warning"
    QUOTA_EXHAUSTED = "quota.exhausted"


@dataclass(frozen=True, slots=True)
class Event:
    kind: str
    harness: str
    session_id: str
    project_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    confidence: Confidence = Confidence.EXACT
    source: str = "adapter"
    cwd: str | None = None
    timestamp: str = field(default_factory=utc_now)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    sequence: int | None = None
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confidence"] = self.confidence.value
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Event:
        required = ("kind", "harness", "session_id", "project_id")
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"event missing required fields: {', '.join(missing)}")
        return cls(
            kind=str(data["kind"]),
            harness=str(data["harness"]),
            session_id=str(data["session_id"]),
            project_id=str(data["project_id"]),
            payload=dict(data.get("payload", {})),
            confidence=Confidence(data.get("confidence", Confidence.EXACT)),
            source=str(data.get("source", "adapter")),
            cwd=str(data["cwd"]) if data.get("cwd") else None,
            timestamp=str(data.get("timestamp", utc_now())),
            event_id=str(data.get("event_id", uuid4())),
            sequence=int(data["sequence"]) if data.get("sequence") is not None else None,
            schema_version=int(data.get("schema_version", 1)),
        )


@dataclass(frozen=True, slots=True)
class Capsule:
    project_id: str
    source_harness: str
    source_session_id: str
    objective: str
    current_state: str
    last_user_prompt: str | None
    last_model_response: str | None
    modified_files: tuple[str, ...]
    recent_failures: tuple[str, ...]
    recent_events: tuple[Mapping[str, Any], ...]
    git: Mapping[str, Any]
    transcript: Mapping[str, Any]
    event_count: int
    notes: tuple[str, ...] = ()
    event_watermark: int | None = None
    created_at: str = field(default_factory=utc_now)
    capsule_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["modified_files"] = list(self.modified_files)
        data["recent_failures"] = list(self.recent_failures)
        data["recent_events"] = list(self.recent_events)
        data["notes"] = list(self.notes)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Capsule:
        return cls(
            project_id=str(data["project_id"]),
            source_harness=str(data["source_harness"]),
            source_session_id=str(data["source_session_id"]),
            objective=str(data.get("objective", "Continue the previous coding session.")),
            current_state=str(data.get("current_state", "Session checkpointed.")),
            last_user_prompt=data.get("last_user_prompt"),
            last_model_response=data.get("last_model_response"),
            modified_files=tuple(data.get("modified_files", ())),
            recent_failures=tuple(data.get("recent_failures", ())),
            recent_events=tuple(data.get("recent_events", ())),
            git=dict(data.get("git", {})),
            transcript=dict(data.get("transcript", {})),
            event_count=int(data.get("event_count", 0)),
            notes=tuple(data.get("notes", ())),
            event_watermark=(
                int(data["event_watermark"])
                if data.get("event_watermark") is not None
                else None
            ),
            created_at=str(data.get("created_at", utc_now())),
            capsule_id=str(data.get("capsule_id", uuid4())),
            schema_version=int(data.get("schema_version", 1)),
        )
