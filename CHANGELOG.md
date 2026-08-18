# Changelog

## 0.4.4 - 2026-08-18

- Let Codex `exact <label>` bootstrap a bounded snapshot of the active chat when
  Elephant was installed before its lifecycle hooks could journal the session.
- Match Codex transcripts by exact project working directory and recent activity
  so a label can never attach to an older or unrelated chat.

## 0.4.3 - 2026-08-17

- Treat the first `exact` after a mid-session install as a bounded transcript
  snapshot instead of claiming complete coverage.
- Keep the newest 256 KiB of redacted chat and report the snapshot limit and
  truncation state in transcript metadata.

## 0.4.2 - 2026-08-17

- Capture Claude Code `UserPromptExpansion` events so `/elephant:exact <label>`
  can save the active chat immediately after a mid-session install or reload.
- Add a regression test proving the slash-command hook records the current
  session and complete transcript before the MCP command runs.

## 0.4.1 - 2026-08-17

- Isolate Claude Code components from the root Agent Plugins/Copilot hook
  manifest so Claude no longer rejects lower-case hook event names.

## 0.4.0 - 2026-08-17

- Add durable `exact <label>` full-chat snapshots and cross-harness
  `pull <label>` recovery, including prompt-hook capture before quota failures.
- Support Python 3.10 plugin hosts instead of failing on the 3.11-only
  `enum.StrEnum` import.

## 0.3.0 - 2026-08-13

- Add the shared `elephant` command router with memorize, resume, help, status,
  history, peek, note, doctor, usage, clean, pin, unpin, compact, and confirmed
  forget operations.
- Add preview-first cleanup for ancient sessions, pin protection, disk-usage
  reporting, and safe SQLite compaction.
- Add Claude plugin commands, the Codex-compatible `$elephant` skill, and native
  `/elephant` routing for Hermes and Pi.
- Rebuild stale recovery capsules from newer journal events so abrupt quota
  failures preserve in-progress prompts and tool work.
- Archive an exact host transcript when available and an observed, redacted
  event transcript otherwise, with explicit coverage metadata.
- Bound persisted payload sizes, sanitize transcript archive paths, make capture
  hooks fail open, and add scoped deletion for capsule, session, and project data.

## 0.2.1 - 2026-08-13

- Adopt the Agent Plugins v1.0.0 root manifest and fixed component locations.
- Add a portable `mcp.json` while retaining native harness MCP configurations.
- Move Copilot hook discovery to `hooks/hooks.json` without changing the nine
  lifecycle handlers.

## 0.2.0 - 2026-08-13

- Add native lifecycle capture for Claude Code, Codex, Hermes, OpenCode, Pi,
  and GitHub Copilot CLI.
- Add automatic cross-harness recovery capsules and the Elephant Resume skill.
- Add Claude, Codex, and Copilot marketplace catalogs plus Gemini, Pi, and
  Hermes install surfaces.
- Add live-host and cross-harness conformance tests.
