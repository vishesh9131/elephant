from __future__ import annotations

from typing import Any, Mapping

from elephant.adapters.base import Capabilities, error_text, event_context, is_quota_failure
from elephant.models import Confidence, Event, EventKind


class CodexAdapter:
    name = "codex"
    capabilities = Capabilities(
        native_hooks=True,
        session_lifecycle=True,
        prompts=True,
        tool_calls=True,
        model_responses=True,
        transcript_path=True,
        context_usage=False,
        quota_usage=False,
        failure_reason=False,
    )

    _EVENTS = {
        "SessionStart": EventKind.SESSION_STARTED,
        "UserPromptSubmit": EventKind.USER_PROMPTED,
        "PreToolUse": EventKind.TOOL_STARTED,
        "PostToolUse": EventKind.TOOL_COMPLETED,
        "PreCompact": EventKind.CONTEXT_COMPACTING,
        "PostCompact": EventKind.CONTEXT_USAGE,
        "Stop": EventKind.MODEL_RESPONDED,
        "SessionEnd": EventKind.SESSION_ENDED,
    }

    def normalize(
        self,
        event_name: str,
        raw: Mapping[str, Any],
        *,
        project_id: str,
        cwd: str,
    ) -> list[Event]:
        session_id, actual_cwd = event_context(raw, cwd)
        if event_name in {"Error", "TurnFailed"}:
            quota = is_quota_failure(raw)
            kind = EventKind.QUOTA_EXHAUSTED if quota else EventKind.MODEL_FAILED
            return [
                Event(
                    kind=kind,
                    harness=self.name,
                    session_id=session_id,
                    project_id=project_id,
                    payload={"error": error_text(raw), "hook": event_name},
                    confidence=Confidence.EXACT if quota else Confidence.UNKNOWN,
                    source="wrapper",
                    cwd=actual_cwd,
                )
            ]

        kind = self._EVENTS.get(event_name)
        if not kind:
            raise ValueError(f"unsupported Codex hook: {event_name}")
        payload: dict[str, Any] = {
            "hook": event_name,
            "transcript_path": raw.get("transcript_path"),
        }
        if event_name == "UserPromptSubmit":
            payload["prompt"] = raw.get("prompt")
        elif event_name in {"PreToolUse", "PostToolUse"}:
            payload.update(tool_name=raw.get("tool_name"), tool_input=raw.get("tool_input"))
        elif event_name == "Stop":
            payload["response"] = raw.get("last_assistant_message")
        payload = {key: value for key, value in payload.items() if value is not None}
        return [
            Event(
                kind=kind,
                harness=self.name,
                session_id=session_id,
                project_id=project_id,
                payload=payload,
                source="native-hook",
                cwd=actual_cwd,
            )
        ]

