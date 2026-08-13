# Elephant privacy notice

Last updated: August 13, 2026

Elephant runs locally. It does not include analytics, advertising, telemetry,
accounts, or a hosted service. It stores redacted coding-session events,
recovery capsules, Git metadata, and optional compressed transcript copies under
`~/.elephant/` by default. `ELEPHANT_DATA_DIR` can change that location.

Elephant does not intentionally transmit this data. A coding harness, model
provider, operating system, package registry, or Git host may process data under
its own privacy terms. Users control and can delete Elephant's local data.

The `forget` command can delete one capsule, one recorded session, or all
Elephant data for the current project. `clean` can delete unpinned sessions older
than a chosen age while retaining a chosen number of recent sessions. Both
destructive operations require an explicit `--yes` confirmation; `clean` is a
read-only preview without it. `pin` protects a session from cleanup. `compact`
reclaims unused SQLite pages but does not logically delete memories. Transcript
coverage is reported as `complete` only when a host exposes its transcript;
otherwise Elephant reports an `observed` event archive rather than implying that
unseen messages were captured.

Report privacy or security concerns through the repository's private security
reporting feature or its public issue tracker.
