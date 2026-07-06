#!/usr/bin/env python3
"""Extract QA management DOCX/XLSX source documents into text-friendly files.

The script is intentionally dependency-free. It reads Office Open XML files
directly as ZIP/XML packages and writes Markdown, CSV, JSONL, and manifest files.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
XLSX_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract DOCX/XLSX QA source docs into analysis-friendly files."
    )
    parser.add_argument(
        "--source-root",
        default=r"G:\My Drive\QA_Management\00_Source_Docs",
        help="Folder with project source documents.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Extraction output folder. Defaults to G:\\My Drive\\QA_Management\\80_Exports\\source_extracts\\YYYY-MM-DD.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting files in an existing extraction folder.",
    )
    return parser.parse_args()


def safe_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.rstrip(". ") or "unnamed"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def infer_role(path: Path) -> str:
    text = f"{path.parent.name} {path.name}".casefold()
    if "m1_monthly_report" in text or ("m1" in text and "monthly" in text and "report" in text):
        return "m1_monthly_report"
    if "m2_monthly_report" in text or ("m2" in text and "monthly" in text and "report" in text):
        return "m2_monthly_report"
    if any(token in text for token in ("1to1", "1x1", "one-to-one")):
        return "one_to_one_source"
    if "свод" in text or "brief" in text:
        return "project_summary"
    if "риск" in text or "risk" in text:
        return "project_risk"
    if "метрик" in text or "metric" in text:
        if "проект" in text or "project" in text:
            return "project_metrics"
        return "individual_metrics"
    if "план" in text or "development" in text:
        if "проект" in text or "project" in text:
            return "project_development_plan"
        return "individual_development_plan"
    if path.suffix.casefold() == ".xlsx":
        return "workbook_source"
    if path.suffix.casefold() == ".docx":
        return "document_source"
    return "unknown"


def docx_paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        document = ET.fromstring(zf.read("word/document.xml"))

    paragraphs: list[str] = []
    for paragraph in document.findall(".//w:p", WORD_NS):
        parts = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)]
        text = re.sub(r"\s+", " ", "".join(parts)).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def docx_comments(path: Path) -> list[dict[str, str]]:
    comments: list[dict[str, str]] = []
    with zipfile.ZipFile(path) as zf:
        if "word/comments.xml" not in zf.namelist():
            return comments
        root = ET.fromstring(zf.read("word/comments.xml"))

    for comment in root.findall("w:comment", WORD_NS):
        parts = []
        for paragraph in comment.findall(".//w:p", WORD_NS):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                parts.append(text)
        if parts:
            comments.append(
                {
                    "id": comment.attrib.get(f"{{{WORD_NS['w']}}}id", ""),
                    "author": comment.attrib.get(f"{{{WORD_NS['w']}}}author", ""),
                    "date": comment.attrib.get(f"{{{WORD_NS['w']}}}date", ""),
                    "text": "\n".join(parts),
                }
            )
    return comments


def docx_to_markdown(path: Path, relative_source: str, role: str) -> str:
    paragraphs = docx_paragraphs(path)
    comments = docx_comments(path)
    lines = [
        "---",
        f"source_file: {json.dumps(relative_source, ensure_ascii=False)}",
        f"document_role: {role}",
        f"extracted_at: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "---",
        "",
        f"# {path.stem}",
        "",
    ]

    for text in paragraphs:
        if text.startswith("#"):
            lines.append(text)
        elif len(text) <= 90 and not text.endswith(".") and not text.endswith(":"):
            lines.extend([f"## {text}", ""])
        elif text.startswith("- ") or text.startswith("• "):
            lines.append(text)
        else:
            lines.extend([text, ""])

    if comments:
        lines.extend(["", "## Word Comments", ""])
        for index, comment in enumerate(comments, start=1):
            lines.extend(
                [
                    f"### Comment {index}",
                    "",
                    f"- id: {comment['id']}",
                    f"- author: {comment['author']}",
                    f"- date: {comment['date']}",
                    "",
                    comment["text"],
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall("main:si", XLSX_NS):
        values.append("".join(node.text or "" for node in item.findall(".//main:t", XLSX_NS)))
    return values


def read_workbook_relationships(zf: zipfile.ZipFile) -> dict[str, str]:
    root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rels = {}
    for rel in root:
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target", "")
        if rel_id:
            rels[rel_id] = target
    return rels


def read_sheets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = read_workbook_relationships(zf)
    sheets = []
    rel_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    for sheet in workbook.findall("main:sheets/main:sheet", XLSX_NS):
        name = sheet.attrib.get("name", "Sheet")
        rel_id = sheet.attrib.get(rel_key)
        target = rels.get(rel_id or "", "")
        sheet_path = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
        sheets.append((name, sheet_path))
    return sheets


def column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 1
    result = 0
    for char in match.group(1):
        result = result * 26 + ord(char) - 64
    return result


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", XLSX_NS)).strip()

    value_node = cell.find("main:v", XLSX_NS)
    if value_node is None or value_node.text is None:
        return ""

    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)].strip()
        except (IndexError, ValueError):
            return value
    return value.strip()


def read_sheet_rows(zf: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(zf.read(sheet_path))
    rows: list[list[str]] = []
    for row in root.findall("main:sheetData/main:row", XLSX_NS):
        values: list[str] = []
        for cell in row.findall("main:c", XLSX_NS):
            idx = column_index(cell.attrib.get("r", "A1"))
            while len(values) < idx - 1:
                values.append("")
            values.append(cell_value(cell, shared_strings))
        while values and values[-1] == "":
            values.pop()
        if any(value.strip() for value in values):
            rows.append(values)
    return rows


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_xlsx(path: Path, out_dir: Path, relative_source: str, role: str) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        shared_strings = read_shared_strings(zf)
        sheets = []
        for sheet_name, sheet_path in read_sheets(zf):
            rows = read_sheet_rows(zf, sheet_path, shared_strings)
            csv_name = f"{safe_name(path.stem)}__{safe_name(sheet_name)}.csv"
            write_csv(out_dir / csv_name, rows)
            sheets.append(
                {
                    "sheet_name": sheet_name,
                    "row_count": len(rows),
                    "column_count": max((len(row) for row in rows), default=0),
                    "csv_file": csv_name,
                    "preview_rows": rows[:5],
                }
            )

    data = {
        "source_file": relative_source,
        "document_role": role,
        "extracted_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sheets": sheets,
    }
    write_json(out_dir / f"{safe_name(path.stem)}.json", data)
    return data


def write_manifest(output_root: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "project",
        "source_file",
        "extension",
        "document_role",
        "size_bytes",
        "modified_at",
        "sha256",
        "extract_file",
        "sheet_count",
        "status",
        "error",
    ]
    with (output_root / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    write_json(output_root / "manifest.json", rows)


def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root)
    if args.output_root:
        output_root = Path(args.output_root)
    else:
        output_root = (
            Path(r"G:\My Drive\QA_Management\80_Exports\source_extracts")
            / dt.date.today().isoformat()
        )

    if not source_root.exists():
        print(f"Source root does not exist: {source_root}", file=sys.stderr)
        return 2
    if output_root.exists() and any(output_root.iterdir()) and not args.overwrite:
        print(f"Output folder is not empty; pass --overwrite: {output_root}", file=sys.stderr)
        return 2

    output_root.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    source_files = sorted(
        [p for p in source_root.rglob("*") if p.is_file() and p.suffix.casefold() in (".docx", ".xlsx")],
        key=lambda p: str(p).casefold(),
    )

    for source_file in source_files:
        relative = source_file.relative_to(source_root)
        project = relative.parts[0] if len(relative.parts) > 1 else "_root"
        role = infer_role(source_file)
        project_out = output_root / safe_name(project)
        stat = source_file.stat()
        row: dict[str, Any] = {
            "project": project,
            "source_file": str(relative),
            "extension": source_file.suffix.casefold(),
            "document_role": role,
            "size_bytes": stat.st_size,
            "modified_at": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "sha256": sha256_file(source_file),
            "extract_file": "",
            "sheet_count": "",
            "status": "ok",
            "error": "",
        }

        try:
            if source_file.suffix.casefold() == ".docx":
                docx_out = project_out / "docx" / f"{safe_name(source_file.stem)}.md"
                docx_out.parent.mkdir(parents=True, exist_ok=True)
                docx_out.write_text(
                    docx_to_markdown(source_file, str(relative), role),
                    encoding="utf-8",
                )
                row["extract_file"] = str(docx_out.relative_to(output_root))
            elif source_file.suffix.casefold() == ".xlsx":
                xlsx_out = project_out / "xlsx" / safe_name(source_file.stem)
                data = extract_xlsx(source_file, xlsx_out, str(relative), role)
                row["extract_file"] = str((xlsx_out / f"{safe_name(source_file.stem)}.json").relative_to(output_root))
                row["sheet_count"] = len(data["sheets"])
        except Exception as exc:  # Keep batch extraction moving and record failures.
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"

        manifest.append(row)

    write_manifest(output_root, manifest)
    print(f"Extracted {len(manifest)} source files into {output_root}")
    errors = [row for row in manifest if row["status"] != "ok"]
    if errors:
        print(f"Completed with {len(errors)} extraction errors; see manifest.csv", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
