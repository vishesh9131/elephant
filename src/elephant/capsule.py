from __future__ import annotations

from typing import Any, Iterable, Mapping

from elephant.models import Capsule, Event, EventKind
from elephant.project import git_state


def _text(event: Event, *keys: str) -> str | None:
    for key in keys:
        value = event.payload.get(key)
        if value:
            return str(value)
    return None


def build_capsule(events: Iterable[Event], cwd: str) -> Capsule:
    history = list(events)
    if not history:
        raise ValueError("cannot build a capsule without events")

    prompts = [
        _text(event, "prompt", "text")
        for event in history
        if event.kind == EventKind.USER_PROMPTED
    ]
    responses = [
        _text(event, "response", "message", "text")
        for event in history
        if event.kind == EventKind.MODEL_RESPONDED
    ]
    failures = [
        _text(event, "error", "reason", "message") or event.kind
        for event in history
        if event.kind in {
            EventKind.MODEL_FAILED,
            EventKind.TOOL_FAILED,
            EventKind.QUOTA_EXHAUSTED,
            EventKind.SESSION_INTERRUPTED,
        }
    ]
    git = git_state(cwd)
    files = set(git.get("changed_files", ()))
    for event in history:
        files.update(_file_paths(event.payload))

    last = history[-1]
    last_prompt = next((value for value in reversed(prompts) if value), None)
    last_response = next((value for value in reversed(responses) if value), None)
    objective = last_prompt or next((value for value in prompts if value), None)
    objective = objective or "Continue the previous coding session."
    state = _current_state(last, last_response, files)
    recent = tuple(
        {
            "sequence": event.sequence,
            "kind": event.kind,
            "harness": event.harness,
            "summary": _event_summary(event),
        }
        for event in history[-20:]
    )
    return Capsule(
        project_id=last.project_id,
        source_harness=last.harness,
        source_session_id=last.session_id,
        objective=objective,
        current_state=state,
        last_user_prompt=last_prompt,
        last_model_response=last_response,
        modified_files=tuple(sorted(files)),
        recent_failures=tuple(failures[-5:]),
        recent_events=recent,
        git=git,
        transcript={},
        event_count=len(history),
    )


def _current_state(last: Event, response: str | None, files: set[str]) -> str:
    if last.kind == EventKind.QUOTA_EXHAUSTED:
        return "The source harness hit a quota limit; resume from the recorded worktree."
    if last.kind == EventKind.CONTEXT_COMPACTING:
        return "The source harness was about to compact context; verify the worktree and continue."
    if last.kind == EventKind.SESSION_INTERRUPTED:
        return "The source session was interrupted; inspect recent failures before continuing."
    if response:
        return response
    if files:
        return f"Work is in progress with {len(files)} modified file(s)."
    return f"Last recorded event: {last.kind}."


def _event_summary(event: Event) -> str:
    return (
        _text(event, "prompt", "response", "error", "reason", "tool_name")
        or event.kind
    )[:500]


def _file_paths(value: Any) -> set[str]:
    paths: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"path", "file", "file_path"} and isinstance(item, str):
                paths.add(item)
            else:
                paths.update(_file_paths(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            paths.update(_file_paths(item))
    return paths
