---
description: Pull a labeled Elephant chat from another harness
argument-hint: "<label>"
---

Call `elephant_command` with action `pull`, arguments `$ARGUMENTS`, cwd
`${CLAUDE_PROJECT_DIR}`, harness `claude-code`, and session_id
`${CLAUDE_SESSION_ID}`. Read the full returned transcript as context, tell the
user which harness they left, give a short summary, then wait for their next
instruction.
