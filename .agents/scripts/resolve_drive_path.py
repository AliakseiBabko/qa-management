#!/usr/bin/env python3
"""Resolve a local Google-Drive-for-desktop mirror path to its real Drive
file/folder, via the Drive API - no browser needed, and works for
Google-native placeholders (.gdoc/.gsheet/.gslides) that carry no readable
bytes on disk at all (see AGENTS.md / api-sharing-editing.md for why direct
file reads on those fail with "Incorrect function").

The local mirror (Google Drive for Desktop, "Mirror" mode) is a 1:1 copy of
this Drive account's folder tree rooted at `G:\\My Drive\\QA_Management`
(qa_manage.DATA_ROOT), which is itself the Drive folder
`sync_m2_source_docs_to_sheets.ROOT_FOLDER_ID`. Resolving a local path is
just walking that same folder tree by name via the Drive API - the same
technique qa_manage.compute_source_file_hash already uses internally for
Google-native placeholders, generalized here as a standalone lookup anyone
can call directly instead of falling back to opening a browser.

Usage:
    python resolve_drive_path.py "G:\\My Drive\\QA_Management\\00_Inbox\\PKF"
    python resolve_drive_path.py "G:\\My Drive\\QA_Management\\00_Inbox\\PKF\\PKF - Perfomance Strategy v2.gdoc"
    python resolve_drive_path.py --json "<path>"

Prints id, name, mimeType, and webViewLink (the browser-openable Drive URL)
for a folder or a file at that path. For a Google-native file, the returned
`id` is also what Docs/Sheets export endpoints need directly:
    https://docs.google.com/document/d/<id>/export?format=txt
    https://docs.google.com/spreadsheets/d/<id>/export?format=xlsx
or, with this OAuth client's scopes, via
`docs_service.documents().get(documentId=id)` /
`sheets_service.spreadsheets().values().get(spreadsheetId=id, ...)` directly
- no export URL or browser required either way.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from m2_workspace_layout import drive_query, find_child_folder, find_folder_path, q_escape
from pipeline_common import get_services
from qa_manage import DATA_ROOT
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

GOOGLE_NATIVE_EXTS = {".gdoc", ".gsheet", ".gslides", ".gform", ".gdrew"}
FOLDER_MIME = "application/vnd.google-apps.folder"


class ResolveError(Exception):
    pass


def resolve(drive: Any, local_path: Path) -> dict[str, Any]:
    """Resolve a local mirror path to its Drive file/folder metadata.

    Raises ResolveError with a clear message if the path isn't under
    DATA_ROOT, or if a folder/file along the way isn't found - the walk is
    literal (name-by-name), so a rename in Drive that hasn't synced locally
    yet, or a typo, surfaces immediately rather than silently matching the
    wrong item.
    """
    try:
        rel = local_path.resolve().relative_to(DATA_ROOT.resolve())
    except ValueError:
        raise ResolveError(
            f"{local_path} is not under the QA_Management Drive mirror root ({DATA_ROOT}). "
            "Only paths under that root are resolvable this way."
        )

    parts = [p for p in rel.parts if p not in ("", ".")]
    if not parts:
        return {"id": ROOT_FOLDER_ID, "name": DATA_ROOT.name, "mimeType": FOLDER_MIME,
                 "webViewLink": f"https://drive.google.com/drive/folders/{ROOT_FOLDER_ID}"}

    *folder_parts, leaf = parts
    parent = find_folder_path(drive, ROOT_FOLDER_ID, folder_parts)
    if not parent:
        raise ResolveError(f"Could not find folder path {'/'.join(folder_parts)!r} under {DATA_ROOT}")

    ext = Path(leaf).suffix.lower()
    if ext == "":
        # A folder - leaf itself has no extension.
        found = find_child_folder(drive, parent["id"], leaf)
        if not found:
            raise ResolveError(f"Could not find folder {leaf!r} under {'/'.join(folder_parts) or DATA_ROOT.name}")
        return found

    stem = leaf[: -len(ext)] if ext in GOOGLE_NATIVE_EXTS else leaf
    matches = drive_query(
        drive,
        f"'{parent['id']}' in parents and trashed = false and "
        f"(name = '{q_escape(leaf)}' or name = '{q_escape(stem)}')",
    )
    if ext in GOOGLE_NATIVE_EXTS:
        matches = [m for m in matches if m.get("name") in (leaf, stem)]
    if not matches:
        raise ResolveError(f"Could not find file {leaf!r} under {'/'.join(folder_parts) or DATA_ROOT.name}")
    if len(matches) > 1:
        raise ResolveError(f"Ambiguous match for {leaf!r} under {'/'.join(folder_parts) or DATA_ROOT.name}: "
                            f"{[m['id'] for m in matches]}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help=r"Local path under G:\My Drive\QA_Management (folder or file, "
                                      r"including a .gdoc/.gsheet placeholder)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    services = get_services()
    try:
        result = resolve(services["drive"], Path(args.path))
    except ResolveError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    else:
        print(f"id:      {result.get('id')}")
        print(f"name:    {result.get('name')}")
        print(f"mime:    {result.get('mimeType')}")
        print(f"link:    {result.get('webViewLink', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
