from job_hunter import runner
from job_hunter.config import Config, EmailConfig, NtfyConfig, Search, Settings
from job_hunter.linkedin import Job
from job_hunter.storage import SeenStore


def make_config(**search_kwargs):
    search = Search(name="Finans", keywords=["finans"], **search_kwargs)
    return Config(
        searches=[search],
        email=EmailConfig(enabled=False),
        ntfy=NtfyConfig(),
        settings=Settings(request_delay_seconds=0),
    )


def stub_client(monkeypatch, jobs):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, **kwargs):
            return list(jobs)

    monkeypatch.setattr(runner, "LinkedInClient", FakeClient)


def job(job_id, title, company=""):
    return Job(id=job_id, title=title, company=company, location="", url=f"u/{job_id}")


def test_company_name_alone_does_not_match(monkeypatch, tmp_path):
    stub_client(
        monkeypatch,
        [
            job("1", "Finans Uzmanı", "Acme"),
            job("2", "Şişli Şube - Portföy Yönetmeni", "Türkiye Finans"),
        ],
    )
    found = runner.collect_new_jobs(make_config(), SeenStore(tmp_path / "s.json"))
    assert [j.id for j in found] == ["1"]


def test_already_seen_jobs_are_skipped(monkeypatch, tmp_path):
    stub_client(monkeypatch, [job("1", "Finans Uzmanı"), job("2", "Finans Müdürü")])
    store = SeenStore(tmp_path / "s.json")
    store.mark("1")
    found = runner.collect_new_jobs(make_config(), store)
    assert [j.id for j in found] == ["2"]


def test_dry_run_records_nothing(monkeypatch, tmp_path):
    stub_client(monkeypatch, [job("1", "Finans Uzmanı")])
    config = make_config()
    config.settings.state_file = str(tmp_path / "s.json")
    assert runner.run(config, dry_run=True) == 0
    assert len(SeenStore(tmp_path / "s.json")) == 0


def test_each_address_only_receives_its_own_search(monkeypatch):
    mine = Search(name="Benim", keywords=["finans"], recipients=["me@example.com"])
    theirs = Search(name="Arkadaşım", keywords=["denetim"], recipients=["friend@example.com"])
    config = Config(
        searches=[mine, theirs],
        email=EmailConfig(enabled=True, recipients=[]),
        ntfy=NtfyConfig(),
        settings=Settings(),
    )

    sent: dict[str, list[str]] = {}
    monkeypatch.setattr(
        runner,
        "send_email",
        lambda cfg, to, jobs: sent.setdefault(to[0], [j.title for j in jobs]),
    )

    my_job = job("1", "Finans Uzmanı")
    my_job.search_name = "Benim"
    their_job = job("2", "Denetim Uzmanı")
    their_job.search_name = "Arkadaşım"

    assert runner.notify(config, [my_job, their_job]) == []
    assert sent == {
        "me@example.com": ["Finans Uzmanı"],
        "friend@example.com": ["Denetim Uzmanı"],
    }


def test_postings_outside_the_time_window_are_dropped(monkeypatch, tmp_path):
    from datetime import date, timedelta

    old = (date.today() - timedelta(days=5)).isoformat()
    fresh = date.today().isoformat()
    jobs = [job("1", "Finans Uzmanı"), job("2", "Finans Müdürü")]
    jobs[0].posted_at, jobs[0].posted_label = old, "5 gün önce"
    jobs[1].posted_at, jobs[1].posted_label = fresh, "1 saat önce"
    stub_client(monkeypatch, jobs)

    found = runner.collect_new_jobs(make_config(), SeenStore(tmp_path / "s.json"))
    assert [j.id for j in found] == ["2"]


def test_excluded_locations_are_dropped(monkeypatch, tmp_path):
    jobs = [job("1", "Finans Uzmanı"), job("2", "Finans Müdürü")]
    jobs[0].location = "Bükreş, Romanya"
    jobs[1].location = "Kadıköy"
    stub_client(monkeypatch, jobs)

    config = make_config(exclude_locations=["Romanya"])
    found = runner.collect_new_jobs(config, SeenStore(tmp_path / "s.json"))
    assert [j.id for j in found] == ["2"]


def test_location_filter_is_off_when_no_terms_are_configured(monkeypatch, tmp_path):
    jobs = [job("1", "Finans Uzmanı")]
    jobs[0].location = "Bükreş, Romanya"
    stub_client(monkeypatch, jobs)

    found = runner.collect_new_jobs(make_config(), SeenStore(tmp_path / "s.json"))
    assert [j.id for j in found] == ["1"]
