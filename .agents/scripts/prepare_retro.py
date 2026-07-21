"""Slice the material for a qa-retro pass: everything since the last retro.

Reads `_skill_invocations`, finds the most recent row with
`Source type == retro` (the marker the previous retro wrote via
`log_skill_invocation`), and prints:

1. every invocation row after that marker (all rows if no retro has ever
   run), with `feedback:` notes flagged - those are the user
   corrections/overrides captured during intake passes, the primary retro
   input;
2. repo commits over the same window (`git log` since the marker row's
   date), because rule changes already made by hand are part of the same
   picture.

Read-only: it gathers, it doesn't judge. Grouping, the repeat threshold,
and drafting edits are qa-retro's (the agent's) job. The retro itself,
once done, logs its own `retro` row - that's what makes the next run's
window start here.

Usage:
    python prepare_retro.py
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_common import get_services, get_skill_invocations_sheet
from sync_m2_source_docs_to_sheets import read_sheet_values


def main() -> int:
    services = get_services()
    sheet = get_skill_invocations_sheet(services)
    rows = read_sheet_values(services, sheet["id"])
    body = rows[1:] if rows else []

    last_retro_idx = None
    for i, row in enumerate(body):
        if len(row) > 2 and row[2].strip().lower() == "retro":
            last_retro_idx = i

    if last_retro_idx is None:
        window = body
        since_date = None
        print("No previous retro row found - the window is the entire log.\n")
    else:
        window = body[last_retro_idx + 1:]
        marker = body[last_retro_idx]
        since_date = marker[0] if marker else None
        print(f"Last retro: {since_date} | notes: {marker[7] if len(marker) > 7 else ''}\n")

    if not window:
        print("No invocation rows since the last retro.")
    else:
        print(f"{len(window)} invocation row(s) since the last retro:\n")
        feedback_count = 0
        for row in window:
            padded = list(row) + [""] * (8 - len(row))
            date, source, stype, project, person, skills, docs, notes = padded[:8]
            flag = ""
            if "feedback:" in notes.lower():
                flag = "  <-- FEEDBACK"
                feedback_count += 1
            print(f"  {date} | {stype:18s} | {skills}")
            print(f"      source: {source}" + (f" | project: {project}" if project else "")
                  + (f" | person: {person}" if person else ""))
            if docs:
                print(f"      touched: {docs}")
            if notes:
                print(f"      notes: {notes}{flag}")
            print()
        print(f"feedback: notes in window: {feedback_count}")

    print()
    git_range = ["--since", since_date] if since_date else ["-20"]
    try:
        log = subprocess.run(
            ["git", "log", "--oneline", "--date=short", *git_range],
            capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2],
            check=True,
        ).stdout.strip()
        header = (f"Repo commits since {since_date}:" if since_date
                  else "Recent repo commits (no retro marker, showing last 20):")
        print(header)
        print(log or "  (none)")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"Could not read git log: {exc}")

    print()
    print("Next (qa-retro): group by target skill/reference/graph node; "
          "repeat threshold applies - once = trace, twice+ = draft an edit; "
          "finish by logging a source_type=retro row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
