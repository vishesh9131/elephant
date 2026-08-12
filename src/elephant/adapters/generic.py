from __future__ import annotations

from typing import Any, Mapping

from elephant.adapters.base import Capabilities, event_context
from elephant.models import Confidence, Event


class GenericAdapter:
    name = "generic"
    capabilities = Capabilities(
        native_hooks=False,
        session_lifecycle=True,
        prompts=True,
        tool_calls=True,
        model_responses=True,
        transcript_path=False,
        context_usage=False,
        quota_usage=False,
        failure_reason=False,
    )

    def __init__(self, name: str = "generic") -> None:
        self.name = name

    def normalize(
        self,
        event_name: str,
        raw: Mapping[str, Any],
        *,
        project_id: str,
        cwd: str,
    ) -> list[Event]:
        session_id, actual_cwd = event_context(raw, cwd)
        payload = dict(raw.get("payload") or raw)
        aliases = {
            "toolName": "tool_name",
            "toolArgs": "tool_input",
            "toolResult": "tool_output",
            "transcriptPath": "transcript_path",
            "initialPrompt": "prompt",
            "errorMessage": "error",
        }
        for source, target in aliases.items():
            if source in payload and target not in payload:
                payload[target] = payload[source]
        return [
            Event(
                kind=str(raw.get("kind") or event_name),
                harness=str(raw.get("harness") or self.name),
                session_id=session_id,
                project_id=project_id,
                payload=payload,
                confidence=Confidence(raw.get("confidence", Confidence.UNKNOWN)),
                source=str(raw.get("source", "generic-adapter")),
                cwd=actual_cwd,
            )
        ]
