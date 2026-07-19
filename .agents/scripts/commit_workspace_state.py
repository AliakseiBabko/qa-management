"""Export the Drive workspace's canonical documents into a local git mirror
and commit - the data-side history store.

The public repo versions the logic (skills); this gives the same semantics
to the data. One commit per skill pass captures every document that pass
touched, so a bad pass can be rolled back as one unit (see
`rollback_from_mirror.py`) instead of fighting Google's per-file,
auto-consolidating revision history.

Each Google-native document is exported in two layers:

- diff layer: one CSV per Sheet tab / Markdown per Doc - what `git diff`
  and `git log -p` actually show;
- restore layer: `.xlsx` / `.docx` - what `rollback_from_mirror.py` pushes
  back into the *same* live file ID via `files.update` with conversion.

Scope caveat: the token uses `drive.file`, so Drive-content calls (xlsx/
docx/markdown export) only work on files the pipeline itself created;
manually-created files 403. The Sheets/Docs API scopes are full, so every
Sheet additionally gets a `.values.json` restore layer via the Sheets API
(values of all tabs - restorable for *any* sheet, formatting regenerated
by reformat_sheet anyway), and a 403'd Doc falls back to plain text via
the Docs API (diff layer only, not restorable). Upgrading SCOPES in
google_api_smoke_test.py to full `drive` (+ deleting token.json and
re-consenting once) removes the caveat entirely.

`_manifest.json` at the mirror root maps restore-layer paths to Drive file
IDs. Non-native files (txt transcripts, recordings) are skipped - Drive
itself preserves those; this mirror is for the documents skills rewrite.
`90_Archive` and `01_Recordings` are excluded.

The mirror repo lives OUTSIDE both the public skills repo (it holds real
names - it must never share a git history with anything public) and the
synced Drive folder (Drive sync chokes on `.git` object files). Default:
`~/Documents/qa-drive-mirror`, auto-initialized on first run. After every
commit the full history is packed into a single-file `git bundle` under
`90_Archive/_git_mirror_backups/` on Drive, so a dead laptop costs nothing:
restore with `git clone mirror.bundle`.

Usage (from the skills-repo root, where .local/google lives):

    python .agents/scripts/commit_workspace_state.py -m "after m2-1to1-apply: <source>"
    python .agents/scripts/commit_workspace_state.py            # timestamp message

Run it at the end of every pass that wrote to canonical documents (and it
is harmless anytime - no changes means no commit).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import subprocess
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_common import get_services
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

DEFAULT_MIRROR = Path.home() / "Documents" / "qa-drive-mirror"
BUNDLE_DIR = Path(r"G:\My Drive\QA_Management\90_Archive\_git_mirror_backups")
SKIP_FOLDERS = {"90_Archive", "01_Recordings"}

MIME_FOLDER = "application/vnd.google-apps.folder"
MIME_GSHEET = "application/vnd.google-apps.spreadsheet"
MIME_GDOC = "application/vnd.google-apps.document"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

MIRROR_README = """# qa-drive-mirror (PRIVATE)

Auto-generated git mirror of the QA Management Drive workspace's canonical
documents - real names and judgments throughout. Never push this repo to a
public remote, never move it inside the public skills repo. Written by
`commit_workspace_state.py`; restore documents with
`rollback_from_mirror.py`. Do not edit files here by hand - they are
overwritten wholesale on every run.
"""


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(".")


def run_git(mirror: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(mirror), *args],
                          capture_output=True, text=True, encoding="utf-8")


def list_children(drive, folder_id: str) -> list[dict]:
    items, token = [], None
    while True:
        resp = drive.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=200, pageToken=token,
        ).execute()
        items.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            return items


def is_403(exc: Exception) -> bool:
    return "403" in str(exc) and "appNotAuthorizedToFile" in str(exc)


def with_retry(fn, attempts: int = 3):
    """Retry transient failures (timeouts, 5xx); 403s are permanent, raise at once."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if is_403(exc) or i == attempts - 1:
                raise
            time.sleep(2 * (i + 1))


def export_bytes(drive, file_id: str, mime: str) -> bytes:
    return with_retry(lambda: drive.files().export(fileId=file_id, mimeType=mime).execute())


