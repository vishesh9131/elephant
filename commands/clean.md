---
description: Preview or delete ancient Elephant sessions
argument-hint: [age] [--keep N] [--yes]
disable-model-invocation: true
---

Call `elephant_command` with action `clean`, arguments `$ARGUMENTS`, and cwd
`${CLAUDE_PROJECT_DIR}`. Never add `--yes`; only pass it when the user explicitly
typed it. With no `--yes`, return the cleanup preview and delete nothing.
