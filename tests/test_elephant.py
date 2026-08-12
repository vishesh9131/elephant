from __future__ import annotations

import tempfile
import unittest
import gzip
import json
from pathlib import Path

from elephant.adapters import adapter_manifest
from elephant.kernel import Elephant
from elephant.mcp_stdio import ElephantMCP
from elephant.models import Event, EventKind
from elephant.plugin_runtime import handle_hook
from elephant.redaction import redact
from elephant.store import Journal


class JournalTests(unittest.TestCase):
    def test_sequences_are_monotonic_per_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory) / "events.db")
            first = journal.append(
                Event(
                    kind=EventKind.SESSION_STARTED,
                    harness="test",
                    session_id="s1",
                    project_id="p1",
                )
            )
            second = journal.append(
                Event(
                    kind=EventKind.USER_PROMPTED,
                    harness="test",
                    session_id="s1",
                    project_id="p1",
                    payload={"prompt": "ship it"},
                )
            )

            self.assertEqual((first.sequence, second.sequence), (1, 2))
            self.assertEqual(journal.events("s1")[1].payload["prompt"], "ship it")


class RedactionTests(unittest.TestCase):
    def test_nested_secrets_are_removed(self) -> None:
        result = redact(
            {
                "header": "Bearer abcdefghijklmnopqrstuvwxyz",
                "nested": ["ghp_abcdefghijklmnopqrstuvwxyz123456"],
                "api_key": "plain-value-that-must-not-survive",
            }
        )
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz", str(result))
        self.assertNotIn("plain-value", str(result))
        self.assertIn("[REDACTED]", str(result))


class HandoffTests(unittest.TestCase):
    def test_claude_quota_failure_recovers_in_codex(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = root / "claude-session.jsonl"
            transcript.write_text(
                '{"role":"user","content":"Implement durable handoff"}\n'
                '{"role":"assistant","content":"Working on kernel.py","api_key":"secret-value"}\n'
            )
            elephant = Elephant(root / "elephant.db")
            common = {
                "session_id": "claude-session",
                "cwd": str(root),
                "transcript_path": str(transcript),
            }

            elephant.capture("claude-code", "SessionStart", common, cwd=root)
            elephant.capture(
                "claude-code",
                "UserPromptSubmit",
                {**common, "prompt": "Implement durable handoff"},
                cwd=root,
            )
            elephant.capture(
                "claude-code",
                "PostToolUse",
                {**common, "tool_name": "Write", "tool_input": {"file_path": "kernel.py"}},
                cwd=root,
            )
            events, capsule = elephant.capture(
                "claude-code",
                "StopFailure",
                {**common, "failure_type": "rate_limit", "error": "Rate limit reached"},
                cwd=root,
            )

            self.assertEqual(events[0].kind, EventKind.QUOTA_EXHAUSTED)
            self.assertIsNotNone(capsule)
            packet = elephant.recover(cwd=root, target_harness="codex")
            recovered = packet["capsule"]
            self.assertEqual(packet["target_harness"], "codex")
            self.assertEqual(recovered["objective"], "Implement durable handoff")
            self.assertEqual(recovered["source_harness"], "claude-code")
            self.assertGreaterEqual(recovered["event_count"], 4)
            self.assertIn("Rate limit reached", recovered["recent_failures"])
            self.assertIn("kernel.py", recovered["modified_files"])
            archive = Path(recovered["transcript"]["archive"])
            self.assertTrue(archive.is_file())
            with gzip.open(archive, "rt") as stream:
                archived = stream.read()
            self.assertIn("Implement durable handoff", archived)
            self.assertNotIn("secret-value", archived)

    def test_priority_adapter_capabilities_are_declared(self) -> None:
        manifest = adapter_manifest()
        self.assertEqual(set(manifest), {"claude-code", "codex", "hermes", "generic"})
        self.assertTrue(manifest["claude-code"]["native_hooks"])
        self.assertTrue(manifest["hermes"]["context_usage"])
        self.assertFalse(manifest["codex"]["quota_usage"])

    def test_plugin_injects_previous_session_on_start(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "elephant.db"
            elephant = Elephant(database)
            old = {"session_id": "old", "cwd": str(root)}
            elephant.capture("claude-code", "SessionStart", old, cwd=root)
            elephant.capture(
                "claude-code",
                "UserPromptSubmit",
                {**old, "prompt": "Finish the portability adapters"},
                cwd=root,
            )
            elephant.capture(
                "claude-code",
                "Stop",
                {**old, "last_assistant_message": "Claude completed the plugin core."},
                cwd=root,
            )

            output = handle_hook(
                "codex",
                "SessionStart",
                {"session_id": "new", "cwd": str(root)},
                database=database,
            )
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Finish the portability adapters", context)
            self.assertIn("Claude completed the plugin core", context)

    def test_dependency_free_mcp_exposes_recovery_tools(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            server = ElephantMCP(Path(directory) / "elephant.db")
            response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            names = {tool["name"] for tool in response["result"]["tools"]}
            self.assertEqual(
                names,
                {
                    "elephant_checkpoint",
                    "elephant_recover",
                    "elephant_status",
                    "elephant_transcript",
                },
            )


class PluginContractTests(unittest.TestCase):
    def test_all_json_manifests_parse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifests = (
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
            ".mcp.json",
            ".agents/plugins/marketplace.json",
            ".devin-plugin/plugin.json",
            ".github/plugin/marketplace.json",
            ".github/plugin/plugin.json",
            ".grok-plugin/marketplace.json",
            ".qoder-plugin/plugin.json",
            "gemini-extension.json",
            "hooks/claude-hooks.json",
            "hooks/copilot-hooks.json",
            "hooks/qoder-hooks.json",
            "opencode.json",
            "package.json",
            "plugin.json",
        )
        for relative in manifests:
            with self.subTest(manifest=relative):
                with (root / relative).open() as stream:
                    self.assertIsInstance(json.load(stream), dict)

    def test_ponytail_style_platform_surfaces_are_present(self) -> None:
        root = Path(__file__).resolve().parents[1]
        surfaces = (
            "AGENTS.md",
            ".agents/plugins/marketplace.json",
            ".agents/rules/elephant.md",
            ".claude-plugin/plugin.json",
            ".clinerules/elephant.md",
            ".codex-plugin/plugin.json",
            ".cursor/rules/elephant.mdc",
            ".devin-plugin/plugin.json",
            ".github/copilot-instructions.md",
            ".github/plugin/plugin.json",
            ".grok-plugin/marketplace.json",
            ".kiro/steering/elephant.md",
            ".openclaw/skills/resume/SKILL.md",
            ".opencode/plugins/elephant.mjs",
            ".qoder-plugin/plugin.json",
            ".qoder/rules/elephant.md",
            ".windsurf/rules/elephant.md",
            "gemini-extension.json",
            "pi-extension/index.js",
            "plugin.yaml",
        )
        missing = [relative for relative in surfaces if not (root / relative).is_file()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
