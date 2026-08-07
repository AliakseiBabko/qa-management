#!/usr/bin/env python3
"""Read a Google Doc's full plain text - given either a local Drive-mirror
path (resolved the same way `resolve_drive_path.py` does) or a raw Docs
document ID directly - and print it (or write it to a file).

Exists because this repo re-implemented the same "walk a Docs API
`documents().get()` response and flatten `paragraph`/`table` elements into
text" logic independently in several scripts (`show_project_state.py`,
`commit_workspace_state.py`, `apply_person_card.py`, `pipeline_common.py`)
with none of them exposed as a standalone read-only tool - so answering "what
does this project's ops runbook / knowledge base doc actually say" from
outside those scripts' own specific flows meant re-deriving the extraction
logic from scratch each time. This is that logic, once, as a CLI.

Read-only: never writes to Drive, only ever reads.

Usage:
    python read_google_doc.py "G:\\My Drive\\QA_Management\\30_Project_Knowledge\\PKF\\qa_docs\\ops_runbook.gdoc"
    python read_google_doc.py --id 1oMKzoyQs-i0mcxjflGM6BeFAU-rI4oaBg5r9zkEsvw0
    python read_google_doc.py "<path>" --out notes.txt

Table cells are flattened in reading order (row by row, cell by cell) with
no column alignment - fine for grep/search, not for reproducing layout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_services
from resolve_drive_path import ResolveError, resolve


def extract_text(doc: dict[str, Any]) -> str:
    """Flatten a Docs API `documents().get()` response body into plain text.

    Walks `paragraph` elements for their `textRun` content and recurses into
    `table` -> `tableRows` -> `tableCells` -> `content` so table text isn't
    silently dropped (a real gap in some of this repo's other ad hoc
    extractors, which only handle paragraphs)."""
    def walk(elements: list[dict[str, Any]]) -> str:
        out = []
        for element in elements:
            if "paragraph" in element:
                for run in element["paragraph"].get("elements", []):
                    text_run = run.get("textRun")
                    if text_run:
                        out.append(text_run.get("content", ""))
            elif "table" in element:
                for row in element["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        out.append(walk(cell.get("content", [])))
        return "".join(out)

    return walk(doc.get("body", {}).get("content", []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", help=r"Local path under G:\My Drive\QA_Management to a .gdoc")
    parser.add_argument("--id", help="Docs document ID directly, skipping path resolution")
    parser.add_argument("--out", help="Write text to this file instead of stdout (always UTF-8)")
    args = parser.parse_args()

    if not args.path and not args.id:
        parser.error("Provide either a local .gdoc path or --id")

    ensure_utf8_stdout()
    services = get_services()

    doc_id = args.id
    if not doc_id:
        try:
            resolved = resolve(services["drive"], Path(args.path))
        except ResolveError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        if resolved.get("mimeType") != "application/vnd.google-apps.document":
            print(f"Error: {args.path} is not a Google Doc (mimeType: {resolved.get('mimeType')})",
                  file=sys.stderr)
            return 1
        doc_id = resolved["id"]

    doc = services["docs"].documents().get(documentId=doc_id).execute()
    text = extract_text(doc)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Wrote {len(text)} chars to {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
