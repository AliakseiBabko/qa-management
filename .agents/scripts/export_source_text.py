import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

from mirror_common import assert_private_mirror
from qa_manage import DATA_ROOT, MIRROR, find_queue, read_queue

# --- Constraints & Constants ---
SOURCE_TEXT_SEARCH_ROOTS = [
    DATA_ROOT / "02_Transcripts_Inbox",
    DATA_ROOT / "03_Transcripts_Processed",
    DATA_ROOT / "01_Recordings",
    DATA_ROOT / "00_Source_Docs" / "01_Meeting_Transcripts",
    DATA_ROOT / "00_Source_Docs" / "02_Chats_and_Emails"
]

SOURCE_TEXT_TYPES = {"qa_1to1", "strategy_chat", "meeting_transcript", "people_case_chat"}
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx"}

MAX_ZIP_MEMBERS = 2000
MAX_ZIP_SIZE = 500 * 1024 * 1024
MAX_XML_SIZE = 100 * 1024 * 1024
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

class ExtractionError(Exception):
    pass

# --- Extraction Logic ---

def extract_paragraph(p_elem: ET.Element) -> str:
    parts = []
    for node in p_elem.iter():
        tag = node.tag.split('}')[-1] if '}' in node.tag else node.tag
        if tag == "t" and node.text:
            parts.append(node.text)
        elif tag == "tab":
            parts.append("\t")
        elif tag in ("br", "cr"):
            parts.append("\n")
    return "".join(parts)

def extract_table(tbl_elem: ET.Element) -> str:
    rows = []
    for tr in tbl_elem.findall(".//w:tr", WORD_NS):
        cells = []
        for tc in tr.findall(".//w:tc", WORD_NS):
            cell_parts = []
            for child in tc:
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag == "p":
                    # Flatten paragraphs in cells to space or newline. Let's use space to keep table row intact.
                    cell_parts.append(extract_paragraph(child).replace("\n", " "))
                elif tag == "tbl":
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

def resolve_source_file(queue_rel_path: str, queue_hash_prefix: str) -> Tuple[Path, str, bytes]:
    # 1. Try exact path first
    exact_path = DATA_ROOT / queue_rel_path
    if exact_path.exists() and exact_path.is_file():
        try:
            exact_path_resolved = exact_path.resolve()
            if not str(exact_path_resolved).startswith(str(DATA_ROOT.resolve())):
                raise ValueError("Escape")
        except Exception:
            pass
        else:
            b = exact_path.read_bytes()
            full_sha = get_full_sha256(b)
            if full_sha.startswith(queue_hash_prefix):
                return exact_path, full_sha, b

    # 2. Relocation fallback
    candidates = []
    for root in SOURCE_TEXT_SEARCH_ROOTS:
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
    paths.sort(key=lambda x: str(x[0].relative_to(DATA_ROOT)).replace("\\", "/"))
    chosen_path, chosen_bytes = paths[0]
    return chosen_path, full_hash, chosen_bytes


# --- Export Logic ---

def process_row(row: Dict[str, Any], old_manifest: Dict[str, Any], warnings: List[str], errors: List[str], protected_blobs: Set[str], write_blobs: bool = False) -> Optional[Dict[str, Any]]:
    run_id = row.get("Run ID", "")
    state = row.get("State", "")
    src_type = row.get("Source type", "")
    q_path = row.get("Source path", "")
    q_hash = row.get("Source hash", "")
    version_str = str(row.get("Source text version", "")).strip()

    if state not in ("completed", "historical", "terminal"):
        return None

    ext = Path(q_path).suffix.casefold()
    is_eligible = (src_type in SOURCE_TEXT_TYPES and ext in ALLOWED_EXTENSIONS)

    key = f"{run_id}:v1"
    existing = old_manifest.get(key)

    if not is_eligible:
        if version_str == "1":
            errors.append(f"{run_id}: version 1 row is ineligible type/ext")
        return existing # preserve if it happens to be there

    try:
        norm_q_path = normalize_path(q_path)
    except Exception as e:
        if version_str == "1":
            errors.append(f"{run_id}: bad path: {e}")
        else:
            warnings.append(f"{run_id}: legacy backfill failed bad path: {e}")
        return existing

    # if already present and valid, we just keep it
    if existing:
        protected_blobs.add(existing["text_path"])
        return existing

    # We need to extract it
    try:
        actual_path, source_sha256, raw_bytes = resolve_source_file(norm_q_path, q_hash)

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
            out_p = MIRROR / text_path
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_bytes(text_bytes)

        protected_blobs.add(text_path)
        return dict(sorted(entry.items()))

    except ExtractionError as e:
        if version_str == "1":
            errors.append(f"{run_id}: v1 extraction failed: {e}")
        else:
            warnings.append(f"{run_id}: legacy extraction skipped: {e}")
        return None

