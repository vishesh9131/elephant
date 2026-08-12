#!/usr/bin/env python3
"""Run portable contracts, then load plugins in locally installed hosts."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(
    label: str,
    command: list[str],
    *,
    environment: dict[str, str] | None = None,
    input_text: str | None = None,
    expected: tuple[str, ...] = (),
) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode or any(value not in result.stdout for value in expected):
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"FAIL {label}")
    print(f"PASS {label}")


def main() -> int:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    environment["PATH"] = os.pathsep.join(
        (
            "/opt/homebrew/opt/node@22/bin",
            str(Path.home() / ".local" / "bin"),
            environment.get("PATH", ""),
        )
    )
    run("portable plugin contracts", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], environment=environment)
    run("OpenCode JavaScript syntax", ["node", "--check", ".opencode/plugins/elephant.mjs"])
    run("Pi JavaScript syntax", ["node", "--check", "pi-extension/index.js"])

    with tempfile.TemporaryDirectory(prefix="elephant-host-") as directory:
        host_environment = {**environment, "ELEPHANT_DATA_DIR": directory}
        if shutil.which("opencode"):
            run(
                "OpenCode live plugin load",
                ["opencode", "debug", "config", "--print-logs", "--log-level", "INFO"],
                environment=host_environment,
            )
        else:
            print("SKIP OpenCode live plugin load (binary unavailable)")

        if shutil.which("claude"):
            run("Claude plugin validation", ["claude", "plugin", "validate", "."], environment=host_environment)
        else:
            print("SKIP Claude plugin validation (binary unavailable)")

    if shutil.which("pi", path=environment["PATH"]):
        run(
            "Pi live plugin load",
            ["pi", "--mode", "rpc", "--no-session", "--approve", "--offline"],
            environment={**environment, "PI_OFFLINE": "1"},
            input_text='{"id":"commands","type":"get_commands"}\n',
            expected=('"name":"resume"', '"name":"skill:resume"'),
        )
    else:
        print("CONTRACT Pi (binary unavailable; fake host API exercised)")

    if shutil.which("copilot", path=environment["PATH"]):
        run(
            "Copilot live plugin load",
            ["copilot", "--plugin-dir", str(ROOT), "plugin", "list"],
            environment=environment,
            expected=("elephant",),
        )
    else:
        print("CONTRACT Copilot (binary unavailable; native hooks exercised by fixture)")

    if shutil.which("hermes", path=environment["PATH"]):
        run(
            "Hermes live plugin discovery",
            ["hermes", "plugins", "list", "--plain", "--no-bundled"],
            environment=environment,
            expected=("elephant",),
        )
    else:
        print("CONTRACT Hermes (binary unavailable; fake host API exercised)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
