---
name: elephant
description: Save, label, pull, inspect, recover, protect, clean, and compact Elephant coding-session memory across AI harnesses.
---

Read `../../../skills/elephant/SKILL.md` completely and follow it as the single
authoritative Elephant workflow. Resolve its `scripts/command.py` path relative
to that canonical skill file. Do not search for another Elephant skill.

In particular, `exact <label>` saves the active chat under an opaque
user-chosen label; the label is never a session ID. In Codex, run the canonical
bundled command script with `exact`, that label, the absolute current project
directory, and harness `codex` before calling the possibly stale MCP process.
Never ask the user to run the fallback.
