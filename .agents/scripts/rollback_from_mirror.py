"""Restore live Drive documents to a past state recorded in the git mirror.

Counterpart of `commit_workspace_state.py`: that script records history,
this one applies it backwards. It takes a commit in the mirror repo and one
or more restore-layer files (`.xlsx`/`.docx`), reads their content *at that
commit* (`git show <sha>:<path>`), and pushes it back into the same live
file ID via `files.update` with conversion - links, folder location, and
file IDs all survive; only content is replaced.

Dry-run by default: shows what would be overwritten and with what. `--apply`
writes. `--history <path>` lists the commits that changed a document, to
pick the right state first.

A rollback is itself a change, not an erasure - after `--apply`:

1. log it (evidence_log row on the affected project + `_skill_invocations`;
   append-only discipline: the original rows describing the bad pass stay);
2. run `check_cascade_closure.py --touched <docs>` - downstream documents
   built on the reverted content need re-checking;
3. run `commit_workspace_state.py -m "rollback of <sha>: <why>"` so the
   mirror records the post-rollback state too.

Usage (from the skills-repo root):

    python .agents/scripts/rollback_from_mirror.py --history "20_M2_Project_Management/<Project>/project_risk.xlsx"
    python .agents/scripts/rollback_from_mirror.py --commit <sha> --path <path> [--path <path> ...]
    python .agents/scripts/rollback_from_mirror.py --commit <sha> --path <path> --apply
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_MIRROR = Path.home() / "Documents" / "qa-drive-mirror"
MIME_BY_EXT = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def restorable(path: str) -> bool:
    return Path(path).suffix in MIME_BY_EXT or path.endswith(".values.json")


def restore_values(services, file_id: str, content: bytes) -> None:
    """Values-only restore via the Sheets API - works for any spreadsheet,
    including ones the drive.file scope can't touch via Drive content calls.
    Formatting is reformat_sheet()'s job, not history's."""
    all_values = json.loads(content.decode("utf-8"))
    meta = services["sheets"].spreadsheets().get(
        spreadsheetId=file_id, fields="sheets.properties.title").execute()
    live_tabs = {t["properties"]["title"] for t in meta.get("sheets", [])}
    for title, values in all_values.items():
        if title not in live_tabs:
            print(f"    WARNING: tab '{title}' no longer exists in the live sheet - skipped")
            continue
        services["sheets"].spreadsheets().values().clear(
            spreadsheetId=file_id, range=f"'{title}'").execute()
        if values:
            services["sheets"].spreadsheets().values().update(
                spreadsheetId=file_id, range=f"'{title}'!A1",
                valueInputOption="RAW", body={"values": values}).execute()


def git_bytes(mirror: Path, *args: str) -> bytes:
    res = subprocess.run(["git", "-C", str(mirror), *args], capture_output=True)
    if res.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {res.stderr.decode('utf-8', 'replace').strip()}")
    return res.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mirror", default=str(DEFAULT_MIRROR), help="mirror repo path")
    parser.add_argument("--history", metavar="PATH",
                        help="list commits that changed this mirror path, then exit")
    parser.add_argument("--commit", help="mirror commit (sha/ref) to restore from")
    parser.add_argument("--path", action="append", default=[], metavar="PATH",
                        help="restore-layer file (.xlsx/.docx), mirror-relative; repeatable")
    parser.add_argument("--apply", action="store_true", help="actually overwrite the live documents")
    args = parser.parse_args()

    mirror = Path(args.mirror)
    if not (mirror / ".git").exists():
        raise SystemExit(f"No mirror repo at {mirror} - run commit_workspace_state.py first.")

    if args.history:
        log = git_bytes(mirror, "log", "--oneline", "--date=short",
                        "--pretty=format:%h %ad %s", "--", args.history).decode("utf-8", "replace")
        print(log or f"No commits touch {args.history}")
        return 0

    if not args.commit or not args.path:
        parser.error("--commit and at least one --path are required (or use --history)")

    paths = [p.replace("\\", "/") for p in args.path]
    bad_ext = [p for p in paths if not restorable(p)]
    if bad_ext:
        raise SystemExit("Only restore-layer files (.xlsx/.docx/.values.json) can be pushed "
                         f"back; not: {', '.join(bad_ext)}. The .csv/.md files are the diff "
                         "layer - use them to inspect, restore via their restore-layer sibling.")

    manifest = json.loads(git_bytes(mirror, "show", f"{args.commit}:_manifest.json").decode("utf-8"))
    plan = []
    for path in paths:
        entry = manifest.get(path)
        if entry is None:
            raise SystemExit(f"{path} is not in _manifest.json at {args.commit} - "
                             "check the path with --history or `git -C <mirror> ls-tree -r <sha>`.")
        content = git_bytes(mirror, "show", f"{args.commit}:{path}")
        plan.append((path, entry, content))

    sha_line = git_bytes(mirror, "log", "-1", "--pretty=format:%h %ad %s",
                         "--date=short", args.commit).decode("utf-8", "replace")
    print(f"Restore source commit: {sha_line}\n")
    for path, entry, content in plan:
        print(f"  {entry['name']}  ({entry['kind']}, fileId {entry['fileId']})")
        print(f"    from {path} @ {args.commit}  ({len(content)} bytes)")

    if not args.apply:
        print("\nDry run - nothing written. Re-run with --apply to overwrite the live "
              "documents with the content above.")
        return 0

    from googleapiclient.http import MediaIoBaseUpload
    from pipeline_common import get_services

    services = get_services()
    for path, entry, content in plan:
        if path.endswith(".values.json"):
            restore_values(services, entry["fileId"], content)
        else:
            media = MediaIoBaseUpload(io.BytesIO(content),
                                      mimetype=MIME_BY_EXT[Path(path).suffix], resumable=False)
            services["drive"].files().update(fileId=entry["fileId"], media_body=media).execute()
        print(f"RESTORED {entry['name']} <- {path} @ {args.commit}")

    print("\nDone. A rollback is itself a change - now:")
    print("  1. log it: evidence_log row (affected project) + _skill_invocations "
          "(append-only: the original rows stay);")
    print("  2. run check_cascade_closure.py --touched <restored docs> - downstream "
          "documents built on the reverted content need re-checking;")
    print(f"  3. run commit_workspace_state.py -m \"rollback to {args.commit}: <why>\".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
