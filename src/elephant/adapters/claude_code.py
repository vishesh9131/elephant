from __future__ import annotations

from typing import Any, Mapping

from elephant.adapters.base import Capabilities, error_text, event_context, is_quota_failure
from elephant.models import Confidence, Event, EventKind


class ClaudeCodeAdapter:
    name = "claude-code"
    capabilities = Capabilities(
        native_hooks=True,
        session_lifecycle=True,
        prompts=True,
        tool_calls=True,
        model_responses=True,
        transcript_path=True,
        context_usage=False,
        quota_usage=False,
        failure_reason=True,
    )

    _EVENTS = {
        "SessionStart": EventKind.SESSION_STARTED,
        "UserPromptSubmit": EventKind.USER_PROMPTED,
        "UserPromptExpansion": EventKind.USER_PROMPTED,
        "PreToolUse": EventKind.TOOL_STARTED,
        "PostToolUse": EventKind.TOOL_COMPLETED,
        "PostToolUseFailure": EventKind.TOOL_FAILED,
        "PreCompact": EventKind.CONTEXT_COMPACTING,
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
        payload = self._payload(event_name, raw)

        if event_name == "StopFailure":
            failure = EventKind.QUOTA_EXHAUSTED if is_quota_failure(raw) else EventKind.MODEL_FAILED
            confidence = Confidence.EXACT if failure == EventKind.QUOTA_EXHAUSTED else Confidence.UNKNOWN
            return [
                Event(
                    kind=failure,
                    harness=self.name,
                    session_id=session_id,
                    project_id=project_id,
                    payload=payload,
                    confidence=confidence,
                    source="native-hook",
                    cwd=actual_cwd,
                ),
                Event(
                    kind=EventKind.SESSION_INTERRUPTED,
                    harness=self.name,
                    session_id=session_id,
                    project_id=project_id,
                    payload={"reason": error_text(raw)},
                    confidence=confidence,
                    source="native-hook",
                    cwd=actual_cwd,
                ),
            ]

        kind = self._EVENTS.get(event_name)
        if not kind:
            raise ValueError(f"unsupported Claude Code hook: {event_name}")
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

    @staticmethod
    def _payload(event_name: str, raw: Mapping[str, Any]) -> dict[str, Any]:
        common = {
            "hook": event_name,
            "transcript_path": raw.get("transcript_path"),
        }
        if event_name in {"UserPromptSubmit", "UserPromptExpansion"}:
            common["prompt"] = raw.get("prompt")
        elif event_name in {"PreToolUse", "PostToolUse", "PostToolUseFailure"}:
            common.update(
                tool_name=raw.get("tool_name"),
                tool_input=raw.get("tool_input"),
                tool_response=raw.get("tool_response"),
            )
        elif event_name == "Stop":
            common["response"] = raw.get("last_assistant_message")
        elif event_name == "StopFailure":
            common["error"] = error_text(raw)
            common["failure_type"] = raw.get("failure_type")
        return {key: value for key, value in common.items() if value is not None}