def write_if_changed(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def export_sheet(services, item: dict, out_dir: Path, rel: str, manifest: dict,
                 warnings: list[str]) -> list[str]:
    name = sanitize(item["name"])
    rel = f"{rel}/" if rel else ""
    written = []
    # Preferred restore layer (needs Drive content access; 403 on
    # manually-created files under drive.file scope).
    try:
        xlsx = export_bytes(services["drive"], item["id"], MIME_XLSX)
        xlsx_rel = f"{rel}{name}.xlsx"
        write_if_changed(out_dir / f"{name}.xlsx", xlsx)
        manifest[xlsx_rel] = {"fileId": item["id"], "name": item["name"], "kind": "spreadsheet"}
        written.append(xlsx_rel)
    except Exception as exc:
        if not is_403(exc):
            raise
        warnings.append(f"{rel}{item['name']}: no Drive content access (drive.file scope) - "
                        "values-only restore layer")
    # Diff layer (CSV per tab) + universal values restore layer - Sheets API,
    # works regardless of who created the file.
    meta = with_retry(lambda: services["sheets"].spreadsheets().get(
        spreadsheetId=item["id"], fields="sheets.properties.title").execute())
    all_values: dict[str, list] = {}
    for tab in meta.get("sheets", []):
        title = tab["properties"]["title"]
        values = with_retry(lambda t=title: services["sheets"].spreadsheets().values().get(
            spreadsheetId=item["id"], range=f"'{t}'").execute()).get("values", [])
        all_values[title] = values
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows(values)
        tab_rel = f"{rel}{name}.{sanitize(title)}.csv"
        write_if_changed(out_dir / f"{name}.{sanitize(title)}.csv", buf.getvalue().encode("utf-8"))
        written.append(tab_rel)
    values_rel = f"{rel}{name}.values.json"
    write_if_changed(out_dir / f"{name}.values.json",
                     json.dumps(all_values, ensure_ascii=False, indent=1).encode("utf-8"))
    manifest[values_rel] = {"fileId": item["id"], "name": item["name"], "kind": "spreadsheet-values"}
    written.append(values_rel)
    return written


def doc_plain_text(services, doc_id: str) -> str:
    """Docs-API fallback text extraction for docs without Drive content access."""
    doc = with_retry(lambda: services["docs"].documents().get(documentId=doc_id).execute())
    parts: list[str] = []
    for element in doc.get("body", {}).get("content", []):
        for pe in element.get("paragraph", {}).get("elements", []):
            parts.append(pe.get("textRun", {}).get("content", ""))
    return "".join(parts)


def export_doc(services, item: dict, out_dir: Path, rel: str, manifest: dict,
               warnings: list[str]) -> list[str]:
    name = sanitize(item["name"])
    rel = f"{rel}/" if rel else ""
    written = []
    try:
        docx = export_bytes(services["drive"], item["id"], MIME_DOCX)
        docx_rel = f"{rel}{name}.docx"
        write_if_changed(out_dir / f"{name}.docx", docx)
        manifest[docx_rel] = {"fileId": item["id"], "name": item["name"], "kind": "document"}
        written.append(docx_rel)
        try:
            text, ext = export_bytes(services["drive"], item["id"], "text/markdown"), "md"
        except Exception:
            text, ext = export_bytes(services["drive"], item["id"], "text/plain"), "txt"
        md_rel = f"{rel}{name}.{ext}"
        write_if_changed(out_dir / f"{name}.{ext}", text)
        written.append(md_rel)
    except Exception as exc:
        if not is_403(exc):
            raise
        warnings.append(f"{rel}{item['name']}: no Drive content access (drive.file scope) - "
                        "diff layer only via Docs API, NOT restorable")
        txt_rel = f"{rel}{name}.txt"
        write_if_changed(out_dir / f"{name}.txt",
                         doc_plain_text(services, item["id"]).encode("utf-8"))
        written.append(txt_rel)
    return written


def walk(services, folder_id: str, out_dir: Path, rel: str, manifest: dict,
         written: list[str], errors: list[str], warnings: list[str]) -> None:
    for item in sorted(list_children(services["drive"], folder_id), key=lambda i: i["name"]):
        if item["mimeType"] == MIME_FOLDER:
            if item["name"] in SKIP_FOLDERS:
                continue
            sub = sanitize(item["name"])
            walk(services, item["id"], out_dir / sub,
                 f"{rel}/{sub}" if rel else sub, manifest, written, errors, warnings)
        elif item["mimeType"] in (MIME_GSHEET, MIME_GDOC):
            try:
                fn = export_sheet if item["mimeType"] == MIME_GSHEET else export_doc
                written.extend(fn(services, item, out_dir, rel, manifest, warnings))
            except Exception as exc:
                errors.append(f"{rel}/{item['name']}: {exc}")
        # non-native files: Drive keeps them; not this mirror's job


def prune_stale(mirror: Path, expected: set[str]) -> int:
    keep = {"README.md", "_manifest.json"}
    removed = 0
    for path in mirror.rglob("*"):
        if ".git" in path.parts or path.is_dir():
            continue
        rel = path.relative_to(mirror).as_posix()
        if rel in keep or rel in expected:
            continue
        path.unlink()
        removed += 1
    for path in sorted((p for p in mirror.rglob("*") if p.is_dir() and ".git" not in p.parts),
                       key=lambda p: len(p.parts), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-m", "--message", default="",
                        help="commit message; describe the pass that caused the changes "
                             "(skill, source), same info as the _skill_invocations row")
    parser.add_argument("--mirror", default=str(DEFAULT_MIRROR), help="mirror repo path")
    parser.add_argument("--no-bundle", action="store_true", help="skip the Drive bundle backup")
    args = parser.parse_args()

    mirror = Path(args.mirror)
    mirror.mkdir(parents=True, exist_ok=True)
    if not (mirror / ".git").exists():
        subprocess.run(["git", "init"], cwd=mirror, capture_output=True, check=True)
        (mirror / "README.md").write_text(MIRROR_README, encoding="utf-8")
        print(f"Initialized mirror repo at {mirror}")
    # The mirror needs its own identity (no global git config assumed) -
    # borrow the skills repo's, since the same person drives both.
    if not run_git(mirror, "config", "user.email").stdout.strip():
        skills_repo = Path(__file__).resolve().parents[2]
        for key, fallback in (("user.name", "qa-drive-mirror"),
                              ("user.email", "mirror@localhost")):
            val = subprocess.run(["git", "-C", str(skills_repo), "config", key],
                                 capture_output=True, text=True).stdout.strip() or fallback
            run_git(mirror, "config", key, val)

    services = get_services()
    manifest: dict = {}
    written: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    print("Exporting canonical documents (diff layer + restore layer)...")
    walk(services, ROOT_FOLDER_ID, mirror, "", manifest, written, errors, warnings)

    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    write_if_changed(mirror / "_manifest.json", manifest_bytes)
    removed = prune_stale(mirror, set(written))
    print(f"Exported {len(written)} files ({len(manifest)} restore-layer entries), "
          f"pruned {removed} stale.")
    for warn in warnings:
        print(f"  note: {warn}")
    for err in errors:
        print(f"  EXPORT FAILED: {err}")

    run_git(mirror, "add", "-A")
    if not run_git(mirror, "status", "--porcelain").stdout.strip():
        print("No changes since last commit - nothing to do.")
        return 0
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = args.message or f"workspace state {stamp}"
    res = run_git(mirror, "commit", "-m", f"{msg}\n\nExported {stamp} by commit_workspace_state.py")
    if res.returncode != 0:
        print(f"git commit failed: {res.stderr.strip()}")
        return 1
    sha = run_git(mirror, "rev-parse", "--short", "HEAD").stdout.strip()
    print(f"Committed {sha}: {msg}")
    print(run_git(mirror, "show", "--stat", "--oneline", "-s", "HEAD").stdout.strip())
    changed = run_git(mirror, "diff", "--name-only", "HEAD~1", "HEAD").stdout.strip()
    if changed:
        print("Changed files:")
        for line in changed.splitlines():
            print(f"  {line}")

    if not args.no_bundle:
        try:
            BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
            bundle = BUNDLE_DIR / "mirror.bundle"
            res = run_git(mirror, "bundle", "create", str(bundle), "--all")
            if res.returncode == 0:
                print(f"Bundle backup refreshed: {bundle}")
            else:
                print(f"Bundle backup FAILED (history is still safe locally): {res.stderr.strip()}")
        except OSError as exc:
            print(f"Bundle backup FAILED (history is still safe locally): {exc}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
