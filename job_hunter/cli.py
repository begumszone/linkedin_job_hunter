"""Command line entry point."""

from __future__ import annotations

import argparse
import logging
import sys

from .text import fold

from .config import Config, ConfigError, load_config
from .runner import run


def apply_overrides(
    config: Config,
    only_search: str = "",
    hours: int | None = None,
    max_results: int | None = None,
) -> None:
    """Narrow a run to one search and widen its window, for a one-off catch-up.

    Leaving the other searches out matters: a week-long window would otherwise
    send everyone else a week of backlog in one mail.
    """
    if only_search:
        wanted = fold(only_search)
        matched = [s for s in config.searches if wanted in fold(s.name)]
        if not matched:
            names = ", ".join(s.name for s in config.searches)
            raise ConfigError(
                f"'{only_search}' adında bir arama yok. Mevcut aramalar: {names}"
            )
        for search in config.searches:
            search.enabled = search in matched
        log = logging.getLogger(__name__)
        log.info("Yalnızca şu arama çalışacak: %s", ", ".join(s.name for s in matched))

    if hours is not None:
        config.settings.hours = hours
    if max_results is not None:
        for search in config.searches:
            search.max_results = max_results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job_hunter",
        description="LinkedIn'de son 24 saatte yayınlanan ilanları tara ve bildir.",
    )
    parser.add_argument("--config", default="config.yaml", help="Config dosyası yolu")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Bildirim gönderme ve kayıt dosyasını değiştirme, sadece bulunanları yazdır",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Ayrıntılı log")
    parser.add_argument(
        "--only-search",
        default="",
        metavar="AD",
        help="Yalnızca adı bunu içeren aramayı çalıştır (tek seferlik tarama için)",
    )
    parser.add_argument(
        "--hours",
        type=int,
        help="Kaç saat geriye bakılsın (config'teki değeri geçersiz kılar)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        help="Kelime başına taranacak en fazla ilan (config'teki değeri geçersiz kılar)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        config = load_config(args.config)
        apply_overrides(
            config,
            only_search=args.only_search,
            hours=args.hours,
            max_results=args.max_results,
        )
    except ConfigError as exc:
        logging.error("Config hatası: %s", exc)
        return 2

    return run(config, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
