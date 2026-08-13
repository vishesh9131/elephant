from __future__ import annotations

import re
import shlex
from datetime import timedelta
from pathlib import Path
from typing import Any, Sequence

from elephant.kernel import Elephant


COMMANDS: tuple[tuple[str, str], ...] = (
    ("memorize", "Save the freshest recoverable state for this session."),
    ("resume [memory-id]", "Recover the latest memory, or one selected memory."),
    ("help", "Show this command card."),
    ("status", "Show protection, freshness, source, and transcript coverage."),
    ("history [limit]", "List recent memories for this project."),
    ("peek [memory-id]", "Preview what resume will inject without continuing."),
    ("note <text>", "Record an exact, high-priority user instruction."),
    ("doctor", "Check the database and installed capture capabilities."),
    ("usage", "Show Elephant's database and transcript disk usage."),
    ("clean [age] [--keep N] [--yes]", "Preview or delete ancient sessions."),
    ("pin [memory-id]", "Protect a memory's session from cleanup."),
    ("unpin [memory-id]", "Allow a pinned session to be cleaned."),
    ("compact", "Repack the database and reclaim unused space."),
    ("forget <memory-id|session ID|project> --yes", "Delete local Elephant data."),
)


def help_text() -> str:
    width = max(len(name) for name, _description in COMMANDS)
    lines = ["Elephant commands", ""]
    lines.extend(f"  {name.ljust(width)}  {description}" for name, description in COMMANDS)
    lines.extend(
        (
            "",
            "Claude Code: /elephant:<command>",
            "Codex: $elephant <command>",
            "Hermes and Pi: /elephant <command>",
        )
    )
    return "\n".join(lines)


