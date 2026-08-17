---
name: resume
description: Recover and continue coding-agent work captured by Elephant across Claude Code, Codex, Hermes, or another harness. Use when the user asks where a previous session stopped, wants to resume work from another agent, or mentions a lost, quota-ended, or compacted coding session.
---

# Elephant Resume

Use Elephant's recorded event journal and recovery capsule as evidence of prior
work. Never pretend the outgoing agent is still available after its quota ends.

## Recover a session

1. Determine the current project directory.
2. Call the plugin-provided `elephant_command` tool with action `resume`, that
   directory, and the current harness name. If this host loads skills but cannot
   expose plugin tools, execute the bundled `scripts/recover.py` yourself with
   the project directory. Never ask the user to open a terminal.
3. Compare the capsule's Git head, dirty flag, and modified files with the live
   worktree. Treat the worktree as authoritative when it has changed since the
   capsule.
4. Inspect recent failures before editing. Do not repeat work already represented
   by successful events or existing files.
5. Tell the user, briefly, what objective was inherited, what state the code is
   in, and the next concrete action. Then continue the coding task.

If no capsule exists, say that Elephant has no recorded session for this project.
Do not reconstruct one from guesses.

For an explicitly labeled handoff, call `elephant_command` with action `pull`
and the requested label instead. Read the returned full redacted transcript,
say which source harness it came from, summarize where the user left off, and
wait for the user's next instruction rather than automatically continuing.

## Checkpoint a session

Native plugin hooks checkpoint automatically after completed turns and at
compaction, interruption, quota failure, or session end. If the user explicitly
asks to save, call `elephant_command` with action `memorize` and the project
directory. Pass the native session ID when the host exposes it; otherwise
Elephant resolves the newest active project session.

Report the capsule ID. Do not claim an exact quota percentage unless the adapter
marks that signal as `exact`; most harnesses expose no reliable subscription
quota telemetry.

## Safety

- Do not expose secrets found in prompts, tool inputs, or outputs.
- Do not overwrite current work merely to match an older capsule.
- Verify tests and repository state rather than trusting a model summary alone.
- Keep recording new work through the active harness adapter.
