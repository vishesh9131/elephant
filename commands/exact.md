---
description: Save the full redacted chat under a durable Elephant label
argument-hint: <label>
disable-model-invocation: true
---

Call `elephant_command` with action `exact`, arguments `$ARGUMENTS`, cwd
`${CLAUDE_PROJECT_DIR}`, harness `claude-code`, and session_id
`${CLAUDE_SESSION_ID}`. Return its message exactly.
