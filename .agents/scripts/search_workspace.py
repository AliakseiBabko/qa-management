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
import os

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
from mirror_common import assert_private_mirror
import export_source_text

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
        from datetime import date
        d = date.fromisoformat(date_str)
        dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        if end_of_day:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    except ValueError as e:
        raise ValueError(f"Invalid ISO date (must be YYYY-MM-DD): {date_str}") from e

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

def parse_source_manifest(mirror: Path, ref: str, strict: bool = False) -> dict:
    cmd = run_git(mirror, ["show", f"{ref}:_source_text_manifest.json"], check=False)
    if cmd.returncode != 0:
        if strict:
            raise RuntimeError("Failed to read _source_text_manifest.json")
        return {}

    try:
        raw = json.loads(cmd.stdout.decode("utf-8"))
        export_source_text.validate_manifest(raw)
        return raw
    except Exception as e:
        if strict:
            raise RuntimeError(f"Failed to parse _source_text_manifest.json: {e}")
        return {}

def get_metadata(mirror: Path, ref: str, path: str, require_run_id: bool, strict_manifest: bool) -> tuple[dict, list]:
    warnings = []
    runs = []

    # We always need the manifest for this blob if it's a source blob or require_run_id is true
    if require_run_id or path.startswith("_source_text/blobs/v1/"):
        manifest = parse_source_manifest(mirror, ref, strict=strict_manifest)
        queue = []
        try:
            queue = parse_intake_queue(mirror, ref)
        except Exception as e:
            warnings.append({"metadata_ref": ref, "condition": f"Queue error: {e}"})

        for r_id, entry in manifest.items():
            if entry.get("text_path") == path:
                run_id = r_id.split(":")[0] if ":" in r_id else r_id
                meta = {
                    "queue_source_hash": entry.get("queue_source_hash", ""),
                    "source_path": entry.get("source_path", ""),
                    "source_sha256": entry.get("source_sha256", ""),
                    "text_sha256": entry.get("text_sha256", ""),
                    "extractor_profile": entry.get("extractor_profile", ""),
                    "run_id": run_id
                }

                if queue:
                    q_row = next((r for r in queue if r.get("Run ID") == run_id), None)
                    if not q_row:
                        warnings.append({"metadata_ref": ref, "condition": "Missing intake queue entry"})
                    else:
                        meta["source_type"] = q_row.get("Source type", "")
                        meta["route_variant"] = q_row.get("Route variant", "")
                        meta["project"] = q_row.get("Project", "")
                        meta["person"] = q_row.get("Person", "")
                        meta["status"] = q_row.get("Status", "")
                        meta["discovered"] = q_row.get("Discovered", "")
                        meta["started"] = q_row.get("Started", "")
                        meta["completed"] = q_row.get("Completed", "")
                        meta["snapshot"] = q_row.get("Snapshot", "")

                runs.append(meta)

        if not runs:
            warnings.append({"metadata_ref": ref, "condition": "Missing source text manifest entry"})

    return runs, warnings

def resolve_ref(mirror: Path, ref: str) -> str:
    cmd = run_git(mirror, ["rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"], check=True, text=True)
    return cmd.stdout.strip()

def is_allowed_structurally(path: str, kind: str) -> bool:
    if kind in ("canonical", "all"):
        if path.endswith(".md") or path.endswith(".csv"):
            if any(path.startswith(r + "/") for r in CANONICAL_ROOTS):
                return True
    if kind in ("source", "all"):
        if path.startswith("_source_text/blobs/v1/") and path.endswith(".txt"):
            return True
    return False

def is_valid_filter_path(p: str, kind: str) -> bool:
    if kind in ("canonical", "all"):
        if any(p.startswith(r + "/") or p == r or r.startswith(p + "/") or r == p for r in CANONICAL_ROOTS):
            return True
    if kind in ("source", "all"):
        if p.startswith("_source_text/blobs/v1/") or "_source_text/blobs/v1/".startswith(p):
            return True
    return False

