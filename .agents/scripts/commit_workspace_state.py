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
from mirror_common import mirror_git, assert_private_mirror
from qa_manage import DATA_ROOT, find_queue, read_queue
from export_source_text import export as export_source_texts
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import socket

# Some large Sheets exceed the default socket timeout reproducibly.
socket.setdefaulttimeout(180)

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
    """Retry transient failures (timeouts, 5xx); 403s are permanent, raise at
    once. A 429 is the Sheets per-minute read quota (60/min/user) - short
    backoff can't clear it, so wait out the window instead."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if is_403(exc) or i == attempts - 1:
                raise
            if "429" in str(exc) or "RATE_LIMIT_EXCEEDED" in str(exc):
                time.sleep(65)
            else:
                time.sleep(2 * (i + 1))


def export_bytes(drive, file_id: str, mime: str) -> bytes:
    return with_retry(lambda: drive.files().export(fileId=file_id, mimeType=mime).execute())


def write_if_changed(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def export_sheet(services, item: dict, out_dir: Path, rel: str, manifest: dict,
                 warnings: list[str]) -> list[str]:
    name = sanitize(item["name"])
    rel = f"{rel}/" if rel else ""
    written = []
    # Diff layer (CSV per tab) + universal values restore layer - Sheets API,
    # works regardless of who created the file.
    meta = with_retry(lambda: services["sheets"].spreadsheets().get(
        spreadsheetId=item["id"], fields="sheets.properties.title").execute())
    all_values: dict[str, list] = {}
    changed = False
    for tab in meta.get("sheets", []):
        title = tab["properties"]["title"]
        values = with_retry(lambda t=title: services["sheets"].spreadsheets().values().get(
            spreadsheetId=item["id"], range=f"'{t}'").execute()).get("values", [])
        all_values[title] = values
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerows(values)
        if write_if_changed(out_dir / f"{name}.{sanitize(title)}.csv", buf.getvalue().encode("utf-8")):
            changed = True
        written.append(f"{rel}{name}.{sanitize(title)}.csv")
    values_rel = f"{rel}{name}.values.json"
    if write_if_changed(out_dir / f"{name}.values.json",
                        json.dumps(all_values, ensure_ascii=False, indent=1).encode("utf-8")):
        changed = True
    manifest[values_rel] = {"fileId": item["id"], "name": item["name"], "kind": "spreadsheet-values"}
    written.append(values_rel)
    # Preferred restore layer (needs Drive content access; 403 on
    # manually-created files under drive.file scope). Google's binary export
    # is not byte-stable, so only re-export when the content layer actually
    # changed - otherwise every run would churn every binary into a commit.
    xlsx_path = out_dir / f"{name}.xlsx"
    xlsx_rel = f"{rel}{name}.xlsx"
    try:
        if changed or not xlsx_path.exists():
            write_if_changed(xlsx_path, export_bytes(services["drive"], item["id"], MIME_XLSX))
        manifest[xlsx_rel] = {"fileId": item["id"], "name": item["name"], "kind": "spreadsheet"}
        written.append(xlsx_rel)
    except Exception as exc:
        if not is_403(exc):
            raise
        warnings.append(f"{rel}{item['name']}: no Drive content access (drive.file scope) - "
                        "values-only restore layer")
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
        try:
            text, ext = export_bytes(services["drive"], item["id"], "text/markdown"), "md"
        except Exception as exc:
            if is_403(exc):
                raise
            text, ext = export_bytes(services["drive"], item["id"], "text/plain"), "txt"
        changed = write_if_changed(out_dir / f"{name}.{ext}", text)
        written.append(f"{rel}{name}.{ext}")
        # Binary restore layer only when the text layer changed (see
        # export_sheet on byte-unstable exports).
        docx_path = out_dir / f"{name}.docx"
        if changed or not docx_path.exists():
            write_if_changed(docx_path, export_bytes(services["drive"], item["id"], MIME_DOCX))
        docx_rel = f"{rel}{name}.docx"
        manifest[docx_rel] = {"fileId": item["id"], "name": item["name"], "kind": "document"}
        written.append(docx_rel)
    except Exception as exc:
        if not is_403(exc):
            raise
        warnings.append(f"{rel}{item['name']}: no Drive content access (drive.file scope) - "
                        "diff layer only via Docs API, NOT restorable")
        write_if_changed(out_dir / f"{name}.txt",
                         doc_plain_text(services, item["id"]).encode("utf-8"))
        written.append(f"{rel}{name}.txt")
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
    if not (mirror / ".git").exists():
        assert_private_mirror(mirror, DATA_ROOT, init_allowed=True)
        mirror.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=mirror, capture_output=True, check=True)
        (mirror / "README.md").write_text(MIRROR_README, encoding="utf-8")
        print(f"Initialized mirror repo at {mirror}")
    else:
        assert_private_mirror(mirror, DATA_ROOT, init_allowed=False)
    # The mirror needs its own identity (no global git config assumed) -
    # borrow the skills repo's, since the same person drives both.
    if not mirror_git(mirror, "config", "user.email").stdout.strip():
        skills_repo = Path(__file__).resolve().parents[2]
        for key, fallback in (("user.name", "qa-drive-mirror"),
                              ("user.email", "mirror@localhost")):
            val = subprocess.run(["git", "-C", str(skills_repo), "config", key],
                                 capture_output=True, text=True).stdout.strip() or fallback
            mirror_git(mirror, "config", key, val)

    services = get_services()
    manifest: dict = {}
    written: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    print("Exporting canonical documents (diff layer + restore layer)...")
    walk(services, ROOT_FOLDER_ID, mirror, "", manifest, written, errors, warnings)

    print("Exporting source text from queue...")
    try:
        q = find_queue(services)
        if q:
            rows = read_queue(services, q)
            protected_paths, source_errs, source_warns = export_source_texts(rows, DATA_ROOT, mirror_path)
            written.extend(protected_paths)
            errors.extend(source_errs)
            warnings.extend(source_warns)
    except Exception as exc:
        errors.append(f"Source text export failed: {exc}")

    # A doc that failed to export contributes nothing to `manifest`/`written`.
    # Its previously-exported files survive (prune is skipped below), so its
    # previous manifest entries must survive too - otherwise the files sit in
    # the commit unrestorable. Carry over any old entry whose file still
    # exists and wasn't re-exported this run.
    if errors:
        manifest_path = mirror / "_manifest.json"
        if manifest_path.exists():
            old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            carried = 0
            for key, entry in old_manifest.items():
                if key not in manifest and (mirror / key).exists():
                    manifest[key] = entry
                    carried += 1
            if carried:
                print(f"Carried {carried} manifest entr(ies) from failed-export documents forward.")
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    write_if_changed(mirror / "_manifest.json", manifest_bytes)
    # Same reasoning for pruning: after errors it would delete the failed
    # documents' previously-good files. Skip.
    removed = prune_stale(mirror, set(written)) if not errors else 0
    if errors:
        print("Prune skipped because of export errors - stale files (if any) survive until a clean run.")
    print(f"Exported {len(written)} files ({len(manifest)} restore-layer entries), "
          f"pruned {removed} stale.")
    for warn in warnings:
        print(f"  note: {warn}")
    for err in errors:
        print(f"  EXPORT FAILED: {err}")

    mirror_git(mirror, "add", "-A")
    if not mirror_git(mirror, "status", "--porcelain").stdout.strip():
        print("No changes since last commit - nothing to do.")
        return 0
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = args.message or f"workspace state {stamp}"
    if errors:
        msg += f" [PARTIAL: {len(errors)} export failure(s)]"
        body = "\n".join(f"  failed: {e.splitlines()[0][:200]}" for e in errors)
        res = mirror_git(mirror, "commit", "-m",
                      f"{msg}\n\nExported {stamp} by commit_workspace_state.py\n{body}")
    else:
        res = mirror_git(mirror, "commit", "-m", f"{msg}\n\nExported {stamp} by commit_workspace_state.py")
    if res.returncode != 0:
        print(f"git commit failed: {res.stderr.strip()}")
        return 1
    sha = mirror_git(mirror, "rev-parse", "--short", "HEAD").stdout.strip()
    print(f"Committed {sha}: {msg}")
    print(mirror_git(mirror, "show", "--stat", "--oneline", "-s", "HEAD").stdout.strip())
    changed = mirror_git(mirror, "diff", "--name-only", "HEAD~1", "HEAD").stdout.strip()
    if changed:
        print("Changed files:")
        for line in changed.splitlines():
            print(f"  {line}")

    if not args.no_bundle:
        print(refresh_bundle(mirror))
    return 1 if errors else 0


def refresh_bundle(mirror: Path) -> str:
    """Pack the mirror's full history into the single-file Drive bundle.
    Reused by qa_manage.py's terminal queue commits - the architecture
    requires the bundle after every mirror commit, not only full exports.
    Returns a human-readable status; never raises (a failed bundle loses
    nothing locally)."""
    try:
        BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
        bundle = BUNDLE_DIR / "mirror.bundle"
        res = mirror_git(mirror, "bundle", "create", str(bundle), "--all")
        if res.returncode == 0:
            return f"Bundle backup refreshed: {bundle}"
        return f"Bundle backup FAILED (history is still safe locally): {res.stderr.strip()}"
    except OSError as exc:
        return f"Bundle backup FAILED (history is still safe locally): {exc}"


if __name__ == "__main__":
    sys.exit(main())
