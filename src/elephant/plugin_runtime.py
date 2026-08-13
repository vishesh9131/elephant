from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from elephant.kernel import Elephant
from elephant.models import Capsule


def handle_hook(
    harness: str,
    event_name: str,
    payload: Mapping[str, Any],
    *,
    database: str | Path | None = None,
) -> dict[str, Any] | None:
    """Capture a native plugin hook and optionally inject prior-session context."""
    cwd = str(payload.get("cwd") or payload.get("working_directory") or Path.cwd())
    elephant = Elephant(database)
    is_start = event_name in {"SessionStart", "session.started"}
    previous = None
    if is_start:
        try:
            previous = Capsule.from_dict(elephant.recover(cwd=cwd)["capsule"])
        except LookupError:
            pass
    elephant.capture(harness, event_name, payload, cwd=cwd)

    session_id = str(payload.get("session_id") or payload.get("sessionId") or "")
    if previous and previous.source_session_id != session_id:
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": recovery_context(previous),
            }
        }
    return None


def recovery_context(capsule: Capsule) -> str:
    files = ", ".join(capsule.modified_files[:20]) or "none recorded"
    failures = "; ".join(capsule.recent_failures[-3:]) or "none recorded"
    notes = "; ".join(capsule.notes[-3:]) or "none recorded"
    response = (capsule.last_model_response or "none recorded")[-2000:]
    return "\n".join(
        (
            "[Elephant recovered a previous coding session]",
            f"Capsule: {capsule.capsule_id}",
            f"Source: {capsule.source_harness} / {capsule.source_session_id}",
            f"Objective: {capsule.objective}",
            f"State: {capsule.current_state}",
            f"Last agent response: {response}",
            f"Modified files: {files}",
            f"Recent failures: {failures}",
            f"User notes: {notes}",
            "Verify the live Git worktree, avoid repeating completed work, and continue the objective.",
            "Use the Elephant recovery tool if you need the structured capsule and recent event trail.",
        )
    )
