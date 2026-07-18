"""Regenerate every derived view of the project timeline in one command.

Three scripts read from the same underlying source (`action_items` across
projects, plus `_m1_timeline`) and each need re-running whenever that
source changes - nothing forces them to run together, which has already
caused a stale view to sit around after an `action_items` edit (a fixed
action item still showing on the calendar because only `action_items`
itself had been updated, not the sheets/calendar built from it). This
script exists so "I edited an action item" and "every downstream view is
current" happen as one step instead of three remembered separately:

1. `refresh_timeline_registry.py` - rebuilds `_timeline` from every
   project's `action_items` (+ `_m1_timeline`). Always writes.
2. `sync_timeline_to_calendar.py --apply` - projects `_timeline`/
   `_m1_timeline` into the "QA Management Timeline" Google Calendar.
3. `refresh_timeline_looker_view.py --apply` - rebuilds
   `_timeline_looker_view`, the Data Studio-friendly flattened Sheet.

Run this instead of the three individually after any `action_items`
change (a new item, a status flip, a text/ownership correction).

    python refresh_all_timeline_views.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

STEPS = [
    ("refresh_timeline_registry.py", []),
    ("sync_timeline_to_calendar.py", ["--apply"]),
    ("refresh_timeline_looker_view.py", ["--apply"]),
]


def main() -> int:
    for script, extra_args in STEPS:
        print(f"=== {script} {' '.join(extra_args)} ===")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script), *extra_args],
            cwd=Path.cwd(),
        )
        if result.returncode != 0:
            print(f"FAILED: {script} (exit {result.returncode}) - stopping, later views were not refreshed.", file=sys.stderr)
            return result.returncode
        print()
    print("All timeline views refreshed: _timeline, QA Management Timeline (Calendar), _timeline_looker_view.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