class CommandRouter:
    def __init__(self, elephant: Elephant | None = None) -> None:
        self.elephant = elephant or Elephant()

    def execute(
        self,
        action: str,
        arguments: str | Sequence[str] | None = None,
        *,
        cwd: str | Path,
        harness: str = "manual",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            command, values = self._invocation(action, arguments)
            handler = getattr(self, f"_do_{command}", None)
            if handler is None:
                return self._error(
                    command,
                    f"Unknown Elephant command: {command or '(empty)'}\n\n{help_text()}",
                )
            return handler(values, cwd=Path(cwd), harness=harness, session_id=session_id)
        except Exception as exc:
            return self._error(action, f"Elephant: {exc}")

    @staticmethod
    def _invocation(
        action: str, arguments: str | Sequence[str] | None
    ) -> tuple[str, list[str]]:
        raw = action.strip()
        for prefix in ("/elephant:", "/elephant", "$elephant", "elephant"):
            if raw.lower().startswith(prefix):
                raw = raw[len(prefix) :].strip()
                break
        tokens = shlex.split(raw) if raw else []
        if arguments is not None:
            tokens.extend(shlex.split(arguments) if isinstance(arguments, str) else arguments)
        command = tokens.pop(0).lower() if tokens else "help"
        aliases = {"save": "memorize", "checkpoint": "memorize", "list": "history"}
        return aliases.get(command, command), [str(value) for value in tokens]

    def _do_memorize(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if values:
            raise ValueError("usage: elephant memorize")
        capsule = self.elephant.checkpoint_latest(cwd=cwd, session_id=session_id)
        coverage = str(capsule.transcript.get("coverage") or "unavailable")
        message = "\n".join(
            (
                "🐘 Memorized.",
                "",
                f"Source: {capsule.source_harness}",
                f"Session: {capsule.source_session_id}",
                f"Events: {capsule.event_count}",
                f"Modified files: {len(capsule.modified_files)}",
                f"Transcript coverage: {coverage}",
                f"Memory ID: {capsule.capsule_id}",
            )
        )
        return self._ok("memorize", message, {"capsule": capsule.to_dict()})

    def _do_resume(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if len(values) > 1:
            raise ValueError("usage: elephant resume [memory-id]")
        packet = self.elephant.recover(
            cwd=cwd,
            target_harness=harness,
            capsule_id=values[0] if values else None,
        )
        capsule = packet["capsule"]
        notes = capsule.get("notes") or []
        next_hint = notes[-1] if notes else capsule["current_state"]
        message = "\n".join(
            (
                "🐘 Memory restored.",
                "",
                f"From: {capsule['source_harness']} / {capsule['source_session_id']}",
                f"Objective: {capsule['objective']}",
                f"State: {capsule['current_state']}",
                f"Next: {next_hint}",
                f"Memory ID: {capsule['capsule_id']}",
                "",
                "Compare this with the live worktree, then continue without repeating completed work.",
            )
        )
        return self._ok("resume", message, packet)

    def _do_help(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if values:
            raise ValueError("usage: elephant help")
        return self._ok("help", help_text(), {"commands": list(COMMANDS)})

    def _do_status(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if values:
            raise ValueError("usage: elephant status")
        status = self.elephant.status(cwd=cwd)
        capsule = status.get("capsule") or {}
        coverage = (capsule.get("transcript") or {}).get("coverage", "unavailable")
        message = "\n".join(
            (
                "🐘 Elephant status",
                "",
                f"Protected: {'yes' if status['protected'] else 'no'}",
                f"Capsule fresh: {'yes' if status['fresh'] else 'no'}",
                f"Latest source: {capsule.get('source_harness', 'none')}",
                f"Transcript coverage: {coverage}",
                f"Database: {status['database']}",
            )
        )
        return self._ok("status", message, status)

    def _do_history(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if len(values) > 1:
            raise ValueError("usage: elephant history [limit]")
        limit = int(values[0]) if values else 10
        history = self.elephant.history(cwd=cwd, limit=limit)
        if not history:
            return self._ok("history", "Elephant has no memories for this project.", {"memories": []})
        lines = ["🐘 Recent Elephant memories", ""]
        for index, capsule in enumerate(history, 1):
            lines.append(
                f"{index}. {capsule['source_harness']} · {capsule['created_at']} · "
                f"{capsule['objective']} · {capsule['capsule_id']}"
            )
        return self._ok("history", "\n".join(lines), {"memories": history})

    def _do_peek(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if len(values) > 1:
            raise ValueError("usage: elephant peek [memory-id]")
        packet = self.elephant.recover(
            cwd=cwd,
            target_harness=harness,
            capsule_id=values[0] if values else None,
        )
        capsule = packet["capsule"]
        files = ", ".join(capsule["modified_files"][:20]) or "none recorded"
        message = "\n".join(
            (
                "🐘 Memory preview",
                "",
                f"Objective: {capsule['objective']}",
                f"State: {capsule['current_state']}",
                f"Modified files: {files}",
                f"Failures: {'; '.join(capsule['recent_failures']) or 'none recorded'}",
                f"Memory ID: {capsule['capsule_id']}",
            )
        )
        return self._ok("peek", message, packet)

    def _do_note(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        note = " ".join(values).strip()
        if not note:
            raise ValueError("usage: elephant note <text>")
        capsule = self.elephant.note(
            note,
            cwd=cwd,
            harness=harness,
            session_id=session_id,
        )
        return self._ok(
            "note",
            f"🐘 Noted exactly: {note}\nMemory ID: {capsule.capsule_id}",
            {"capsule": capsule.to_dict()},
        )

    def _do_doctor(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if values:
            raise ValueError("usage: elephant doctor")
        report = self.elephant.doctor(cwd=cwd)
        healthy = report["database_check"] == "ok" and report["data_directory_writable"]
        message = "\n".join(
            (
                "🐘 Elephant doctor",
                "",
                f"Healthy: {'yes' if healthy else 'no'}",
                f"Database: {report['database_check']}",
                f"Writable: {'yes' if report['data_directory_writable'] else 'no'}",
                f"Recoverable memory: {'yes' if report['protected'] else 'no'}",
            )
        )
        return self._ok("doctor", message, report)

    def _do_usage(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if values:
            raise ValueError("usage: elephant usage")
        report = self.elephant.usage(cwd=cwd)
        message = "\n".join(
            (
                "🐘 Elephant storage",
                "",
                f"Total on disk: {self._format_bytes(report['total_bytes'])}",
                f"Database: {self._format_bytes(report['database_bytes'])}",
                f"Transcripts: {self._format_bytes(report['transcript_bytes'])}",
                f"This project: {report['project_sessions']} sessions, "
                f"{report['project_capsules']} memories, {report['project_pins']} pinned",
                f"All projects: {report['total_projects']} projects, "
                f"{report['total_sessions']} sessions, {report['total_capsules']} memories",
                "",
                "Use `elephant clean` for a safe preview, then `elephant compact` after cleanup.",
            )
        )
        return self._ok("usage", message, report)

    def _do_clean(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        age, keep, confirmed = self._clean_arguments(values)
        result = self.elephant.clean(
            cwd=cwd,
            older_than=age,
            keep=keep,
            execute=confirmed,
        )
        if confirmed:
            message = (
                "🐘 Cleanup complete. "
                f"Deleted {result['sessions_deleted']} sessions, "
                f"{result['events_deleted']} events, {result['capsules_deleted']} memories, "
                f"and {result['archives_deleted']} transcript archives. "
                "Run `elephant compact` to repack the database."
            )
        else:
            count = len(result["candidates"])
            message = "\n".join(
                (
                    "🐘 Cleanup preview — nothing deleted.",
                    "",
                    f"Eligible ancient sessions: {count}",
                    "Pinned sessions: protected",
                    f"Recent sessions retained: at least {keep}",
                    f"Transcript space eligible: "
                    f"{self._format_bytes(result['reclaimable_archive_bytes'])}",
                    "",
                    "Repeat the same command with `--yes` only if you want these sessions deleted.",
                )
            )
        return self._ok("clean", message, result)

    def _do_pin(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if len(values) > 1:
            raise ValueError("usage: elephant pin [memory-id]")
        result = self.elephant.pin(cwd=cwd, capsule_id=values[0] if values else None)
        return self._ok(
            "pin",
            f"🐘 Pinned session {result['session_id']}. Cleanup will leave it alone.",
            result,
        )

    def _do_unpin(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if len(values) > 1:
            raise ValueError("usage: elephant unpin [memory-id]")
        result = self.elephant.unpin(cwd=cwd, capsule_id=values[0] if values else None)
        state = "Unpinned" if result["was_pinned"] else "Already unpinned"
        return self._ok(
            "unpin",
            f"🐘 {state}: session {result['session_id']}.",
            result,
        )

    def _do_compact(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        if values:
            raise ValueError("usage: elephant compact")
        result = self.elephant.compact()
        message = (
            "🐘 Database compacted. "
            f"Before: {self._format_bytes(result['before_bytes'])}; "
            f"after: {self._format_bytes(result['after_bytes'])}; "
            f"reclaimed: {self._format_bytes(result['reclaimed_bytes'])}."
        )
        return self._ok("compact", message, result)

    def _do_forget(
        self, values: list[str], *, cwd: Path, harness: str, session_id: str | None
    ) -> dict[str, Any]:
        confirmed = "--yes" in values
        values = [value for value in values if value != "--yes"]
        if not confirmed:
            return {
                "ok": False,
                "command": "forget",
                "requires_confirmation": True,
                "message": "Elephant will permanently delete local memory. Repeat with --yes to confirm.",
            }
        if not values:
            raise ValueError("usage: elephant forget <memory-id|session ID|project> --yes")
        if values[0] == "session":
            if len(values) != 2:
                raise ValueError("usage: elephant forget session <session-id> --yes")
            result = self.elephant.forget("session", cwd=cwd, session_id=values[1])
        elif len(values) == 1:
            result = self.elephant.forget(values[0], cwd=cwd)
        else:
            raise ValueError("usage: elephant forget <memory-id|session ID|project> --yes")
        message = (
            "🐘 Forgotten. "
            f"Deleted {result.get('events_deleted', 0)} events, "
            f"{result.get('capsules_deleted', 0)} capsules, and "
            f"{result.get('archives_deleted', 0)} transcript archives."
        )
        return self._ok("forget", message, result)

    @staticmethod
    def _clean_arguments(values: list[str]) -> tuple[timedelta, int, bool]:
        age_text = "30d"
        age_seen = False
        keep = 10
        confirmed = False
        index = 0
        while index < len(values):
            value = values[index]
            if value == "--yes":
                confirmed = True
            elif value == "--keep":
                index += 1
                if index >= len(values):
                    raise ValueError("--keep requires a number")
                keep = int(values[index])
            elif value.startswith("--keep="):
                keep = int(value.split("=", 1)[1])
            elif value.startswith("-"):
                raise ValueError(f"unknown clean option: {value}")
            elif age_seen:
                raise ValueError("usage: elephant clean [age] [--keep N] [--yes]")
            else:
                age_text = value
                age_seen = True
            index += 1
        if keep < 0:
            raise ValueError("--keep cannot be negative")
        match = re.fullmatch(r"(\d+)(h|d|w)", age_text.lower())
        if not match:
            raise ValueError("age must look like 24h, 30d, or 12w")
        amount = int(match.group(1))
        unit = match.group(2)
        age = (
            timedelta(hours=amount)
            if unit == "h"
            else timedelta(days=amount)
            if unit == "d"
            else timedelta(weeks=amount)
        )
        return age, keep, confirmed

    @staticmethod
    def _format_bytes(value: int) -> str:
        size = float(value)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if size < 1024 or unit == "TiB":
                return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TiB"

    @staticmethod
    def _ok(command: str, message: str, data: Any) -> dict[str, Any]:
        return {"ok": True, "command": command, "message": message, "data": data}

    @staticmethod
    def _error(command: str, message: str) -> dict[str, Any]:
        return {"ok": False, "command": command, "message": message}