def extract_matches_for_path(mirror: Path, ref: str, path: str, query: str, is_regex: bool, case_sensitive: bool, context: int, limit: int) -> tuple[list, bool]:
    args = ["grep", "-z", "-n", "-I"]
    if not case_sensitive: args.append("-i")
    if is_regex: args.append("-E")
    else: args.append("-F")
    args.extend(["-e", query, ref, "--", path])

    cmd = run_git(mirror, args, check=False)
    if cmd.returncode not in (0, 1):
        raise RuntimeError(f"Git grep failed: {cmd.stderr.decode('utf-8', errors='replace')}")
    if cmd.returncode == 1:
        return [], False

    raw = cmd.stdout.split(b'\n')
    matches = []

    # Read blob once
    blob_lines = []
    blob_cmd = run_git(mirror, ["show", f"{ref}:{path}"], check=False)
    if blob_cmd.returncode == 0:
        blob_lines = blob_cmd.stdout.decode("utf-8", errors="replace").splitlines()

    # Process all to accurately get truncated flag
    for line in raw:
        if not line: continue
        parts = line.split(b'\0')
        if len(parts) < 3: continue
        try:
            line_no = int(parts[1].decode("utf-8"))
        except: continue

        idx = line_no - 1
        text = ""
        ctx_b = []
        ctx_a = []
        if 0 <= idx < len(blob_lines):
            text = blob_lines[idx]
            start_idx = max(0, idx - context)
            end_idx = min(len(blob_lines), idx + context + 1)
            ctx_b = blob_lines[start_idx:idx]
            ctx_a = blob_lines[idx+1:end_idx]

        matches.append({
            "line": line_no,
            "text": text,
            "context_before": ctx_b,
            "context_after": ctx_a
        })

    # Deterministic sorting for matches inside a file
    matches.sort(key=lambda m: m['line'])

    if limit > 0:
        truncated = len(matches) > limit
        return matches[:limit], truncated
    return matches, False

def current_search(mirror: Path, ref: str, query: str, is_regex: bool, case_sensitive: bool, allowed_paths: list[str], context: int, limit: int, require_run_id: bool, strict_manifest: bool) -> tuple[list, list, bool]:
    if not allowed_paths:
        return [], [], False

    args = ["grep", "-z", "-n", "-I", "-l"] # Only get files first
    if not case_sensitive: args.append("-i")
    if is_regex: args.append("-E")
    else: args.append("-F")
    args.extend(["-e", query, ref, "--"])
    args.extend(allowed_paths)

    cmd = run_git(mirror, args, check=False)
    if cmd.returncode not in (0, 1):
        raise RuntimeError(f"Git grep failed: {cmd.stderr.decode('utf-8', errors='replace')}")
    if cmd.returncode == 1:
        return [], [], False

    files_with_matches = []
    for f in cmd.stdout.split(b'\0'):
        if f:
            try:
                files_with_matches.append(f.decode("utf-8").split(":", 1)[1])
            except:
                pass

    files_with_matches.sort()

    matches = []
    warnings = []
    truncated = False

    for path in files_with_matches:
        if len(matches) >= limit:
            truncated = True
            break

        file_matches, _ = extract_matches_for_path(mirror, ref, path, query, is_regex, case_sensitive, context, limit - len(matches) + 1)

        if file_matches:
            runs, warns = get_metadata(mirror, ref, path, require_run_id, strict_manifest)
            warnings.extend(warns)

            for m in file_matches:
                m["path"] = path
                m["ref"] = ref
                m["source_runs"] = runs
                matches.append(m)

                if len(matches) > limit:
                    truncated = True
                    break

        if truncated:
            break

    return matches[:limit], warnings, truncated

