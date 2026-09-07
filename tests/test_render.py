from job_hunter.linkedin import Job
from job_hunter.notifiers import render


def job(**kwargs):
    base = dict(
        id="1",
        title="Finans Uzmanı",
        company="Acme",
        location="İstanbul",
        url="https://www.linkedin.com/jobs/view/1",
        search_name="Finans",
        matched_keywords=["finans"],
    )
    base.update(kwargs)
    return Job(**base)


def test_subject_names_the_posting_when_there_is_only_one():
    assert render.subject([job()]) == "[İlan] Finans Uzmanı – Acme"


def test_subject_counts_multiple_postings():
    assert render.subject([job(), job(id="2")]) == "[İlan] 2 yeni ilan"


def test_text_body_lists_url_and_matches():
    body = render.as_text([job()])
    assert "https://www.linkedin.com/jobs/view/1" in body
    assert "Eşleşen: finans" in body


def test_html_escapes_hostile_titles():
    body = render.as_html([job(title="<script>alert(1)</script>")])
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;" in body


def test_jobs_are_grouped_per_search():
    grouped = render.group_by_search([job(), job(id="2", search_name="Denetim")])
    assert sorted(grouped) == ["Denetim", "Finans"]
