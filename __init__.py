"""Hermes Agent plugin entrypoint for Elephant."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from elephant.kernel import Elephant  # noqa: E402
from elephant.plugin_runtime import recovery_context  # noqa: E402
from elephant.project import project_id  # noqa: E402


def _cwd(values: dict[str, Any]) -> str:
    return str(values.get("cwd") or values.get("working_directory") or os.getcwd())


def _capture(event_name: str, values: dict[str, Any]) -> None:
    payload = dict(values)
    payload.setdefault("cwd", _cwd(payload))
    if "args" in payload and "tool_input" not in payload:
        payload["tool_input"] = payload["args"]
    if "result" in payload and "tool_output" not in payload:
        payload["tool_output"] = payload["result"]
    if "user_message" in payload and "prompt" not in payload:
        payload["prompt"] = payload["user_message"]
    if "assistant_response" in payload and "response" not in payload:
        payload["response"] = payload["assistant_response"]
    Elephant().capture("hermes", event_name, payload, cwd=payload["cwd"])


def _recover(cwd: str) -> dict[str, Any]:
    return Elephant().recover(cwd=cwd, target_harness="hermes")


def register(ctx) -> None:
    """Register Elephant's native Hermes hooks, tool, skill, and command."""
    injected_sessions: set[str] = set()

    def on_session_start(**kwargs):
        _capture("on_session_start", kwargs)

    def pre_llm_call(**kwargs):
        session_id = str(kwargs.get("session_id") or "unknown-session")
        cwd = _cwd(kwargs)
        previous = Elephant().journal.latest_capsule(project_id(cwd))
        _capture("pre_llm_call", kwargs)
        if previous and previous.source_session_id != session_id and session_id not in injected_sessions:
            injected_sessions.add(session_id)
            return {"context": recovery_context(previous)}
        return None

    def post_llm_call(**kwargs):
        _capture("post_llm_call", kwargs)

    def pre_tool_call(**kwargs):
        _capture("pre_tool_call", kwargs)

    def post_tool_call(**kwargs):
        _capture("post_tool_call", kwargs)

    def on_session_end(**kwargs):
        _capture("on_session_end", kwargs)

    def on_session_finalize(**kwargs):
        _capture("on_session_finalize", kwargs)

    def recover_tool(args: dict, **kwargs) -> str:
        try:
            return json.dumps(_recover(str(args.get("cwd") or _cwd(kwargs))), indent=2)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    recover_schema = {
        "name": "elephant_recover",
        "description": "Recover the previous coding-agent session for this workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "cwd": {
                    "type": "string",
                    "description": "Absolute path to the coding workspace",
                }
            },
        },
    }

    def resume(_raw_args: str) -> str:
        try:
            packet = _recover(os.getcwd())
        except Exception as exc:
            return f"Elephant has no recoverable session here: {exc}"
        capsule = packet["capsule"]
        return (
            f"Elephant recovered {capsule['source_harness']} session "
            f"{capsule['source_session_id']}.\n"
            f"Objective: {capsule['objective']}\n"
            f"State: {capsule['current_state']}"
        )

    ctx.register_tool(
        name="elephant_recover",
        toolset="elephant",
        schema=recover_schema,
        handler=recover_tool,
        description="Recover a coding session from another AI harness.",
    )
    ctx.register_command(
        "elephant",
        handler=resume,
        description="Recover the previous coding-agent session",
    )
    ctx.register_skill("resume", PLUGIN_ROOT / "skills" / "resume" / "SKILL.md")
    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("pre_llm_call", pre_llm_call)
    ctx.register_hook("post_llm_call", post_llm_call)
    ctx.register_hook("pre_tool_call", pre_tool_call)
    ctx.register_hook("post_tool_call", post_tool_call)
    ctx.register_hook("on_session_end", on_session_end)
    ctx.register_hook("on_session_finalize", on_session_finalize)
