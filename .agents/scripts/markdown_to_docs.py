"""Reusable Markdown -> Google Docs engine, plus the append-sequentially
publisher both Markdown-report scripts share.

Extracted from publish_perf_report.py once a second caller appeared
(publish_markdown_doc.py, used by the assessment/interview feedback
skills): the Markdown subset, the block parser, and the Docs append
primitives are not performance-report-specific, only that script's title
defaulting and chart directory were.

WHAT IT SUPPORTS, deliberately a small subset of Markdown:
  # / ## / ###   headings          -> TITLE / HEADING_1 / HEADING_2
  paragraphs, **bold** inline
  - bullets and 1. numbered lists
  | tables |                       -> real Docs tables with a bold header row
  ![alt](path.png)                 -> inline image, uploaded to Drive first
  ```fenced code```                -> monospace paragraphs
  ---                              -> skipped (Docs has no horizontal rule request)

WHY IT APPENDS SEQUENTIALLY. Every insert goes at the document's current end
index, one request batch per block, rather than computing a set of indices
against a single snapshot. That is slower in API calls and immune to the
index-invalidation failure that docs_editing.py exists to guard against: no
edit's index is ever computed against a document state that a later edit has
already shifted.

IMAGES ARE MADE LINK-READABLE. The Docs API can only embed an image from a URI
it can fetch anonymously, so each image is uploaded to Drive and granted
`type=anyone, role=reader`. That is a real sharing action on real files - it is
printed for every image, and share=False refuses to publish images rather than
sharing them silently. A Markdown file with no images never shares anything.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ----------------------------------------------------------------- markdown

BOLD = re.compile(r"\*\*(.+?)\*\*")
IMAGE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$")
HEADING = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
BULLET = re.compile(r"^[-*]\s+(?P<text>.+?)\s*$")
NUMBERED = re.compile(r"^(?P<n>\d+)\.\s+(?P<text>.+?)\s*$")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
TABLE_SEP = re.compile(r"^\|[\s:|-]+\|\s*$")

STYLE_FOR_LEVEL = {1: "TITLE", 2: "HEADING_1", 3: "HEADING_2", 4: "HEADING_3",
                   5: "HEADING_4", 6: "HEADING_5"}


def strip_inline(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Remove ** markers, returning the clean text and the bold ranges within it."""
    out, bolds, pos = [], [], 0
    cursor = 0
    for m in BOLD.finditer(text):
        out.append(text[cursor:m.start()])
        pos += m.start() - cursor
        inner = m.group(1)
        bolds.append((pos, pos + len(inner)))
        out.append(inner)
        pos += len(inner)
        cursor = m.end()
    out.append(text[cursor:])
    clean = "".join(out)
    # Backticks carry no style here; the surrounding prose already reads as code.
    return clean.replace("`", ""), bolds


def parse(md: str) -> list[dict]:
    """Markdown -> a flat list of blocks. Nothing nested, which is the point."""
    blocks: list[dict] = []
    lines = md.splitlines()
    i, para, in_code, code = 0, [], False, []

    def flush_para():
        if para:
            blocks.append({"kind": "para", "text": " ".join(para).strip()})
            para.clear()

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code:
                blocks.append({"kind": "code", "text": "\n".join(code)})
                code.clear()
                in_code = False
            else:
                flush_para()
                in_code = True
            i += 1
            continue
        if in_code:
            code.append(line)
            i += 1
            continue

        if not line.strip():
            flush_para()
            i += 1
            continue
        if line.strip() == "---":
            flush_para()
            i += 1
            continue

        m = IMAGE.match(line.strip())
        if m:
            flush_para()
            blocks.append({"kind": "image", "src": m.group("src"), "alt": m.group("alt")})
            i += 1
            continue

        m = HEADING.match(line)
        if m:
            flush_para()
            blocks.append({"kind": "heading", "level": len(m.group("hashes")),
                           "text": m.group("text")})
            i += 1
            continue

        if TABLE_ROW.match(line):
            flush_para()
            rows = []
            while i < len(lines) and TABLE_ROW.match(lines[i]):
                if not TABLE_SEP.match(lines[i]):
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    rows.append(cells)
                i += 1
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                blocks.append({"kind": "table", "rows": rows})
            continue

        m = BULLET.match(line)
        if m:
            flush_para()
            blocks.append({"kind": "bullet", "text": m.group("text")})
            i += 1
            continue

        m = NUMBERED.match(line)
        if m:
            flush_para()
            blocks.append({"kind": "numbered", "text": m.group("text"),
                           "n": int(m.group("n"))})
            i += 1
            continue

        para.append(line.strip())
        i += 1

    flush_para()
    if in_code and code:
        blocks.append({"kind": "code", "text": "\n".join(code)})
    return blocks


