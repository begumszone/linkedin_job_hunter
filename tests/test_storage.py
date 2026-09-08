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


def test_save_skips_writing_when_nothing_changed(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path)
    store.mark("1")
    assert store.save() is True
    before = path.read_text(encoding="utf-8")

    # Reloading and saving without changes must not touch the file: a
    # timestamp-only rewrite would collide with a concurrent run's commit.
    again = SeenStore(path)
    assert again.save() is False
    assert path.read_text(encoding="utf-8") == before


def test_save_writes_after_a_prune(tmp_path):
    from datetime import datetime, timedelta, timezone

    path = tmp_path / "seen.json"
    store = SeenStore(path, forget_after_days=30)
    store.mark("fresh")
    store.save()

    store = SeenStore(path, forget_after_days=30)
    store._seen["stale"] = {
        "first_seen": (datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
        "title": "",
    }
    store.prune()
    assert store.save() is True
    assert "stale" not in SeenStore(path)


def test_merge_seen_is_a_union(tmp_path):
    from job_hunter.storage import merge_seen

    mine = {"1": {"first_seen": "2026-09-08T10:00:00+00:00", "title": "A"}}
    theirs = {"2": {"first_seen": "2026-09-08T10:05:00+00:00", "title": "B"}}
    assert sorted(merge_seen(mine, theirs)) == ["1", "2"]


def test_merge_seen_keeps_the_earliest_sighting(tmp_path):
    from job_hunter.storage import merge_seen

    early = {"1": {"first_seen": "2026-09-08T10:00:00+00:00", "title": "A"}}
    late = {"1": {"first_seen": "2026-09-08T12:00:00+00:00", "title": "A"}}
    assert merge_seen(early, late)["1"]["first_seen"] == "2026-09-08T10:00:00+00:00"
    assert merge_seen(late, early)["1"]["first_seen"] == "2026-09-08T10:00:00+00:00"


def test_merge_state_files_combines_two_runs(tmp_path):
    from job_hunter.storage import merge_state_files

    a, b, out = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "out.json"
    for path, job_id in ((a, "1"), (b, "2")):
        store = SeenStore(path)
        store.mark(job_id, f"İlan {job_id}")
        store.save()

    assert merge_state_files(a, b, out) == 2
    merged = SeenStore(out)
    assert "1" in merged and "2" in merged


def test_merge_state_files_tolerates_a_missing_side(tmp_path):
    from job_hunter.storage import merge_state_files

    a, out = tmp_path / "a.json", tmp_path / "out.json"
    store = SeenStore(a)
    store.mark("1")
    store.save()

    assert merge_state_files(a, tmp_path / "yok.json", out) == 1
