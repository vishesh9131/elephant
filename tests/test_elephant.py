from __future__ import annotations

import tempfile
import unittest
import gzip
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from elephant.adapters import adapter_manifest
from elephant.commands import CommandRouter
from elephant.kernel import Elephant
from elephant.mcp_stdio import ElephantMCP
from elephant.models import Event, EventKind
from elephant.plugin_runtime import handle_hook
from elephant.project import project_id
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
                    "elephant_command",
                    "elephant_checkpoint",
                    "elephant_recover",
                    "elephant_status",
                    "elephant_transcript",
                },
            )
            command = server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "elephant_command",
                        "arguments": {"action": "help", "cwd": directory},
                    },
                }
            )
            payload = json.loads(command["result"]["content"][0]["text"])
            self.assertTrue(payload["ok"])
            self.assertIn("Elephant commands", payload["message"])


class ManualCommandTests(unittest.TestCase):
    def test_recovery_projects_events_newer_than_the_last_capsule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            elephant = Elephant(root / "elephant.db")
            common = {"session_id": "claude-stale", "cwd": str(root)}
            elephant.capture("claude-code", "SessionStart", common, cwd=root)
            elephant.capture(
                "claude-code",
                "UserPromptSubmit",
                {**common, "prompt": "Implement the first handoff"},
                cwd=root,
            )
            elephant.capture(
                "claude-code",
                "Stop",
                {**common, "last_assistant_message": "The first handoff is complete."},
                cwd=root,
            )
            elephant.capture(
                "claude-code",
                "UserPromptSubmit",
                {**common, "prompt": "Add crash-safe recovery"},
                cwd=root,
            )
            elephant.capture(
                "claude-code",
                "PostToolUse",
                {**common, "tool_name": "Write", "tool_input": {"file_path": "fresh.py"}},
                cwd=root,
            )

            recovered = elephant.recover(cwd=root, target_harness="codex")["capsule"]
            self.assertEqual(recovered["objective"], "Add crash-safe recovery")
            self.assertIn("fresh.py", recovered["modified_files"])
            self.assertEqual(recovered["transcript"]["coverage"], "observed")

    def test_manual_command_suite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            elephant = Elephant(root / "elephant.db")
            common = {"session_id": "manual-suite", "cwd": str(root)}
            elephant.capture("claude-code", "SessionStart", common, cwd=root)
            elephant.capture(
                "claude-code",
                "UserPromptSubmit",
                {**common, "prompt": "Build the command suite"},
                cwd=root,
            )
            router = CommandRouter(elephant)

            memorized = router.execute(
                "memorize", cwd=root, harness="claude-code", session_id="manual-suite"
            )
            self.assertTrue(memorized["ok"])
            self.assertIn("Memorized", memorized["message"])
            memory_id = memorized["data"]["capsule"]["capsule_id"]

            noted = router.execute(
                "note",
                "Run the websocket test next",
                cwd=root,
                harness="claude-code",
                session_id="manual-suite",
            )
            self.assertTrue(noted["ok"])
            self.assertIn("Run the websocket test next", noted["data"]["capsule"]["notes"])
            self.assertTrue(router.execute("status", cwd=root)["data"]["fresh"])
            self.assertEqual(len(router.execute("history", cwd=root)["data"]["memories"]), 1)
            self.assertEqual(
                router.execute("peek", memory_id, cwd=root)["data"]["capsule"]["objective"],
                "Build the command suite",
            )
            self.assertIn("Elephant commands", router.execute("help", cwd=root)["message"])
            self.assertEqual(router.execute("doctor", cwd=root)["data"]["database_check"], "ok")

            warning = router.execute("forget", "project", cwd=root)
            self.assertTrue(warning["requires_confirmation"])
            forgotten = router.execute("forget", "project --yes", cwd=root)
            self.assertTrue(forgotten["ok"])
            self.assertFalse(elephant.status(cwd=root)["protected"])

    def test_storage_commands_preview_protect_clean_and_compact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            elephant = Elephant(root / "data" / "elephant.db")
            router = CommandRouter(elephant)
            identity = project_id(root)
            now = datetime.now(timezone.utc)
            memories = {}
            for session_id, days_old in (
                ("recent", 1),
                ("old-pinned", 90),
                ("old-delete", 80),
            ):
                elephant.journal.append(
                    Event(
                        kind=EventKind.USER_PROMPTED,
                        harness="test",
                        session_id=session_id,
                        project_id=identity,
                        cwd=str(root),
                        timestamp=(now - timedelta(days=days_old)).isoformat(),
                        payload={"prompt": f"Continue {session_id}"},
                    )
                )
                memories[session_id] = elephant.checkpoint(session_id, cwd=root)

            pinned = router.execute(
                "pin", memories["old-pinned"].capsule_id, cwd=root
            )
            self.assertTrue(pinned["ok"])

            usage = router.execute("usage", cwd=root)["data"]
            self.assertEqual(usage["project_sessions"], 3)
            self.assertEqual(usage["project_pins"], 1)
            self.assertGreater(usage["total_bytes"], 0)

            preview = router.execute("clean", "30d --keep 1", cwd=root)
            self.assertTrue(preview["ok"])
            self.assertTrue(preview["data"]["dry_run"])
            self.assertEqual(
                [item["session_id"] for item in preview["data"]["candidates"]],
                ["old-delete"],
            )
            self.assertTrue(elephant.journal.events("old-delete"))

            cleaned = router.execute("clean", "30d --keep 1 --yes", cwd=root)
            self.assertTrue(cleaned["ok"])
            self.assertEqual(cleaned["data"]["sessions_deleted"], 1)
            self.assertFalse(elephant.journal.events("old-delete"))
            self.assertTrue(elephant.journal.events("old-pinned"))

            unpinned = router.execute(
                "unpin", memories["old-pinned"].capsule_id, cwd=root
            )
            self.assertTrue(unpinned["data"]["was_pinned"])
            second_clean = router.execute("clean", "30d --keep 1 --yes", cwd=root)
            self.assertEqual(second_clean["data"]["sessions_deleted"], 1)
            self.assertFalse(elephant.journal.events("old-pinned"))

            compacted = router.execute("compact", cwd=root)
            self.assertTrue(compacted["ok"])
            self.assertGreater(compacted["data"]["after_bytes"], 0)

    def test_control_prompt_does_not_replace_the_real_objective(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            elephant = Elephant(root / "elephant.db")
            common = {"session_id": "control-prompt", "cwd": str(root)}
            elephant.capture("claude-code", "SessionStart", common, cwd=root)
            elephant.capture(
                "claude-code",
                "UserPromptSubmit",
                {**common, "prompt": "Fix production authentication"},
                cwd=root,
            )
            elephant.capture(
                "claude-code",
                "UserPromptSubmit",
                {**common, "prompt": "/elephant:memorize"},
                cwd=root,
            )
            capsule = elephant.checkpoint_latest(cwd=root, session_id="control-prompt")
            self.assertEqual(capsule.objective, "Fix production authentication")

    def test_native_session_id_cannot_escape_transcript_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "data" / "elephant.db"
            elephant = Elephant(database)
            common = {"session_id": "../../outside", "cwd": str(root)}
            elephant.capture("claude-code", "SessionStart", common, cwd=root)
            elephant.capture(
                "claude-code",
                "UserPromptSubmit",
                {**common, "prompt": "Preserve this safely"},
                cwd=root,
            )
            capsule = elephant.checkpoint_latest(cwd=root, session_id="../../outside")
            archive = Path(capsule.transcript["archive"]).resolve()
            self.assertTrue(archive.is_relative_to(database.parent.resolve()))

    def test_capture_bridge_fails_open_on_bad_hook_input(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / "hooks" / "capture.py"), "claude-code", "NotAHook"],
            input="{}",
            text=True,
            capture_output=True,
            cwd=root,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


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
            ".grok-plugin/marketplace.json",
            "hooks/hooks.json",
            "mcp.json",
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
            ".github/plugin/marketplace.json",
            ".grok-plugin/marketplace.json",
            ".kiro/steering/elephant.md",
            ".openclaw/skills/resume/SKILL.md",
            ".openclaw/skills/elephant/SKILL.md",
            ".opencode/plugins/elephant.mjs",
            ".qoder-plugin/plugin.json",
            ".qoder/rules/elephant.md",
            ".windsurf/rules/elephant.md",
            "gemini-extension.json",
            "hooks/hooks.json",
            "mcp.json",
            "pi-extension/index.js",
            "plugin.yaml",
            "skills/elephant/SKILL.md",
            "commands/memorize.md",
            "commands/resume.md",
            "commands/help.md",
            "commands/status.md",
            "commands/history.md",
            "commands/peek.md",
            "commands/note.md",
            "commands/doctor.md",
            "commands/usage.md",
            "commands/clean.md",
            "commands/pin.md",
            "commands/unpin.md",
            "commands/compact.md",
            "commands/forget.md",
        )
        missing = [relative for relative in surfaces if not (root / relative).is_file()]
        self.assertEqual(missing, [])

    def test_agent_plugins_v1_manifest_uses_fixed_component_locations(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with (root / "plugin.json").open() as stream:
            manifest = json.load(stream)
        self.assertEqual(
            manifest["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertLessEqual(
            set(manifest),
            {
                "$schema",
                "name",
                "version",
                "description",
                "author",
                "homepage",
                "repository",
                "license",
                "keywords",
                "extensions",
            },
        )
        self.assertFalse((root / ".github/plugin/plugin.json").exists())
        with (root / "mcp.json").open() as stream:
            mcp = json.load(stream)
        self.assertEqual(
            mcp["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        )
        self.assertEqual(mcp["mcpServers"]["memory"]["type"], "stdio")
        self.assertEqual(
            (root / "hooks/hooks.json").read_text(),
            (root / "hooks/copilot-hooks.json").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
