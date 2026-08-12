from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from elephant.models import Event
from elephant.redaction import redact, redact_text


def archive_transcript(events: Iterable[Event], data_dir: str | Path) -> dict[str, Any] | None:
    history = list(events)
    source = _latest_transcript(history)
    if source is None:
        return None

    content = _redacted_transcript(source)
    digest = hashlib.sha256(content).hexdigest()
    last = history[-1]
    destination = (
        Path(data_dir)
        / "transcripts"
        / last.project_id
        / last.session_id
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

