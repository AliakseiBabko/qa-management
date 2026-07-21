"""Phase 11 operator telemetry: best-effort extraction of actual token usage
from local agent-runtime logs, for use with finalize_operator_run.py
--telemetry-json.

Adapted from the erp-web-tests benchmark-playwright-debugging skill's
scripts/extract_telemetry.py, reduced to what this repo needs: a single
session's summed usage, written as a small JSON blob (never the raw log
content) that finalize_operator_run.py merges into a CSV row's actual_*
token fields.

Supported runtimes
------------------
- Claude Code: reads ~/.claude/projects/<hash>/<session-uuid>.jsonl,
  summing message.usage.{input_tokens,output_tokens,
  cache_creation_input_tokens,cache_read_input_tokens} across all
  type=assistant entries in the session. This is the same log this Claude
  Code session itself is writing.

Documented limitation
----------------------
- Codex and Antigravity session-log locations/formats are runtime-specific
  and were not verified against this repo's actual environment (unlike the
  erp-web-tests benchmark skill, which verified them on that machine). Rather
  than guess at paths that may not match this machine's install, this script
  raises a clear NotImplementedError for those runtimes and points at the
  manual fallback: pass --actual-input-tokens/--actual-output-tokens/etc.
  directly to finalize_operator_run.py, or build a --telemetry-json file by
  hand from whatever the runtime's own UI/CLI reports for that session. This
  does not block Phase 11 - manual token entry is a first-class supported
  path, not a workaround.

Usage
-----
  python .agents/scripts/extract_agent_telemetry.py --runtime claude \\
      --session-id <session-uuid> --out tmp/telemetry/telemetry.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def extract_claude(session_id: str) -> dict:
    projects_dir = Path.home() / ".claude" / "projects"
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

    totals = {
        "actual_input_tokens": 0,
        "actual_output_tokens": 0,
        "actual_cache_creation_tokens": 0,
        "actual_cache_read_tokens": 0,
    }
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
            if entry.get("type") != "assistant":
                continue
            usage = entry.get("message", {}).get("usage", {})
            if not usage:
                continue
            totals["actual_input_tokens"] += usage.get("input_tokens", 0)
            totals["actual_output_tokens"] += usage.get("output_tokens", 0)
            totals["actual_cache_creation_tokens"] += usage.get("cache_creation_input_tokens", 0)
            totals["actual_cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)
            turns += 1

    if turns == 0:
        raise ValueError(f"Session {session_id} log found but had no assistant usage entries.")

    return totals


def extract_unsupported(runtime: str) -> dict:
    raise NotImplementedError(
        f"Automatic telemetry extraction for runtime='{runtime}' is not implemented - its session "
        "log location/format was not verified on this machine (see this script's module docstring). "
        "Use the manual fallback instead: pass --actual-input-tokens/--actual-output-tokens/"
        "--actual-cache-creation-tokens/--actual-cache-read-tokens directly to "
        "finalize_operator_run.py, or write a small JSON file by hand with those four keys and pass "
        "it via --telemetry-json. This is a first-class supported path, not a workaround."
    )


EXTRACTORS = {
    "claude": extract_claude,
    "codex": lambda session_id: extract_unsupported("codex"),
    "antigravity": lambda session_id: extract_unsupported("antigravity"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime", required=True, choices=sorted(EXTRACTORS))
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--out", help="Write the extracted JSON to this path instead of stdout.")
    args = parser.parse_args()

    try:
        totals = EXTRACTORS[args.runtime](args.session_id)
    except (FileNotFoundError, ValueError, NotImplementedError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    payload = json.dumps(totals, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"Wrote telemetry to {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