def read_manifest(manifest_path: Path) -> Dict[str, Any]:
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        # validation
        for k, v in data.items():
            if not isinstance(v, dict):
                raise ValueError("Manifest entries must be dicts")
            tp = v.get("text_path")
            ts = v.get("text_sha256")
            if not tp or not ts or tp != f"_source_text/blobs/v1/{ts}.txt":
                raise ValueError(f"Invalid text_path derivation for {k}")
        return data
    except Exception as e:
        raise RuntimeError(f"Malformed manifest: {e}")


def export(queue_rows: List[Dict[str, Any]]) -> Tuple[Set[str], List[str], List[str]]:
    """Mutating export intended to be called by commit_workspace_state.py"""
    assert_private_mirror(MIRROR, DATA_ROOT)
    manifest_path = MIRROR / "_source_text_manifest.json"

    try:
        old_manifest = read_manifest(manifest_path)
    except Exception as e:
        # Crucially: we do not swallow malformed manifest. We fail out.
        return set(), [f"Manifest read error: {e}"], []

    warnings: List[str] = []
    errors: List[str] = []
    protected_paths: Set[str] = {"_source_text_manifest.json"}

    new_manifest = {}
    for row in queue_rows:
        entry = process_row(row, old_manifest, warnings, errors, protected_paths, write_blobs=True)
        key = f"{row.get('Run ID', '')}:v1"
        if entry:
            new_manifest[key] = entry

    # Also preserve things in old_manifest that aren't in the current queue
    # because they might be historical runs dropped from the queue.
    # Actually wait: queue is the source of truth. Does the queue drop terminal runs?
    # No, queue keeps historical/terminal rows forever unless manually deleted.
    # But just in case, we retain manifest entries if they exist in old but weren't processed.
    for k, v in old_manifest.items():
        if k not in new_manifest:
            new_manifest[k] = v
            protected_paths.add(v["text_path"])

    if not errors:
        # Write updated manifest deterministically
        sorted_manifest = dict(sorted(new_manifest.items()))
        json_bytes = json.dumps(sorted_manifest, indent=2, ensure_ascii=False).encode("utf-8")
        # exactly one trailing LF
        manifest_path.write_bytes(json_bytes + b"\n")

    return protected_paths, errors, warnings

def audit() -> int:
    try:
        q = find_queue(DATA_ROOT)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 1

    manifest_path = MIRROR / "_source_text_manifest.json"
    try:
        old_manifest = read_manifest(manifest_path)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 1

    queue_rows = read_queue(get_services_cached(), q)
    warnings = []
    errors = []
    protected = set()
    for row in queue_rows:
        process_row(row, old_manifest, warnings, errors, protected, write_blobs=False)

    out = {
        "errors": errors,
        "warnings": warnings,
        "protected_blobs_count": len(protected)
    }
    print(json.dumps(out))
    return 1 if errors else 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["audit", "export"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.mode == "audit":
        if args.json:
            sys.exit(audit())
        else:
            sys.exit("audit only supports --json")
    elif args.mode == "export":
        # export is primarily an internal module function, but could be called via CLI for testing
        q = find_queue(DATA_ROOT)
        rows = read_queue(get_services_cached(), q)
        protected, errs, warns = export(rows)
        out = {"errors": errs, "warnings": warns, "protected": list(protected)}
        print(json.dumps(out))
        sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
