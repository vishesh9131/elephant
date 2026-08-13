from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from elephant.models import Event
from elephant.redaction import redact, redact_text


def archive_transcript(events: Iterable[Event], data_dir: str | Path) -> dict[str, Any] | None:
    history = list(events)
    source = _latest_transcript(history)
    if source is None:
        content = _observed_transcript(history)
        coverage = "observed"
        source_path = None
    else:
        content = _redacted_transcript(source)
        coverage = "complete"
        source_path = str(source)
    digest = hashlib.sha256(content).hexdigest()
    last = history[-1]
    destination = (
        Path(data_dir)
        / "transcripts"
        / _safe_component(last.project_id)
        / _safe_component(last.session_id)
        / f"{digest[:16]}.jsonl.gz"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        with gzip.open(destination, "wb", compresslevel=6) as stream:
            stream.write(content)
    return {
        "archive": str(destination),
        "sha256": digest,
        "bytes": len(content),
        "format": "jsonl.gz",
        "redacted": True,
        "coverage": coverage,
        "source": source_path,
    }


def _latest_transcript(events: list[Event]) -> Path | None:
    for event in reversed(events):
        value = event.payload.get("transcript_path")
        if not value:
            continue
        path = Path(str(value)).expanduser()
        if path.is_file():
            return path
    return None


def _redacted_transcript(path: Path) -> bytes:
    output: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            stripped = line.rstrip("\n")
            try:
                value = redact(json.loads(stripped))
                output.append(json.dumps(value, separators=(",", ":"), ensure_ascii=False))
            except json.JSONDecodeError:
                output.append(redact_text(stripped))
    return ("\n".join(output) + "\n").encode("utf-8")


def _observed_transcript(events: list[Event]) -> bytes:
    lines = [
        json.dumps(redact(event.to_dict()), separators=(",", ":"), ensure_ascii=False)
        for event in events
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _safe_component(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")[:80] or "session"
    digest = hashlib.sha256(value.encode()).hexdigest()[:10]
    return f"{slug}-{digest}"
