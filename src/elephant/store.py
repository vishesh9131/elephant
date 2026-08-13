from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Iterator

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

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

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
                CREATE TABLE IF NOT EXISTS pins (
                    project_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    pinned_at TEXT NOT NULL,
                    PRIMARY KEY(project_id, session_id)
                );
                CREATE INDEX IF NOT EXISTS pins_project
                    ON pins(project_id);
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

    def session_stats(self, project_id: str) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT events.session_id,
                       MAX(events.timestamp) AS last_seen,
                       COUNT(*) AS event_count,
                       (
                           SELECT COUNT(*) FROM capsules
                           WHERE capsules.project_id = events.project_id
                             AND capsules.source_session_id = events.session_id
                       ) AS capsule_count,
                       EXISTS(
                           SELECT 1 FROM pins
                           WHERE pins.project_id = events.project_id
                             AND pins.session_id = events.session_id
                       ) AS pinned
                FROM events
                WHERE events.project_id = ?
                GROUP BY events.project_id, events.session_id
                ORDER BY last_seen DESC
                """,
                (project_id,),
            ).fetchall()
        return [
            {
                "session_id": str(row["session_id"]),
                "last_seen": str(row["last_seen"]),
                "event_count": int(row["event_count"]),
                "capsule_count": int(row["capsule_count"]),
                "pinned": bool(row["pinned"]),
            }
            for row in rows
        ]

    def statistics(self, project_id: str) -> dict[str, int]:
        with self.connect() as connection:
            project = connection.execute(
                """
                SELECT COUNT(*) AS events,
                       COUNT(DISTINCT session_id) AS sessions
                FROM events WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
            capsules = connection.execute(
                "SELECT COUNT(*) AS count FROM capsules WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            pins = connection.execute(
                "SELECT COUNT(*) AS count FROM pins WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            global_counts = connection.execute(
                """
                SELECT COUNT(*) AS events,
                       COUNT(DISTINCT project_id) AS projects,
                       COUNT(DISTINCT project_id || char(0) || session_id) AS sessions
                FROM events
                """
            ).fetchone()
            global_capsules = connection.execute(
                "SELECT COUNT(*) AS count FROM capsules"
            ).fetchone()
        return {
            "project_events": int(project["events"]),
            "project_sessions": int(project["sessions"]),
            "project_capsules": int(capsules["count"]),
            "project_pins": int(pins["count"]),
            "total_events": int(global_counts["events"]),
            "total_projects": int(global_counts["projects"]),
            "total_sessions": int(global_counts["sessions"]),
            "total_capsules": int(global_capsules["count"]),
        }

    def pin_session(self, project_id: str, session_id: str, pinned_at: str) -> bool:
        with self.connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM events WHERE project_id = ? AND session_id = ? LIMIT 1",
                (project_id, session_id),
            ).fetchone()
            if not exists:
                return False
            connection.execute(
                """
                INSERT INTO pins(project_id, session_id, pinned_at)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id, session_id)
                DO UPDATE SET pinned_at = excluded.pinned_at
                """,
                (project_id, session_id, pinned_at),
            )
        return True

    def unpin_session(self, project_id: str, session_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM pins WHERE project_id = ? AND session_id = ?",
                (project_id, session_id),
            )
        return cursor.rowcount > 0

    def last_event(self, session_id: str) -> Event | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY sequence DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        return self._row_to_event(row) if row else None

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

    def capsule(self, capsule_id: str) -> Capsule | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT capsule_json FROM capsules WHERE capsule_id = ?",
                (capsule_id,),
            ).fetchone()
        return Capsule.from_dict(json.loads(row["capsule_json"])) if row else None

    def capsules_for_project(self, project_id: str, limit: int = 20) -> list[Capsule]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT capsule_json FROM capsules WHERE project_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (project_id, max(1, min(int(limit), 10_000))),
            ).fetchall()
        return [Capsule.from_dict(json.loads(row["capsule_json"])) for row in rows]

    def delete_capsule(self, capsule_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM capsules WHERE capsule_id = ?", (capsule_id,)
            )
        return cursor.rowcount > 0

    def delete_session(self, session_id: str, project_id: str) -> tuple[int, int]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            capsule_count = connection.execute(
                "SELECT COUNT(*) AS count FROM capsules WHERE source_session_id = ? AND project_id = ?",
                (session_id, project_id),
            ).fetchone()["count"]
            event_count = connection.execute(
                "SELECT COUNT(*) AS count FROM events WHERE session_id = ? AND project_id = ?",
                (session_id, project_id),
            ).fetchone()["count"]
            connection.execute(
                "DELETE FROM capsules WHERE source_session_id = ? AND project_id = ?",
                (session_id, project_id),
            )
            connection.execute(
                "DELETE FROM events WHERE session_id = ? AND project_id = ?",
                (session_id, project_id),
            )
            connection.execute(
                "DELETE FROM pins WHERE session_id = ? AND project_id = ?",
                (session_id, project_id),
            )
        return int(event_count), int(capsule_count)

    def delete_project(self, project_id: str) -> tuple[int, int]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            capsule_count = connection.execute(
                "SELECT COUNT(*) AS count FROM capsules WHERE project_id = ?", (project_id,)
            ).fetchone()["count"]
            event_count = connection.execute(
                "SELECT COUNT(*) AS count FROM events WHERE project_id = ?", (project_id,)
            ).fetchone()["count"]
            connection.execute("DELETE FROM capsules WHERE project_id = ?", (project_id,))
            connection.execute("DELETE FROM events WHERE project_id = ?", (project_id,))
            connection.execute("DELETE FROM pins WHERE project_id = ?", (project_id,))
        return int(event_count), int(capsule_count)

    def compact(self) -> None:
        with sqlite3.connect(self.path, timeout=30) as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("VACUUM")
            connection.execute("PRAGMA optimize")

    def quick_check(self) -> str:
        with self.connect() as connection:
            row = connection.execute("PRAGMA quick_check").fetchone()
        return str(row[0])

    def archive_is_referenced(self, archive: str) -> bool:
        with self.connect() as connection:
            rows = connection.execute("SELECT capsule_json FROM capsules").fetchall()
        return any(
            str(Capsule.from_dict(json.loads(row["capsule_json"])).transcript.get("archive"))
            == archive
            for row in rows
        )

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
