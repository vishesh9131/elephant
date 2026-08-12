from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from elephant.adapters import adapter_manifest, get_adapter
from elephant.artifacts import archive_transcript
from elephant.capsule import build_capsule
from elephant.models import Capsule, Event, EventKind
from elephant.project import project_id
from elephant.redaction import redact
from elephant.store import Journal


class Elephant:
    def __init__(self, database: str | Path | None = None) -> None:
        self.journal = Journal(database)

    def capture(
        self,
        harness: str,
        event_name: str,
        raw: Mapping[str, Any],
        *,
        cwd: str | Path,
    ) -> tuple[list[Event], Capsule | None]:
        cwd_string = str(Path(cwd).expanduser().resolve())
        identity = project_id(cwd_string)
        adapter = get_adapter(harness)
        normalized = adapter.normalize(
            event_name,
            raw,
            project_id=identity,
            cwd=cwd_string,
        )
        stored: list[Event] = []
        capsule: Capsule | None = None
        for event in normalized:
            safe = replace(event, payload=redact(event.payload))
            saved = self.journal.append(safe)
            stored.append(saved)
            if self._checkpoint_worthy(saved):
                capsule = self.checkpoint(saved.session_id, cwd=cwd_string)
        return stored, capsule

    def checkpoint(self, session_id: str, *, cwd: str | Path) -> Capsule:
        events = self.journal.events(session_id)
        capsule = build_capsule(events, str(cwd))
        transcript = archive_transcript(events, self.journal.path.parent)
        if transcript:
            capsule = replace(capsule, transcript=transcript)
        return self.journal.save_capsule(capsule)

    def recover(self, *, cwd: str | Path, target_harness: str | None = None) -> dict[str, Any]:
        identity = project_id(cwd)
        capsule = self.journal.latest_capsule(identity)
        if capsule is None:
            sessions = self.journal.sessions_for_project(identity)
            if not sessions:
                raise LookupError("no Elephant session exists for this project")
            capsule = self.checkpoint(sessions[0], cwd=cwd)
        return {
            "capsule": capsule.to_dict(),
            "target_harness": target_harness,
            "resume_instructions": [
                "Compare the capsule Git head and dirty files with the current worktree.",
                "Inspect recent failures before changing code.",
                "Continue the objective; do not repeat completed work.",
                "Record new progress through Elephant hooks.",
            ],
        }

    @staticmethod
    def adapters() -> dict[str, dict[str, bool]]:
        return adapter_manifest()

    @staticmethod
    def _checkpoint_worthy(event: Event) -> bool:
        if event.kind in {
            EventKind.QUOTA_WARNING,
            EventKind.QUOTA_EXHAUSTED,
            EventKind.CONTEXT_COMPACTING,
            EventKind.SESSION_INTERRUPTED,
            EventKind.SESSION_ENDED,
            EventKind.MODEL_RESPONDED,
            EventKind.MODEL_FAILED,
            EventKind.TOOL_FAILED,
        }:
            return True
        if event.kind == EventKind.CONTEXT_USAGE:
            usage = event.payload.get("ratio") or event.payload.get("context_usage")
            try:
                return float(usage) >= 0.98
            except (TypeError, ValueError):
                return False
        return False
