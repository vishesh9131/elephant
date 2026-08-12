from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from elephant.models import Capsule, Event


def default_database_path() -> Path:
    override = os.environ.get("ELEPHANT_DATABASE")
    if override:
        return Path(override).expanduser()
    plugin_data = os.environ.get("ELEPHANT_DATA_DIR")
    if plugin_data:
        return Path(plugin_data).expanduser() / "elephant.db"
    return Path.home() / ".elephant" / "elephant.db"


class Journal:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    harness TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    source TEXT NOT NULL,
                    cwd TEXT,
                    payload_json TEXT NOT NULL,
                    UNIQUE(session_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS events_project_time
                    ON events(project_id, timestamp);
                CREATE INDEX IF NOT EXISTS events_session_sequence
                    ON events(session_id, sequence);
                CREATE TABLE IF NOT EXISTS capsules (
                    capsule_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    capsule_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS capsules_project_time
                    ON capsules(project_id, created_at DESC);
                """
            )

    def append(self, event: Event) -> Event:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence "
                "FROM events WHERE session_id = ?",
                (event.session_id,),
            ).fetchone()
            stored = replace(event, sequence=int(row["next_sequence"]))
            connection.execute(
                """
                INSERT INTO events (
                    event_id, schema_version, kind, harness, session_id,
                    project_id, sequence, timestamp, confidence, source, cwd,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.event_id,
                    stored.schema_version,
                    stored.kind,
                    stored.harness,
                    stored.session_id,
                    stored.project_id,
                    stored.sequence,
                    stored.timestamp,
                    stored.confidence.value,
                    stored.source,
                    stored.cwd,
                    json.dumps(stored.payload, sort_keys=True),
                ),
            )
        return stored

    def events(self, session_id: str) -> list[Event]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY sequence",
                (session_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def sessions_for_project(self, project_id: str) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id, MAX(timestamp) AS last_seen
                FROM events WHERE project_id = ?
                GROUP BY session_id ORDER BY last_seen DESC
                """,
                (project_id,),
            ).fetchall()
        return [str(row["session_id"]) for row in rows]

    def save_capsule(self, capsule: Capsule) -> Capsule:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO capsules (
                    capsule_id, project_id, source_session_id, created_at,
                    capsule_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    capsule.capsule_id,
                    capsule.project_id,
                    capsule.source_session_id,
                    capsule.created_at,
                    json.dumps(capsule.to_dict(), sort_keys=True),
                ),
            )
        return capsule

    def latest_capsule(self, project_id: str) -> Capsule | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT capsule_json FROM capsules WHERE project_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        return Capsule.from_dict(json.loads(row["capsule_json"])) if row else None

    def iter_project_events(self, project_id: str) -> Iterable[Event]:
        for session_id in reversed(self.sessions_for_project(project_id)):
            yield from self.events(session_id)

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event.from_dict(
            {
                "event_id": row["event_id"],
                "schema_version": row["schema_version"],
                "kind": row["kind"],
                "harness": row["harness"],
                "session_id": row["session_id"],
                "project_id": row["project_id"],
                "sequence": row["sequence"],
                "timestamp": row["timestamp"],
                "confidence": row["confidence"],
                "source": row["source"],
                "cwd": row["cwd"],
                "payload": json.loads(row["payload_json"]),
            }
        )
