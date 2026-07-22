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
`90_Storage` and `01_Recordings` are excluded.

The mirror repo lives OUTSIDE both the public skills repo (it holds real
names - it must never share a git history with anything public) and the
synced Drive folder (Drive sync chokes on `.git` object files). Default:
`~/Documents/qa-drive-mirror`, auto-initialized on first run. After every
commit the full history is packed into a single-file `git bundle` under
`90_Storage/Backups/` on Drive, so a dead laptop costs nothing:
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
from typing import TypeVar, Callable
from mirror_common import mirror_git, assert_private_mirror
from qa_manage import DATA_ROOT, find_queue, read_queue
from export_source_text import export as export_source_texts
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import socket

# Some large Sheets exceed the default socket timeout reproducibly.
socket.setdefaulttimeout(180)

from pipeline_common import get_services
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

DEFAULT_MIRROR = Path.home() / "Documents" / "qa-drive-mirror"
BUNDLE_DIR = Path(r"G:\My Drive\QA_Management\90_Storage\Backups")
SKIP_FOLDERS = {"90_Storage", "01_Recordings"}
DEFAULT_SLOWEST_FILES_LIMIT = 10


class ExportStats:
    """Per-run export instrumentation, collected during `walk()`/the export
    helpers and printed as a summary (optionally dumped via --stats-out).
    Purely observational - never influences what gets written, pruned, or
    the process exit code. `mode` exists so a future scoped-export mode
    (Phase 14) can reuse this same collector; only "full" is produced
    today."""

    def __init__(self, mode: str = "full") -> None:
        self.mode = mode
        self.folders_scanned = 0
        self.files_considered = 0
        self.files_exported_or_checked = 0
        self.files_written_changed = 0
        self.files_skipped_unchanged = 0
        self.retries_total = 0
        self.errors_count = 0
        self.warnings_count = 0
        self.elapsed_total_ms = 0.0
        self._file_timings: list[tuple[str, float, str]] = []
        # Scoped mode only (Phase 14B) - always 0/empty for full mode.
        self.scoped_prefix_count = 0
        self.scoped_exact_count = 0
        self.scope_warnings: list[str] = []

    def record_file(self, path: str, elapsed_ms: float, operation: str) -> None:
        self._file_timings.append((path, elapsed_ms, operation))

    def record_retry(self) -> None:
        self.retries_total += 1

    def slowest_files(self, limit: int = DEFAULT_SLOWEST_FILES_LIMIT) -> list[dict]:
        top = sorted(self._file_timings, key=lambda t: t[1], reverse=True)[:limit]
        return [{"path": p, "elapsed_ms": round(e, 1), "operation": op} for p, e, op in top]

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "folders_scanned": self.folders_scanned,
            "files_considered": self.files_considered,
            "files_exported_or_checked": self.files_exported_or_checked,
            "files_written_changed": self.files_written_changed,
            "files_skipped_unchanged": self.files_skipped_unchanged,
            "retries_total": self.retries_total,
            "errors_count": self.errors_count,
            "warnings_count": self.warnings_count,
            "elapsed_total_ms": round(self.elapsed_total_ms, 1),
            "slowest_files": self.slowest_files(),
            "scoped_prefix_count": self.scoped_prefix_count,
            "scoped_exact_count": self.scoped_exact_count,
            "scope_warnings": list(self.scope_warnings),
        }

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


def run_git(mirror: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(mirror), *args],
                          capture_output=True, text=True, encoding="utf-8")


def refresh_bundle(mirror: Path) -> str:
    """Pack the mirror's full history into the Drive recovery bundle."""
    try:
        BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
        bundle = BUNDLE_DIR / "mirror.bundle"
        res = mirror_git(mirror, "bundle", "create", str(bundle), "--all")
        if res.returncode == 0:
            return f"Bundle backup refreshed: {bundle}"
        return f"Bundle backup FAILED (history is still safe locally): {res.stderr.strip()}"
    except OSError as exc:
        return f"Bundle backup FAILED (history is still safe locally): {exc}"


