#!/usr/bin/env python3
"""Deterministic Elephant command fallback for skill-only hosts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from elephant.commands import CommandRouter  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(prog="elephant")
    parser.add_argument("action", nargs="?", default="help")
    parser.add_argument("arguments", nargs="*")
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--harness", default="skill")
    parser.add_argument("--session-id")
    values, extras = parser.parse_known_args()
    result = CommandRouter().execute(
        values.action,
        [*values.arguments, *extras],
        cwd=Path(values.cwd).resolve(),
        harness=values.harness,
        session_id=values.session_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
