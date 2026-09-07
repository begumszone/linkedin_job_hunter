"""Tie search, matching, de-duplication and notification together."""

from __future__ import annotations

import logging

from .config import Config
from .linkedin import Job, LinkedInClient, RateLimited, build_query
from .matching import matches
from .notifiers.email_notifier import EmailError, send_email
from .notifiers.ntfy_notifier import send_ntfy
from .storage import SeenStore

log = logging.getLogger(__name__)


def collect_new_jobs(config: Config, store: SeenStore) -> list[Job]:
    """Search every configured query and return the postings not seen before."""
    client = LinkedInClient(
        user_agent=config.settings.user_agent,
        delay_seconds=config.settings.request_delay_seconds,
    )
    new_jobs: list[Job] = []
    seen_this_run: set[str] = set()

    for search in config.active_searches():
        for query in build_query(search.keywords, search.match_mode):
            try:
                results = client.search(
                    keywords=query,
                    location=search.location,
                    hours=config.settings.hours,
                    max_results=search.max_results,
                    remote_only=search.remote_only,
                )
            except RateLimited as exc:
                # Stop this search rather than hammering LinkedIn further; the
                # next scheduled run picks the postings up again.
                log.warning("%s: %s", search.name, exc)
                break
            except Exception as exc:  # network hiccup, layout change, ...
                log.error("%s / '%s' araması başarısız: %s", search.name, query, exc)
                continue

            for job in results:
                if job.id in store or job.id in seen_this_run:
                    continue
                # Title only: a bank called "Türkiye Finans" would otherwise
                # match every posting it publishes, whatever the role.
                hits = matches(
                    job.title,
                    search.keywords,
                    mode=search.match_mode,
                    exclude=search.exclude,
                )
                if not hits:
                    continue
                job.search_name = search.name
                job.matched_keywords = hits
                seen_this_run.add(job.id)
                new_jobs.append(job)

    return new_jobs


def notify(config: Config, jobs: list[Job]) -> list[str]:
    """Send the digest through every enabled channel; return error messages."""
    errors: list[str] = []

    if config.email.enabled:
        # One digest per address, holding only the searches that address asked
        # for — nobody receives someone else's alerts.
        per_recipient: dict[str, list[Job]] = {}
        by_name = {s.name: s for s in config.searches}
        for job in jobs:
            search = by_name.get(job.search_name)
            if search is None:
                continue
            for address in config.recipients_for(search):
                per_recipient.setdefault(address, []).append(job)

        for address, address_jobs in per_recipient.items():
            try:
                send_email(config.email, [address], address_jobs)
            except EmailError as exc:
                errors.append(str(exc))

    if config.ntfy.enabled:
        try:
            send_ntfy(config.ntfy, jobs)
        except Exception as exc:
            errors.append(f"ntfy gönderilemedi: {exc}")

    return errors


def run(config: Config, dry_run: bool = False) -> int:
    """Run one hunt. Returns the process exit code."""
    store = SeenStore(config.settings.state_file, config.settings.forget_after_days)
    log.info("Kayıtlı ilan sayısı: %d", len(store))

    jobs = collect_new_jobs(config, store)
    if not jobs:
        log.info("Yeni ilan yok.")
        store.prune()
        store.save()
        return 0

    log.info("%d yeni ilan bulundu.", len(jobs))
    for job in jobs:
        log.info("  • %s — %s (%s)", job.title, job.company, job.url)

    if dry_run:
        log.info("dry-run: bildirim gönderilmedi, kayıt dosyası güncellenmedi.")
        return 0

    errors = notify(config, jobs)
    if errors:
        for message in errors:
            log.error(message)
        # Nothing is marked as seen, so the next run retries these postings
        # instead of silently dropping them.
        return 1

    for job in jobs:
        store.mark(job.id, job.title)
    store.prune()
    store.save()
    return 0