def list_children(drive, folder_id: str) -> list[dict]:
    items, token = [], None
    while True:
        resp = drive.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, headRevisionId)",
            pageSize=200, pageToken=token,
        ).execute()
        items.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            return items


def is_403(exc: Exception) -> bool:
    return "403" in str(exc) and "appNotAuthorizedToFile" in str(exc)


def drive_fingerprint(item: dict, mirror_path: str) -> dict:
    """Non-volatile Drive-side metadata for a manifest entry: identifies
    *which* Drive revision was exported without any wall-clock timestamp, so
    re-running the export over an unchanged file never dirties the manifest
    (see orchestrate_export). Fields are best-effort - `list_children` may
    not populate headRevisionId/modifiedTime for every file type, and older
    manifest entries predate this function entirely; missing values are
    always blank, never a failure."""
    return {
        "drive_path": mirror_path,
        "mimeType": item.get("mimeType", ""),
        "headRevisionId": item.get("headRevisionId", ""),
        "modifiedTime": item.get("modifiedTime", ""),
    }


T = TypeVar("T")


def with_retry(fn: Callable[[], T], attempts: int = 3, stats: "ExportStats | None" = None) -> T:
    """Retry transient failures (timeouts, 5xx); 403s are permanent, raise at
    once. A 429 is the Sheets per-minute read quota (60/min/user) - short
    backoff can't clear it, so wait out the window instead."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if is_403(exc) or i == attempts - 1:
                raise
            if stats is not None:
                stats.record_retry()
            if "429" in str(exc) or "RATE_LIMIT_EXCEEDED" in str(exc):
                time.sleep(65)
            else:
                time.sleep(2 * (i + 1))
    raise RuntimeError("Retry limit reached")


def export_bytes(drive, file_id: str, mime: str, stats: "ExportStats | None" = None) -> bytes:
    res = with_retry(lambda: drive.files().export(fileId=file_id, mimeType=mime).execute(),
                     stats=stats)
    return res if isinstance(res, bytes) else b""


def write_if_changed(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def export_sheet(services, item: dict, out_dir: Path, rel: str, manifest: dict,
                 warnings: list[str], stats: "ExportStats | None" = None) -> list[str]:
    name = sanitize(item["name"])
    rel = f"{rel}/" if rel else ""
    written = []
    # Diff layer (CSV per tab) + universal values restore layer - Sheets API,
    # works regardless of who created the file.
    meta = with_retry(lambda: services["sheets"].spreadsheets().get(
        spreadsheetId=item["id"], fields="sheets.properties.title").execute(), stats=stats)
    all_values: dict[str, list] = {}
    changed = False
    sheets = meta.get("sheets", []) if isinstance(meta, dict) else []
    for tab in sheets:
        title = tab["properties"]["title"]
        val_resp = with_retry(lambda t=title: services["sheets"].spreadsheets().values().get(
            spreadsheetId=item["id"], range=f"'{t}'").execute(), stats=stats)
        values = val_resp.get("values", []) if isinstance(val_resp, dict) else []
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
    manifest[values_rel] = {"fileId": item["id"], "name": item["name"], "kind": "spreadsheet-values",
                            **drive_fingerprint(item, values_rel)}
    written.append(values_rel)
    # Preferred restore layer (needs Drive content access; 403 on
    # manually-created files under drive.file scope). Google's binary export
    # is not byte-stable, so only re-export when the content layer actually
    # changed - otherwise every run would churn every binary into a commit.
    xlsx_path = out_dir / f"{name}.xlsx"
    xlsx_rel = f"{rel}{name}.xlsx"
    try:
        if changed or not xlsx_path.exists():
            if write_if_changed(xlsx_path, export_bytes(services["drive"], item["id"], MIME_XLSX, stats=stats)):
                changed = True
        manifest[xlsx_rel] = {"fileId": item["id"], "name": item["name"], "kind": "spreadsheet",
                              **drive_fingerprint(item, xlsx_rel)}
        written.append(xlsx_rel)
    except Exception as exc:
        if not is_403(exc):
            raise
        warnings.append(f"{rel}{item['name']}: no Drive content access (drive.file scope) - "
                        "values-only restore layer")
    if stats is not None:
        stats.files_exported_or_checked += 1
        if changed:
            stats.files_written_changed += 1
        else:
            stats.files_skipped_unchanged += 1
    return written


def doc_plain_text(services, doc_id: str) -> str:
    """Docs-API fallback text extraction for docs without Drive content access."""
    doc = with_retry(lambda: services["docs"].documents().get(documentId=doc_id).execute())
    parts: list[str] = []
    body_content = doc.get("body", {}).get("content", []) if isinstance(doc, dict) else []
    for element in body_content:
        if isinstance(element, dict):
            for pe in element.get("paragraph", {}).get("elements", []):
                if isinstance(pe, dict):
                    parts.append(pe.get("textRun", {}).get("content", ""))
    return "".join(parts)


def export_doc(services, item: dict, out_dir: Path, rel: str, manifest: dict,
               warnings: list[str], stats: "ExportStats | None" = None) -> list[str]:
    name = sanitize(item["name"])
    rel = f"{rel}/" if rel else ""
    written = []
    changed = False
    try:
        try:
            text, ext = export_bytes(services["drive"], item["id"], "text/markdown", stats=stats), "md"
        except Exception as exc:
            if is_403(exc):
                raise
            text, ext = export_bytes(services["drive"], item["id"], "text/plain", stats=stats), "txt"
        changed = write_if_changed(out_dir / f"{name}.{ext}", text)
        written.append(f"{rel}{name}.{ext}")
        # Binary restore layer only when the text layer changed (see
        # export_sheet on byte-unstable exports).
        docx_path = out_dir / f"{name}.docx"
        if changed or not docx_path.exists():
            if write_if_changed(docx_path, export_bytes(services["drive"], item["id"], MIME_DOCX, stats=stats)):
                changed = True
        docx_rel = f"{rel}{name}.docx"
        manifest[docx_rel] = {"fileId": item["id"], "name": item["name"], "kind": "document",
                              **drive_fingerprint(item, docx_rel)}
        written.append(docx_rel)
    except Exception as exc:
        if not is_403(exc):
            raise
        warnings.append(f"{rel}{item['name']}: no Drive content access (drive.file scope) - "
                        "diff layer only via Docs API, NOT restorable")
        changed = write_if_changed(out_dir / f"{name}.txt",
                                   doc_plain_text(services, item["id"]).encode("utf-8"))
        written.append(f"{rel}{name}.txt")
    if stats is not None:
        stats.files_exported_or_checked += 1
        if changed:
            stats.files_written_changed += 1
        else:
            stats.files_skipped_unchanged += 1
    return written


def walk(services, folder_id: str, out_dir: Path, rel: str, manifest: dict,
         written: list[str], errors: list[str], warnings: list[str],
         stats: "ExportStats | None" = None, recursive: bool = True,
         name_filter: "set[str] | None" = None) -> None:
    """`recursive=False` exports only this folder's direct Sheet/Doc
    children and does not descend into subfolders - used by scoped mode
    (Phase 14B) for workspace-root and lane-root "direct file children"
    scans. `name_filter`, when given, further restricts direct children to
    items whose sanitized name is in the set (used for the workspace-root
    scan, which must only ever pick up the fixed always-include names)."""
    if stats is not None:
        stats.folders_scanned += 1
    for item in sorted(list_children(services["drive"], folder_id), key=lambda i: i["name"]):
        if item["mimeType"] == MIME_FOLDER:
            if not recursive:
                continue
            if item["name"] in SKIP_FOLDERS:
                continue
            sub = sanitize(item["name"])
            walk(services, item["id"], out_dir / sub,
                 f"{rel}/{sub}" if rel else sub, manifest, written, errors, warnings, stats)
        elif item["mimeType"] in (MIME_GSHEET, MIME_GDOC):
            if name_filter is not None and sanitize(item["name"]) not in name_filter:
                continue
            if stats is not None:
                stats.files_considered += 1
            label = f"{rel}/{item['name']}" if rel else item["name"]
            operation = "sheet" if item["mimeType"] == MIME_GSHEET else "doc"
            start = time.perf_counter()
            try:
                fn = export_sheet if item["mimeType"] == MIME_GSHEET else export_doc
                written.extend(fn(services, item, out_dir, rel, manifest, warnings, stats))
            except Exception as exc:
                errors.append(f"{rel}/{item['name']}: {exc}")
            finally:
                if stats is not None:
                    stats.record_file(label, (time.perf_counter() - start) * 1000, operation)
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


class ScopedExportRefused(Exception):
    """A --scoped run's scope could not be safely resolved to Drive
    folders/graph data. Scoped mode must fail closed here rather than ever
    silently narrowing what it exports - the caller (main()) reports this
    and the operator re-runs in full mode."""


# Physical paths/prefixes a scoped export never touches for pruning
# purposes, regardless of scope: `_manifest.json` and
# `_source_text_manifest.json` are rewritten by the export itself (not
# stale-pruned - see merge_scoped_manifest), and every source-text blob is
# already independently protected by export_source_text.py's own
# carry-forward logic (blobs for runs outside this scope must never be
# treated as candidates just because they happen to live in the mirror).
SCOPED_ALWAYS_PROTECTED = {"README.md", "_manifest.json", "_source_text_manifest.json"}
SCOPED_ALWAYS_PROTECTED_PREFIXES = ("_source_text/",)


def path_in_scope(rel: str, scoped_prefixes: "set[str]", scoped_shallow_prefixes: "set[str]") -> bool:
    """True when `rel` (a mirror-relative path) falls inside this run's
    scope: either under a recursive project/person subtree prefix, or a
    DIRECT child of a shallow-scanned prefix (workspace root is the ""
    prefix; a lane root is its sanitized folder name). A file nested
    deeper under a shallow prefix than one level (i.e. inside some OTHER
    project/person folder under the same lane root) is correctly NOT in
    scope unless it's also under one of scoped_prefixes."""
    for prefix in scoped_prefixes:
        if rel == prefix or rel.startswith(prefix + "/"):
            return True
    parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
    return parent in scoped_shallow_prefixes


