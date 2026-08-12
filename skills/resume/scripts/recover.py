#!/usr/bin/env python3
"""Elephant Resume fallback for hosts that cannot expose plugin MCP tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "src"))

from elephant.kernel import Elephant  # noqa: E402


def main() -> int:
    cwd = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    try:
        packet = Elephant().recover(cwd=cwd)
    except LookupError as exc:
        print(json.dumps({"recoverable": False, "error": str(exc)}))
        return 1
    print(json.dumps({"recoverable": True, **packet}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
