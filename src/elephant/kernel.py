from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import gzip
import os
from pathlib import Path
import re
import shutil
from typing import Any, Mapping
from uuid import uuid4

from elephant.adapters import adapter_manifest, get_adapter
from elephant.artifacts import archive_transcript
from elephant.capsule import build_capsule, is_control_prompt
from elephant.models import Capsule, Event, EventKind, utc_now
from elephant.project import project_id
from elephant.redaction import redact
from elephant.store import Journal


class Elephant:
    def __init__(self, database: str | Path | None = None) -> None:
        self.journal = Journal(database)

    def capture(
        self,
        harness: str,
        event_name: str,
        raw: Mapping[str, Any],
        *,
        cwd: str | Path,
    ) -> tuple[list[Event], Capsule | None]:
        cwd_string = str(Path(cwd).expanduser().resolve())
        identity = project_id(cwd_string)
        adapter = get_adapter(harness)
        normalized = adapter.normalize(
            event_name,
            raw,
            project_id=identity,
            cwd=cwd_string,
        )
        stored: list[Event] = []
        capsule: Capsule | None = None
        for event in normalized:
            safe = replace(event, payload=redact(event.payload))
            saved = self.journal.append(safe)
            stored.append(saved)
            label = self._exact_label(saved)
            if label:
                try:
                    capsule = self.exact(
                        label, cwd=cwd_string, session_id=saved.session_id
                    )["capsule"]
                except (LookupError, ValueError):
                    pass
            if self._checkpoint_worthy(saved):
                capsule = self.checkpoint(saved.session_id, cwd=cwd_string)
                for current_label in self.journal.labels_for_session(
                    identity, saved.session_id
                ):
                    self._store_exact(current_label, capsule)
        return stored, capsule

    def checkpoint(self, session_id: str, *, cwd: str | Path) -> Capsule:
        events = self.journal.events(session_id)
        if not events:
            raise LookupError(f"no Elephant session exists with id {session_id}")
        capsule = build_capsule(events, str(cwd))
        transcript = archive_transcript(events, self.journal.path.parent)
        if transcript:
            capsule = replace(capsule, transcript=transcript)
        return self.journal.save_capsule(capsule)

    def checkpoint_latest(
        self,
        *,
        cwd: str | Path,
        session_id: str | None = None,
    ) -> Capsule:
        identity = project_id(cwd)
        selected = session_id
        if selected:
            events = self.journal.events(selected)
            if not events or events[-1].project_id != identity:
                raise LookupError(f"no Elephant session exists with id {selected} for this project")
        else:
            candidate = self._latest_meaningful_session(identity)
            if candidate is None:
                sessions = self.journal.sessions_for_project(identity)
                if not sessions:
                    raise LookupError("no Elephant session exists for this project")
                selected = sessions[0]
            else:
                selected = candidate[0]
        return self.checkpoint(selected, cwd=cwd)

    def recover(
        self,
        *,
        cwd: str | Path,
        target_harness: str | None = None,
        capsule_id: str | None = None,
    ) -> dict[str, Any]:
        identity = project_id(cwd)
        if capsule_id:
            capsule = self.journal.capsule(capsule_id)
            if capsule is None or capsule.project_id != identity:
                raise LookupError(f"no Elephant memory exists with id {capsule_id} for this project")
        else:
            capsule = self._freshest_capsule(identity, cwd)
            if capsule is None:
                raise LookupError("no Elephant session exists for this project")
        return {
            "capsule": capsule.to_dict(),
            "target_harness": target_harness,
            "resume_instructions": [
                "Compare the capsule Git head and dirty files with the current worktree.",
                "Inspect recent failures before changing code.",
                "Continue the objective; do not repeat completed work.",
                "Record new progress through Elephant hooks.",
            ],
        }

    def status(self, *, cwd: str | Path) -> dict[str, Any]:
        identity = project_id(cwd)
        capsule = self.journal.latest_capsule(identity)
        candidate = self._latest_meaningful_session(identity)
        last_event = candidate[2] if candidate else None
        fresh = bool(
            capsule
            and (
                last_event is None
                or last_event.timestamp <= capsule.created_at
            )
        )
        return {
            "project_id": identity,
            "protected": capsule is not None or candidate is not None,
            "fresh": fresh,
            "database": str(self.journal.path),
            "capsule": capsule.to_dict() if capsule else None,
            "latest_session_id": candidate[0] if candidate else None,
            "latest_event": last_event.to_dict() if last_event else None,
        }

    def history(self, *, cwd: str | Path, limit: int = 10) -> list[dict[str, Any]]:
        identity = project_id(cwd)
        memories: list[dict[str, Any]] = []
        seen_sessions: set[str] = set()
        for capsule in self.journal.capsules_for_project(identity, limit=100):
            if capsule.source_session_id in seen_sessions:
                continue
            seen_sessions.add(capsule.source_session_id)
            memories.append(capsule.to_dict())
            if len(memories) >= max(1, min(int(limit), 50)):
                break
        return memories

    def note(
        self,
        text: str,
        *,
        cwd: str | Path,
        harness: str = "manual",
        session_id: str | None = None,
    ) -> Capsule:
        note = text.strip()
        if not note:
            raise ValueError("note text is required")
        identity = project_id(cwd)
        selected = session_id
        if not selected:
            candidate = self._latest_meaningful_session(identity)
            selected = candidate[0] if candidate else f"manual-{uuid4()}"
        event = Event(
            kind=EventKind.USER_NOTED,
            harness=harness,
            session_id=selected,
            project_id=identity,
            payload=redact({"note": note}),
            source="manual-command",
            cwd=str(Path(cwd).expanduser().resolve()),
        )
        self.journal.append(event)
        return self.checkpoint(selected, cwd=cwd)

    def exact(
        self,
        label: str,
        *,
        cwd: str | Path,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        normalized = self._label(label)
        capsule = self.checkpoint_latest(cwd=cwd, session_id=session_id)
        existing = self.journal.labeled_memory(capsule.project_id, normalized)
        if existing and existing["source_session_id"] != capsule.source_session_id:
            raise ValueError(f"label already belongs to another session: {normalized}")
        self._store_exact(normalized, capsule)
        self.journal.pin_session(capsule.project_id, capsule.source_session_id, utc_now())
        return {
            "label": normalized,
            "coverage": str(capsule.transcript.get("coverage") or "unavailable"),
            "capsule": capsule,
        }

    def pull(
        self,
        label: str,
        *,
        cwd: str | Path,
        target_harness: str | None = None,
    ) -> dict[str, Any]:
        normalized = self._label(label)
        memory = self.journal.labeled_memory(project_id(cwd), normalized)
        if memory is None:
            raise LookupError(f"no Elephant label exists for this project: {normalized}")
        capsule = memory["capsule"]
        return {
            "label": memory["label"],
            "source_harness": memory["source_harness"],
            "source_session_id": memory["source_session_id"],
            "target_harness": target_harness,
            "coverage": memory["coverage"],
            "capsule": capsule.to_dict(),
            "transcript": gzip.decompress(memory["transcript_gzip"]).decode(
                "utf-8", errors="replace"
            ),
        }

    def doctor(self, *, cwd: str | Path) -> dict[str, Any]:
        status = self.status(cwd=cwd)
        parent = self.journal.path.parent
        return {
            **status,
            "database_check": self.journal.quick_check(),
            "data_directory_exists": parent.is_dir(),
            "data_directory_writable": parent.is_dir() and os.access(parent, os.W_OK),
            "adapters": self.adapters(),
        }

    def usage(self, *, cwd: str | Path) -> dict[str, Any]:
        identity = project_id(cwd)
        database_files = [
            self.journal.path,
            Path(f"{self.journal.path}-wal"),
            Path(f"{self.journal.path}-shm"),
        ]
        database_bytes = sum(
            path.stat().st_size
            for path in database_files
            if path.is_file() and not path.is_symlink()
        )
        transcript_root = self.journal.path.parent / "transcripts"
        transcript_bytes = self._tree_size(transcript_root)
        capsules = self.journal.capsules_for_project(identity, limit=10_000)
        project_transcript_bytes = self._archive_bytes(capsules)
        counts = self.journal.statistics(identity)
        return {
            **counts,
            "database": str(self.journal.path),
            "database_bytes": database_bytes,
            "transcript_bytes": transcript_bytes,
            "project_transcript_bytes": project_transcript_bytes,
            "total_bytes": database_bytes + transcript_bytes,
        }

    def pin(self, *, cwd: str | Path, capsule_id: str | None = None) -> dict[str, Any]:
        identity = project_id(cwd)
        capsule = self._select_capsule(identity, capsule_id)
        if not self.journal.pin_session(identity, capsule.source_session_id, utc_now()):
            raise LookupError(
                f"no Elephant session exists with id {capsule.source_session_id} for this project"
            )
        return {
            "capsule_id": capsule.capsule_id,
            "session_id": capsule.source_session_id,
            "pinned": True,
        }

    def unpin(self, *, cwd: str | Path, capsule_id: str | None = None) -> dict[str, Any]:
        identity = project_id(cwd)
        capsule = self._select_capsule(identity, capsule_id)
        removed = self.journal.unpin_session(identity, capsule.source_session_id)
        return {
            "capsule_id": capsule.capsule_id,
            "session_id": capsule.source_session_id,
            "pinned": False,
            "was_pinned": removed,
        }

    def clean(
        self,
        *,
        cwd: str | Path,
        older_than: timedelta,
        keep: int = 10,
        execute: bool = False,
    ) -> dict[str, Any]:
        if older_than.total_seconds() < 0:
            raise ValueError("cleanup age cannot be negative")
        if keep < 0:
            raise ValueError("--keep cannot be negative")
        identity = project_id(cwd)
        cutoff = datetime.now(timezone.utc) - older_than
        sessions = self.journal.session_stats(identity)
        capsules_by_session: dict[str, list[Capsule]] = {}
        for capsule in self.journal.capsules_for_project(identity, limit=10_000):
            capsules_by_session.setdefault(capsule.source_session_id, []).append(capsule)
        candidates: list[dict[str, object]] = []
        for index, item in enumerate(sessions):
            last_seen = datetime.fromisoformat(str(item["last_seen"]))
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            if index < keep or bool(item["pinned"]) or last_seen >= cutoff:
                continue
            candidates.append(
                {
                    **item,
                    "archive_bytes": self._archive_bytes(
                        capsules_by_session.get(str(item["session_id"]), [])
                    ),
                }
            )

        result: dict[str, Any] = {
            "dry_run": not execute,
            "older_than_seconds": int(older_than.total_seconds()),
            "keep": keep,
            "cutoff": cutoff.isoformat(),
            "candidates": candidates,
            "sessions_deleted": 0,
            "events_deleted": 0,
            "capsules_deleted": 0,
            "archives_deleted": 0,
            "reclaimable_archive_bytes": sum(
                int(item["archive_bytes"]) for item in candidates
            ),
        }
        if not execute:
            return result
        for item in candidates:
            deleted = self.forget(
                "session", cwd=cwd, session_id=str(item["session_id"])
            )
            result["sessions_deleted"] += 1
            result["events_deleted"] += deleted["events_deleted"]
            result["capsules_deleted"] += deleted["capsules_deleted"]
            result["archives_deleted"] += deleted["archives_deleted"]
        return result

    def compact(self) -> dict[str, Any]:
        before = self._database_size()
        self.journal.compact()
        after = self._database_size()
        return {
            "database": str(self.journal.path),
            "before_bytes": before,
            "after_bytes": after,
            "reclaimed_bytes": max(0, before - after),
        }

    def forget(
        self,
        target: str,
        *,
        cwd: str | Path,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        identity = project_id(cwd)
        normalized = target.strip()
        if normalized == "project":
            capsules = self.journal.capsules_for_project(identity, limit=10_000)
            events, capsule_count = self.journal.delete_project(identity)
            removed = self._remove_archives(capsules)
            transcript_root = self.journal.path.parent / "transcripts"
            children = transcript_root.glob(f"{identity}-*") if transcript_root.is_dir() else ()
            for child in children:
                self._remove_tree(child, transcript_root)
            return {
                "scope": "project",
                "events_deleted": events,
                "capsules_deleted": capsule_count,
                "archives_deleted": removed,
            }
        if normalized == "session":
            if not session_id:
                raise ValueError("session id is required")
            capsules = [
                item
                for item in self.journal.capsules_for_project(identity, limit=10_000)
                if item.source_session_id == session_id
            ]
            events, capsule_count = self.journal.delete_session(session_id, identity)
            if not events and not capsule_count:
                raise LookupError(f"no Elephant session exists with id {session_id} for this project")
            return {
                "scope": "session",
                "session_id": session_id,
                "events_deleted": events,
                "capsules_deleted": capsule_count,
                "archives_deleted": self._remove_archives(capsules),
            }
        capsule = self.journal.capsule(normalized)
        if capsule is None or capsule.project_id != identity:
            raise LookupError(f"no Elephant memory exists with id {normalized} for this project")
        deleted = self.journal.delete_capsule(normalized)
        return {
            "scope": "capsule",
            "capsule_id": normalized,
            "capsules_deleted": int(deleted),
            "archives_deleted": self._remove_archives([capsule]),
        }

    @staticmethod
    def adapters() -> dict[str, dict[str, bool]]:
        return adapter_manifest()

    def _freshest_capsule(self, identity: str, cwd: str | Path) -> Capsule | None:
        capsule = self.journal.latest_capsule(identity)
        candidate = self._latest_meaningful_session(identity)
        if candidate is None:
            return capsule
        session_id, _events, last_event = candidate
        if capsule is None or last_event.timestamp > capsule.created_at:
            return self.checkpoint(session_id, cwd=cwd)
        return capsule

    def _select_capsule(self, identity: str, capsule_id: str | None) -> Capsule:
        capsule = (
            self.journal.capsule(capsule_id)
            if capsule_id
            else self.journal.latest_capsule(identity)
        )
        if capsule is None or capsule.project_id != identity:
            suffix = f" with id {capsule_id}" if capsule_id else ""
            raise LookupError(f"no Elephant memory exists{suffix} for this project")
        return capsule

    def _store_exact(self, label: str, capsule: Capsule) -> None:
        archive = capsule.transcript.get("archive")
        if not archive:
            raise LookupError("no archived transcript exists for this session")
        self.journal.save_labeled_memory(
            label,
            capsule,
            Path(str(archive)).read_bytes(),
            str(capsule.transcript.get("coverage") or "unavailable"),
        )

    @staticmethod
    def _label(value: str) -> str:
        label = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", label):
            raise ValueError(
                "label must be 1-64 letters, numbers, dots, underscores, or hyphens"
            )
        return label

    @staticmethod
    def _exact_label(event: Event) -> str | None:
        if event.kind != EventKind.USER_PROMPTED:
            return None
        prompt = str(event.payload.get("prompt") or event.payload.get("text") or "")
        match = re.fullmatch(
            r"\s*(?:@elephant\s+|/elephant(?::|\s+)|\$?elephant\s+)exact\s+(\S+)\s*",
            prompt,
            re.IGNORECASE,
        )
        return match.group(1) if match else None

    def _latest_meaningful_session(
        self, identity: str
    ) -> tuple[str, list[Event], Event] | None:
        for session_id in self.journal.sessions_for_project(identity):
            events = self.journal.events(session_id)
            meaningful = [event for event in events if self._recovery_worthy(event)]
            if meaningful:
                return session_id, events, meaningful[-1]
        return None

    @staticmethod
    def _recovery_worthy(event: Event) -> bool:
        if event.kind == EventKind.USER_PROMPTED:
            prompt = str(event.payload.get("prompt") or event.payload.get("text") or "")
            return bool(prompt and not is_control_prompt(prompt))
        return event.kind in {
            EventKind.USER_NOTED,
            EventKind.MODEL_REQUESTED,
            EventKind.MODEL_RESPONDED,
            EventKind.MODEL_FAILED,
            EventKind.TOOL_STARTED,
            EventKind.TOOL_COMPLETED,
            EventKind.TOOL_FAILED,
            EventKind.FILE_READ,
            EventKind.FILE_CHANGED,
            EventKind.COMMAND_COMPLETED,
            EventKind.VERIFICATION_COMPLETED,
            EventKind.QUOTA_WARNING,
            EventKind.QUOTA_EXHAUSTED,
            EventKind.SESSION_INTERRUPTED,
        }

    def _remove_archives(self, capsules: list[Capsule]) -> int:
        removed = 0
        data_root = self.journal.path.parent.resolve()
        for capsule in capsules:
            value = capsule.transcript.get("archive")
            if not value:
                continue
            path = Path(str(value)).expanduser().resolve()
            if (
                path.is_relative_to(data_root)
                and path.is_file()
                and not self.journal.archive_is_referenced(str(value))
            ):
                path.unlink()
                removed += 1
        return removed

    def _database_size(self) -> int:
        return sum(
            path.stat().st_size
            for path in (
                self.journal.path,
                Path(f"{self.journal.path}-wal"),
                Path(f"{self.journal.path}-shm"),
            )
            if path.is_file() and not path.is_symlink()
        )

    def _archive_bytes(self, capsules: list[Capsule]) -> int:
        data_root = self.journal.path.parent.resolve()
        paths: set[Path] = set()
        for capsule in capsules:
            value = capsule.transcript.get("archive")
            if not value:
                continue
            path = Path(str(value)).expanduser().resolve()
            if path.is_relative_to(data_root):
                paths.add(path)
        return sum(
            path.stat().st_size
            for path in paths
            if path.is_file() and not path.is_symlink()
        )

    @staticmethod
    def _tree_size(root: Path) -> int:
        if not root.is_dir() or root.is_symlink():
            return 0
        return sum(
            path.stat().st_size
            for path in root.rglob("*")
            if path.is_file() and not path.is_symlink()
        )

    @staticmethod
    def _remove_tree(path: Path, parent: Path) -> None:
        resolved = path.resolve()
        if resolved.is_relative_to(parent.resolve()) and resolved.is_dir():
            shutil.rmtree(resolved)

    @staticmethod
    def _checkpoint_worthy(event: Event) -> bool:
        if event.kind in {
            EventKind.QUOTA_WARNING,
            EventKind.QUOTA_EXHAUSTED,
            EventKind.CONTEXT_COMPACTING,
            EventKind.SESSION_INTERRUPTED,
            EventKind.SESSION_ENDED,
            EventKind.MODEL_RESPONDED,
            EventKind.MODEL_FAILED,
            EventKind.TOOL_FAILED,
        }:
            return True
        if event.kind == EventKind.CONTEXT_USAGE:
            usage = event.payload.get("ratio") or event.payload.get("context_usage")
            try:
                return float(usage) >= 0.98
            except (TypeError, ValueError):
                return False
        return False