def merge_scoped_manifest(old_manifest: dict, fresh_manifest: dict,
                          scoped_prefixes: "set[str]", scoped_shallow_prefixes: "set[str]") -> dict:
    """Start from the full old manifest (untouched, byte-for-byte, for
    every path outside this run's scope), overlay this run's freshly
    exported entries, and drop only entries that are BOTH inside scope and
    no longer backed by a live export this run (stale-within-scope)."""
    new_manifest = dict(old_manifest)
    new_manifest.update(fresh_manifest)
    for path in list(new_manifest):
        if path in fresh_manifest:
            continue
        if path_in_scope(path, scoped_prefixes, scoped_shallow_prefixes):
            del new_manifest[path]
    return new_manifest


def prune_stale_scoped(mirror: Path, expected: "set[str]",
                       scoped_prefixes: "set[str]", scoped_shallow_prefixes: "set[str]") -> int:
    """Like prune_stale(), but a physical file is only a delete candidate
    when it is both stale (not in `expected`) AND inside this run's scope.
    Anything outside scope is never inspected for deletion, no matter how
    old or orphaned it looks - that's the whole safety property scoped
    mode exists to preserve."""
    removed = 0
    for path in mirror.rglob("*"):
        if ".git" in path.parts or path.is_dir():
            continue
        rel = path.relative_to(mirror).as_posix()
        if rel in expected or rel in SCOPED_ALWAYS_PROTECTED:
            continue
        if any(rel.startswith(p) for p in SCOPED_ALWAYS_PROTECTED_PREFIXES):
            continue
        if not path_in_scope(rel, scoped_prefixes, scoped_shallow_prefixes):
            continue
        path.unlink()
        removed += 1
    # Empty-dir cleanup restricted to the scoped subtree roots themselves -
    # never a global sweep (full mode's prune_stale sweeps the whole
    # mirror; scoped mode must not touch directories outside its prefixes
    # even if they happen to be empty for unrelated reasons).
    for prefix in scoped_prefixes:
        d = mirror / prefix
        if not d.exists() or not d.is_dir():
            continue
        for sub in sorted((p for p in d.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(sub.iterdir()):
                sub.rmdir()
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
    return removed


def orchestrate_export_scoped(services, mirror: Path, data_root: Path, run_id: str,
                              walk_fn=walk, export_source_texts_fn=export_source_texts,
                              find_queue_fn=find_queue, read_queue_fn=read_queue,
                              resolve_scope_fn=None,
                              stats: "ExportStats | None" = None):
    """Scoped counterpart of orchestrate_export(): exports only the
    folders/files run_id's scope needs, per scope_resolver.resolve_scope(),
    plus workspace-root/lane-root bookkeeping and source-text as always.
    Raises ScopedExportRefused (never partially narrows scope) when
    resolution fails at either the graph/queue level or the Drive-folder
    level. Full mode (orchestrate_export) is completely untouched by this
    function."""
    t0 = time.perf_counter()
    if stats is None:
        stats = ExportStats(mode="scoped")
    if resolve_scope_fn is None:
        from scope_resolver import resolve_scope as resolve_scope_fn

    resolution = resolve_scope_fn(services, run_id)
    if not resolution.ok:
        raise ScopedExportRefused(resolution.reason)
    stats.scope_warnings = list(resolution.warnings)
    stats.scoped_prefix_count = len(resolution.subtree_prefixes)
    stats.scoped_exact_count = len(resolution.always_include_names) + len(resolution.lane_root_prefixes)

    manifest_path = mirror / "_manifest.json"
    if not manifest_path.exists():
        raise ScopedExportRefused(
            "No _manifest.json in the mirror yet - run a full export first "
            "(scoped mode always starts from an existing, trustworthy manifest)."
        )
    try:
        old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ScopedExportRefused(f"Malformed _manifest.json - refusing to prune or merge: {exc}")

    fresh_manifest: dict = {}
    written: list[str] = []
    errors: list[str] = []
    warnings: list[str] = list(resolution.warnings)

    from m2_workspace_layout import find_folder_path
    drive = services["drive"]

    # 1. Workspace-root direct files (name-filtered to the fixed always-include set).
    walk_fn(services, ROOT_FOLDER_ID, mirror, "", fresh_manifest, written, errors, warnings, stats,
           recursive=False, name_filter=set(resolution.always_include_names))

    scoped_shallow_prefixes = {""}
    lane_root_ids: dict[str, str] = {}

    def resolve_lane_root(lane_prefix: str) -> str:
        found = find_folder_path(drive, ROOT_FOLDER_ID, [lane_prefix])
        if not found:
            raise ScopedExportRefused(f"Lane root folder {lane_prefix!r} not found in Drive.")
        return str(found["id"])

    # 2. Lane-root direct files (unfiltered - any live direct file child).
    for lane_prefix in sorted(resolution.lane_root_prefixes):
        lane_root_ids[lane_prefix] = resolve_lane_root(lane_prefix)
        sanitized_lane = sanitize(lane_prefix)
        scoped_shallow_prefixes.add(sanitized_lane)
        walk_fn(services, lane_root_ids[lane_prefix], mirror / sanitized_lane, sanitized_lane,
               fresh_manifest, written, errors, warnings, stats, recursive=False)

    scoped_prefixes: set[str] = set()

    # 3. Project/person subtrees, recursively.
    for subtree in sorted(resolution.subtree_prefixes):
        lane_prefix, _, entity = subtree.partition("/")
        if lane_prefix not in lane_root_ids:
            lane_root_ids[lane_prefix] = resolve_lane_root(lane_prefix)
        entity_folder = find_folder_path(drive, lane_root_ids[lane_prefix], [entity])
        if not entity_folder:
            raise ScopedExportRefused(f"Scoped folder {subtree!r} not found in Drive.")
        rel = f"{sanitize(lane_prefix)}/{sanitize(entity)}"
        scoped_prefixes.add(rel)
        walk_fn(services, str(entity_folder["id"]), mirror / rel, rel,
               fresh_manifest, written, errors, warnings, stats, recursive=True)

    # 4. Source-text export - unchanged, always covers every eligible queue
    #    row (cheap/local, no Drive calls; see export_source_text.py).
    try:
        rows = read_queue_fn(services, find_queue_fn(services))
        protected_paths, source_errs, source_warns = export_source_texts_fn(rows, data_root, mirror)
        written.extend(protected_paths)
        errors.extend(source_errs)
        warnings.extend(source_warns)
    except Exception as exc:
        errors.append(f"Source text export failed: {exc}")

    manifest = merge_scoped_manifest(old_manifest, fresh_manifest, scoped_prefixes, scoped_shallow_prefixes)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    write_if_changed(manifest_path, manifest_bytes)

    removed = (prune_stale_scoped(mirror, set(written), scoped_prefixes, scoped_shallow_prefixes)
              if not errors else 0)

    stats.errors_count = len(errors)
    stats.warnings_count = len(warnings)
    stats.elapsed_total_ms = (time.perf_counter() - t0) * 1000

    return written, manifest, removed, warnings, errors, stats


def orchestrate_export(services, mirror, data_root, walk_fn, export_source_texts_fn, find_queue_fn, read_queue_fn,
                       stats: "ExportStats | None" = None):
    t0 = time.perf_counter()
    if stats is None:
        stats = ExportStats(mode="full")
    manifest: dict = {}
    written: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    walk_fn(services, ROOT_FOLDER_ID, mirror, "", manifest, written, errors, warnings, stats)

    try:
        q = find_queue_fn(services)
        if q:
            rows = read_queue_fn(services, q)
            protected_paths, source_errs, source_warns = export_source_texts_fn(rows, data_root, mirror)
            written.extend(protected_paths)
            errors.extend(source_errs)
            warnings.extend(source_warns)
    except Exception as exc:
        errors.append(f"Source text export failed: {exc}")

    if errors:
        manifest_path = mirror / "_manifest.json"
        if manifest_path.exists():
            old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            carried = 0
            for key, entry in old_manifest.items():
                if key not in manifest and (mirror / key).exists():
                    manifest[key] = entry
                    carried += 1

    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    write_if_changed(mirror / "_manifest.json", manifest_bytes)

    removed = prune_stale(mirror, set(written)) if not errors else 0

    stats.errors_count = len(errors)
    stats.warnings_count = len(warnings)
    stats.elapsed_total_ms = (time.perf_counter() - t0) * 1000

    return written, manifest, removed, warnings, errors, stats

def main() -> int:
    module_doc = __doc__ or "Commit the Google Workspace state to the private mirror"
    parser = argparse.ArgumentParser(description=module_doc.splitlines()[0])
    parser.add_argument("-m", "--message", default="",
                        help="commit message; describe the pass that caused the changes "
                             "(skill, source), same info as the _skill_invocations row")
    parser.add_argument("--mirror", default=str(DEFAULT_MIRROR), help="mirror repo path")
    parser.add_argument("--no-bundle", action="store_true", help="skip the Drive bundle backup")
    parser.add_argument("--stats-out", default=None,
                        help="write a JSON export-stats object to this path (opt-in; nothing is "
                             "written unless this is passed). Local/private output only - may "
                             "contain real Drive path names.")
    parser.add_argument("--scoped", action="store_true",
                        help="Phase 14B: export only the folders/files --run-id's scope needs, "
                             "plus workspace/lane bookkeeping and source-text (opt-in; full "
                             "export remains the default). Requires --run-id.")
    parser.add_argument("--run-id", default=None,
                        help="run id whose scope to export; required with --scoped")
    args = parser.parse_args()
    if args.scoped and not args.run_id:
        parser.error("--scoped requires --run-id")

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

    if args.scoped:
        print(f"Exporting scoped documents for run {args.run_id!r} and source text...")
        try:
            written, manifest, removed, warnings, errors, stats = orchestrate_export_scoped(
                services, mirror, DATA_ROOT, args.run_id
            )
        except ScopedExportRefused as exc:
            print(f"Scoped export refused: {exc}")
            print("Re-run without --scoped (full export) instead.")
            return 1
    else:
        print("Exporting canonical documents and source text...")
        written, manifest, removed, warnings, errors, stats = orchestrate_export(
            services, mirror, DATA_ROOT, walk, export_source_texts, find_queue, read_queue
        )

    if errors:
        print("Prune skipped because of export errors - stale files (if any) survive until a clean run.")
    print(f"Exported {len(written)} files ({len(manifest)} restore-layer entries), "
          f"pruned {removed} stale.")
    for warn in warnings:
        print(f"  note: {warn}")
    for err in errors:
        print(f"  EXPORT FAILED: {err}")

    print(f"  stats: mode={stats.mode} folders_scanned={stats.folders_scanned} "
          f"files_considered={stats.files_considered} "
          f"files_exported_or_checked={stats.files_exported_or_checked} "
          f"files_written_changed={stats.files_written_changed} "
          f"files_skipped_unchanged={stats.files_skipped_unchanged} "
          f"retries_total={stats.retries_total} errors={stats.errors_count} "
          f"warnings={stats.warnings_count} elapsed_total_ms={stats.elapsed_total_ms:.0f}")
    if stats.mode == "scoped":
        # scope_warnings are also already in `warnings` above (printed as
        # "note:") - this line is just the scoped-mode-specific counts.
        print(f"  scoped: run_id={args.run_id} scoped_prefix_count={stats.scoped_prefix_count} "
              f"scoped_exact_count={stats.scoped_exact_count}")
    slowest = stats.slowest_files()
    if slowest:
        print("  slowest files:")
        for f in slowest:
            print(f"    {f['elapsed_ms']:.0f}ms {f['operation']:5s} {f['path']}")
    if args.stats_out:
        stats_path = Path(args.stats_out)
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Stats written to {stats_path}")

    mirror_git(mirror, "add", "-A")
    if not mirror_git(mirror, "status", "--porcelain").stdout.strip():
        print("No changes since last commit - nothing to do.")
        return 0
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = args.message or f"workspace state {stamp}"
    exported_by = (f"Exported {stamp} by commit_workspace_state.py "
                  f"(scoped export, run {args.run_id})" if args.scoped
                  else f"Exported {stamp} by commit_workspace_state.py")
    if errors:
        msg += f" [PARTIAL: {len(errors)} export failure(s)]"
        body = "\n".join(f"  failed: {e.splitlines()[0][:200]}" for e in errors)
        res = mirror_git(mirror, "commit", "-m", f"{msg}\n\n{exported_by}\n{body}")
    else:
        res = mirror_git(mirror, "commit", "-m", f"{msg}\n\n{exported_by}")
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


if __name__ == "__main__":
    sys.exit(main())
