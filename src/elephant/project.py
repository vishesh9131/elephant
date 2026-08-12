from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any


def _git(cwd: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def project_root(cwd: str | Path) -> Path:
    path = Path(cwd).expanduser().resolve()
    root = _git(path, "rev-parse", "--show-toplevel")
    return Path(root) if root else path


def project_id(cwd: str | Path) -> str:
    root = project_root(cwd)
    remote = _git(root, "config", "--get", "remote.origin.url")
    identity = remote or str(root)
    slug = root.name.lower().replace(" ", "-") or "project"
    digest = hashlib.sha256(identity.encode()).hexdigest()[:12]
    return f"{slug}-{digest}"


def git_state(cwd: str | Path) -> dict[str, Any]:
    root = project_root(cwd)
    status = _git(root, "status", "--porcelain=v1") or ""
    changed = sorted(
        line[3:].strip()
        for line in status.splitlines()
        if len(line) > 3 and line[3:].strip()
    )
    return {
        "root": str(root),
        "branch": _git(root, "branch", "--show-current"),
        "head": _git(root, "rev-parse", "HEAD"),
        "remote": _git(root, "config", "--get", "remote.origin.url"),
        "changed_files": changed,
        "dirty": bool(changed),
    }