def history_search(mirror: Path, ref: str, query: str, is_regex: bool, case_sensitive: bool, kind: str, allowed_paths: list[str], path_filters_active: bool, context: int, limit: int, since: datetime, until: datetime, require_run_id: bool, strict_manifest: bool) -> tuple[list, list, bool]:
    args = ["log", "--first-parent", "-z", "--format=%H%x00%cI%x00%s"]
    if since: args.append(f"--since={since.isoformat()}")
    if until: args.append(f"--until={until.isoformat()}")
    args.append(ref)

    log_cmd = run_git(mirror, args, check=False, text=True)
    if log_cmd.returncode != 0:
        raise RuntimeError(f"Git log failed: {log_cmd.stderr}")

    commits_raw = log_cmd.stdout.split("\0")
    commits_out = []
    warnings_out = []
    truncated = False

    i = 0
    while i < len(commits_raw) - 2:
        commit = commits_raw[i].strip()
        ts_str = commits_raw[i+1].strip()
        subj = commits_raw[i+2].strip()
        i += 3

        if not commit: continue

        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)

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

            if status and path and is_allowed_structurally(path, kind):
                if not path_filters_active or any(path == p or path.startswith(p + "/") or (p.endswith("/") and path.startswith(p)) for p in allowed_paths):
                    changed_files.append((status, path))

        if not changed_files:
            continue

        changed_files.sort(key=lambda x: x[1])

        changes = []
        for status, path in changed_files:
            matches_before, before_trunc = [], False
            matches_after, after_trunc = [], False

            if status != "A":
                matches_before, before_trunc = extract_matches_for_path(mirror, parent, path, query, is_regex, case_sensitive, context, 0)
            if status != "D":
                matches_after, after_trunc = extract_matches_for_path(mirror, commit, path, query, is_regex, case_sensitive, context, 0)

            # Compare contexts
            if matches_before != matches_after:
                change_type = "changed"
                if not matches_before and matches_after: change_type = "introduced"
                elif matches_before and not matches_after: change_type = "removed"
                elif not matches_before and not matches_after: continue # Should not happen unless grep logic changed
                before_trunc = len(matches_before) > 100
                after_trunc = len(matches_after) > 100
                matches_before = matches_before[:100]
                matches_after = matches_after[:100]

                meta_ref = parent if status == "D" else commit
                runs, warns = get_metadata(mirror, meta_ref, path, require_run_id, strict_manifest)
                warnings_out.extend(warns)

                change_dict = {
                    "path": path,
                    "change": change_type,
                    "matches_before": matches_before,
                    "matches_before_truncated": before_trunc,
                    "matches_after": matches_after,
                    "matches_after_truncated": after_trunc,
                    "metadata_ref": meta_ref
                }
                change_dict["source_runs"] = runs
                changes.append(change_dict)









        if changes:
            commits_out.append({
                "commit": commit,
                "timestamp": ts_str,
                "subject": subj,
                "changes": changes
            })

            if len(commits_out) > limit:
                truncated = True
                break

    return commits_out[:limit], warnings_out, truncated

class StrictParser(argparse.ArgumentParser):
    def error(self, message):
        raise SystemExit(message)

