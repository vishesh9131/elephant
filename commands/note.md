---
description: Add an exact user instruction to Elephant memory
argument-hint: <message>
disable-model-invocation: true
---

Call `elephant_command` with action `note`, arguments `$ARGUMENTS`, cwd
`${CLAUDE_PROJECT_DIR}`, harness `claude-code`, and session_id
`${CLAUDE_SESSION_ID}`. Return its message.
