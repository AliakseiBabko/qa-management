#!/usr/bin/env python3
"""
Deterministic Workspace Search

Read-only, deterministic query interface over the private git mirror.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
import collections
import re

# Exclusions
EXCLUDED_EXTS = {".xlsx", ".docx", ".gsheet"}
EXCLUDED_FILES = {"_manifest.json", "_source_text_manifest.json", "README.md"}
EXCLUDED_DIRS = {".git"}

CANONICAL_ROOTS = [
    "05_People_Management",
    "10_M1_People_Management",
    "20_M2_Project_Management",
]

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from mirror_common import assert_private_mirror
except ImportError:
    def assert_private_mirror(mirror, data_root, init_allowed=False): pass

DEFAULT_MIRROR = Path.home() / "Documents" / "qa-drive-mirror"

def run_git(mirror: Path, args: list[str], check=True, text=False) -> subprocess.CompletedProcess:
    res = subprocess.run(
        ["git", "--literal-pathspecs"] + args,
        cwd=mirror,
        capture_output=True,
        text=text,
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"Git command failed: git {' '.join(args)}\nError: {res.stderr}")
    return res

def _normalize_iso_date(date_str: str, end_of_day: bool = False) -> datetime:
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if end_of_day:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    except ValueError as e:
        raise ValueError(f"Invalid ISO date: {date_str}") from e

def build_envelope(command, query, regex, case_sensitive, kind, resolved_ref, ok=True, data=None, warnings=None, errors=None):
    payload = data or {}
    payload["query"] = query
    payload["regex"] = regex
    payload["case_sensitive"] = case_sensitive
    payload["kind"] = kind
    payload["resolved_ref"] = resolved_ref
    
    return {
        "schema_version": 1,
        "ok": ok,
        "command": command,
        "data": payload,
        "warnings": warnings or [],
        "errors": errors or [],
    }

def print_envelope(env):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(env, ensure_ascii=False, indent=2))

def parse_intake_queue(mirror: Path, ref: str) -> list[dict]:
    cmd = run_git(mirror, ["show", f"{ref}:_intake_queue.values.json"], check=False)
    if cmd.returncode != 0:
        raise RuntimeError("Failed to read _intake_queue.values.json")
    
    try:
        raw = json.loads(cmd.stdout.decode("utf-8"))
        for k, v in raw.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], list):
                headers = v[0]
                rows = []
                for row in v[1:]:
                    row_dict = {}
                    for i, header in enumerate(headers):
                        row_dict[header] = row[i] if i < len(row) else ""
                    rows.append(row_dict)
                return rows
        raise ValueError("Invalid _intake_queue.values.json format")
    except Exception as e:
        raise RuntimeError(f"Failed to parse _intake_queue.values.json: {e}")

def parse_source_manifest(mirror: Path, ref: str) -> dict:
    cmd = run_git(mirror, ["show", f"{ref}:_source_text_manifest.json"], check=False)
    if cmd.returncode != 0:
        raise RuntimeError("Failed to read _source_text_manifest.json")
    
    try:
        raw = json.loads(cmd.stdout.decode("utf-8"))
        if not isinstance(raw, dict) or "exported_files" not in raw:
            raise ValueError("Missing exported_files key")
        return raw.get("exported_files", {})
    except Exception as e:
        raise RuntimeError(f"Failed to parse _source_text_manifest.json: {e}")

def get_metadata(mirror: Path, ref: str, path: str, require_run_id: bool) -> tuple[dict, list]:
    warnings = []
    meta = {}
    
    if require_run_id or path.startswith("_source_text/blobs/v1/"):
        try:
            manifest = parse_source_manifest(mirror, ref)
            entry = None
            run_id = None
            for r_id, run_entry in manifest.items():
                if run_entry.get("text_path") == path:
                    entry = run_entry
                    run_id = r_id.split(":")[0] if ":" in r_id else r_id
                    break
                    
            if not entry:
                warnings.append({"metadata_ref": path, "condition": "Missing source text manifest entry"})
            else:
                meta["source_hash"] = entry.get("source_hash", "")
                meta["extractor_profile"] = entry.get("extractor_profile", "")
                meta["run_id"] = run_id
                
                try:
                    queue = parse_intake_queue(mirror, ref)
                    q_row = next((r for r in queue if r.get("Run ID") == run_id), None)
                    if not q_row:
                        warnings.append({"metadata_ref": path, "condition": "Missing intake queue entry"})
                    else:
                        meta["source_type"] = q_row.get("Source type", "")
                        meta["route_variant"] = q_row.get("Route variant", "")
                        meta["created"] = q_row.get("Created", "")
                        meta["snapshot"] = q_row.get("Snapshot", "")
                except Exception as e:
                    warnings.append({"metadata_ref": path, "condition": f"Queue error: {e}"})
        except Exception as e:
            warnings.append({"metadata_ref": path, "condition": f"Manifest error: {e}"})
            
    return meta, warnings

def resolve_ref(mirror: Path, ref: str) -> str:
    cmd = run_git(mirror, ["rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"], check=True, text=True)
    return cmd.stdout.strip()

def is_allowed_structurally(path: str, kind: str) -> bool:
    if kind == "canonical" or kind == "all":
        if path.endswith(".md") or path.endswith(".csv"):
            if any(path.startswith(r + "/") for r in CANONICAL_ROOTS):
                return True
    if kind == "source" or kind == "all":
        if path.startswith("_source_text/blobs/v1/") and path.endswith(".txt"):
            return True
    return False

def extract_context(mirror: Path, ref: str, path: str, line_no: int, context_lines: int) -> tuple[str, list[str], list[str]]:
    cmd = run_git(mirror, ["show", f"{ref}:{path}"], check=False)
    if cmd.returncode != 0:
        return "", [], []
        
    lines = cmd.stdout.decode("utf-8", errors="replace").splitlines()
    if not lines or line_no < 1 or line_no > len(lines):
        return "", [], []
        
    idx = line_no - 1
    text = lines[idx]
    
    start_idx = max(0, idx - context_lines)
    end_idx = min(len(lines), idx + context_lines + 1)
    
    ctx_b = lines[start_idx:idx]
    ctx_a = lines[idx+1:end_idx]
    
    return text, ctx_b, ctx_a

def current_search(mirror: Path, ref: str, query: str, is_regex: bool, case_sensitive: bool, allowed_paths: list[str], context: int, limit: int, require_run_id: bool) -> tuple[list, list]:
    if not allowed_paths:
        return [], []
        
    args = ["grep", "-z", "-n", "-I"]
    if not case_sensitive:
        args.append("-i")
    if is_regex:
        args.append("-E")
    else:
        args.append("-F")
        
    args.extend(["-e", query, ref, "--"])
    args.extend(allowed_paths)
    
    cmd = run_git(mirror, args, check=False)
    if cmd.returncode not in (0, 1):
        raise RuntimeError(f"Git grep failed: {cmd.stderr.decode('utf-8', errors='replace')}")
    if cmd.returncode == 1:
        return [], []
        
    raw = cmd.stdout.split(b'\n')
    matches = []
    warnings = []
    
    for line in raw:
        if not line:
            continue
            
        parts = line.split(b'\0')
        if len(parts) < 3:
            continue
            
        try:
            path = parts[0].decode("utf-8").split(":", 1)[1]
            line_no = int(parts[1].decode("utf-8"))
        except Exception:
            continue
            
        text, ctx_b, ctx_a = extract_context(mirror, ref, path, line_no, context)
        
        meta, warns = get_metadata(mirror, ref, path, require_run_id)
        warnings.extend(warns)
        
        matches.append({
            "path": path,
            "line": line_no,
            "text": text,
            "context_before": ctx_b,
            "context_after": ctx_a,
            "metadata": meta
        })
        
        if len(matches) > limit:
            break
            
    return matches, warnings

def history_search(mirror: Path, ref: str, query: str, is_regex: bool, case_sensitive: bool, allowed_paths: list[str], context: int, limit: int, since: datetime, until: datetime, require_run_id: bool) -> tuple[list, list]:
    args = ["log", "--first-parent", "-z", "--format=%H%x00%cI%x00%s"]
    if since:
        args.append(f"--since={since.isoformat()}")
    if until:
        args.append(f"--until={until.isoformat()}")
        
    args.append(ref)
    
    log_cmd = run_git(mirror, args, check=False, text=True)
    if log_cmd.returncode != 0:
        raise RuntimeError(f"Git log failed: {log_cmd.stderr}")
        
    commits_raw = log_cmd.stdout.split("\0")
    commits_out = []
    warnings_out = []
    
    i = 0
    while i < len(commits_raw) - 2:
        commit = commits_raw[i].strip()
        ts_str = commits_raw[i+1].strip()
        subj = commits_raw[i+2].strip()
        i += 3
        
        if not commit:
            continue
            
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
            
        parent_cmd = run_git(mirror, ["rev-parse", f"{commit}^1"], check=False, text=True)
        parent = parent_cmd.stdout.strip() if parent_cmd.returncode == 0 else "4b825dc642cb6eb9a060e54bf8d69288fbee4904" 
        diff_cmd = run_git(mirror, ["diff-tree", "-r", "-z", "--name-status", "--no-renames", parent, commit], check=False, text=True)
        if diff_cmd.returncode != 0:
            raise RuntimeError(f"Git diff-tree failed: {diff_cmd.stderr}")
        
        diff_raw = diff_cmd.stdout.split("\0")
        changed_files = []
        j = 0
        while j < len(diff_raw) - 1:
            status = diff_raw[j]
            path = diff_raw[j+1]
            j += 2
            
            if status and path and is_allowed_structurally(path, "all"):
                if not allowed_paths or path in allowed_paths:
                    changed_files.append((status, path))
                    
        if not changed_files:
            continue
            
        changes = []
        for status, path in changed_files:
            # Check grep in parent and commit
            parent_grep = 0
            if status != "A":
                grep_args = ["grep", "-z", "-c", "-I"]
                if not case_sensitive: grep_args.append("-i")
                if is_regex: grep_args.append("-E")
                else: grep_args.append("-F")
                grep_args.extend(["-e", query, f"{parent}:{path}"])
                pg_cmd = run_git(mirror, grep_args, check=False)
                if pg_cmd.returncode == 0:
                    try:
                        parent_grep = int(pg_cmd.stdout.strip().split(b'\0')[-1])
                    except ValueError:
                        pass
                        
            commit_grep = 0
            if status != "D":
                grep_args = ["grep", "-z", "-c", "-I"]
                if not case_sensitive: grep_args.append("-i")
                if is_regex: grep_args.append("-E")
                else: grep_args.append("-F")
                grep_args.extend(["-e", query, f"{commit}:{path}"])
                cg_cmd = run_git(mirror, grep_args, check=False)
                if cg_cmd.returncode == 0:
                    try:
                        commit_grep = int(cg_cmd.stdout.strip().split(b'\0')[-1])
                    except ValueError:
                        pass
            
            if parent_grep != commit_grep:
                change_type = "changed"
                if parent_grep == 0 and commit_grep > 0: change_type = "introduced"
                elif parent_grep > 0 and commit_grep == 0: change_type = "removed"
                
                meta, warns = get_metadata(mirror, commit, path, require_run_id)
                if status == "D":
                    warnings_out.extend(warns)
                else:
                    warnings_out.extend(warns)
                    
                changes.append({
                    "path": path,
                    "change": change_type,
                    "metadata": meta
                })
                
        if changes:
            commits_out.append({
                "commit": commit,
                "timestamp": ts_str,
                "subject": subj,
                "changes": changes
            })
            
            if len(commits_out) > limit:
                break
                
    return commits_out, warnings_out

class StrictParser(argparse.ArgumentParser):
    def error(self, message):
        raise SystemExit(message)

def main():
    parser = StrictParser(add_help=False)
    parser.add_argument("command", nargs="?", choices=["search", "history"])
    parser.add_argument("query", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mirror", default=str(DEFAULT_MIRROR))
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--case-sensitive", action="store_true")
    parser.add_argument("--regex", action="store_true")
    parser.add_argument("--kind", choices=["source", "canonical", "all"], default="all")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--run-id")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--context", type=int, default=2)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("-h", "--help", action="store_true")
    
    args = sys.argv[1:]
    is_json = "--json" in args
    
    try:
        parsed, unknown = parser.parse_known_args(args)
        if unknown:
            raise SystemExit(f"Unrecognized arguments: {' '.join(unknown)}")
        if parsed.help:
            if not is_json:
                print("Usage: search_workspace.py {search,history} <query> ...")
            sys.exit(0)
        if not parsed.command:
            raise SystemExit("Subcommand required")
        if not parsed.query:
            raise SystemExit("Empty query")
    except SystemExit as e:
        msg = str(e)
        if is_json:
            print_envelope(build_envelope("error", "", False, False, "all", "", False, errors=[msg]))
        else:
            sys.stderr.write(f"{msg}\n")
        sys.exit(1)
        
    def exit_err(msg):
        if is_json:
            print_envelope(build_envelope(parsed.command, parsed.query, getattr(parsed, 'regex', False), getattr(parsed, 'case_sensitive', False), getattr(parsed, 'kind', 'all'), "", False, errors=[msg]))
        else:
            sys.stderr.write(f"{msg}\n")
        sys.exit(1)
        
    if len(parsed.query) > 100:
        exit_err("Query exceeds maximum length of 100 characters")
            
    if parsed.limit < 1 or parsed.limit > 1000:
        exit_err("Limit must be 1..1000")
        
    if parsed.context < 0 or parsed.context > 20:
        exit_err("Context must be 0..20")
        
    mirror = Path(parsed.mirror).resolve()
    try:
        assert_private_mirror(mirror, Path("G:/My Drive/QA_Management"), init_allowed=False)
    except Exception as e:
        exit_err(f"Mirror error: {e}")
        
    try:
        resolved_ref = resolve_ref(mirror, parsed.ref)
    except Exception as e:
        exit_err("Invalid ref")
        
    if parsed.run_id and parsed.kind == "canonical":
        exit_err("--run-id and --kind canonical are incompatible")
        
    since = None
    until = None
    if parsed.command == "history":
        try:
            if parsed.since: since = _normalize_iso_date(parsed.since, end_of_day=False)
            if parsed.until: until = _normalize_iso_date(parsed.until, end_of_day=True)
            if since and until and since > until:
                raise ValueError("since > until")
        except ValueError as e:
            exit_err(f"Date error: {e}")
            
    allowed = []
    
    try:
        if parsed.command == "search":
            cmd = run_git(mirror, ["ls-tree", "-r", "-z", "--name-only", resolved_ref], check=True)
            files = cmd.stdout.split(b'\0')
            for f in files:
                if not f: continue
                path = f.decode("utf-8")
                if is_allowed_structurally(path, parsed.kind):
                    allowed.append(path)
    except Exception as e:
        exit_err("Failed to get allowed paths")
        
    valid_paths = set()
    for p in parsed.path:
        if p.startswith("/") or p.startswith("\\\\") or ".." in p or "*" in p or "?" in p or "[" in p:
            exit_err(f"Invalid --path value: {p}")
        if is_allowed_structurally(p, parsed.kind):
            valid_paths.add(p)
            
    if parsed.path:
        if parsed.command == "search":
            allowed = [p for p in allowed if p in valid_paths]
        else:
            allowed = list(valid_paths)
        
    filter_run_id = None
    if parsed.run_id:
        try:
            manifest = parse_source_manifest(mirror, resolved_ref)
        except Exception:
            manifest = {}
            
        entry = manifest.get(f"{parsed.run_id}:v1")
        if not entry:
            exit_err(f"Unknown run ID or missing v1 entry: {parsed.run_id}")
            
        tp = entry.get("text_path")
        if not tp:
            exit_err(f"Run ID {parsed.run_id} missing text_path")
            
        if parsed.command == "search":
            if tp not in allowed:
                allowed = []
            else:
                allowed = [tp]
        else:
            if parsed.path and tp not in allowed:
                allowed = []
            else:
                allowed = [tp]
            
        filter_run_id = parsed.run_id
        
    allowed = sorted(list(set(allowed)))
    if (parsed.run_id or parsed.path) and not allowed:
        if parsed.command == "search":
            if is_json:
                print_envelope(build_envelope(parsed.command, parsed.query, parsed.regex, parsed.case_sensitive, parsed.kind, resolved_ref, data={"result_count": 0, "truncated": False, "matches": []}))
            else:
                pass
            return

    try:
        if parsed.command == "search":
            if not allowed:
                matches, warns = [], []
            else:
                matches, warns = current_search(mirror, resolved_ref, parsed.query, parsed.regex, parsed.case_sensitive, allowed, parsed.context, parsed.limit, bool(parsed.run_id))
            
            unique_warnings = []
            seen = set()
            for w in warns:
                k = (w["metadata_ref"], w["condition"])
                if k not in seen:
                    seen.add(k)
                    unique_warnings.append(w)
            
            truncated = len(matches) > parsed.limit
            matches = matches[:parsed.limit]
            
            data = {
                "result_count": len(matches),
                "truncated": truncated,
                "matches": matches
            }
            if is_json:
                print_envelope(build_envelope(parsed.command, parsed.query, parsed.regex, parsed.case_sensitive, parsed.kind, resolved_ref, data=data, warnings=unique_warnings))
            else:
                for m in matches:
                    print(f"{m['path']}:{m['line']}: {m['text']}")
                for w in unique_warnings:
                    print(f"Warning: {w}")
                    
        elif parsed.command == "history":
            commits, warns = history_search(mirror, resolved_ref, parsed.query, parsed.regex, parsed.case_sensitive, allowed, parsed.context, parsed.limit, since, until, bool(parsed.run_id))
            
            unique_warnings = []
            seen = set()
            for w in warns:
                k = (w["metadata_ref"], w["condition"])
                if k not in seen:
                    seen.add(k)
                    unique_warnings.append(w)
                    
            truncated = len(commits) > parsed.limit
            commits = commits[:parsed.limit]
            
            data = {
                "result_count": len(commits),
                "truncated": truncated,
                "commits": commits
            }
            if filter_run_id:
                data["filter_run_id"] = filter_run_id
                
            if is_json:
                print_envelope(build_envelope(parsed.command, parsed.query, parsed.regex, parsed.case_sensitive, parsed.kind, resolved_ref, data=data, warnings=unique_warnings))
            else:
                for c in commits:
                    print(f"Commit: {c['commit']} ({c['timestamp']}) - {c['subject']}")
                    for ch in c['changes']:
                        print(f"  {ch['change']}: {ch['path']}")
                for w in unique_warnings:
                    print(f"Warning: {w}")
    except Exception as e:
        err = str(e)
        if not parsed.debug:
            err = err.splitlines()[-1]
        exit_err(err)

if __name__ == "__main__":
    main()
