# Operator Telemetry (Phase 11)

Measurement layer for the QA-management operator workflow: does
`dashboard`/`guide`/`classify`/`pack`/`triage`/`search_workspace`/
`show_project_state` actually reduce output size and token usage versus an
older full-read/manual workflow - and, since Phase 13.1's follow-up fixes,
a mandatory closing step for every real pass, not just ad hoc measurement
runs (see AGENTS.md's intake-workflow bullet). Which row is mandatory
depends on whether the pass had a queue `run_id`:

- **Queue-backed intake run** (went through `start`/.../`complete`): record
  one `operator-runs.csv` row after `complete` -
  `measure_operator_outputs.py --case completed_run_review --run-id
  <run-id> --append-csv`.
- **No-queue direct-note or conversational rollup pass** (an M2 answer
  pass, a repo-maintenance fix, a direct owner-note enrichment - anything
  that ends with its own `commit_workspace_state.py` snapshot but never
  had a `run_id` to `start`/`complete`): `completed_run_review` cannot be
  recorded - it requires a `run_id`. Record one `agent-sessions.csv` row
  instead - `record_agent_session.py ... --append-csv` (see "Recording an
  agent session" below). This is the pass-level record for this shape of
  work; an `operator-runs.csv` row here is optional and only measures
  whichever single command you happened to run, never a stand-in for the
  whole pass.

This directory holds the canonical CSVs and run-note template; the
scripts live in `.agents/scripts/` alongside every other pipeline script
(this repo's convention - scripts are not nested under per-topic
subfolders).

## Three CSVs, three different questions

- **`operator-runs.csv`** answers *"how large was this command's output?"*
  - one row per measured read-only command invocation (`measure_operator_outputs.py` / `finalize_operator_run.py`).
- **`agent-sessions.csv`** answers *"how many model tokens did this agent session actually consume?"*
  - one row per recorded agent-runtime session (`record_agent_session.py`).
- **`task-outcomes.csv`** answers *"what derived closure facts and deliverables were accomplished by this pass?"*
  - one row per completed intake run or task (`record_task_outcome.py --from-run <run-id>`).

They are separate on purpose:
1. `extract_agent_telemetry.py` returns a SESSION-WIDE token total that cannot be sliced back into individual command cost.
2. `task-outcomes.csv` records objective derived closure facts (scope updates, cascade edges resolved, source text blob sizes) extracted automatically from machine-readable state (`qa_manage.py review --json`, `_source_text_manifest.json` keyed by `<run_id>:v1`), eliminating manual bookkeeping burden.

### Execution Sequence for Queue-Backed Intake Runs
For every queue-backed intake run, `record_task_outcome.py` is mandatory and runs as the final telemetry step in this exact sequence:
```powershell
# 1. Archive source
python .agents/scripts/qa_manage.py archive-source <run-id>

# 2. Commit workspace mirror state (creates _source_text_manifest.json blob entry <run_id>:v1)
python .agents/scripts/commit_workspace_state.py -m "..."

# 3. Complete intake run
python .agents/scripts/qa_manage.py complete <run-id>

# 4. Record task outcome closure telemetry
python .agents/scripts/record_task_outcome.py --from-run <run-id> --linked-session-run-id <session-row-id> --append-csv
```
## Raw Telemetry vs Authoritative Common-Ground Analytics

`agent-sessions.csv` preserves raw, provider-native telemetry evidence (`actual_input_tokens`, `actual_cache_read_tokens`, `actual_reasoning_tokens`, etc.) without modifying raw provider data at ingestion time.

> [!IMPORTANT]
> **Do NOT compare raw `total_tokens` directly across runtimes (Claude, Antigravity, Codex, Cline, manual)!**
> Raw totals differ wildly because provider logs account for context reuse and KV prompt caching differently. Always use `.agents/scripts/summarize_agent_telemetry.py` as the authoritative layer for cross-runtime comparison.

`summarize_agent_telemetry.py` computes normalized common-ground metrics:

- **Work Done (`work_done_tokens`)**: `actual_input_tokens + actual_output_tokens + actual_reasoning_tokens` — excludes cache-read multiplication; this is the primary metric for fair cross-runtime comparison of generative work done.
- **Context Pressure (`context_pressure_tokens`)**: `actual_input_tokens + actual_cache_read_tokens` — measures total context window accumulation over multi-turn sessions.
- **Billable Estimate (`billable_estimate_usd`)**: Provider-specific financial cost calculated only when `model_label` and pricing are explicitly known; returns `null` / `N/A` otherwise to prevent cost invention.

### Key Data Interpretation Principles
1. **Claude Cache-Read Multiplication vs Antigravity/Gemini DB Extraction**: Anthropic prompt caching (`claude_log`) records `cache_read_input_tokens` on every single turn. In long multi-turn sessions, cache-read tokens accumulate to hundreds of millions or billions of tokens; they represent context window re-reads and must not be confused with fresh input tokens or new work done. Antigravity SQLite DB extraction maps uncached prompt tokens to `actual_input_tokens` and cached tokens separately to `actual_cache_read_tokens` (`medium` confidence).
2. **Cumulative Session Snapshots**: `agent-sessions.csv` preserves historical cumulative session snapshots for multi-pass runs sharing the same `session_id`. Do not sum duplicate `session_id` rows directly; `summarize_agent_telemetry.py`'s default mode (`deduplicated_latest`) selects the latest snapshot per session for deduplicated totals. Pass `--include-snapshots` only for debugging.
3. **User-Configured Default Model Labels**: When `model_label` is omitted during session recording, default labels are automatically assigned by runtime (`antigravity` → `gemini-3.6-flash-medium`, `claude`/`claude-code` → `claude-sonnet-5-medium`, `codex` → `codex-5.5-medium`). These reflect the user's default runtime configuration.

## Directory layout

```
.agents/telemetry/
  README.md                 this file
  operator-runs.csv         command-footprint rows (one per measured command run)
  agent-sessions.csv        session-level token-usage rows (one per recorded session)
  templates/
    operator-run-note.md    run-note template (committed structure only, never filled-in content)

.agents/scripts/
  operator_telemetry_common.py   shared schema for BOTH CSVs, case catalog,
                                  append/validate/diff-guard helpers (generic
                                  internals, thin CSV-specific wrappers)
  measure_operator_outputs.py    run one read-only case, measure it, optionally append a row
  finalize_operator_run.py       append one enriched operator-runs.csv row (manual
                                  token telemetry, baseline ratio)
  check_operator_csv.py          validate either CSV / diff-guard a specific row's append
                                  (--sessions selects agent-sessions.csv)
  extract_agent_telemetry.py     best-effort actual-token extraction from local agent-runtime logs
                                  (Claude Code, Codex, Cline, Antigravity - see below)
  record_agent_session.py        append one agent-sessions.csv row from extracted
                                  or manually-entered session telemetry

tmp/telemetry/               gitignored - local-only working space
  <run_id>.md                 run notes written by measure_operator_outputs.py
  <run_id>.json                measured row, if --keep-raw / --json was used
  *.raw.txt                    raw stdout, only if --keep-raw was passed
  telemetry.json                extracted session totals, written by extract_agent_telemetry.py
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
(for an `operator-runs.csv` row) or `record_agent_session.py --manual
--actual-input-tokens ...` (for a session row) - either is a first-class
supported path, not a fallback of last resort. `actual_*` token fields
stay blank only when extraction was never run or no reliable telemetry
source exists for that session - never invented.

Manual `record_agent_session.py --manual` rows must include at least one
`--actual-*-tokens` value; otherwise the script refuses to append a row
with no token data. CLI runtime aliases are normalized before writing:
for example `--runtime claude-code` reads through the Claude adapter but
persists `runtime=claude`. Historical rows written before this
normalization may still contain `claude-code` and remain valid for
validation.

## Recording an agent session

```sh
python .agents/scripts/record_agent_session.py \
    --runtime claude --session-id <session-id> \
    --model-label claude-sonnet-5 \
    --objective "project knowledge source processing" \
    --linked-operator-run-ids <op-run-id-1>,<op-run-id-2> \
    --append-csv

# Manual entry when automatic extraction isn't available for this runtime/session
python .agents/scripts/record_agent_session.py \
    --runtime antigravity --session-id <session-id> --manual \
    --actual-input-tokens 12000 --actual-output-tokens 3400 \
    --confidence manual --objective "..." --append-csv

# Dry run - extract/compute and print, write nothing
python .agents/scripts/record_agent_session.py \
    --runtime claude --session-id <session-id> --objective "..." --dry-run
```

`confidence` defaults from `extraction_method` (override with
`--confidence`): `claude_log`/`codex_log`/`cline_history`/`antigravity_cli`
→ `high`; `antigravity_db` (the heuristic SQLite fallback, no authoritative
schema) → `medium`; manual entry → `manual` (a 4th confidence value,
deliberately distinct from high/medium/low - see
`operator_telemetry_common.VALID_CONFIDENCE`).

A `--linked-operator-run-ids` entry that isn't actually in
`operator-runs.csv` is a **warning, not a failure** - linking is
informational cross-referencing, not a structural guarantee, and a typo
shouldn't block recording real session telemetry. The row is still
appended; the warning prints to stderr.

`total_tokens` sums the five `actual_*` fields the same way as
`operator-runs.csv`. `estimated_cost_usd` prefers a runtime-REPORTED cost
(e.g. Cline's own `totalCost`, passed straight through) over a
pricing-table estimate; an unrecognized `model_label` yields a blank cost,
never a failure - same contract as `finalize_operator_run.py`.

## Validating the CSVs

```sh
python .agents/scripts/check_operator_csv.py
python .agents/scripts/check_operator_csv.py --diff-guard --run-id <run_id>

python .agents/scripts/check_operator_csv.py --sessions
python .agents/scripts/check_operator_csv.py --sessions --diff-guard --session-run-id <session_run_id>
```

## Rules

1. `case_id`/`command_name` must come from the catalog in
   `operator_telemetry_common.py` - do not hand-invent a new case without
   adding it there first.
2. Only read-only commands may be measured; `measure_operator_outputs.py`
   refuses to run any argv containing a `qa_manage.py` mutating verb.
3. Append one row per completed measurement/session only - never rewrite an
   existing row, in either CSV. `finalize_operator_run.py`,
   `record_agent_session.py`, and `check_operator_csv.py [--sessions]
   --diff-guard` all enforce this. In particular: **never backfill an
   existing `operator-runs.csv` row's `actual_*` fields from a
   multi-purpose agent session** - several rows commonly share one long
   session, and a session's cumulative total cannot be honestly
   attributed back to any single command within it (this is exactly why
   `agent-sessions.csv` exists as its own table - see "Two CSVs" above).
4. Real names/projects/output text never go in either CSV, run notes
   template, or any committed file under this directory - only under
   gitignored `tmp/telemetry/`. No raw agent/session logs are ever stored
   in the repo - `extract_agent_telemetry.py --out` writes only small
   numeric-summary JSON, conventionally under `tmp/telemetry/`.
5. Every real pass records one mandatory closing telemetry row (see
   AGENTS.md's intake-workflow bullet) - not optional instrumentation -
   and WHICH CSV depends on whether the pass had a queue `run_id`:
   - Queue-backed intake run → one `operator-runs.csv` row
     (`completed_run_review`, tied to that `run_id`).
   - No-queue direct-note/conversational rollup pass (no `run_id` to tie
     `completed_run_review` to) → one `agent-sessions.csv` row
     (`record_agent_session.py`) instead. An `operator-runs.csv` row is
     optional here and measures only whichever single command you ran,
     never a substitute for the session-level row.
   Never invent actual token numbers to fill either row faster: leave
   `actual_*` token fields blank unless you have real agent-log data for
   that pass (`extract_agent_telemetry.py` or manual entry from the
   runtime's own reporting) - the deterministic byte/char/token estimate
   columns on `operator-runs.csv` rows are always populated regardless.
