"""Turn a batch of new postings into the text and HTML shown in a notification."""

from __future__ import annotations

import html
from collections import defaultdict
from typing import Iterable

from ..linkedin import Job


def group_by_search(jobs: Iterable[Job]) -> dict[str, list[Job]]:
    grouped: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        grouped[job.search_name].append(job)
    return dict(grouped)


def subject(jobs: list[Job], prefix: str = "[İlan]") -> str:
    count = len(jobs)
    if count == 1:
        job = jobs[0]
        title = job.title or "Yeni ilan"
        company = f" – {job.company}" if job.company else ""
        return f"{prefix} {title}{company}"
    return f"{prefix} {count} yeni ilan"


def as_text(jobs: list[Job]) -> str:
    lines: list[str] = []
    for search_name, group in group_by_search(jobs).items():
        lines.append(f"## {search_name} ({len(group)} yeni ilan)")
        for job in group:
            lines.append(f"- {job.title or 'İsimsiz ilan'}")
            details = " | ".join(
                part for part in (job.company, job.location, job.posted_label) if part
            )
            if details:
                lines.append(f"  {details}")
            if job.matched_keywords:
                lines.append(f"  Eşleşen: {', '.join(job.matched_keywords)}")
            lines.append(f"  {job.url}")
        lines.append("")
    return "\n".join(lines).strip()


def _job_html(job: Job) -> str:
    title = html.escape(job.title or "İsimsiz ilan")
    url = html.escape(job.url, quote=True)
    meta = " &middot; ".join(
        html.escape(part)
        for part in (job.company, job.location, job.posted_label)
        if part
    )
    keywords = "".join(
        f'<span style="display:inline-block;background:#eef2ff;color:#3730a3;'
        f'border-radius:10px;padding:2px 9px;margin:2px 4px 0 0;font-size:12px;">'
        f"{html.escape(kw)}</span>"
        for kw in job.matched_keywords
    )
    return f"""
      <tr><td style="padding:14px 0;border-bottom:1px solid #e5e7eb;">
        <a href="{url}" style="font-size:16px;font-weight:600;color:#0a66c2;text-decoration:none;">{title}</a>
        <div style="color:#4b5563;font-size:13px;margin-top:4px;">{meta}</div>
        <div style="margin-top:6px;">{keywords}</div>
      </td></tr>"""


def as_html(jobs: list[Job]) -> str:
    sections = []
    for search_name, group in group_by_search(jobs).items():
        rows = "".join(_job_html(job) for job in group)
        sections.append(
            f"""
      <h2 style="font-size:15px;color:#111827;margin:26px 0 4px;">
        {html.escape(search_name)}
        <span style="color:#6b7280;font-weight:400;">({len(group)} yeni ilan)</span>
      </h2>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>"""
        )

    body = "".join(sections)
    return f"""<!doctype html>
<html lang="tr"><body style="margin:0;background:#f9fafb;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <div style="max-width:640px;margin:0 auto;padding:24px;background:#ffffff;">
    <p style="font-size:13px;color:#6b7280;margin:0 0 4px;">LinkedIn Job Hunter</p>
    <h1 style="font-size:20px;color:#111827;margin:0;">{len(jobs)} yeni ilan bulundu</h1>
    {body}
    <p style="color:#9ca3af;font-size:12px;margin-top:28px;border-top:1px solid #e5e7eb;padding-top:12px;">
      Bu e-posta senin kurduğun ilan takipçisi tarafından otomatik gönderildi.
      Anahtar kelimeleri veya konumu değiştirmek için config.yaml dosyasını düzenle.
    </p>
  </div>
</body></html>"""
