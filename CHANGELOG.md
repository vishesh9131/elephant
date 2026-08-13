# Changelog

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
