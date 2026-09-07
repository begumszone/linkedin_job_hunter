from job_hunter.linkedin import build_query, parse_jobs

SAMPLE = """
<li>
  <div class="base-card relative job-search-card"
       data-entity-urn="urn:li:jobPosting:4012345678">
    <a class="base-card__full-link"
       href="https://www.linkedin.com/jobs/view/finans-uzmani-at-acme-4012345678?refId=abc&amp;trk=guest">
      <span class="sr-only">Finans Uzmanı</span>
    </a>
    <h3 class="base-search-card__title">Finans Uzmanı</h3>
    <h4 class="base-search-card__subtitle"><a>Acme A.Ş.</a></h4>
    <div class="base-search-card__metadata">
      <span class="job-search-card__location">İstanbul, Türkiye</span>
      <time class="job-search-card__listdate--new" datetime="2026-09-07">2 saat önce</time>
    </div>
  </div>
</li>
"""


def test_parse_jobs_extracts_the_card_fields():
    (job,) = parse_jobs(SAMPLE)
    assert job.id == "4012345678"
    assert job.title == "Finans Uzmanı"
    assert job.company == "Acme A.Ş."
    assert job.location == "İstanbul, Türkiye"
    assert job.posted_at == "2026-09-07"
    assert job.posted_label == "2 saat önce"


def test_parse_jobs_strips_tracking_query_string():
    (job,) = parse_jobs(SAMPLE)
    assert job.url == (
        "https://www.linkedin.com/jobs/view/finans-uzmani-at-acme-4012345678"
    )


def test_parse_jobs_tolerates_empty_html():
    assert parse_jobs("") == []


def test_build_query_any_mode_searches_each_keyword():
    assert build_query(["finans", "IFRS"], "any") == ["finans", "IFRS"]


def test_build_query_all_mode_joins_with_and():
    assert build_query(["finans", "IFRS"], "all") == ["finans AND IFRS"]


def _card(job_id: int) -> str:
    return f"""
<li><div class="base-card" data-entity-urn="urn:li:jobPosting:{job_id}">
  <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/x-{job_id}"></a>
  <h3 class="base-search-card__title">İlan {job_id}</h3>
</div></li>"""


def test_search_keeps_paging_past_linkedins_own_page_size(monkeypatch):
    from job_hunter.linkedin import LinkedInClient

    # LinkedIn returns 10 cards per request; three pages then empty.
    pages = [
        "".join(_card(i) for i in range(0, 10)),
        "".join(_card(i) for i in range(10, 20)),
        "".join(_card(i) for i in range(20, 25)),
        "",
    ]
    seen_starts = []

    client = LinkedInClient("ua", delay_seconds=0)
    monkeypatch.setattr(
        client,
        "_get",
        lambda params: (seen_starts.append(params["start"]), pages.pop(0))[1],
    )

    jobs = client.search("finans", max_results=50)
    assert len(jobs) == 25
    assert seen_starts == [0, 10, 20, 25]


def test_search_stops_when_a_page_repeats_itself(monkeypatch):
    from job_hunter.linkedin import LinkedInClient

    same_page = "".join(_card(i) for i in range(0, 10))
    client = LinkedInClient("ua", delay_seconds=0)
    monkeypatch.setattr(client, "_get", lambda params: same_page)

    jobs = client.search("finans", max_results=50)
    assert len(jobs) == 10
