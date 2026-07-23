"""Phase 11 operator telemetry: best-effort extraction of actual token usage
from local agent-runtime logs, for use with finalize_operator_run.py
--telemetry-json.

Ported from the erp-web-tests benchmark-playwright-debugging skill's
scripts/extract_telemetry.py (Claude/Codex/Cline/Antigravity adapters),
reduced and re-normalized to what this repo needs: a single session's
summed usage, written as a small JSON blob (never the raw log content,
never written anywhere but --out - default tmp/telemetry/, gitignored)
that finalize_operator_run.py merges into a CSV row's actual_* token
fields.

Output field names are QA-management's own CSV schema
(operator_telemetry_common.CSV_HEADER), not the ERP benchmark's
input_tokens/output_tokens/etc. - every adapter below normalizes to:

    actual_input_tokens
    actual_cache_creation_tokens
    actual_cache_read_tokens
    actual_output_tokens
    actual_reasoning_tokens
    model_label            (optional - only when trivially available)
    estimated_cost_usd     (optional - only a runtime-REPORTED cost, e.g.
                             Cline's totalCost; never a pricing-table
                             estimate computed here - that stays
                             finalize_operator_run.py's job, keyed off
                             model_label, so there is exactly one place
                             pricing assumptions live)

Every adapter also tags two extra keys consumed by record_agent_session.py
(harmless extras that finalize_operator_run.py's operator-runs.csv path
simply ignores, since it only reads specific known keys):

    extraction_method      one of claude_log/codex_log/cline_history/
                             antigravity_cli/antigravity_db - always set
    session_started_at     ISO timestamp of the first log line seen, when
    session_ended_at       trivially available (Claude/Codex/Cline only -
                             Antigravity's DB fallback has no reliable
                             per-step timestamp to use)

Supported runtimes
-------------------
- claude / claude-code: reads ~/.claude/projects/<hash>/<session-uuid>.jsonl,
  summing message.usage.{input_tokens,output_tokens,
  cache_creation_input_tokens,cache_read_input_tokens} across all
  type=assistant entries in the session. Verified against this repo's own
  Claude Code sessions (the exact same log this session itself writes).
- codex: reads ~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*-<session-uuid>.jsonl,
  including continuation files linked via session_meta, using the LAST
  token_count event per file and summing across files. Ported from the
  ERP benchmark skill's verified logic, and confirmed against a real Codex
  session log on this machine (a session from other work, not this repo's
  own history) - not just fake-log tests.
- cline: reads the VSCode extension's taskHistory.json (Windows:
  %APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/state/
  taskHistory.json). Ported because it's a plain JSON read, no
  subprocess/binary parsing - lowest-risk of the three new adapters.
- antigravity: tries `agy usage --session <id> --json` first (no working
  `agy` CLI is installed on this machine), then a best-effort SQLite
  conversation-DB fallback (heuristic protobuf field scan, not a verified
  schema - see AntigravityAdapter's docstring). Tried against a real local
  `.db` file on this machine and it decoded plausible, coherently-scaled
  numbers, but there is no independent ground truth to confirm the field
  mapping is exactly right - treat Antigravity figures as lower-confidence
  than Claude/Codex. Raises a clear, actionable error with manual-fallback
  instructions if neither path yields data. Never attempts to parse a raw
  .pb file.

Usage
-----
  python .agents/scripts/extract_agent_telemetry.py --runtime claude \\
      --session-id <session-uuid> --out tmp/telemetry/telemetry.json

  python .agents/scripts/extract_agent_telemetry.py --runtime codex \\
      --session-id <session-uuid> --out tmp/telemetry/telemetry.json

  python .agents/scripts/extract_agent_telemetry.py --runtime antigravity \\
      --session-id <session-id> --out tmp/telemetry/telemetry.json
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _empty_totals() -> dict:
    return {
        "actual_input_tokens": 0,
        "actual_output_tokens": 0,
        "actual_cache_creation_tokens": 0,
        "actual_cache_read_tokens": 0,
        "actual_reasoning_tokens": 0,
    }


class ClaudeAdapter:
    """Parses ~/.claude/projects/<project-hash>/<session-uuid>.jsonl - the
    same log this Claude Code session itself is writing right now."""

    def extract(self, session_id: str, home: Path | None = None) -> dict:
        home = home or Path.home()
        projects_dir = home / ".claude" / "projects"
        if not projects_dir.exists():
            raise FileNotFoundError(f"Claude Code projects directory not found: {projects_dir}")

        log_path = None
        for p in projects_dir.iterdir():
            candidate = p / f"{session_id}.jsonl"
            if candidate.exists():
                log_path = candidate
                break
        if log_path is None:
            raise FileNotFoundError(
                f"No Claude Code JSONL found for session {session_id} under {projects_dir}"
            )

        totals = _empty_totals()
        model_label = ""
        first_ts = ""
        last_ts = ""
        turns = 0
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = entry.get("timestamp")
                if ts:
                    first_ts = first_ts or ts
                    last_ts = ts
                if entry.get("type") != "assistant":
                    continue
                message = entry.get("message", {})
                usage = message.get("usage", {})
                if not usage:
                    continue
                totals["actual_input_tokens"] += usage.get("input_tokens", 0)
                totals["actual_output_tokens"] += usage.get("output_tokens", 0)
                totals["actual_cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
                totals["actual_cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)
                if not model_label and message.get("model"):
                    model_label = str(message["model"])
                turns += 1

        if turns == 0:
            raise ValueError(f"Session {session_id} log found but had no assistant usage entries.")

        if model_label:
            totals["model_label"] = model_label
        if first_ts:
            totals["session_started_at"] = first_ts
        if last_ts:
            totals["session_ended_at"] = last_ts
        totals["extraction_method"] = "claude_log"
        return totals


class CodexAdapter:
    """Parses ~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*-<session-uuid>.jsonl.

    A Codex session can span multiple JSONL files (main run + a
    continuation, e.g. an action-assessment pass). Each file's
    token_count events are INDEPENDENT - they reset at the start of each
    file, not cumulative across the whole session. This uses the LAST
    token_count in each file and SUMS across all files for the session.

    Verified schema (event_msg entries with payload.type=="token_count"):
      payload.info.total_token_usage.{input_tokens,cached_input_tokens,
      output_tokens,reasoning_output_tokens}

    Codex has no cache-write/cache-creation concept distinct from a plain
    cache read - actual_cache_creation_tokens is always 0 for this
    adapter, not a missing/unavailable value.
    """

    def extract(self, session_id: str, home: Path | None = None) -> dict:
        home = home or Path.home()
        logs = self._find_logs(session_id, home)
        if not logs:
            raise FileNotFoundError(
                f"No Codex rollout JSONL for session {session_id}\n"
                f"Searched under: {home / '.codex' / 'sessions'}"
            )

        totals = _empty_totals()
        first_ts = ""
        last_ts = ""
        for log in logs:
            last_count: dict[str, Any] | None = None
            with open(log, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = entry.get("timestamp")
                    if ts:
                        first_ts = first_ts or ts
                        last_ts = ts
                    if entry.get("type") != "event_msg":
                        continue
                    payload = entry.get("payload", {})
                    if payload.get("type") == "token_count":
                        last_count = payload.get("info", {}).get("total_token_usage", {})
            if last_count:
                totals["actual_input_tokens"] += last_count.get("input_tokens", 0)
                totals["actual_output_tokens"] += last_count.get("output_tokens", 0)
                totals["actual_cache_read_tokens"] += last_count.get("cached_input_tokens", 0)
                totals["actual_reasoning_tokens"] += last_count.get("reasoning_output_tokens", 0)

        if not any(totals[k] for k in totals):
            raise ValueError(f"No token_count events found in any Codex file for session {session_id}")

        if first_ts:
            totals["session_started_at"] = first_ts
        if last_ts:
            totals["session_ended_at"] = last_ts
        totals["extraction_method"] = "codex_log"
        return totals

    def _find_logs(self, session_id: str, home: Path) -> list[Path]:
        # The session_id may appear in the filename itself, OR in the
        # session_meta payload of a continuation file started under a
        # different UUID. Strategy: find files whose name contains the
        # UUID, then check sibling files in the same date directory for
        # matching session_meta payloads.
        sid_short = session_id[:8]
        base = home / ".codex" / "sessions"
        direct = sorted(glob.glob(str(base / "**" / f"*{session_id}*.jsonl"), recursive=True))
        if not direct:
            return []

        direct_paths = [Path(p) for p in direct]
        date_dir = direct_paths[0].parent

        siblings = sorted(date_dir.glob("rollout-*.jsonl"))
        matched: list[Path] = list(direct_paths)

        for sib in siblings:
            if sib in matched:
                continue
            try:
                with open(sib, encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        if i > 20:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        p = entry.get("payload", {})
                        sid = p.get("session_id", "")
                        if sid == session_id or sid.startswith(sid_short):
                            matched.append(sib)
                            break
            except (OSError, json.JSONDecodeError):
                pass

        return sorted(matched)


class ClineAdapter:
    """Reads Cline task history from the VSCode extension's global storage.
    Plain JSON read - no subprocess, no binary parsing - the lowest-risk of
    the three new adapters, ported as an optional extra."""

    def _task_history_path(self, appdata: str) -> Path:
        return (
            Path(appdata) / "Code" / "User" / "globalStorage"
            / "saoudrizwan.claude-dev" / "state" / "taskHistory.json"
        )

    def extract(self, session_id: str, appdata: str | None = None) -> dict:
        import os
        appdata = appdata if appdata is not None else os.environ.get("APPDATA", "")
        history_path = self._task_history_path(appdata)
        if not history_path.exists():
            raise FileNotFoundError(f"Cline taskHistory not found: {history_path}")

        with open(history_path, encoding="utf-8") as f:
            history = json.load(f)

        target = str(session_id)
        task = next(
            (t for t in history if str(t.get("id")) == target or str(t.get("ulid")) == target),
            None,
        )
        if not task:
            raise ValueError(
                f"No Cline task found for id={session_id}. "
                f"Available ids: {[str(t.get('id')) for t in history[-5:]]}"
            )

        totals = {
            "actual_input_tokens": task.get("tokensIn", 0),
            "actual_output_tokens": task.get("tokensOut", 0),
            "actual_cache_creation_tokens": task.get("cacheWrites", 0),
            "actual_cache_read_tokens": task.get("cacheReads", 0),
            "actual_reasoning_tokens": 0,
        }
        if task.get("modelId"):
            totals["model_label"] = str(task["modelId"])
        # Cline reports its own already-computed cost - a directly-reported
        # figure, not a pricing-table estimate, so it's safe to pass through.
        if task.get("totalCost") is not None:
            totals["estimated_cost_usd"] = f"{float(task['totalCost']):.6f}"
        if task.get("id"):
            try:
                from datetime import datetime, timezone
                totals["session_started_at"] = datetime.fromtimestamp(
                    int(task["id"]) / 1000, tz=timezone.utc).isoformat()
            except (ValueError, OSError, OverflowError):
                pass
        totals["extraction_method"] = "cline_history"
        return totals


class AntigravityAdapter:
    """Extracts token usage from Google Antigravity.

    Primary: the `agy` CLI (`agy usage --session <id> --json`).
    Fallback: a heuristic scan of the conversation SQLite DB, if one
    exists, for a protobuf-encoded usage submessage - a best-effort field-
    position guess (matches the ERP benchmark skill's verified approach on
    that machine), NOT a documented/verified schema. Never attempts to
    parse a raw .pb file directly (no schema for that at all).

    Raises a clear, actionable RuntimeError with manual-fallback
    instructions when neither path yields data - this is a first-class
    supported outcome for this runtime, not a bug.
    """

    def extract(self, session_id: str, home: Path | None = None) -> dict:
        home = home or Path.home()
        result = self._try_agy_cli(session_id)
        if result:
            return result

        result = self._try_db(session_id, home)
        if result:
            return result

        raise RuntimeError(
            f"Cannot extract Antigravity telemetry for session {session_id!r} automatically.\n"
            "Options:\n"
            "  1. Run: agy usage --session <id> --json (if a working agy CLI is installed)\n"
            f"  2. Check whether {home / '.gemini' / 'antigravity' / 'conversations'}/<id>.db exists\n"
            "  3. Read token counts from the Antigravity sidebar/UI and pass them directly to "
            "finalize_operator_run.py via --actual-input-tokens/--actual-output-tokens/etc., or "
            "write a small JSON file by hand with the actual_* keys and pass it via --telemetry-json.\n"
            "This is a first-class supported outcome, not a workaround - manual entry after reading "
            "the runtime's own usage UI is expected for Antigravity today."
        )

    def _try_agy_cli(self, session_id: str) -> dict | None:
        try:
            result = subprocess.run(
                ["agy", "usage", "--session", session_id, "--json"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                return None
            data = json.loads(result.stdout)
            meta = data.get("usage_metadata", data)
            return {
                "actual_input_tokens": meta.get("prompt_token_count", 0),
                "actual_output_tokens": meta.get("candidates_token_count", 0),
                "actual_cache_read_tokens": meta.get("cached_content_token_count", 0),
                "actual_reasoning_tokens": meta.get("thinking_token_count", 0),
                "actual_cache_creation_tokens": 0,
                "extraction_method": "antigravity_cli",
            }
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    def _try_db(self, session_id: str, home: Path) -> dict | None:
        paths = [
            home / ".gemini" / "antigravity" / "conversations" / f"{session_id}.db",
            home / ".gemini" / "antigravity-ide" / "conversations" / f"{session_id}.db",
        ]
        db_path = next((p for p in paths if p.exists()), None)
        if db_path is None:
            return None

        def decode_varint(data: bytes, pos: int) -> tuple[int, int]:
            val = 0
            shift = 0
            while True:
                b = data[pos]
                pos += 1
                val |= (b & 0x7f) << shift
                if not (b & 0x80):
                    break
                shift += 7
            return val, pos

        def decode_proto(data: bytes, pos: int = 0, end: int | None = None) -> list:
            if end is None:
                end = len(data)
            result = []
            while pos < end:
                try:
                    tag, pos = decode_varint(data, pos)
                except IndexError:
                    break
                field_num = tag >> 3
                wire_type = tag & 0x07
                if wire_type == 0:
                    try:
                        val, pos = decode_varint(data, pos)
                        result.append((field_num, "varint", val))
                    except IndexError:
                        break
                elif wire_type == 1:
                    val = data[pos:pos + 8]
                    pos += 8
                    result.append((field_num, "fixed64", val))
                elif wire_type == 2:
                    try:
                        length, pos = decode_varint(data, pos)
                    except IndexError:
                        break
                    val = data[pos:pos + length]
                    pos += length
                    try:
                        sub_parsed = decode_proto(val)
                        result.append((field_num, "submessage", sub_parsed) if sub_parsed
                                     else (field_num, "bytes", val))
                    except Exception:
                        result.append((field_num, "bytes", val))
                elif wire_type == 5:
                    val = data[pos:pos + 4]
                    pos += 4
                    result.append((field_num, "fixed32", val))
                else:
                    break
            return result

        def find_usage_submessage(parsed: list) -> dict | None:
            local_keys = {fnum for fnum, _wtype, _val in parsed}
            if {1, 2, 3, 5}.issubset(local_keys):
                return {fnum: val for fnum, wtype, val in parsed
                       if wtype in ("varint", "fixed32", "fixed64")}
            for fnum, wtype, val in parsed:
                if wtype == "submessage":
                    res = find_usage_submessage(val)
                    if res:
                        return res
            return None

        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT idx, metadata, step_payload FROM steps ORDER BY idx ASC")
            rows = cur.fetchall()

            totals = _empty_totals()
            has_data = False
            for _idx, metadata, step_payload in rows:
                usage = None
                for blob in (metadata, step_payload):
                    if usage or not blob:
                        continue
                    try:
                        usage = find_usage_submessage(decode_proto(blob))
                    except Exception:
                        usage = None
                if usage:
                    uncached = usage.get(2, 0)
                    cached = usage.get(5, 0)
                    output = usage.get(3, 0)
                    thinking = usage.get(10, 0)
                    if output > 0 or uncached > 0:
                        totals["actual_input_tokens"] += uncached
                        totals["actual_output_tokens"] += output
                        totals["actual_cache_read_tokens"] += cached
                        totals["actual_reasoning_tokens"] += thinking
                        has_data = True
            if has_data:
                totals["extraction_method"] = "antigravity_db"
            return totals if has_data else None
        except Exception:
            return None
        finally:
            if conn is not None:
                conn.close()


ADAPTERS: dict[str, Any] = {
    "claude": ClaudeAdapter(),
    "claude-code": ClaudeAdapter(),
    "claudecode": ClaudeAdapter(),
    "codex": CodexAdapter(),
    "cline": ClineAdapter(),
    "antigravity": AntigravityAdapter(),
}


def extract(runtime: str, session_id: str) -> dict:
    key = runtime.lower().replace(" ", "-")
    adapter = ADAPTERS.get(key)
    if not adapter:
        raise ValueError(f"Unknown runtime {runtime!r}. Supported: {sorted(ADAPTERS)}")
    return adapter.extract(session_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime", required=True, choices=sorted(ADAPTERS))
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--out", help="Write the extracted JSON to this path instead of stdout. "
                                      "Use a tmp/telemetry/ path - never a committed one.")
    args = parser.parse_args()

    try:
        totals = extract(args.runtime, args.session_id)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    payload = json.dumps(totals, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
        print(f"Wrote telemetry to {out_path}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
