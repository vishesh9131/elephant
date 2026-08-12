from __future__ import annotations

from elephant.adapters.base import Adapter
from elephant.adapters.claude_code import ClaudeCodeAdapter
from elephant.adapters.codex import CodexAdapter
from elephant.adapters.generic import GenericAdapter
from elephant.adapters.hermes import HermesAdapter


_ADAPTERS: dict[str, Adapter] = {
    "claude-code": ClaudeCodeAdapter(),
    "claude": ClaudeCodeAdapter(),
    "codex": CodexAdapter(),
    "hermes": HermesAdapter(),
    "generic": GenericAdapter(),
}


def get_adapter(name: str) -> Adapter:
    normalized = name.strip().lower()
    return _ADAPTERS.get(normalized) or GenericAdapter(normalized)


def adapter_manifest() -> dict[str, dict[str, bool]]:
    canonical = ("claude-code", "codex", "hermes", "generic")
    return {name: _ADAPTERS[name].capabilities.to_dict() for name in canonical}


__all__ = ["adapter_manifest", "get_adapter"]
