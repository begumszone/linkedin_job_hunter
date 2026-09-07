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
