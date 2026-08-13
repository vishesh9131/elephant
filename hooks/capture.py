#!/usr/bin/env python3
"""Native plugin hook bridge. Users never call this directly."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from elephant.plugin_runtime import handle_hook  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    try:
        payload = json.load(sys.stdin)
        output = handle_hook(sys.argv[1], sys.argv[2], payload)
        if output:
            print(json.dumps(output, separators=(",", ":")))
    except Exception as exc:
        if os.environ.get("ELEPHANT_DEBUG"):
            print(f"Elephant capture skipped: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
