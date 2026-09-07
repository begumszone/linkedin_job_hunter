"""Command line entry point."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import ConfigError, load_config
from .runner import run


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
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        logging.error("Config hatası: %s", exc)
        return 2

    return run(config, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
