from datetime import datetime, timedelta, timezone

from job_hunter.storage import SeenStore


def test_marks_and_persists_across_instances(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path)
    store.mark("123", "Finans Uzmanı")
    store.save()

    assert "123" in SeenStore(path)
    assert "456" not in SeenStore(path)


def test_prune_drops_entries_past_the_window(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path, forget_after_days=30)
    store.mark("fresh")
    store._seen["stale"] = {
        "first_seen": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
        "title": "",
    }

    assert store.prune() == 1
    assert "fresh" in store and "stale" not in store


def test_corrupt_state_file_does_not_crash(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("{ bozuk json", encoding="utf-8")
    assert len(SeenStore(path)) == 0