def main():
    parser = StrictParser(add_help=False)
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

    raw_args = sys.argv[1:]
    is_json = "--json" in raw_args

    command = None
    query = None
    filtered_args = []

    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        if arg in ("search", "history") and command is None:
            command = arg
            if i + 1 < len(raw_args):
                query = raw_args[i+1]
                i += 1
        else:
            filtered_args.append(arg)
        i += 1

    try:
        parsed, unknown = parser.parse_known_args(filtered_args)
        if unknown:
            raise SystemExit(f"Unrecognized arguments: {' '.join(unknown)}")
        if parsed.help:
            if not is_json:
                print("Usage: search_workspace.py {search,history} <query> ...")
            sys.exit(0)
        if not command:
            raise SystemExit("Subcommand required")
        if not query:
            raise SystemExit("Empty query")
        parsed.command = command
        parsed.query = query
    except SystemExit as e:
        msg = str(e)
        if is_json:
            print_envelope(build_envelope("error", getattr(parsed, 'query', ''), getattr(parsed, 'regex', False), getattr(parsed, 'case_sensitive', False), getattr(parsed, 'kind', 'all'), "", False, errors=[msg]))
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
    except (Exception, SystemExit) as e:
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

    valid_paths = []
    for p in parsed.path:
        if p.startswith("/") or p.startswith("\\") or ".." in p or "*" in p or "?" in p or "[" in p:
            exit_err(f"Invalid --path value: {p}")
        if not is_valid_filter_path(p, parsed.kind):
            exit_err(f"Path outside allowed structural boundaries for kind {parsed.kind}: {p}")
        valid_paths.append(p)

    path_filters_active = bool(valid_paths)
    allowed = []
    has_source_blobs = False

    try:
        if parsed.command == "search":
            if parsed.since or parsed.until:
                exit_err("--since and --until are only allowed in history search")
            cmd = run_git(mirror, ["ls-tree", "-r", "-z", "--name-only", resolved_ref], check=True)
            files = cmd.stdout.split(b'\0')
            for f in files:
                if not f: continue
                p = f.decode("utf-8")
                if is_allowed_structurally(p, parsed.kind):
                    if is_allowed_structurally(p, "source"):
                        has_source_blobs = True

                    if path_filters_active:
                        if not any(p == flt or p.startswith(flt + "/") or (flt.endswith("/") and p.startswith(flt)) for flt in valid_paths):
                            continue
                    allowed.append(p)
        else:
            # We don't build `allowed` fully for history, we use path_filters_active and history_allowed_paths
            # But we need to know if the target ref has source blobs for strictness.
            cmd = run_git(mirror, ["ls-tree", "-r", "-z", "--name-only", resolved_ref], check=True)
            files = cmd.stdout.split(b'\0')
            for f in files:
                if not f: continue
                if is_allowed_structurally(f.decode("utf-8"), "source"):
                    has_source_blobs = True
                    break
    except Exception as e:
        exit_err("Failed to get allowed paths")

    strict_manifest = False
    if parsed.kind == "source" or parsed.run_id or (parsed.kind == "all" and has_source_blobs):
        strict_manifest = True

    if strict_manifest:
        try:
            parse_source_manifest(mirror, resolved_ref, strict=True)
        except Exception as e:
            exit_err(str(e))
    filter_run_id = None
    history_allowed_paths = list(valid_paths)

    if parsed.run_id:
        try:
            manifest = parse_source_manifest(mirror, resolved_ref, strict=strict_manifest)
        except Exception as e:
            exit_err(str(e))

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
            if path_filters_active:
                if not any(tp == flt or tp.startswith(flt + "/") for flt in valid_paths):
                    history_allowed_paths = []
                else:
                    history_allowed_paths = [tp]
            else:
                history_allowed_paths = [tp]

        filter_run_id = parsed.run_id
        path_filters_active = True

    if parsed.command == "search":
        allowed = sorted(list(set(allowed)))

    if path_filters_active:
        if parsed.command == "search" and not allowed:
            if is_json:
                print_envelope(build_envelope(parsed.command, parsed.query, parsed.regex, parsed.case_sensitive, parsed.kind, resolved_ref, data={"result_count": 0, "truncated": False, "matches": []}))
            return
        elif parsed.command == "history" and not history_allowed_paths:
            if is_json:
                print_envelope(build_envelope(parsed.command, parsed.query, parsed.regex, parsed.case_sensitive, parsed.kind, resolved_ref, data={"result_count": 0, "truncated": False, "commits": []}))
            return

    try:
        if parsed.command == "search":
            matches, warns, truncated = current_search(mirror, resolved_ref, parsed.query, parsed.regex, parsed.case_sensitive, allowed, parsed.context, parsed.limit, bool(parsed.run_id), strict_manifest)

            unique_warnings = []
            seen = set()
            for w in warns:
                k = (w["metadata_ref"], w["condition"])
                if k not in seen:
                    seen.add(k)
                    unique_warnings.append(w)

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
            commits, warns, truncated = history_search(mirror, resolved_ref, parsed.query, parsed.regex, parsed.case_sensitive, parsed.kind, history_allowed_paths, path_filters_active, parsed.context, parsed.limit, since, until, bool(parsed.run_id), strict_manifest)

            unique_warnings = []
            seen = set()
            for w in warns:
                k = (w["metadata_ref"], w["condition"])
                if k not in seen:
                    seen.add(k)
                    unique_warnings.append(w)

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
