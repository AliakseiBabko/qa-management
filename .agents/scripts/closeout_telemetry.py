#!/usr/bin/env python3
"""One-command telemetry closeout for a completed queue-backed intake run.

The explicit closing sequence for a queue-backed intake run (Phase 11) is:
1. `measure_operator_outputs.py --case completed_run_review --run-id <id> --append-csv`
2. `record_agent_session.py --from-run <id> --runtime ... --session-id ...`
3. `record_task_outcome.py --from-run <id> --linked-session-run-id <...>`
4. Six validators (check_operator_csv.py x3, summarize_agent_telemetry.py --json,
   check_sensitive_data.py, git diff --check)
5. A commit touching only the three telemetry CSVs.

Doing this by hand every time is exactly the "routine prompt/checklist
burden" AGENTS.md's Routine Shortcut Contract exists to compress. This
script performs the whole sequence as one command, reporting every created
row id and validator result, and only commits when explicitly asked.

Never touches Drive, the intake queue, the private mirror, or any business
document - every step below is either read-only (`qa_manage.py review`,
the validators) or an append to one of the three telemetry CSVs under
`.agents/telemetry/`. The only git operations are `git status --porcelain`,
`git diff --check`, and (with --commit) `git add`/`git commit` restricted to
those same three CSV paths.

Usage
-----
    python .agents/scripts/closeout_telemetry.py \\
        --run-id <run-id> --runtime claude --session-id <session-id> \\
        [--model-label claude-sonnet-5] [--commit] [--json]

Runtime windowing
-----------------
`record_agent_session.py --from-run` only derives a task-scoped time window
for the Claude adapter today (see that script's own docstring). For any
other runtime this script deliberately does NOT pass --from-run - a
whole-session agent-session row is recorded instead, with a loud warning
that its tokens are NOT scoped to this one run. This is a graceful-fallback
choice, not a bug: pretending a whole-session extraction is task-scoped
would be a worse lie than clearly labeling it as a fallback.

Safety
------
- Refuses to run at all if the run isn't `completed` yet (checked via
  `qa_manage.py review <run-id> --json`) - no telemetry row is written for
  an unfinished run.
- Refuses to commit if any validator failed - the change stays uncommitted
  and the exact next command is printed.
- The generic objective/notes text passed to the underlying scripts never
  names a real project, file, or person - see GENERIC_OBJECTIVE below.
  The underlying scripts' own ASCII-safe/email/`--check-registry` leak
  guards still apply on top of that.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent

# Kept generic/public-safe on purpose - never a project name, filename, or
# person - see the module docstring's Safety section.
GENERIC_OBJECTIVE = "queue-backed intake run telemetry closeout"
GENERIC_COMMIT_MESSAGE = (
    "telemetry: closeout rows for a completed queue-backed intake run\n\n"
    "Adds the completed_run_review operator row, an agent-session row, and "
    "a task-outcome row via closeout_telemetry.py, linking all three "
    "together."
)

# The single canonical runtime vocabulary this script accepts - the union
# of what record_agent_session.py's extractor adapters support (the
# strictest/most complete of the three wrapped scripts). Each step below
# maps this down to whatever narrower vocabulary that particular script
# actually accepts.
RUNTIME_CHOICES = ["antigravity", "claude", "claude-code", "claudecode", "cline", "codex", "manual"]

# --from-run task-windowing only works for the Claude adapter today (see
# record_agent_session.py / extract_agent_telemetry.py) - any other runtime
# here gets a whole-session fallback instead, never a silently-wrong
# "windowed" claim.
CLAUDE_RUNTIME_ALIASES = {"claude", "claude-code", "claudecode"}

# record_task_outcome.py's --runtime has no claude-code/claudecode spelling.
TASK_OUTCOME_RUNTIME_MAP = {
    "claude": "claude", "claude-code": "claude", "claudecode": "claude",
    "antigravity": "antigravity", "codex": "codex", "cline": "cline", "manual": "manual",
}

# measure_operator_outputs.py's --runtime is a small, differently-spelled,
# title-cased set with no Cline case at all.
MEASURE_RUNTIME_MAP = {
    "claude": "Claude Code", "claude-code": "Claude Code", "claudecode": "Claude Code",
    "antigravity": "Antigravity", "codex": "Codex",
    "cline": "manual_script", "manual": "manual_script",
}

TELEMETRY_CSV_PATHS = [
    ".agents/telemetry/operator-runs.csv",
    ".agents/telemetry/agent-sessions.csv",
    ".agents/telemetry/task-outcomes.csv",
]


class CloseoutError(RuntimeError):
    """A clean, user-facing refusal or failure - never a bare traceback."""


def canonical_runtime(runtime: str) -> str:
    return runtime.strip().lower().replace(" ", "-")


def run_subprocess(argv: list[str]) -> subprocess.CompletedProcess:
    """The single chokepoint every sibling-script/git call goes through -
    tests mock this one function rather than patching subprocess.run at
    every call site."""
    return subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True)


def parse_json_prefix(text: str) -> dict[str, Any] | None:
    """Parse the first JSON object at the start of `text`, ignoring any
    trailing non-JSON line a script prints after it (e.g. measure_operator_
    outputs.py's own "Appended row to ..." line after its --json blob).
    None if `text` doesn't start with a JSON object at all."""
    try:
        obj, _ = json.JSONDecoder().raw_decode(text)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def check_run_completed(run_id: str) -> None:
    """Refuse early - before any telemetry row is written - unless the
    queue run is actually completed."""
    proc = run_subprocess([sys.executable, str(SCRIPTS_DIR / "qa_manage.py"), "review", run_id, "--json"])
    envelope = parse_json_prefix(proc.stdout) or {}
    if not envelope:
        raise CloseoutError(
            f"Could not read qa_manage.py review {run_id} --json output: "
            f"{(proc.stderr or proc.stdout).strip()}"
        )
    if not envelope.get("ok", False):
        errors = envelope.get("errors") or [(proc.stderr or proc.stdout).strip() or "unknown error"]
        raise CloseoutError(f"qa_manage.py review {run_id} failed: {'; '.join(errors)}")
    status = (envelope.get("data") or {}).get("status", "")
    if status != "completed":
        raise CloseoutError(
            f"Run {run_id} is not completed yet (status={status!r}) - telemetry closeout only runs "
            "for a completed queue-backed run. Finish `qa_manage.py complete <run-id>` first."
        )


def step_operator_run(run_id: str, runtime: str, model_label: str) -> str:
    """Step 1: completed_run_review via measure_operator_outputs.py.
    Returns the created operator-runs.csv run_id."""
    argv = [
        sys.executable, str(SCRIPTS_DIR / "measure_operator_outputs.py"),
        "--case", "completed_run_review", "--run-id", run_id,
        "--runtime", MEASURE_RUNTIME_MAP.get(runtime, "manual_script"),
        "--append-csv", "--json",
    ]
    if model_label:
        argv += ["--model-label", model_label]
    proc = run_subprocess(argv)
    if proc.returncode != 0:
        raise CloseoutError(f"measure_operator_outputs.py failed:\n{(proc.stderr or proc.stdout).strip()}")
    row = parse_json_prefix(proc.stdout)
    if not row or not row.get("run_id"):
        raise CloseoutError(
            f"measure_operator_outputs.py did not report a run_id:\n{proc.stdout}\n{proc.stderr}"
        )
    return str(row["run_id"])


def step_agent_session(run_id: str, runtime: str, session_id: str,
                       model_label: str) -> tuple[str, list[str]]:
    """Step 2: task-windowed (Claude) or whole-session (every other
    runtime) agent-session row via record_agent_session.py. Returns
    (session_run_id, warnings)."""
    warnings: list[str] = []
    windowed = runtime in CLAUDE_RUNTIME_ALIASES
    argv = [
        sys.executable, str(SCRIPTS_DIR / "record_agent_session.py"),
        "--runtime", runtime, "--session-id", session_id,
        "--objective", GENERIC_OBJECTIVE, "--check-registry", "--append-csv",
    ]
    if windowed:
        argv += ["--from-run", run_id]
    else:
        warnings.append(
            f"runtime {runtime!r} does not support --from-run task-windowing yet (only "
            "claude/claude-code/claudecode do) - recorded a WHOLE-SESSION agent-session row instead "
            "of a task-scoped one. Its token counts are NOT scoped to this run alone."
        )
    if model_label:
        argv += ["--model-label", model_label]
    proc = run_subprocess(argv)
    if proc.returncode != 0:
        raise CloseoutError(f"record_agent_session.py failed:\n{(proc.stderr or proc.stdout).strip()}")
    match = re.search(r"session_run_id=(\S+)", proc.stdout)
    if not match:
        raise CloseoutError(
            f"record_agent_session.py did not report a session_run_id:\n{proc.stdout}\n{proc.stderr}"
        )
    return match.group(1), warnings


def step_task_outcome(run_id: str, runtime: str, session_run_id: str) -> str:
    """Step 3: task-outcomes.csv row via record_task_outcome.py."""
    argv = [
        sys.executable, str(SCRIPTS_DIR / "record_task_outcome.py"),
        "--from-run", run_id, "--linked-session-run-id", session_run_id,
        "--runtime", TASK_OUTCOME_RUNTIME_MAP.get(runtime, "manual"),
        "--check-registry", "--append-csv",
    ]
    proc = run_subprocess(argv)
    if proc.returncode != 0:
        raise CloseoutError(f"record_task_outcome.py failed:\n{(proc.stderr or proc.stdout).strip()}")
    match = re.search(r"task_outcome_id=(\S+)", proc.stdout)
    if not match:
        raise CloseoutError(
            f"record_task_outcome.py did not report a task_outcome_id:\n{proc.stdout}\n{proc.stderr}"
        )
    return match.group(1)


def run_validators() -> list[dict[str, Any]]:
    checks = [
        ("check_operator_csv", [sys.executable, str(SCRIPTS_DIR / "check_operator_csv.py")]),
        ("check_operator_csv --sessions",
         [sys.executable, str(SCRIPTS_DIR / "check_operator_csv.py"), "--sessions"]),
        ("check_operator_csv --outcomes",
         [sys.executable, str(SCRIPTS_DIR / "check_operator_csv.py"), "--outcomes"]),
        ("summarize_agent_telemetry --json",
         [sys.executable, str(SCRIPTS_DIR / "summarize_agent_telemetry.py"), "--json"]),
        ("check_sensitive_data", [sys.executable, str(SCRIPTS_DIR / "check_sensitive_data.py")]),
        ("git diff --check", ["git", "diff", "--check"]),
    ]
    results = []
    for name, argv in checks:
        proc = run_subprocess(argv)
        results.append({
            "name": name,
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout.strip().splitlines()[-5:],
            "stderr_tail": proc.stderr.strip().splitlines()[-5:],
        })
    return results


def changed_telemetry_files() -> list[str]:
    proc = run_subprocess(["git", "status", "--porcelain", "--"] + TELEMETRY_CSV_PATHS)
    files = []
    for line in proc.stdout.splitlines():
        # Porcelain short format: two status chars, one space, then the path.
        path = line[3:].strip() if len(line) > 3 else ""
        if path:
            files.append(path)
    return files


def commit_telemetry(files: list[str], message: str) -> str:
    if not files:
        raise CloseoutError("Nothing to commit - no telemetry file changed.")
    add_proc = run_subprocess(["git", "add"] + files)
    if add_proc.returncode != 0:
        raise CloseoutError(f"git add failed:\n{(add_proc.stderr or add_proc.stdout).strip()}")
    commit_proc = run_subprocess(["git", "commit", "-m", message])
    if commit_proc.returncode != 0:
        raise CloseoutError(f"git commit failed:\n{(commit_proc.stderr or commit_proc.stdout).strip()}")
    sha_proc = run_subprocess(["git", "rev-parse", "HEAD"])
    return sha_proc.stdout.strip()


def build_envelope(**overrides: Any) -> dict[str, Any]:
    """A stable, always-the-same-shape result dict regardless of which path
    through main() produced it - a strict JSON envelope, not one whose keys
    vary by outcome."""
    envelope: dict[str, Any] = {
        "ok": False,
        "run_id": None,
        "runtime": None,
        "operator_run_id": None,
        "session_run_id": None,
        "task_outcome_id": None,
        "warnings": [],
        "errors": [],
        "validators": [],
        "validators_ok": None,
        "changed_telemetry_files": [],
        "committed": False,
        "commit_sha": None,
        "next_command": None,
    }
    envelope.update(overrides)
    return envelope


def print_human(envelope: dict[str, Any]) -> None:
    run_id = envelope.get("run_id")
    print(f"Telemetry closeout for {run_id}:")
    # Print whatever row ids were actually created even on failure - a step
    # failing partway through must never hide the rows earlier steps
    # already appended (a human resuming needs to know those exist).
    if envelope.get("operator_run_id"):
        print(f"  operator_run_id: {envelope['operator_run_id']}")
    if envelope.get("session_run_id"):
        print(f"  session_run_id: {envelope['session_run_id']}")
    if envelope.get("task_outcome_id"):
        print(f"  task_outcome_id: {envelope['task_outcome_id']}")
    if envelope["errors"]:
        for err in envelope["errors"]:
            print(f"  ERROR: {err}")
        return
    for warning in envelope["warnings"]:
        print(f"  WARNING: {warning}")
    print("  validators:")
    for v in envelope["validators"]:
        print(f"    {'OK  ' if v['ok'] else 'FAIL'}  {v['name']}")
    print("  changed telemetry files:")
    for f in envelope["changed_telemetry_files"]:
        print(f"    {f}")
    if envelope["committed"]:
        print(f"  committed: {envelope['commit_sha']}")
    elif envelope["next_command"]:
        print(f"  not committed - next command: {envelope['next_command']}")


def build_next_command(files: list[str]) -> str:
    if not files:
        return "(nothing to commit)"
    quoted_files = " ".join(files)
    return f'git add {quoted_files} && git commit -m "telemetry: closeout rows for a completed queue-backed intake run"'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runtime", required=True, choices=RUNTIME_CHOICES)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--model-label", default="")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    runtime = canonical_runtime(args.runtime)

    def emit(envelope: dict[str, Any]) -> int:
        if args.json:
            print(json.dumps(envelope, indent=2))
        else:
            print_human(envelope)
        return 0 if envelope["ok"] else 1

    try:
        check_run_completed(args.run_id)
    except CloseoutError as exc:
        return emit(build_envelope(run_id=args.run_id, runtime=runtime, errors=[str(exc)]))

    # Filled in progressively so a step failing partway through still
    # reports whichever earlier rows actually got created - never lost
    # just because a later step raised (see print_human/build_envelope).
    progress: dict[str, Any] = {"operator_run_id": None, "session_run_id": None, "task_outcome_id": None}
    warnings: list[str] = []
    try:
        progress["operator_run_id"] = step_operator_run(args.run_id, runtime, args.model_label)
        session_run_id, session_warnings = step_agent_session(args.run_id, runtime, args.session_id, args.model_label)
        progress["session_run_id"] = session_run_id
        warnings.extend(session_warnings)
        progress["task_outcome_id"] = step_task_outcome(args.run_id, runtime, session_run_id)
    except CloseoutError as exc:
        return emit(build_envelope(run_id=args.run_id, runtime=runtime, warnings=warnings,
                                   errors=[str(exc)], **progress))
    operator_run_id = progress["operator_run_id"]
    session_run_id = progress["session_run_id"]
    task_outcome_id = progress["task_outcome_id"]

    validators = run_validators()
    validators_ok = all(v["ok"] for v in validators)
    changed_files = changed_telemetry_files()

    commit_sha = None
    next_command = None
    errors: list[str] = []
    if args.commit:
        if not validators_ok:
            errors.append("Refusing --commit: at least one validator failed - see validators above.")
        else:
            try:
                commit_sha = commit_telemetry(changed_files, GENERIC_COMMIT_MESSAGE)
            except CloseoutError as exc:
                errors.append(str(exc))
    if commit_sha is None:
        next_command = build_next_command(changed_files)

    envelope = build_envelope(
        ok=validators_ok and not errors,
        run_id=args.run_id,
        runtime=runtime,
        operator_run_id=operator_run_id,
        session_run_id=session_run_id,
        task_outcome_id=task_outcome_id,
        warnings=warnings,
        errors=errors,
        validators=validators,
        validators_ok=validators_ok,
        changed_telemetry_files=changed_files,
        committed=bool(commit_sha),
        commit_sha=commit_sha,
        next_command=next_command,
    )
    return emit(envelope)


if __name__ == "__main__":
    sys.exit(main())
