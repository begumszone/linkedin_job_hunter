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
        return len(stale)

    def save(self) -> None:
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
