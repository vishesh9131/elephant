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
from elephant.commands import CommandRouter  # noqa: E402
from elephant.plugin_runtime import recovery_context  # noqa: E402


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
    active = {"session_id": None, "cwd": os.getcwd()}

    def on_session_start(**kwargs):
        active["session_id"] = str(kwargs.get("session_id") or "hermes-session")
        active["cwd"] = _cwd(kwargs)
        _capture("on_session_start", kwargs)

    def pre_llm_call(**kwargs):
        session_id = str(kwargs.get("session_id") or "unknown-session")
        cwd = _cwd(kwargs)
        active["session_id"] = session_id
        active["cwd"] = cwd
        try:
            previous = Elephant().recover(cwd=cwd)["capsule"]
        except LookupError:
            previous = None
        _capture("pre_llm_call", kwargs)
        if previous and previous["source_session_id"] != session_id and session_id not in injected_sessions:
            injected_sessions.add(session_id)
            from elephant.models import Capsule

            return {"context": recovery_context(Capsule.from_dict(previous))}
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

    def elephant_command(raw_args: str) -> str:
        result = CommandRouter().execute(
            raw_args or "help",
            cwd=str(active["cwd"]),
            harness="hermes",
            session_id=str(active["session_id"]) if active["session_id"] else None,
        )
        if result.get("ok") and result.get("command") == "resume":
            inject = getattr(ctx, "inject_message", None)
            if callable(inject):
                inject(
                    f"{result['message']}\n\nContinue the inherited objective now. "
                    "Inspect the live worktree first and do not repeat completed work."
                )
                return "🐘 Memory restored. Continuing in Hermes."
        if result.get("ok") and result.get("command") == "pull":
            inject = getattr(ctx, "inject_message", None)
            if callable(inject):
                inject(
                    f"{result['message']}\n\n"
                    f"[Full redacted chat from {result['data']['source_harness']}]\n"
                    f"{result['data']['transcript']}\n\n"
                    "Acknowledge that Elephant told you where the user left off, "
                    "give a short summary, then wait for the user's next instruction."
                )
                return "🐘 Labeled chat restored in Hermes."
        return str(result["message"])

    ctx.register_tool(
        name="elephant_recover",
        toolset="elephant",
        schema=recover_schema,
        handler=recover_tool,
        description="Recover a coding session from another AI harness.",
    )
    ctx.register_command(
        "elephant",
        handler=elephant_command,
        description="Save, recover, inspect, and manage Elephant session memory",
    )
    ctx.register_skill("elephant", PLUGIN_ROOT / "skills" / "elephant" / "SKILL.md")
    ctx.register_skill("resume", PLUGIN_ROOT / "skills" / "resume" / "SKILL.md")
    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("pre_llm_call", pre_llm_call)
    ctx.register_hook("post_llm_call", post_llm_call)
    ctx.register_hook("pre_tool_call", pre_tool_call)
    ctx.register_hook("post_tool_call", post_tool_call)
    ctx.register_hook("on_session_end", on_session_end)
    ctx.register_hook("on_session_finalize", on_session_finalize)
