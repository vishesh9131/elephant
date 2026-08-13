#!/usr/bin/env python3
"""Native host bridge for Elephant's shared command router."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from elephant.commands import CommandRouter  # noqa: E402


def main() -> int:
    payload = json.load(sys.stdin)
    result = CommandRouter().execute(
        str(payload.get("action") or "help"),
        str(payload.get("arguments") or ""),
        cwd=str(payload.get("cwd") or Path.cwd()),
        harness=str(payload.get("harness") or "native"),
        session_id=payload.get("session_id"),
    )
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
