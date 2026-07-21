"""Extract and normalize text from file-backed sources.

Supports strict JSON output or human-readable mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Set, Tuple

def source_text_requirement(row: dict) -> str:
    src_type = row.get("Source type", "")
    ext = Path(row.get("Source", "")).suffix.casefold()
    if src_type in {"qa_1to1", "strategy_chat", "meeting_transcript", "people_case_chat",
                    # Project Knowledge lane (30_Project_Knowledge) - same file-backed
                    # transcript/document/chat/notes treatment as their M1/M2 counterparts
                    # above. All four are discovered via the same file-based intake queue
                    # (scan/classify/start), never a purely conversational source like
                    # m2_conversation/admin_note below, so the same extension-gated
                    # "required" rule applies uniformly - including project_knowledge_notes,
                    # whose short-note shape affects whether a *summary* doc gets written
                    # (see project-knowledge-intake), not whether the raw source text is
                    # worth preserving.
                    "project_knowledge_transcript", "project_knowledge_document",
                    "project_knowledge_chat", "project_knowledge_notes"}:
        if ext in {".txt", ".md", ".docx"}:
            return "required"
    if src_type in {"admin_note", "m2_conversation"}:
        return "not_applicable"
    return "optional"


# We do NOT import qa_manage here at module load.
from mirror_common import assert_private_mirror

SOURCE_TEXT_TYPES = {
    "qa_1to1", "strategy_chat", "meeting_transcript", "people_case_chat",
    "project_knowledge_transcript", "project_knowledge_document",
    "project_knowledge_chat", "project_knowledge_notes",
}
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx"}
SOURCE_TEXT_SEARCH_ROOTS = (
    "00_Inbox",
    "90_Storage/Processed_Sources",
)

MAX_ZIP_MEMBERS = 1000
MAX_UNCOMPRESSED_TOTAL_SIZE = 50 * 1024 * 1024
MAX_XML_SIZE = 50 * 1024 * 1024
MIN_COMPRESSION_RATIO = 0.005  # 200x limit

class ExtractionError(Exception):
    pass

class ParserError(Exception):
    pass

class StrictArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParserError(message)

def print_envelope_and_exit(success: bool, mode: str, data: dict, warnings: list, errors: list) -> NoReturn:
    for k, v in data.items():
        if isinstance(v, list) or isinstance(v, set):
            data[k] = sorted(list(v))

    envelope = {
        "schema_version": 1,
        "command": mode,
        "data": data,
        "warnings": sorted(warnings),
        "errors": sorted(errors),
        "ok": success
    }
    print(json.dumps(envelope, indent=2, ensure_ascii=False))
    sys.exit(0 if success else 1)

def get_full_sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def normalize_path(q_path: str) -> str:
    p = Path(q_path).as_posix()
    if p.startswith("/") or ".." in p.split("/") or ":" in p:
        raise ValueError("Unsafe path traversal")
    return p

def extract_paragraph(p_elem: ET.Element) -> str:
    def _walk(node) -> str:
        tag = node.tag.split('}')[-1] if '}' in node.tag else node.tag
        if tag in ("del", "instrText"):
            return ""

        text = ""
        if tag == "t" and node.text:
            text = node.text
        elif tag == "tab":
            text = "\t"
        elif tag in ("br", "cr"):
            text = "\n"

        for child in list(node):
            text += _walk(child)
        return text

    return _walk(p_elem)

def docx_to_text_v1(raw_bytes: bytes) -> str:
    import zipfile
    import io

    parts = []
    total_uncompressed = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            infolist = zf.infolist()
            if len(infolist) > MAX_ZIP_MEMBERS:
                raise ExtractionError(f"DOCX has too many members: {len(infolist)}")

            for info in infolist:
                total_uncompressed += info.file_size
                if info.compress_size > 0:
                    ratio = info.compress_size / float(info.file_size) if info.file_size > 0 else 1.0
                    if ratio < MIN_COMPRESSION_RATIO:
                        raise ExtractionError(f"Suspicious compression ratio {ratio} in {info.filename}")

            if total_uncompressed > MAX_UNCOMPRESSED_TOTAL_SIZE:
                raise ExtractionError(f"DOCX total uncompressed size exceeds {MAX_UNCOMPRESSED_TOTAL_SIZE} bytes")

            try:
                doc_info = zf.getinfo("word/document.xml")
            except KeyError:
                raise ExtractionError("word/document.xml missing")

            if doc_info.file_size > MAX_XML_SIZE:
                raise ExtractionError(f"document.xml size {doc_info.file_size} exceeds {MAX_XML_SIZE}")

            with zf.open("word/document.xml") as f:
                tree = ET.parse(f)
                root = tree.getroot()

                ns = ""
                if "}" in root.tag:
                    ns = root.tag.split("}")[0] + "}"

                body = root.find(f"{ns}body") if ns else root.find("body")
                if body is None:
                    raise ExtractionError("No body tag found")

                def extract_table(tbl) -> str:
                    rows = []
                    for child in list(tbl):
                        ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if ctag == "tr":
                            rows.append(extract_row(child))
                    return "\n".join(rows)

                def extract_row(row) -> str:
                    cells = []
                    for child in list(row):
                        ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if ctag == "tc":
                            cells.append(extract_cell(child))
                    return "\t".join(cells)

                def extract_cell(cell) -> str:
                    cell_parts = []
                    for child in list(cell):
                        ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if ctag == "p":
                            cell_parts.append(extract_paragraph(child))
                        elif ctag == "tbl":
                            cell_parts.append(extract_table(child))
                    return "\n".join(cell_parts)

                for child in list(body):
                    ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if ctag == "p":
                        parts.append(extract_paragraph(child))
                    elif ctag == "tbl":
                        parts.append(extract_table(child))

    except zipfile.BadZipFile:
        raise ExtractionError("Not a valid ZIP/DOCX file")
    except ET.ParseError as e:
        raise ExtractionError(f"XML parse error: {e}")

    text = "\n".join(parts)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip("\n") + "\n"

def process_utf8_v1(raw_bytes: bytes) -> str:
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ExtractionError(f"Invalid UTF-8: {e}")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip("\n") + "\n"

def resolve_first_export(data_root: Path, norm_q_path: str, q_hash: str) -> Tuple[Path, str, bytes]:
    """Search for a file matching 16-char q_hash prefix in approved roots."""
    if not isinstance(q_hash, str) or len(q_hash) != 16 or not all(c in "0123456789abcdef" for c in q_hash):
        raise ExtractionError(f"Invalid q_hash: {q_hash}")

    data_root_res = data_root.resolve()

    exact_path = data_root / norm_q_path
    if exact_path.is_file():
        try:
            for root_rel in SOURCE_TEXT_SEARCH_ROOTS:
                approved = (data_root / root_rel).resolve()
                if not approved.is_relative_to(data_root_res):
                    continue
                if exact_path.resolve().is_relative_to(approved):
                    b = exact_path.read_bytes()
                    h = get_full_sha256(b)
                    if h.startswith(q_hash):
                        return exact_path, h, b
        except Exception:
            pass

    # Hash groupings: dict[full_hash] -> list[Path]
    groupings: Dict[str, List[Path]] = {}

    for root_rel in SOURCE_TEXT_SEARCH_ROOTS:
        search_dir = data_root / root_rel
        if not search_dir.is_dir():
            continue

        approved = search_dir.resolve()
        if not approved.is_relative_to(data_root_res):
            continue

        for root, dirs, files in os.walk(search_dir):
            for fname in files:
                candidate = Path(root) / fname
                try:
                    if candidate.suffix.casefold() not in ALLOWED_EXTENSIONS:
                        continue
                    if not candidate.resolve().is_relative_to(approved):
                        continue
                    b = candidate.read_bytes()
                    h = get_full_sha256(b)
                    if h.startswith(q_hash):
                        groupings.setdefault(h, []).append(candidate)
                except Exception:
                    continue

    if not groupings:
        raise ExtractionError(f"No file matching hash prefix {q_hash} found in approved roots")

    if len(groupings) > 1:
        raise ExtractionError(f"Ambiguous hash prefix {q_hash}: found {len(groupings)} distinct full hashes")

    full_hash = list(groupings.keys())[0]
    candidates = groupings[full_hash]

    if len(candidates) == 1:
        return candidates[0], full_hash, candidates[0].read_bytes()

    def score_candidate(p: Path) -> Tuple[str, str]:
        rel_posix = p.relative_to(data_root).as_posix()
        return (rel_posix.casefold(), rel_posix)

    candidates.sort(key=score_candidate)
    chosen = candidates[0]
    return chosen, full_hash, chosen.read_bytes()

def resolve_relocation(data_root: Path, full_sha256: str) -> Tuple[Path, str, bytes]:
    """Search approved roots exclusively for exact 64-char equivalence, disregarding basenames."""
    import re
    if not isinstance(full_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", full_sha256):
        raise ExtractionError(f"Invalid full_hash: {full_sha256}")

    data_root_res = data_root.resolve()
    matches = []

    for root_rel in SOURCE_TEXT_SEARCH_ROOTS:
        search_dir = data_root / root_rel
        if not search_dir.is_dir():
            continue

        approved = search_dir.resolve()
        if not approved.is_relative_to(data_root_res):
            continue

        for root, dirs, files in os.walk(search_dir):
            for fname in files:
                candidate = Path(root) / fname
                try:
                    if candidate.suffix.casefold() not in ALLOWED_EXTENSIONS:
                        continue
                    if not candidate.resolve().is_relative_to(approved):
                        continue
                    b = candidate.read_bytes()
                    h = get_full_sha256(b)
                    if h == full_sha256:
                        matches.append((candidate, h, b))
                except Exception:
                    continue

    if not matches:
        raise ExtractionError(f"Could not resolve file matching exact hash {full_sha256}")

    matches.sort(key=lambda x: (x[0].relative_to(data_root).as_posix().casefold(), x[0].relative_to(data_root).as_posix()))
    return matches[0]

def verify_manifest_entry(row: Dict[str, Any], manifest_entry: Dict[str, Any], blob_loader, raw_source_resolver=None) -> List[str]:
    """Pure verifier for a manifest entry against a queue row and physical blob."""
    errs = []

    q_path = row.get("Source", "")
    try:
        norm_q_path = normalize_path(q_path)
    except Exception as e:
        norm_q_path = None
        errs.append(f"Bad source path in row: {e}")

    if norm_q_path and manifest_entry.get("source_path") != norm_q_path:
        errs.append(f"source_path mismatch: manifest has {manifest_entry.get('source_path')!r}, row has {norm_q_path!r}")

    q_hash = row.get("Source hash", "")
    if manifest_entry.get("queue_source_hash") != q_hash:
        errs.append(f"queue_source_hash mismatch: manifest has {manifest_entry.get('queue_source_hash')!r}, row has {q_hash!r}")

    text_path = manifest_entry.get("text_path", "")
    text_sha256 = manifest_entry.get("text_sha256", "")
    try:
        blob_bytes = blob_loader(text_path)
        actual_sha = get_full_sha256(blob_bytes)
        if actual_sha != text_sha256:
            errs.append(f"Blob hash mismatch: expected {text_sha256}, got {actual_sha}")
    except Exception as e:
        errs.append(f"Missing or unreadable blob at {text_path}: {e}")

    if raw_source_resolver and norm_q_path:
        expected_full_hash = manifest_entry.get("source_sha256", "")
        try:
            _, actual_full_hash, _ = raw_source_resolver(norm_q_path, expected_full_hash)
            if actual_full_hash != expected_full_hash:
                errs.append(f"Raw source full hash mismatch: expected {expected_full_hash}, got {actual_full_hash}")
        except Exception as e:
            errs.append(f"Raw source resolution failed: {e}")

    return errs

def process_row(row: Dict[str, Any], old_manifest: Dict[str, Any], data_root: Path, mirror: Path, warnings: List[str], errors: List[str], protected_blobs: Set[str], write_blobs: bool = False) -> Optional[Dict[str, Any]]:
    run_id = row.get("Run ID", "")
    state = row.get("Status", "")
    src_type = row.get("Source type", "")
    q_path = row.get("Source", "")
    q_hash = row.get("Source hash", "")
    version_str = str(row.get("Source text version", "")).strip()

    is_v1 = (version_str == "1")

    if is_v1:
        if state not in ("needs_scope", "processing", "blocked", "finalizing", "completed"):
            return None
    elif state in ("completed", "historical"):
        pass
    else:
        return None

    ext = Path(q_path).suffix.casefold()
    is_eligible = (src_type in SOURCE_TEXT_TYPES and ext in ALLOWED_EXTENSIONS)

    key = f"{run_id}:v1"
    existing = old_manifest.get(key)

    if not is_eligible:
        if is_v1:
            errors.append(f"{run_id}: version 1 row is ineligible type/ext")
        return existing

    try:
        norm_q_path = normalize_path(q_path)
    except Exception as e:
        if is_v1:
            errors.append(f"{run_id}: bad path: {e}")
        else:
            warnings.append(f"{run_id}: legacy backfill failed bad path: {e}")
        return existing

    if existing:
        def blob_loader(p):
            return (mirror / p).read_bytes()
        def raw_source_resolver(p, expected_hash):
            return resolve_relocation(data_root, expected_hash)

        verr = verify_manifest_entry(row, existing, blob_loader, raw_source_resolver)
        if not verr:
            protected_blobs.add(existing["text_path"])
            return existing

        if existing.get("source_path") != norm_q_path or existing.get("queue_source_hash") != q_hash:
            msg = f"{run_id}: existing entry metadata mismatch: {'; '.join(verr)}"
            if is_v1:
                errors.append(msg)
            else:
                warnings.append(msg)
            return existing

        try:
            expected_full_hash = existing.get("source_sha256", "")
            actual_path, actual_sha256, raw_bytes = resolve_relocation(data_root, expected_full_hash)

            if ext == ".docx":
                profile = "docx_body_v1"
                text_val = docx_to_text_v1(raw_bytes)
            else:
                profile = "utf8_text_v1"
                text_val = process_utf8_v1(raw_bytes)

            text_bytes = text_val.encode("utf-8")
            text_sha256 = get_full_sha256(text_bytes)

            if profile != existing.get("extractor_profile") or text_sha256 != existing.get("text_sha256"):
                msg = f"{run_id}: regenerated blob hash/profile mismatch"
                if is_v1: errors.append(msg)
                else: warnings.append(msg)
                return existing

            text_path = f"_source_text/blobs/v1/{text_sha256}.txt"

            if write_blobs:
                out_p = mirror / text_path
                assert_private_mirror(mirror, data_root)
                out_p.parent.mkdir(parents=True, exist_ok=True)
                out_p.write_bytes(text_bytes)

            protected_blobs.add(text_path)
            return dict(sorted(existing.items()))
        except ExtractionError as e:
            msg = f"{run_id}: missing/corrupt blob and exact reconstruction impossible: {e}"
            if is_v1: errors.append(msg)
            else: warnings.append(msg)
            return existing

    try:
        actual_path, source_sha256, raw_bytes = resolve_first_export(data_root, norm_q_path, q_hash)

        if ext == ".docx":
            profile = "docx_body_v1"
            text_val = docx_to_text_v1(raw_bytes)
        else:
            profile = "utf8_text_v1"
            text_val = process_utf8_v1(raw_bytes)

        text_bytes = text_val.encode("utf-8")
        text_sha256 = get_full_sha256(text_bytes)
        text_path = f"_source_text/blobs/v1/{text_sha256}.txt"

        entry = {
            "source_path": norm_q_path,
            "queue_source_hash": q_hash,
            "source_sha256": source_sha256,
            "text_sha256": text_sha256,
            "text_path": text_path,
            "extractor_profile": profile
        }

        if write_blobs:
            out_p = mirror / text_path
            assert_private_mirror(mirror, data_root)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_bytes(text_bytes)

        protected_blobs.add(text_path)
        return dict(sorted(entry.items()))

    except ExtractionError as e:
        if is_v1:
            errors.append(f"{run_id}: v1 extraction failed: {e}")
        else:
            warnings.append(f"{run_id}: legacy extraction skipped: {e}")
        return None

def validate_manifest(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Manifest must be a dict")
    for k, v in data.items():
        if not isinstance(v, dict):
            raise ValueError(f"Manifest entry {k} must be a dict")
        if not k.endswith(":v1"):
            raise ValueError(f"Malformed key {k}")

        req_fields = {"source_path", "queue_source_hash", "source_sha256", "text_sha256", "text_path", "extractor_profile"}
        if set(v.keys()) != req_fields:
            raise ValueError(f"Manifest entry {k} has missing or extra fields")

        qsh = v["queue_source_hash"]
        ssha = v["source_sha256"]
        tsha = v["text_sha256"]
        tp = v["text_path"]
        sp = v["source_path"]
        prof = v["extractor_profile"]

        if not (isinstance(qsh, str) and len(qsh) == 16 and all(c in "0123456789abcdef" for c in qsh)):
            raise ValueError(f"Manifest entry {k} queue_source_hash invalid")

        if not (isinstance(ssha, str) and len(ssha) == 64 and all(c in "0123456789abcdef" for c in ssha)):
            raise ValueError(f"Manifest entry {k} source_sha256 invalid")

        if not (isinstance(tsha, str) and len(tsha) == 64 and all(c in "0123456789abcdef" for c in tsha)):
            raise ValueError(f"Manifest entry {k} text_sha256 invalid")

        if not ssha.startswith(qsh):
            raise ValueError(f"Manifest entry {k} source_sha256 does not start with queue_source_hash")

        if prof not in ("docx_body_v1", "utf8_text_v1"):
            raise ValueError(f"Manifest entry {k} extractor_profile invalid")

        if (prof == "docx_body_v1" and not sp.endswith(".docx")) or (prof == "utf8_text_v1" and not (sp.endswith(".txt") or sp.endswith(".md"))):
            raise ValueError(f"Manifest entry {k} extractor_profile invalid for extension")

        if tp != f"_source_text/blobs/v1/{tsha}.txt":
            raise ValueError(f"Manifest entry {k} invalid text_path derivation")

        if ".." in sp.split("/") or sp.startswith("/") or ":" in sp:
            raise ValueError(f"Manifest entry {k} unsafe source_path")

def read_manifest(manifest_path: Path) -> Dict[str, Any]:
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_manifest(data)
        return data
    except Exception as e:
        raise RuntimeError(f"Malformed manifest: {e}")

def export(queue_rows: List[Dict[str, Any]], data_root: Path, mirror: Path) -> Tuple[Set[str], List[str], List[str]]:
    assert_private_mirror(mirror, data_root)
    manifest_path = mirror / "_source_text_manifest.json"

    try:
        old_manifest = read_manifest(manifest_path)
    except Exception as e:
        return set(), [f"Manifest read error: {e}"], []

    warnings: List[str] = []
    errors: List[str] = []
    protected_paths: Set[str] = {"_source_text_manifest.json"}

    new_manifest = {}
    for row in queue_rows:
        entry = process_row(row, old_manifest, data_root, mirror, warnings, errors, protected_paths, write_blobs=True)
        key = f"{row.get('Run ID', '')}:v1"
        if entry:
            new_manifest[key] = entry

    for k, v in old_manifest.items():
        if k not in new_manifest:
            new_manifest[k] = v
            protected_paths.add(v["text_path"])

    if not errors:
        try:
            validate_manifest(new_manifest)
        except Exception as e:
            return set(), [f"New manifest validation failed: {e}"], []

        sorted_manifest = dict(sorted(new_manifest.items()))
        json_bytes = json.dumps(sorted_manifest, indent=2, ensure_ascii=False).encode("utf-8")
        assert_private_mirror(mirror, data_root)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(json_bytes + b"\n")

    return protected_paths, errors, warnings

def audit(data_root: Path, mirror: Path, queue_rows: list, is_json: bool) -> None:
    manifest_path = mirror / "_source_text_manifest.json"
    old_manifest: dict = {}
    try:
        old_manifest = read_manifest(manifest_path)
    except Exception as e:
        if is_json:
            print_envelope_and_exit(False, "audit", {}, [], [str(e)])
        else:
            sys.stderr.write(f"Error: {e}\n")
            sys.exit(1)

    warnings = []
    errors = []
    protected = set()
    for row in queue_rows:
        key = f"{row.get('Run ID', '')}:v1"
        existing = old_manifest.get(key)

        is_v1 = (str(row.get("Source text version", "")).strip() == "1")
        req = source_text_requirement(row)

        if is_v1 and req != "required":
            errors.append(f"{row.get('Run ID', '')}: Source text version is 1 but requirement is {req}")

        if existing:
            def blob_loader(p):
                return (mirror / p).read_bytes()
            def raw_source_resolver(p, expected_hash):
                return resolve_relocation(data_root, expected_hash)
            verr = verify_manifest_entry(row, existing, blob_loader, raw_source_resolver)
            if verr:
                msg = f"{row.get('Run ID', '')}: audit failed: {'; '.join(verr)}"
                if is_v1: errors.append(msg)
                else: warnings.append(msg)
            else:
                protected.add(existing["text_path"])
        else:
            state = row.get("Status", "")
            if is_v1 and state in ("needs_scope", "processing", "blocked", "finalizing", "completed"):
                if req == "required":
                    errors.append(f"{row.get('Run ID', '')}: missing mandatory v1 manifest entry")

    if is_json:
        out = {"protected_blobs_count": len(protected)}
        print_envelope_and_exit(not errors, "audit", out, warnings, errors)
    else:
        if errors:
            for e in errors: print(f"ERROR: {e}")
        if warnings:
            for w in warnings: print(f"WARNING: {w}")
        if not errors and not warnings:
            print("Audit successful. No issues found.")
        sys.exit(1 if errors else 0)

def main():
    is_json = "--json" in sys.argv
    if "--help" in sys.argv or "-h" in sys.argv:
        if is_json:
            print_envelope_and_exit(True, "help", {"help": "Usage: python export_source_text.py <audit|export> [--json]"}, [], [])
        else:
            print("Usage: python export_source_text.py <audit|export> [--json]")
            sys.exit(0)

    parser = StrictArgumentParser(add_help=False)
    parser.add_argument("mode", choices=["audit", "export"])
    parser.add_argument("--json", action="store_true")

    args = None
    try:
        args = parser.parse_args()
    except ParserError as e:
        if is_json:
            print_envelope_and_exit(False, "unknown", {}, [], [str(e)])
        else:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args is None:
        sys.exit(1)

    mode = args.mode

    DATA_ROOT = None
    MIRROR = None
    find_queue = None
    read_queue = None
    get_services_cached = None

    try:
        from qa_manage import DATA_ROOT as DR, MIRROR as MR, find_queue as FQ, read_queue as RQ, get_services_cached as GSC
        DATA_ROOT, MIRROR, find_queue, read_queue, get_services_cached = DR, MR, FQ, RQ, GSC
    except ImportError as e:
        if is_json:
            print_envelope_and_exit(False, mode, {}, [], [f"Failed to import qa_manage: {e}"])
        else:
            print(f"Failed to import qa_manage: {e}", file=sys.stderr)
            sys.exit(1)

    rows: list = []
    try:
        if find_queue and get_services_cached and read_queue:
            q = find_queue(get_services_cached())
            rows = read_queue(get_services_cached(), q) if q else []
    except Exception as e:
        if is_json:
            print_envelope_and_exit(False, mode, {}, [], [f"Queue read error: {e}"])
        else:
            print(f"Queue read error: {e}", file=sys.stderr)
            sys.exit(1)

    if DATA_ROOT is None or MIRROR is None:
        if is_json:
            print_envelope_and_exit(False, mode, {}, [], ["DATA_ROOT or MIRROR uninitialized"])
        else:
            print("DATA_ROOT or MIRROR uninitialized", file=sys.stderr)
            sys.exit(1)

    assert DATA_ROOT is not None and MIRROR is not None

    if mode == "audit":
        audit(DATA_ROOT, MIRROR, rows, is_json)
    elif mode == "export":
        try:
            protected, errs, warns = export(rows, DATA_ROOT, MIRROR)
            if is_json:
                print_envelope_and_exit(not errs, "export", {"protected": sorted(list(protected))}, warns, errs)
            else:
                for w in warns: print(f"WARNING: {w}")
                for e in errs: print(f"ERROR: {e}")
                print(f"Exported {len(protected)} protected blobs.")
                sys.exit(1 if errs else 0)
        except Exception as e:
            if is_json:
                print_envelope_and_exit(False, "export", {}, [], [str(e)])
            else:
                print(f"Export failed: {e}", file=sys.stderr)
                sys.exit(1)

if __name__ == "__main__":
    main()