# ------------------------------------------------------------------- drive

def upload_image(services, path: Path, folder_id: str | None, share: bool) -> str:
    from googleapiclient.http import MediaFileUpload

    drive = services["drive"]
    meta = {"name": path.name}
    if folder_id:
        meta["parents"] = [folder_id]
    media = MediaFileUpload(str(path), mimetype="image/png", resumable=False)
    f = drive.files().create(body=meta, media_body=media, fields="id",
                             supportsAllDrives=True).execute()
    fid = f["id"]
    if not share:
        raise SystemExit(
            "refusing to embed %s: the Docs API can only fetch an image it can read "
            "anonymously, so publishing images requires sharing them. Re-run without "
            "--no-share, or remove the images from the report." % path.name)
    drive.permissions().create(fileId=fid, body={"type": "anyone", "role": "reader"},
                               supportsAllDrives=True).execute()
    print("    uploaded and shared link-readable: %s (%s)" % (path.name, fid))
    return "https://drive.google.com/uc?id=%s" % fid


# --------------------------------------------------------------- docs writes

def end_index(docs, doc_id: str) -> int:
    doc = docs.documents().get(documentId=doc_id).execute()
    return doc["body"]["content"][-1]["endIndex"] - 1


def append_text(docs, doc_id: str, text: str, style: str,
                bolds: list[tuple[int, int]] | None = None, mono: bool = False) -> None:
    at = end_index(docs, doc_id)
    body = text + "\n"
    reqs: list[dict] = [{"insertText": {"location": {"index": at}, "text": body}}]
    rng = {"startIndex": at, "endIndex": at + len(body)}
    reqs.append({"updateParagraphStyle": {
        "range": rng, "paragraphStyle": {"namedStyleType": style},
        "fields": "namedStyleType"}})
    if mono:
        reqs.append({"updateTextStyle": {
            "range": {"startIndex": at, "endIndex": at + len(text)},
            "textStyle": {"weightedFontFamily": {"fontFamily": "Roboto Mono"},
                          "fontSize": {"magnitude": 9, "unit": "PT"}},
            "fields": "weightedFontFamily,fontSize"}})
    for b0, b1 in (bolds or []):
        reqs.append({"updateTextStyle": {
            "range": {"startIndex": at + b0, "endIndex": at + b1},
            "textStyle": {"bold": True}, "fields": "bold"}})
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()


def append_list_item(docs, doc_id: str, text: str, numbered: bool) -> None:
    at = end_index(docs, doc_id)
    clean, bolds = strip_inline(text)
    body = clean + "\n"
    reqs: list[dict] = [{"insertText": {"location": {"index": at}, "text": body}}]
    rng = {"startIndex": at, "endIndex": at + len(body)}
    reqs.append({"updateParagraphStyle": {
        "range": rng, "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
        "fields": "namedStyleType"}})
    for b0, b1 in bolds:
        reqs.append({"updateTextStyle": {
            "range": {"startIndex": at + b0, "endIndex": at + b1},
            "textStyle": {"bold": True}, "fields": "bold"}})
    reqs.append({"createParagraphBullets": {
        "range": rng,
        "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN" if numbered
        else "BULLET_DISC_CIRCLE_SQUARE"}})
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()


