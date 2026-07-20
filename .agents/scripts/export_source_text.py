import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

from mirror_common import assert_private_mirror

# --- Constraints & Constants ---
SOURCE_TEXT_TYPES = {"qa_1to1", "strategy_chat", "meeting_transcript", "people_case_chat"}
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx"}

MAX_ZIP_MEMBERS = 2000
MAX_ZIP_SIZE = 500 * 1024 * 1024
MAX_XML_SIZE = 100 * 1024 * 1024
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

class ExtractionError(Exception):
    pass

# --- JSON Envelope ---

def build_json_envelope(ok: bool, command: str, data: dict, warnings: list, errors: list) -> dict:
    return {
        "schema_version": 1,
        "ok": ok,
        "command": command,
        "data": data,
        "warnings": warnings,
        "errors": errors
    }

def print_envelope_and_exit(ok: bool, command: str, data: dict, warnings: list, errors: list):
    envelope = build_json_envelope(ok, command, data, warnings, errors)
    print(json.dumps(envelope, ensure_ascii=False, indent=1))
    sys.exit(0 if ok else 1)

# --- Extraction Logic ---

def extract_paragraph(p_elem: ET.Element) -> str:
    parts = []
    # Avoid text from w:del
    for node in p_elem.iter():
        tag = node.tag.split('}')[-1] if '}' in node.tag else node.tag
        if tag == "del":
            # Skip entire subtree of deleted content
            continue
        # Also skip field instructions
        if tag == "instrText":
            continue
        if tag == "t" and node.text:
            parts.append(node.text)
        elif tag == "tab":
            parts.append("\t")
        elif tag in ("br", "cr"):
            parts.append("\n")
    return "".join(parts)

def extract_table(tbl_elem: ET.Element) -> str:
    rows = []
    # Direct child traversal to avoid processing nested tables multiple times
    for tr in tbl_elem:
        tag_tr = tr.tag.split('}')[-1] if '}' in tr.tag else tr.tag
        if tag_tr != "tr":
            continue
        cells = []
        for tc in tr:
            tag_tc = tc.tag.split('}')[-1] if '}' in tc.tag else tc.tag
            if tag_tc != "tc":
                continue
            cell_parts = []
            for child in tc:
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag == "p":
                    # Keep table row intact
                    cell_parts.append(extract_paragraph(child).replace("\n", " "))
                elif tag == "tbl":
                    # Nested table traversed exactly once
                    cell_parts.append(extract_table(child).replace("\n", " "))
            cells.append(" ".join(cell_parts).strip())
        rows.append("\t".join(cells))
    return "\n".join(rows)

def docx_to_text_v1(docx_bytes: bytes) -> str:
    import io
    if len(docx_bytes) > MAX_ZIP_SIZE:
        raise ExtractionError(f"DOCX size {len(docx_bytes)} exceeds {MAX_ZIP_SIZE}")

    try:
        zf = zipfile.ZipFile(io.BytesIO(docx_bytes))
    except zipfile.BadZipFile as e:
        raise ExtractionError(f"Bad DOCX zip: {e}")

    infolist = zf.infolist()
    if len(infolist) > MAX_ZIP_MEMBERS:
        raise ExtractionError(f"DOCX members {len(infolist)} exceeds {MAX_ZIP_MEMBERS}")

    doc_info = None
    for info in infolist:
        if info.filename == "word/document.xml":
            doc_info = info
            break

    if not doc_info:
        raise ExtractionError("word/document.xml not found")

    if doc_info.file_size > MAX_XML_SIZE:
        raise ExtractionError(f"document.xml size {doc_info.file_size} exceeds {MAX_XML_SIZE}")

    # ZIP bomb protection: compression ratio
    if doc_info.compress_size > 0 and doc_info.file_size / doc_info.compress_size > 100:
        raise ExtractionError("Highly compressed document.xml suspected zip bomb")

    xml_bytes = zf.read("word/document.xml")
    if len(xml_bytes) > MAX_XML_SIZE:
        raise ExtractionError("document.xml uncompressed size too large")

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ExtractionError(f"XML parse error: {e}")

    body = root.find("w:body", WORD_NS)
    if body is None:
        return "\n"

    parts = []
    for child in body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == "p":
            text = extract_paragraph(child)
            if text:
                parts.append(text)
        elif tag == "tbl":
            text = extract_table(child)
            if text:
                parts.append(text)

    res = "\n".join(parts).rstrip() + "\n"
    if res == "\n":
        return "\n"
    return res

def process_utf8_v1(raw_bytes: bytes) -> str:
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ExtractionError(f"Invalid UTF-8: {e}")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.rstrip() + "\n"


# --- Hash & Resolution ---

def get_full_sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def normalize_path(p: str) -> str:
    p = p.replace("\\", "/")
    if ".." in p.split("/") or p.startswith("/") or ":" in p:
        raise ValueError(f"Invalid path {p}")
    return p

