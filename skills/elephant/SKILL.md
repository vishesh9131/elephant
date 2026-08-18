---
name: elephant
description: Save, label, pull, inspect, recover, protect, clean, and compact Elephant coding-session memory across Claude Code, Codex, Hermes, Pi, OpenCode, and other harnesses. Use when the user invokes or mentions Elephant commands such as memorize, exact, pull, resume, help, status, history, peek, note, doctor, usage, clean, pin, unpin, compact, or forget; asks to continue work from another coding agent; wants to preserve a session before switching agents; or wants to manage Elephant disk usage.
---

# Elephant

Interpret the text following the skill invocation as an Elephant command. Hosts
that support argument substitution expose this text as `$ARGUMENTS`. Use `help`
when it is empty.

1. Determine the absolute current project directory.
2. Call `elephant_command` with the first argument as `action`, the remaining
   text as `arguments`, the project directory as `cwd`, and this harness name.
3. If the tool is unavailable, execute `scripts/command.py` with the same action,
   remaining arguments, `--cwd`, and `--harness`. Never ask the user to operate
   Elephant from a terminal.
4. Return the command's `message` concisely.

For `resume`, treat the capsule as evidence, compare it with the live Git
worktree, state the inherited objective briefly, and immediately continue the
unfinished coding task. Do not repeat completed work.

For `exact`, treat its argument as an opaque user-chosen label, never as a
session ID. Report that label and the transcript coverage exactly as returned by
the tool. Native prompt hooks also handle this command, so the label is saved
even if the model cannot answer because its quota is exhausted. In Codex, the
tool can bootstrap the active project chat when Elephant was just installed and
its hooks have not captured a turn yet. `snapshot` coverage is that bounded
transcript tail; do not describe it as a complete chat.

For `pull`, read all of `data.transcript` as prior-chat context, but treat the
live Git worktree as authoritative. Tell the user, “Elephant told me where you
left off in <source_harness>,” give a short summary, and stop so the user can
choose the next work. Do not claim the chat is complete unless `coverage` is
`complete`.

For `peek`, show the memory without continuing it. For `clean` and `forget`,
never add `--yes` yourself; require the user's explicit confirmation. `clean`
without `--yes` is a safe preview. Never claim complete transcript coverage
unless the result says `complete`.
