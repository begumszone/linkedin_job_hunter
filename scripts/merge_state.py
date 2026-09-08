"""Merge two seen-job state files into one.

Used by the workflow when a concurrent run has already pushed its own state:
rebasing a machine-generated JSON file conflicts, but the union of two runs'
sightings is always correct.

    python scripts/merge_state.py MINE THEIRS OUT
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from job_hunter.storage import merge_state_files  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    count = merge_state_files(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"{count} ilan kaydı birleştirildi")
