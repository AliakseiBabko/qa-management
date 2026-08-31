"""Publish a cbs-devops performance session report to Google Docs.

The report is authored as Markdown in the session directory that holds the data
and charts, because it belongs next to the runs and CI can write it there. This
script is the one-way bridge from that Markdown to the client-facing Doc, and it
lives here because this is where the Google credentials and the Docs conventions
already are.

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

IMAGES ARE MADE LINK-READABLE. The Docs API can only embed an image from a URI it
can fetch anonymously, so each chart is uploaded to Drive and granted
`type=anyone, role=reader`. That is a real sharing action on real files - it is
printed for every image, and --no-share refuses to publish images rather than
sharing them silently.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_common  # noqa: E402


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

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("session", help="path to the session directory (may be absolute)")
    ap.add_argument("--report", default="report.md")
    ap.add_argument("--title", default=None)
    ap.add_argument("--folder-id", default=None, help="Drive folder for the Doc and charts")
    ap.add_argument("--doc-id", default=None, help="update this Doc instead of creating one")
    ap.add_argument("--no-share", action="store_true",
                    help="refuse to make chart images link-readable (images then cannot embed)")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report what would be written; touches no Google API")
    args = ap.parse_args()

    session = Path(args.session).resolve()
    report_path = session / args.report
    if not report_path.is_file():
        sys.stderr.write("no report at %s\n" % report_path)
        return 2
    blocks = parse(report_path.read_text(encoding="utf-8"))

    title = args.title or "CBS Performance Test Report - %s" % session.name
    counts: dict[str, int] = {}
    for b in blocks:
        counts[b["kind"]] = counts.get(b["kind"], 0) + 1

    print("session : %s" % session)
    print("title   : %s" % title)
    print("blocks  : %s" % ", ".join("%s=%d" % kv for kv in sorted(counts.items())))

    missing = [b["src"] for b in blocks
               if b["kind"] == "image" and not (session / b["src"]).is_file()]
    if missing:
        sys.stderr.write("missing chart files: %s\n" % ", ".join(missing))
        return 2

    if args.dry_run:
        print("\ndry run - nothing was sent to Google. Outline:")
        for b in blocks:
            if b["kind"] == "heading":
                print("  %s%s" % ("  " * (b["level"] - 1), b["text"]))
            elif b["kind"] == "image":
                print("      [image] %s" % b["src"])
            elif b["kind"] == "table":
                print("      [table] %d x %d" % (len(b["rows"]), len(b["rows"][0])))
        return 0

    os.chdir(Path(__file__).resolve().parents[2])  # get_services uses relative paths
    services = pipeline_common.get_services()
    docs, drive = services["docs"], services["drive"]

    if args.doc_id:
        doc_id = args.doc_id
        doc = docs.documents().get(documentId=doc_id).execute()
        tail = doc["body"]["content"][-1]["endIndex"] - 1
        if tail > 1:
            docs.documents().batchUpdate(documentId=doc_id, body={"requests": [
                {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": tail}}}]}
            ).execute()
        print("updating existing doc %s (previous content cleared)" % doc_id)
    else:
        meta = {"name": title, "mimeType": "application/vnd.google-apps.document"}
        if args.folder_id:
            meta["parents"] = [args.folder_id]
        doc_id = drive.files().create(body=meta, fields="id",
                                      supportsAllDrives=True).execute()["id"]
        print("created doc %s" % doc_id)

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
            uri = upload_image(services, session / b["src"], args.folder_id,
                               share=not args.no_share)
            append_image(docs, doc_id, uri)
        if n % 20 == 0:
            print("  ...%d/%d blocks" % (n, len(blocks)))

    print("\ndone: https://docs.google.com/document/d/%s/edit" % doc_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