def append_table(docs, doc_id: str, rows: list[list[str]]) -> None:
    import docs_editing
    at = end_index(docs, doc_id)
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
        {"insertTable": {"location": {"index": at}, "rows": len(rows),
                         "columns": len(rows[0])}}]}).execute()
    doc = docs.documents().get(documentId=doc_id).execute()
    table_el = docs_editing.find_table_at_or_after(doc, at)
    cleaned = [[strip_inline(c)[0] for c in row] for row in rows]
    reqs = docs_editing.build_table_fill_requests(table_el, cleaned, bold_header=True)
    if reqs:
        docs.documents().batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()


def append_image(docs, doc_id: str, uri: str, width_pt: float = 460) -> None:
    at = end_index(docs, doc_id)
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
        {"insertInlineImage": {"location": {"index": at}, "uri": uri,
                               "objectSize": {"width": {"magnitude": width_pt,
                                                        "unit": "PT"}}}}]}).execute()


# ---------------------------------------------------------------------- main


# ------------------------------------------------------------------ publish

DOC_MIME = "application/vnd.google-apps.document"


def create_or_reset_doc(services: dict[str, Any], title: str,
                        folder_id: str | None = None,
                        doc_id: str | None = None) -> str:
    """Create a new Doc (optionally in `folder_id`) or clear an existing one
    so a republish replaces its body instead of appending a second copy.
    Returns the document id in both cases."""
    docs, drive = services["docs"], services["drive"]
    if doc_id:
        doc = docs.documents().get(documentId=doc_id).execute()
        tail = doc["body"]["content"][-1]["endIndex"] - 1
        if tail > 1:
            docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
                {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": tail}}}]}
            ).execute()
        print("updating existing doc %s (previous content cleared)" % doc_id)
        return doc_id
    meta: dict[str, Any] = {"name": title, "mimeType": DOC_MIME}
    if folder_id:
        meta["parents"] = [folder_id]
    new_id = drive.files().create(body=meta, fields="id",
                                  supportsAllDrives=True).execute()["id"]
    print("created doc %s" % new_id)
    return new_id


def render_blocks(services: dict[str, Any], doc_id: str, blocks: list[dict],
                  asset_root: Path | None = None, share: bool = True,
                  folder_id: str | None = None) -> None:
    """Append every parsed block to the document, in order. `asset_root` is
    the directory image `src` paths resolve against; an images-free document
    never needs it."""
    docs = services["docs"]
    for n, b in enumerate(blocks, 1):
        kind = b["kind"]
        if kind == "heading":
            clean, _ = strip_inline(b["text"])
            append_text(docs, doc_id, clean, STYLE_FOR_LEVEL.get(b["level"], "HEADING_3"))
        elif kind == "para":
            clean, bolds = strip_inline(b["text"])
            append_text(docs, doc_id, clean, "NORMAL_TEXT", bolds)
        elif kind == "code":
            append_text(docs, doc_id, b["text"], "NORMAL_TEXT", mono=True)
        elif kind in ("bullet", "numbered"):
            append_list_item(docs, doc_id, b["text"], numbered=(kind == "numbered"))
        elif kind == "table":
            append_table(docs, doc_id, b["rows"])
        elif kind == "image":
            if asset_root is None:
                raise ValueError("document contains an image but no asset_root was given")
            uri = upload_image(services, asset_root / b["src"], folder_id, share=share)
            append_image(docs, doc_id, uri)
        if n % 20 == 0:
            print("  ...%d/%d blocks" % (n, len(blocks)))


def block_counts(blocks: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for b in blocks:
        counts[b["kind"]] = counts.get(b["kind"], 0) + 1
    return counts


def print_outline(blocks: list[dict]) -> None:
    """Dry-run view: headings indented by level, tables/images summarized."""
    for b in blocks:
        if b["kind"] == "heading":
            print("  %s%s" % ("  " * (b["level"] - 1), b["text"]))
        elif b["kind"] == "image":
            print("      [image] %s" % b["src"])
        elif b["kind"] == "table":
            print("      [table] %d x %d" % (len(b["rows"]), len(b["rows"][0])))
