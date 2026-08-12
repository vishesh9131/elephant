from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from elephant.kernel import Elephant


ROOT = Path(__file__).resolve().parents[1]


class JavaScriptPluginConformanceTests(unittest.TestCase):
    def test_opencode_pi_cross_harness_flow(self) -> None:
        result = subprocess.run(
            ["node", str(ROOT / "tests" / "plugin_conformance.mjs")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OpenCode → Pi → secondary recovery: pass", result.stdout)


class CopilotConformanceTests(unittest.TestCase):
    def test_every_documented_copilot_hook_reaches_the_journal(self) -> None:
        expected = {
            "sessionStart",
            "sessionEnd",
            "userPromptSubmitted",
            "preToolUse",
            "postToolUse",
            "postToolUseFailure",
            "agentStop",
            "errorOccurred",
            "preCompact",
        }
        manifest = json.loads((ROOT / "hooks" / "copilot-hooks.json").read_text())
        self.assertEqual(set(manifest["hooks"]), expected)

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            workspace = temporary / "workspace"
            workspace.mkdir()
            environment = {
                **os.environ,
                "ELEPHANT_DATA_DIR": str(temporary / "data"),
                "PLUGIN_ROOT": str(ROOT),
            }
            fixtures = {
                "sessionStart": {},
                "userPromptSubmitted": {"prompt": "Verify Copilot native hooks"},
                "preToolUse": {"toolName": "edit", "toolArgs": {"file_path": "copilot.py"}},
                "postToolUse": {"toolName": "edit", "toolResult": "ok"},
                "postToolUseFailure": {"toolName": "test", "errorMessage": "one expected failure"},
                "agentStop": {"message": "Copilot adapter verified."},
                "errorOccurred": {"errorMessage": "provider disconnected"},
                "preCompact": {},
                "sessionEnd": {},
            }
            for name in fixtures:
                hook = manifest["hooks"][name][0]
                payload = {
                    "sessionId": "copilot-session",
                    "cwd": str(workspace),
                    "transcriptPath": str(temporary / "copilot.jsonl"),
                    **fixtures[name],
                }
                result = subprocess.run(
                    hook["bash"],
                    shell=True,
                    input=json.dumps(payload),
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=hook["timeoutSec"],
                )
                self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")

            elephant = Elephant(temporary / "data" / "elephant.db")
            events = elephant.journal.events("copilot-session")
            self.assertEqual(len(events), len(expected))
            self.assertEqual(events[1].payload["prompt"], "Verify Copilot native hooks")
            self.assertEqual(events[2].payload["tool_name"], "edit")
            packet = elephant.recover(cwd=workspace, target_harness="codex")
            self.assertEqual(packet["capsule"]["objective"], "Verify Copilot native hooks")
            self.assertIn("provider disconnected", packet["capsule"]["recent_failures"])


class SecondaryHarnessConformanceTests(unittest.TestCase):
    def test_hermes_native_contract_and_skill_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            workspace = temporary / "workspace"
            workspace.mkdir()
            data = temporary / "data"
            with patch.dict(os.environ, {"ELEPHANT_DATA_DIR": str(data)}):
                spec = importlib.util.spec_from_file_location("elephant_hermes_plugin", ROOT / "__init__.py")
                module = importlib.util.module_from_spec(spec)
                assert spec.loader
                spec.loader.exec_module(module)

                class HermesContext:
                    def __init__(self) -> None:
                        self.hooks = {}
                        self.commands = {}
                        self.tools = {}
                        self.skills = {}

                    def register_hook(self, name, handler):
                        self.hooks[name] = handler

                    def register_command(self, name, **values):
                        self.commands[name] = values

                    def register_tool(self, **values):
                        self.tools[values["name"]] = values

                    def register_skill(self, name, path):
                        self.skills[name] = path

                context = HermesContext()
                module.register(context)
                self.assertEqual(len(context.hooks), 7)
                self.assertIn("elephant_recover", context.tools)
                self.assertIn("elephant", context.commands)

                common = {"session_id": "hermes-session", "cwd": str(workspace)}
                context.hooks["on_session_start"](**common)
                context.hooks["pre_llm_call"](**common, prompt="Verify Hermes native hooks")
                context.hooks["post_llm_call"](**common, response="Hermes adapter verified.")
                context.hooks["on_session_finalize"](**common)

                result = subprocess.run(
                    [sys.executable, str(ROOT / "skills" / "resume" / "scripts" / "recover.py"), str(workspace)],
                    cwd=ROOT,
                    env={**os.environ, "ELEPHANT_DATA_DIR": str(data)},
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                recovered = json.loads(result.stdout)
                self.assertTrue(recovered["recoverable"])
                self.assertEqual(recovered["capsule"]["source_harness"], "hermes")
                self.assertEqual(recovered["capsule"]["objective"], "Verify Hermes native hooks")


if __name__ == "__main__":
    unittest.main()