def resolve_source_file(data_root: Path, queue_rel_path: str, queue_hash_prefix: str) -> Tuple[Path, str, bytes]:
    # 1. Try exact path first
    exact_path = data_root / queue_rel_path
    if exact_path.exists() and exact_path.is_file():
        try:
            exact_path_resolved = exact_path.resolve()
            if not str(exact_path_resolved).startswith(str(data_root.resolve())):
                raise ValueError("Escape")
        except Exception:
            pass
        else:
            b = exact_path.read_bytes()
            full_sha = get_full_sha256(b)
            if full_sha.startswith(queue_hash_prefix):
                return exact_path, full_sha, b

    # 2. Relocation fallback
    search_roots = [
        data_root / "02_Transcripts_Inbox",
        data_root / "03_Transcripts_Processed",
        data_root / "01_Recordings",
        data_root / "00_Source_Docs" / "01_Meeting_Transcripts",
        data_root / "00_Source_Docs" / "02_Chats_and_Emails"
    ]
    candidates = []
    for root in search_roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.casefold() in ALLOWED_EXTENSIONS:
                candidates.append(p)

    matching = {}
    for cand in candidates:
        try:
            b = cand.read_bytes()
            h = get_full_sha256(b)
            if h.startswith(queue_hash_prefix):
                if h not in matching:
                    matching[h] = []
                matching[h].append((cand, b))
        except Exception:
            pass

    if not matching:
        raise ExtractionError(f"Missing source file for hash {queue_hash_prefix}")
    if len(matching) > 1:
        raise ExtractionError(f"Ambiguous full hashes for prefix {queue_hash_prefix}")

    # exactly 1 full hash
    full_hash = list(matching.keys())[0]
    paths = matching[full_hash]
    # sort lexically by normalized relative path
    paths.sort(key=lambda x: str(x[0].relative_to(data_root)).replace("\\", "/"))
    chosen_path, chosen_bytes = paths[0]
    return chosen_path, full_hash, chosen_bytes


# --- Export Logic ---

def process_row(row: Dict[str, Any], old_manifest: Dict[str, Any], data_root: Path, mirror: Path, warnings: List[str], errors: List[str], protected_blobs: Set[str], write_blobs: bool = False) -> Optional[Dict[str, Any]]:
    run_id = row.get("Run ID", "")
    state = row.get("Status", "")
    src_type = row.get("Source type", "")
    q_path = row.get("Source", "")
    q_hash = row.get("Source hash", "")
    version_str = str(row.get("Source text version", "")).strip()

    is_v1 = (version_str == "1")

    # Determine eligibility by version and status
    if is_v1:
        # Mandatory export in active and completed states
        if state not in ("needs_scope", "processing", "blocked", "finalizing", "completed"):
            return None
    elif state in ("completed", "historical"):
        # Optional legacy backfill
        pass
    else:
        # Other blank-version active states or ignored/failed -> skip
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
        protected_blobs.add(existing["text_path"])
        return existing

    # Extract
    try:
        actual_path, source_sha256, raw_bytes = resolve_source_file(data_root, norm_q_path, q_hash)

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
    # Reject entire manifest if any record violates rules
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
    """Mutating export intended to be called by commit_workspace_state.py"""
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

def audit(data_root: Path, mirror: Path, queue_rows: list) -> None:
    manifest_path = mirror / "_source_text_manifest.json"
    try:
        old_manifest = read_manifest(manifest_path)
    except Exception as e:
        print_envelope_and_exit(False, "audit", {}, [], [str(e)])

    warnings = []
    errors = []
    protected = set()
    for row in queue_rows:
        process_row(row, old_manifest, data_root, mirror, warnings, errors, protected, write_blobs=False)

    out = {
        "protected_blobs_count": len(protected)
    }
    print_envelope_and_exit(not errors, "audit", out, warnings, errors)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["audit", "export"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    # Lazy import of queue logic
    try:
        from qa_manage import DATA_ROOT, MIRROR, find_queue, read_queue, get_services_cached
    except ImportError as e:
        print_envelope_and_exit(False, args.mode, {}, [], [f"Failed to import qa_manage: {e}"])

    if args.mode == "audit":
        if args.json:
            try:
                q = find_queue(get_services_cached())
                rows = read_queue(get_services_cached(), q) if q else []
            except Exception as e:
                print_envelope_and_exit(False, "audit", {}, [], [str(e)])
            audit(DATA_ROOT, MIRROR, rows)
        else:
            sys.exit("audit only supports --json")
    elif args.mode == "export":
        try:
            q = find_queue(get_services_cached())
            rows = read_queue(get_services_cached(), q) if q else []
            protected, errs, warns = export(rows, DATA_ROOT, MIRROR)
            print_envelope_and_exit(not errs, "export", {"protected": list(protected)}, warns, errs)
        except Exception as e:
            print_envelope_and_exit(False, "export", {}, [], [str(e)])

if __name__ == "__main__":
    main()
