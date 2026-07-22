# Operator Telemetry (Phase 11)

Measurement layer for the QA-management operator workflow: does
`dashboard`/`guide`/`classify`/`pack`/`triage`/`search_workspace`/
`show_project_state` actually reduce output size and token usage versus an
older full-read/manual workflow - and, since Phase 13.1's follow-up fixes,
a mandatory closing step: **every real intake/rollup pass records one
telemetry row after `complete`/its own mirror snapshot** (see AGENTS.md's
intake-workflow bullet), not just ad hoc measurement runs. This directory
holds the canonical CSV and run-note template; the scripts live in
`.agents/scripts/` alongside every other pipeline script (this repo's
convention - scripts are not nested under per-topic subfolders).

Methodology adapted from the erp-web-tests repo's
`benchmark-playwright-debugging` skill (canonical append-only CSV,
finalizer/extractor split, diff-guarded rewrites, deterministic derived
metrics). The debugging-specific concepts (fix/patch counts, EQA/IRR,
diagnostic profiles, worktree isolation) do not apply here and were not
carried over - this is pure output/token measurement, not a debugging
benchmark.

## Directory layout

```
.agents/telemetry/
  README.md                 this file
  operator-runs.csv         canonical metrics table (one row per measured command run)
  templates/
    operator-run-note.md    run-note template (committed structure only, never filled-in content)

.agents/scripts/
  operator_telemetry_common.py   shared CSV schema, case catalog, append/validate/diff-guard helpers
  measure_operator_outputs.py    run one read-only case, measure it, optionally append a row
  finalize_operator_run.py       append one enriched row (manual token telemetry, baseline ratio)
  check_operator_csv.py          validate the CSV / diff-guard a specific run_id's append
  extract_agent_telemetry.py     best-effort actual-token extraction from local agent-runtime logs
                                  (Claude Code, Codex, Cline, Antigravity - see below)

tmp/telemetry/               gitignored - local-only working space
  <run_id>.md                 run notes written by measure_operator_outputs.py
  <run_id>.json                measured row, if --keep-raw / --json was used
  *.raw.txt                    raw stdout, only if --keep-raw was passed
```

## What the CSV stores - and what it never stores

`operator-runs.csv` stores **counts and redacted labels only**: byte/char
counts, elapsed time, token estimates, enum-valued flags, and a redacted
command label (e.g. `qa_manage.py guide <target> --json` - never the real
run id, project name, or person name). It never stores real command output,
source previews, transcript text, or real names/projects. See
`operator_telemetry_common.is_ascii_safe()` for the structural leak-guard
applied to `command_args_redacted`/`notes`/`notes_file` on every row, and
the module docstring for why this is a backstop rather than the primary
safeguard (the primary safeguard is that `measure_operator_outputs.py`
substitutes a live `--target` value back to its placeholder form before
writing anything to disk).

Any live raw output inspected during measurement goes under `tmp/telemetry/`
(gitignored) - never committed.

## Measurement cases

See `operator_telemetry_common.CASES` for the authoritative catalog:
`dashboard_overview`, `guide_discovered`, `classify_discovered`,
`pack_discovered`, `completed_run_review` (`qa_manage.py review` - the case
to use for the mandatory post-`complete` telemetry row), `triage_overview`,
`triage_one`, `search_current`, `search_history`,
`show_project_state_targeted`, `show_project_state_full_project` (the last
one doubles as the baseline for `guide`/`classify`/`pack`/
`show_project_state_targeted` - the "read the whole project state by hand"
comparison point).

```sh
python .agents/scripts/measure_operator_outputs.py --list
```

## Recording a run

