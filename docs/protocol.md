# Elephant Event Protocol

Elephant stores facts, not model-specific transcripts. Adapters normalize native
harness hooks into an append-only event stream. Schema version `1` requires:

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "kind": "tool.completed",
  "harness": "claude-code",
  "session_id": "native-session-id",
  "project_id": "repo-name-stable-hash",
  "sequence": 12,
  "timestamp": "2026-08-13T12:00:00+00:00",
  "confidence": "exact",
  "source": "native-hook",
  "cwd": "/path/to/repo",
  "payload": {}
}
```

## Event families

- `session.*`: started, resumed, interrupted, completed, ended
- `user.prompted`
- `user.noted`: an explicit user-authored handoff instruction
- `model.*`: requested, responded, failed
- `tool.*`: started, completed, failed
- `file.*`: read, changed
- `command.completed` and `verification.completed`
- `context.*`: usage, compacting
- `quota.*`: warning, exhausted

Adapters may introduce new dotted event names. Consumers must ignore unknown
events rather than rejecting the entire session.

`exact <label>` stores a redacted, gzip-compressed transcript snapshot and its
capsule in SQLite. Native prompt hooks create the label before model execution
and refresh it on later checkpoints, including quota failures. `pull <label>`
returns that transcript with its source harness and coverage; consumers must not
describe `observed` or `snapshot` coverage as complete. When Elephant is first
installed during an active Claude session, `exact` keeps the newest 256 KiB of
the host transcript and reports `snapshot` coverage rather than copying an
unbounded chat.

## Confidence

- `exact`: supplied directly by a harness or observed as a hard failure
- `estimated`: inferred from token counts, timing, or output
- `unknown`: the adapter cannot verify the signal

Elephant must never present an estimated subscription quota as exact. A harness
without quota telemetry is still protected by continuous journaling, compaction
hooks, lifecycle hooks, and hard-failure detection.

## Recovery capsule

A capsule is a derived, portable view of the journal. It contains the current
objective, last exchange, recent failures, modified files, Git identity, exact
user notes, an event watermark, and a short recent-event window. Raw harness
transcript formats are deliberately not the interchange contract because those
formats can change independently. Transcript metadata says `complete` when a
host transcript was fully archived, `snapshot` for the bounded first-install
tail, and `observed` when Elephant reconstructed the archive from captured events.
