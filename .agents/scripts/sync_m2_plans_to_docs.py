#!/usr/bin/env python3
"""Sync project/individual development plans from extracted references into Google Docs.

Development plans are narrative documents (business context, current state,
a plan broken into review horizons, open decisions, risks) rather than
tabular records, so they are stored as Google Docs instead of Google Sheets:

- 20_M2_Project_Management/<Project>/private/project_development_plan
- 20_M2_Project_Management/<Project>/people/<Person>/shared/individual_development_plan

Any pre-existing Sheet with the same title is archived (renamed and moved into
90_Archive/20_M2_Project_Management/<Project>/) rather than deleted, since it
may still be useful history. Archives live under the single workspace-wide
90_Archive tree rather than inside each active project folder, so there is
one place to look for retired artifacts instead of two.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

from m2_workspace_layout import ensure_document_folder

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials, move_file_to_folder
from generate_m2_outputs import read_manifest
from sync_m2_source_docs_to_sheets import (
    ROOT_FOLDER_ID,
    IGNORED_PROJECTS,
    SHEET_MIME_TYPE,
    drive_query,
    find_or_create_folder,
    markdown_for,
    parse_person_from_heading,
    q_escape,
    resolve_existing_person_dir,
)

DOC_MIME_TYPE = "application/vnd.google-apps.document"
METADATA_PREFIXES = ("обновлено", "review cycle", "stream")


def parse_args() -> argparse.Namespace:
    today = dt.date.today().isoformat()
    parser = argparse.ArgumentParser(description="Sync development-plan Google Docs from extracted source docs.")
    parser.add_argument(
        "--extract-root",
        default=rf"G:\My Drive\QA_Management\_System\extracts\source\{today}",
        help="Dated extraction folder produced by qa_source_extract.py.",
    )
    parser.add_argument(
        "--credentials",
        default=".local/google/credentials.json",
        help="OAuth desktop client JSON path.",
    )
    parser.add_argument(
        "--token",
        default=".local/google/token.json",
        help="OAuth token cache path.",
    )
    return parser.parse_args()


def find_file_in_folder(drive: Any, folder_id: str, title: str, mime_type: str) -> dict[str, Any] | None:
    matches = drive_query(
        drive,
        (
            f"'{folder_id}' in parents and name = '{q_escape(title)}' and "
            f"mimeType = '{mime_type}' and trashed = false"
        ),
        fields="id,name,mimeType",
    )
    return matches[0] if matches else None


def archive_existing_sheet(drive: Any, folder_id: str, archive_folder_id: str, title: str, label: str) -> None:
    existing = find_file_in_folder(drive, folder_id, title, SHEET_MIME_TYPE)
    if not existing:
        return
    superseded_name = f"{label}_superseded_by_doc_{dt.date.today().isoformat()}"
    drive.files().update(fileId=existing["id"], body={"name": superseded_name}, fields="id,name").execute()
    move_file_to_folder(drive, existing["id"], archive_folder_id)


def parse_blocks(markdown: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    metadata_parts: list[str] = []
    seen_title = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading_match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading_match:
            hashes, text = heading_match.groups()
            if text.startswith("- ") or text.startswith("• "):
                blocks.append({"type": "bullet", "text": text[2:].strip()})
                continue
            if len(hashes) == 1:
                # Redundant "# <filename>" heading; the real title is the next line.
                continue
            if any(text.casefold().startswith(prefix) for prefix in METADATA_PREFIXES):
                metadata_parts.append(text)
                continue
            if not seen_title:
                blocks.append({"type": "title", "text": text})
                seen_title = True
            else:
                blocks.append({"type": "heading", "text": text})
            continue
        bullet_match = re.match(r"^[-•]\s+(.*)$", line)
        if bullet_match:
            blocks.append({"type": "bullet", "text": bullet_match.group(1).strip()})
            continue
        blocks.append({"type": "paragraph", "text": line})

    if metadata_parts:
        insert_at = 1 if blocks and blocks[0]["type"] == "title" else 0
        blocks.insert(insert_at, {"type": "metadata", "text": " · ".join(metadata_parts)})
    return blocks


INLINE_TOKEN_RE = re.compile(r"\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)]+)\)")


def render_inline(text: str) -> tuple[str, list[tuple[int, int, str]]]:
    """Parse inline **bold** and [label](url) markup out of a block's text.

    Returns (plain_text, styles) where styles is a list of
    (start, end, kind) local offsets into plain_text; kind is "bold" or a
    URL string (meaning a link should be applied to that range).
    """
    parts: list[str] = []
    styles: list[tuple[int, int, str]] = []
    pos = 0
    length = 0
    for m in INLINE_TOKEN_RE.finditer(text):
        before = text[pos : m.start()]
        parts.append(before)
        length += len(before)
        if m.group(1) is not None:
            label, kind = m.group(1), "bold"
        else:
            label, kind = m.group(2), m.group(3)
        parts.append(label)
        styles.append((length, length + len(label), kind))
        length += len(label)
        pos = m.end()
    parts.append(text[pos:])
    return "".join(parts), styles


def build_doc_requests(blocks: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
    text_parts: list[str] = []
    heading1: list[tuple[int, int]] = []
    heading2: list[tuple[int, int]] = []
    bullets: list[tuple[int, int]] = []
    bold: list[tuple[int, int]] = []
    links: list[tuple[int, int, str]] = []
    cursor = 1
    for block in blocks:
        display_text, inline_styles = render_inline(block["text"])
        content = display_text + "\n"
        start = cursor
        end = cursor + len(content)
        if block["type"] == "title":
            heading1.append((start, end))
        elif block["type"] == "heading":
            heading2.append((start, end))
        elif block["type"] == "bullet":
            bullets.append((start, end))
        elif block["type"] == "metadata":
            bold.append((start, end))
        for local_start, local_end, kind in inline_styles:
            if kind == "bold":
                bold.append((start + local_start, start + local_end))
            else:
                links.append((start + local_start, start + local_end, kind))
        text_parts.append(content)
        cursor = end

    requests: list[dict[str, Any]] = [{"insertText": {"location": {"index": 1}, "text": "".join(text_parts)}}]
    for start, end in heading1:
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": "HEADING_1"},
                    "fields": "namedStyleType",
                }
            }
        )
    for start, end in heading2:
        requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": "HEADING_2"},
                    "fields": "namedStyleType",
                }
            }
        )
    for start, end in bullets:
        requests.append(
            {
                "createParagraphBullets": {
                    "range": {"startIndex": start, "endIndex": end},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            }
        )
    for start, end in bold:
        requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "textStyle": {"bold": True},
                    "fields": "bold",
                }
            }
        )
    for start, end, url in links:
        requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "textStyle": {"link": {"url": url}},
                    "fields": "link",
                }
            }
        )
    return "".join(text_parts), requests


def clear_doc_body(docs: Any, doc_id: str) -> None:
    document = docs.documents().get(documentId=doc_id).execute()
    end_index = document["body"]["content"][-1]["endIndex"]
    if end_index > 2:
        docs.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}}]},
        ).execute()


def create_doc(services: dict[str, Any], title: str, folder_id: str) -> str:
    document = services["docs"].documents().create(body={"title": title}).execute()
    doc_id = document["documentId"]
    move_file_to_folder(services["drive"], doc_id, folder_id)
    return doc_id


def placeholder_blocks(title: str, source_file: str) -> list[dict[str, str]]:
    return [
        {"type": "title", "text": title},
        {
            "type": "paragraph",
            "text": f"No development-plan content has been captured yet for this scope. Source: {source_file}.",
        },
    ]


def upsert_doc(
    services: dict[str, Any],
    folder_id: str,
    archive_folder_id: str,
    title: str,
    archive_label: str,
    markdown: str,
    fallback_title: str,
    source_file: str,
) -> dict[str, Any]:
    archive_existing_sheet(services["drive"], folder_id, archive_folder_id, title, archive_label)
    existing = find_file_in_folder(services["drive"], folder_id, title, DOC_MIME_TYPE)
    doc_id = existing["id"] if existing else create_doc(services, title, folder_id)

    clear_doc_body(services["docs"], doc_id)
    blocks = parse_blocks(markdown) or placeholder_blocks(fallback_title, source_file)
    _, requests = build_doc_requests(blocks)
    services["docs"].documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    return {"id": doc_id, "name": title}


def archive_project_folder(drive: Any, root_folder_id: str, project: str) -> dict[str, Any]:
    archive_90 = find_or_create_folder(drive, root_folder_id, "90_Archive")
    archive_m2 = find_or_create_folder(drive, archive_90["id"], "20_M2_Project_Management")
    return find_or_create_folder(drive, archive_m2["id"], project)


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    extract_root = Path(args.extract_root)
    if not (extract_root / "manifest.csv").exists():
        raise SystemExit(f"Missing manifest.csv under {extract_root}")

    manifest = read_manifest(extract_root)
    manifest = [item for item in manifest if item["project"] not in IGNORED_PROJECTS]

    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]

    m2_folder = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    results: list[str] = []

    for item in manifest:
        if item["document_role"] != "project_development_plan" or item["status"] != "ok":
            continue
        project = item["project"]
        markdown = markdown_for(extract_root, item)
        project_folder = find_or_create_folder(drive, m2_folder["id"], project)
        archive_folder = archive_project_folder(drive, ROOT_FOLDER_ID, project)
        target_folder = ensure_document_folder(
            drive, project_folder["id"], "project_development_plan"
        )
        meta = upsert_doc(
            services,
            target_folder["id"],
            archive_folder["id"],
            "project_development_plan",
            f"project_development_plan_{project}",
            markdown,
            f"{project} — план развития проекта",
            item["source_file"],
        )
        results.append(f"{project}: {meta['name']}")

    for item in manifest:
        if item["document_role"] != "individual_development_plan" or item["status"] != "ok":
            continue
        project = item["project"]
        markdown = markdown_for(extract_root, item)
        person = parse_person_from_heading(markdown, Path(item["source_file"]).stem)
        folder_name = resolve_existing_person_dir(project, person)

        project_folder = find_or_create_folder(drive, m2_folder["id"], project)
        archive_folder = archive_project_folder(drive, ROOT_FOLDER_ID, project)
        person_folder = ensure_document_folder(
            drive, project_folder["id"], "individual_development_plan", folder_name
        )

        meta = upsert_doc(
            services,
            person_folder["id"],
            archive_folder["id"],
            "individual_development_plan",
            f"individual_development_plan_{project}_{folder_name}",
            markdown,
            f"{person} — план развития ({project})",
            item["source_file"],
        )
        results.append(f"{project}/{folder_name}: {meta['name']}")

    sys.stdout.buffer.write(("\n".join(results) + "\n").encode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
