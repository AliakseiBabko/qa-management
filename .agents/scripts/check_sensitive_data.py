"""Grep-based guard for AGENTS.md's "No Sensitive Data In This Repository"
rule: check whether any added line under `.agents/` in the current git diff
(staged + unstaged) contains a real person name or real project name pulled
live from `_people_registry`/`_project_registry`.

This is a cheap net, not a proof of safety: it only catches names/projects
that are already registered in Drive, matched as literal substrings. It
will not catch a real company name, email, phone number, or paraphrased
transcript content that doesn't happen to match a registry string - those
still need a human read against AGENTS.md before committing. Run this
manually before committing changes under `.agents/`; it is not wired into
a git hook.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_people_registry_sheet, get_services
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_or_create_folder, find_sheet_in_folder, read_sheet_values

MIN_NAME_LEN = 4  # skip short tokens likely to false-positive (e.g. common words)


def load_watch_strings(services: dict[str, Any]) -> set[str]:
    drive = services["drive"]
    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")

    watch: set[str] = set()

    people_sheet = get_people_registry_sheet(services)
    if people_sheet:
        rows = read_sheet_values(services, people_sheet["id"])
        for row in rows[1:]:
            for col in (0, 1):  # Name (RU), Name (EN)
                if len(row) > col and row[col].strip():
                    watch.add(row[col].strip())

    project_sheet = find_sheet_in_folder(drive, m2_root["id"], "_project_registry")
    if project_sheet:
        rows = read_sheet_values(services, project_sheet["id"])
        for row in rows[1:]:
            if row and row[0].strip():
                watch.add(row[0].strip())

    return {s for s in watch if len(s) >= MIN_NAME_LEN}


def added_lines(diff_args: list[str]) -> list[tuple[str, int, str]]:
    """Return (file, line_no, text) for every added line in a unified diff."""
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["git", "diff", "--unified=0", *diff_args, "--", ".agents"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out: list[tuple[str, int, str]] = []
    current_file = ""
    current_line = 0
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        m = hunk_re.match(line)
        if m:
            current_line = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            out.append((current_file, current_line, line[1:]))
            current_line += 1
    return out


def main() -> int:
    ensure_utf8_stdout()
    services = get_services()
    watch = load_watch_strings(services)
    print(f"Loaded {len(watch)} known name(s)/project(s) to watch for.")

    hits: list[tuple[str, int, str, str]] = []
    for diff_args in ([], ["--cached"]):
        for file, line_no, text in added_lines(diff_args):
            for name in watch:
                if name in text:
                    hits.append((file, line_no, name, text.strip()))

    if not hits:
        print("No known real names/projects found in added .agents/ lines. "
              "This does not guarantee the diff is clean - see AGENTS.md.")
        return 0

    print(f"\n{len(hits)} potential sensitive-data hit(s):\n")
    for file, line_no, name, text in hits:
        print(f"  {file}:{line_no} - matched '{name}'")
        print(f"    {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
