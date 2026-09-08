"""Remember which postings were already sent, so only new ones notify."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SeenStore:
    def __init__(self, path: str | Path, forget_after_days: int = 30):
        self.path = Path(path)
        self.forget_after_days = forget_after_days
        self._seen: dict[str, dict] = {}
        # Only rewrite the file when the set of jobs actually changed; a
        # timestamp-only rewrite creates a commit that collides with any other
        # run doing the same thing.
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupt state file must not silence the whole run; the cost is
            # one round of repeat notifications.
            return
        if isinstance(data, dict):
            self._seen = data.get("jobs", {}) if "jobs" in data else data

    def __contains__(self, job_id: str) -> bool:
        return job_id in self._seen

    def __len__(self) -> int:
        return len(self._seen)

    def mark(self, job_id: str, title: str = "") -> None:
        self._dirty = True
        self._seen[job_id] = {
            "first_seen": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": title,
        }

    def prune(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.forget_after_days)
        stale = []
        for job_id, meta in self._seen.items():
            raw = (meta or {}).get("first_seen", "")
            try:
                first_seen = datetime.fromisoformat(raw)
            except ValueError:
                continue
            if first_seen.tzinfo is None:
                first_seen = first_seen.replace(tzinfo=timezone.utc)
            if first_seen < cutoff:
                stale.append(job_id)
        for job_id in stale:
            del self._seen[job_id]
        if stale:
            self._dirty = True
        return len(stale)

    def save(self) -> bool:
        """Write the file when something changed; return whether it was written."""
        if not self._dirty and self.path.exists():
            return False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "jobs": self._seen,
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(self.path)
        self._dirty = False
        return True


def merge_seen(mine: dict, theirs: dict) -> dict:
    """Combine two seen-job maps, keeping the earliest sighting of each job.

    Two runs can finish at once and each writes its own copy of the file; the
    union is always the right answer, since a job seen by either run has been
    notified.
    """
    merged = dict(theirs)
    for job_id, meta in mine.items():
        existing = merged.get(job_id)
        if existing is None:
            merged[job_id] = meta
            continue
        if str(meta.get("first_seen", "")) < str(existing.get("first_seen", "")):
            merged[job_id] = meta
    return merged


def merge_state_files(mine: Path | str, theirs: Path | str, out: Path | str) -> int:
    """Merge two state files on disk. Returns the resulting job count."""

    def load(path: Path | str) -> dict:
        path = Path(path)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data.get("jobs", {}) if isinstance(data, dict) else {}

    merged = merge_seen(load(mine), load(theirs))
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "jobs": merged,
    }
    Path(out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return len(merged)
