from __future__ import annotations

from typing import Any, Mapping

from elephant.adapters.base import Capabilities, error_text, event_context, is_quota_failure
from elephant.models import Confidence, Event, EventKind


class HermesAdapter:
    name = "hermes"
    capabilities = Capabilities(
        native_hooks=True,
        session_lifecycle=True,
        prompts=True,
        tool_calls=True,
        model_responses=True,
        transcript_path=False,
        context_usage=True,
        quota_usage=False,
        failure_reason=True,
    )

    _EVENTS = {
        "on_session_start": EventKind.SESSION_STARTED,
        "on_session_end": EventKind.SESSION_ENDED,
        "on_session_finalize": EventKind.SESSION_COMPLETED,
        "pre_llm_call": EventKind.MODEL_REQUESTED,
        "post_llm_call": EventKind.MODEL_RESPONDED,
        "pre_tool_call": EventKind.TOOL_STARTED,
        "post_tool_call": EventKind.TOOL_COMPLETED,
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
        error = raw.get("error")
        if error:
            quota = is_quota_failure(raw)
            kind = EventKind.QUOTA_EXHAUSTED if quota else EventKind.MODEL_FAILED
            confidence = Confidence.EXACT if quota else Confidence.UNKNOWN
        else:
            kind = self._EVENTS.get(event_name)
            confidence = Confidence.EXACT
        if not kind:
            raise ValueError(f"unsupported Hermes hook: {event_name}")

        payload = {
            key: value
            for key, value in {
                "hook": event_name,
                "prompt": raw.get("prompt"),
                "response": raw.get("response"),
                "tool_name": raw.get("tool_name"),
                "tool_input": raw.get("tool_input"),
                "tool_output": raw.get("tool_output"),
                "error": error_text(raw) if error else None,
                "context_usage": raw.get("context_usage"),
            }.items()
            if value is not None
        }
        events = []
        if event_name == "pre_llm_call" and payload.get("prompt"):
            events.append(
                Event(
                    kind=EventKind.USER_PROMPTED,
                    harness=self.name,
                    session_id=session_id,
                    project_id=project_id,
                    payload={"prompt": payload["prompt"]},
                    confidence=confidence,
                    source="python-hook",
                    cwd=actual_cwd,
                )
            )
        events.append(
            Event(
                kind=kind,
                harness=self.name,
                session_id=session_id,
                project_id=project_id,
                payload=payload,
                confidence=confidence,
                source="python-hook",
                cwd=actual_cwd,
            )
        )
        return events
