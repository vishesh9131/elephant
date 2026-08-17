from __future__ import annotations

import json
import gzip
import sys
from pathlib import Path
from typing import Any, TextIO

from elephant.commands import CommandRouter
from elephant.kernel import Elephant
from elephant.models import Capsule


class ElephantMCP:
    def __init__(self, database: str | Path | None = None) -> None:
        self.elephant = Elephant(database)

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if request_id is None:
            return None
        try:
            if method == "initialize":
                requested = request.get("params", {}).get("protocolVersion")
                result = {
                    "protocolVersion": requested or "2025-06-18",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "elephant", "version": "0.4.0"},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self.tools()}
            elif method == "tools/call":
                params = request.get("params", {})
                result = self.call_tool(str(params.get("name", "")), params.get("arguments") or {})
            else:
                return self._error(request_id, -32601, f"method not found: {method}")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:
            return self._error(request_id, -32000, str(exc))

    @staticmethod
    def tools() -> list[dict[str, Any]]:
        cwd_property = {
            "type": "string",
            "description": "Absolute path to the current coding project",
        }
        return [
            {
                "name": "elephant_command",
                "description": "Run an Elephant memory or storage command such as memorize, exact, pull, resume, help, status, history, peek, note, doctor, usage, clean, pin, unpin, compact, or forget.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "arguments": {"type": "string", "default": ""},
                        "cwd": cwd_property,
                        "harness": {"type": "string", "default": "mcp"},
                        "session_id": {"type": "string"},
                    },
                    "required": ["action", "cwd"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "elephant_recover",
                "description": "Recover the latest coding-agent handoff for this project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cwd": cwd_property,
                        "target_harness": {"type": "string"},
                        "capsule_id": {"type": "string"},
                    },
                    "required": ["cwd"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "elephant_checkpoint",
                "description": "Create a durable recovery capsule for a recorded session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "cwd": cwd_property,
                    },
                    "required": ["cwd"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "elephant_status",
                "description": "Show whether Elephant has recoverable work for this project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"cwd": cwd_property},
                    "required": ["cwd"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "elephant_transcript",
                "description": "Read a page from the archived, redacted source transcript.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cwd": cwd_property,
                        "capsule_id": {"type": "string"},
                        "offset": {"type": "integer", "minimum": 0, "default": 0},
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50000,
                            "default": 20000,
                        },
                    },
                    "required": ["cwd"],
                    "additionalProperties": False,
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "elephant_command":
                value = CommandRouter(self.elephant).execute(
                    str(arguments["action"]),
                    str(arguments.get("arguments") or ""),
                    cwd=str(arguments["cwd"]),
                    harness=str(arguments.get("harness") or "mcp"),
                    session_id=arguments.get("session_id"),
                )
            elif name == "elephant_recover":
                value = self.elephant.recover(
                    cwd=str(arguments["cwd"]),
                    target_harness=arguments.get("target_harness"),
                    capsule_id=arguments.get("capsule_id"),
                )
            elif name == "elephant_checkpoint":
                value = self.elephant.checkpoint_latest(
                    session_id=arguments.get("session_id"),
                    cwd=str(arguments["cwd"]),
                ).to_dict()
            elif name == "elephant_status":
                value = self.elephant.status(cwd=str(arguments["cwd"]))
            elif name == "elephant_transcript":
                cwd = str(arguments["cwd"])
                capsule = Capsule.from_dict(
                    self.elephant.recover(
                        cwd=cwd,
                        capsule_id=arguments.get("capsule_id"),
                    )["capsule"]
                )
                if not capsule or not capsule.transcript.get("archive"):
                    raise LookupError("no archived transcript exists for this project")
                with gzip.open(str(capsule.transcript["archive"]), "rt", encoding="utf-8") as stream:
                    transcript = stream.read()
                offset = max(0, int(arguments.get("offset", 0)))
                limit = min(50000, max(1, int(arguments.get("limit", 20000))))
                end = min(len(transcript), offset + limit)
                value = {
                    "capsule_id": capsule.capsule_id,
                    "offset": offset,
                    "next_offset": end if end < len(transcript) else None,
                    "total_characters": len(transcript),
                    "text": transcript[offset:end],
                }
            else:
                raise ValueError(f"unknown Elephant tool: {name}")
            return {
                "content": [{"type": "text", "text": json.dumps(value, indent=2, sort_keys=True)}]
            }
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": f"Elephant: {exc}"}],
                "isError": True,
            }

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }


def serve(
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    *,
    database: str | Path | None = None,
) -> None:
    server = ElephantMCP(database)
    for line in input_stream:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = server.handle(request)
        except (json.JSONDecodeError, TypeError) as exc:
            response = ElephantMCP._error(None, -32700, str(exc))
        if response is not None:
            output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
            output_stream.flush()