```sh
# Dry run (no subprocess call, nothing written) - always safe
python .agents/scripts/measure_operator_outputs.py --case dashboard_overview --dry-run

# Real run, local note only (tmp/telemetry/, gitignored)
python .agents/scripts/measure_operator_outputs.py --case dashboard_overview \
    --runtime "Claude Code" --model-label claude-sonnet-5

# Real run, also append a redacted row to the committed CSV
python .agents/scripts/measure_operator_outputs.py --case dashboard_overview --append-csv

# Mandatory closing step after a real intake/rollup pass completes and its
# own mirror snapshot is committed - record a review-command measurement
# for that run, tagged with the same run id used elsewhere in the pass
python .agents/scripts/measure_operator_outputs.py --case completed_run_review \
    --target <run-id> --runtime "Claude Code" --model-label claude-sonnet-5 --append-csv

# Enrich with actual token telemetry after the fact - extract_agent_telemetry.py
# writes a small JSON blob (actual_* counts only, never raw log content) that
# finalize_operator_run.py then merges into the row.
python .agents/scripts/extract_agent_telemetry.py --runtime claude \
    --session-id <session-uuid> --out tmp/telemetry/telemetry.json
python .agents/scripts/finalize_operator_run.py --from-json tmp/telemetry/row.json \
    --telemetry-json tmp/telemetry/telemetry.json
```

### Automatic extraction support by runtime

- **claude / claude-code**: reads `~/.claude/projects/<hash>/<session-uuid>.jsonl`
  - the exact log a Claude Code session itself writes. Verified against
  this repo's own sessions.
- **codex**: reads `~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*-<session-uuid>.jsonl`,
  including continuation files linked via `session_meta`, using the last
  `token_count` event per file summed across files. Ported from the
  erp-web-tests benchmark skill's verified logic, and confirmed against a
  real Codex session log on this machine (from other work, not this
  repo's own history) - not just fake-log tests.
- **cline**: reads the VSCode extension's `taskHistory.json` - a plain
  JSON read, lowest-risk of the newly-added adapters.
- **antigravity**: tries the `agy` CLI (`agy usage --session <id> --json`)
  first (no working `agy` CLI is installed on this machine), then a
  best-effort SQLite conversation-DB fallback (a heuristic field-position
  scan, not a documented/verified schema) - tried against a real local
  `.db` file on this machine and it decoded plausible, coherently-scaled
  numbers, but there's no independent ground truth to confirm the field
  mapping is exactly right, so treat Antigravity figures as lower-
  confidence than Claude/Codex. If neither path yields data it raises a
  clear error and falls back to the manual path below - this is a normal,
  expected outcome for Antigravity today, depending on local installation,
  not a bug.

Whenever automatic extraction isn't available for your runtime/session
(unsupported runtime, extraction error, or you'd rather read the
runtime's own usage UI), pass actual token counts manually via
`finalize_operator_run.py --actual-input-tokens ... --actual-output-tokens ...`
- this is a first-class supported path, not a fallback of last resort.
`actual_*` token fields stay blank only when extraction was never run or
no reliable telemetry source exists for that session - never invented.

## Validating the CSV

```sh
python .agents/scripts/check_operator_csv.py
python .agents/scripts/check_operator_csv.py --diff-guard --run-id <run_id>
```

## Rules

1. `case_id`/`command_name` must come from the catalog in
   `operator_telemetry_common.py` - do not hand-invent a new case without
   adding it there first.
2. Only read-only commands may be measured; `measure_operator_outputs.py`
   refuses to run any argv containing a `qa_manage.py` mutating verb.
3. Append one CSV row per completed measurement only - never rewrite an
   existing row. `finalize_operator_run.py` and `check_operator_csv.py
   --diff-guard` both enforce this.
4. Real names/projects/output text never go in the CSV, run notes template,
   or any committed file under this directory - only under gitignored
   `tmp/telemetry/`.
5. Every real intake/rollup pass records one telemetry row after it
   completes (see AGENTS.md's intake-workflow bullet) - this is a mandatory
   closing step, not optional instrumentation. Never invent actual token
   numbers to fill a row faster: leave `actual_*` token fields blank unless
   you have real agent-log data for that pass (`extract_agent_telemetry.py`
   or manual entry from the runtime's own reporting) - the deterministic
   byte/char/token estimate columns are always populated regardless.
