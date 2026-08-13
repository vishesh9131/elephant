---
description: Permanently delete selected local Elephant memory
argument-hint: <memory-id|session ID|project> [--yes]
disable-model-invocation: true
---

Call `elephant_command` with action `forget`, arguments `$ARGUMENTS`, and cwd
`${CLAUDE_PROJECT_DIR}`. Never add `--yes`; only pass it when the user explicitly
typed it. Return the confirmation warning or deletion result.
