# Operator Telemetry (Phase 11)

Measurement layer for the QA-management operator workflow: does
`dashboard`/`guide`/`classify`/`pack`/`triage`/`search_workspace`/
`show_project_state` actually reduce output size and token usage versus an
older full-read/manual workflow - and, since Phase 13.1's follow-up fixes,
a mandatory closing step for every real pass, not just ad hoc measurement
runs (see AGENTS.md's "Start Here" section - this exact cross-reference
went dead once already, in July 2026's AGENTS.md compaction, and
telemetry recording silently stopped for 2+ weeks as a direct result;
if this bullet is ever removed from AGENTS.md again without a
replacement, expect the same silent-stop failure mode, not a harmless
trim). Which row is mandatory depends on whether the pass had a queue
`run_id`:

- **Queue-backed intake run** (went through `start`/.../`complete`): record
  the `operator-runs.csv` `completed_run_review` row, an `agent-sessions.csv`
  row, and a `task-outcomes.csv` row, all cross-linked, after `complete`.
  **Preferred: one command**, `closeout_telemetry.py --run-id <run-id>
  --runtime <runtime> --session-id <session-id> [--model-label <model>]
  [--commit] [--json]` - runs the three underlying scripts in sequence, all
  six validators, and reports every created row id (see "Execution Sequence
  for Queue-Backed Intake Runs" below for the manual step-by-step it
  replaces, still available for anything the wrapper doesn't cover).
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

## This is legacy/local telemetry - ai-telemetry is the central store (Phase 14/15)

`.agents/telemetry/*.csv` (this directory) is qa-management's own
**local** telemetry - it stays exactly as documented above, is not going
away, and nothing in this phase changes how it's read or written.
`C:\Users\User\Documents\ai-telemetry` is a separate, sibling repo that
is now the **central, cross-project canonical store** going forward - it
aggregates telemetry from every AI-agent-assisted project on this
machine (qa-management, price-scrapper, unicard-performance, cbs-devops,
erp-web-tests), not just this one.

**`.agents/telemetry` cannot be removed yet.** Central recording is
opt-in per row: `record_agent_session.py`/`record_task_outcome.py`/
`measure_operator_outputs.py` only dual-write when `--dual-write-central`
is passed (or when called via `closeout_telemetry.py`, which passes it
to all three by default - see below). The local CSVs remain this repo's
own source of truth for everything documented in this file; ai-telemetry
is where that same data ALSO lands, best-effort, for cross-project
analysis.

**How dual-write works:**
- `.agents/scripts/central_telemetry_adapter.py` is a small, fail-soft
  adapter - it calls `ai-telemetry\scripts\record_session.py`/
  `record_task.py`/`record_command_run.py` via subprocess with
  `--project-id qa-management --source-system native` always set, and
  never raises: a missing ai-telemetry checkout, a missing database, or
  any other central-write problem comes back as a warning printed to
  stderr, never a failure of the local closeout that was already written
  by the time the central write is attempted.
- All three local CSVs now have a dual-write path: `agent-sessions.csv`
  -> `sessions`, `task-outcomes.csv` -> `tasks`, `operator-runs.csv` ->
  `command_runs`.
- `record_agent_session.py --dual-write-central`,
  `record_task_outcome.py --dual-write-central`, and
  `measure_operator_outputs.py --dual-write-central` are all opt-in
  (default off) at the individual-script level, so anything that calls
  them without the flag - including the existing automated test suite -
  is completely unaffected.
- `closeout_telemetry.py` (the mandatory queue-backed closeout) passes
  `--dual-write-central` to all three of the scripts it wraps **by
  default**, so a normal `closeout_telemetry.py` run now also
  best-effort-records centrally without you needing to remember an extra
  flag. Pass `--skip-central-write` to opt a single closeout out (e.g. on
  a machine without an ai-telemetry checkout).
- The **no-queue direct-note/conversational-pass path** (calling
  `record_agent_session.py --append-csv` directly, per the bullet list
  above) does NOT dual-write automatically yet - pass
  `--dual-write-central` yourself if you want that pass recorded
  centrally too. Closing this gap (making the no-queue path dual-write by
  default the same way `closeout_telemetry.py` does) is a natural
  follow-up, not done in this phase.
- A dual-written `tasks` row's central `linked_session_row_id` IS
  populated when the corresponding session row was already dual-written
  first (the normal order - `closeout_telemetry.py` and a manual
  step-by-step invocation both record the session before the task): the
  adapter resolves qa-management's own local `linked_session_run_id` to
  ai-telemetry's central `session_row_id` via a targeted read-only query
  (see `central_telemetry_adapter.py`'s `resolve_session_id()`). If no
  matching central session row exists yet (e.g. the session was recorded
  without `--dual-write-central`), the task row is still recorded, just
  without that link, and a generic warning prints - never a hard failure.

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
For every queue-backed intake run, telemetry closeout (`completed_run_review` + an agent-session row + `record_task_outcome.py`) is mandatory and runs as the final step, after `complete`, in this exact sequence:
```powershell
# 1. Archive source
python .agents/scripts/qa_manage.py archive-source <run-id>

# 2. Commit workspace mirror state (creates _source_text_manifest.json blob entry <run_id>:v1)
python .agents/scripts/commit_workspace_state.py -m "..."

# 3. Complete intake run
python .agents/scripts/qa_manage.py complete <run-id>

# 4. Telemetry closeout - preferred: one command
python .agents/scripts/closeout_telemetry.py --run-id <run-id> --runtime <runtime> --session-id <session-id> [--commit]
```
`closeout_telemetry.py` runs `measure_operator_outputs.py --case
completed_run_review`, `record_agent_session.py --from-run`, and
`record_task_outcome.py --from-run --linked-session-run-id` in that order,
then all six validators (`check_operator_csv.py` x3,
`summarize_agent_telemetry.py --json`, `check_sensitive_data.py`,
`git diff --check`), and prints every created row id plus the exact
`git add`/`git commit` command if `--commit` wasn't passed. It refuses to
run at all unless `qa_manage.py review <run-id>` already reports
`completed`, and refuses `--commit` if any validator failed. For a runtime
whose adapter can't derive a task-scoped time window yet (only
Claude/`claude-code` can today - see "Recording an agent session" below),
it records a whole-session `agent-sessions.csv` row instead, with an
explicit warning that it is not task-scoped.

The manual step-4 equivalent, for anything the wrapper doesn't cover:
```powershell
python .agents/scripts/measure_operator_outputs.py --case completed_run_review --run-id <run-id> --append-csv
python .agents/scripts/record_agent_session.py --runtime <runtime> --session-id <session-id> --from-run <run-id> --objective "..." --append-csv
python .agents/scripts/record_task_outcome.py --from-run <run-id> --linked-session-run-id <session-row-id> --append-csv
```
## Raw Telemetry vs Authoritative Common-Ground Analytics

`agent-sessions.csv` preserves raw, provider-native telemetry evidence (`actual_input_tokens`, `actual_cache_read_tokens`, `actual_reasoning_tokens`, etc.) without modifying raw provider data at ingestion time.

> [!IMPORTANT]
> **Do NOT compare raw `total_tokens` directly across runtimes (Claude, Antigravity, Codex, Cline, manual)!**
> Raw totals differ wildly because provider logs account for context reuse and KV prompt caching differently. Always use `.agents/scripts/summarize_agent_telemetry.py` as the authoritative layer for cross-runtime comparison.

`summarize_agent_telemetry.py` prints five sections, ordered by how much
you should trust them for CROSS-RUNTIME comparison (most trustworthy
first):

1. **Task-Outcome Ratios** (`task_outcome_ratios`, recommended layer): cost,
   wall-clock time, and workload counts (docs updated, closure edges
   resolved) PER COMPLETED TASK (a `task-outcomes.csv` row) - `cost_per_task_usd`,
   `wall_time_min_per_task`, `docs_updated_per_task`,
   `closure_edges_resolved_per_task`, `cost_per_source_token_usd`,
   `output_tokens_per_source_token`. These divide numerators/denominators
   that mean the same thing for every provider (money, minutes, a
   completed task) - only computed for a runtime that has both an
   `agent-sessions.csv` session unit and a `task-outcomes.csv` row.
2. **Provider Reporting Mode** (`provider_reporting_mode`, metadata, not a
   metric): a per-runtime table of what `actual_cache_creation_tokens`/
   `actual_cache_read_tokens`/`actual_reasoning_tokens` actually mean for
   that runtime's `extract_agent_telemetry.py` adapter - `not_reported`
   (the provider's own log has no such field at all), `separately_reported`
   (read verbatim from the provider's log), or a heuristic/medium-
   confidence label (Antigravity's DB fallback only). See
   `PROVIDER_REPORTING_MODE` in `summarize_agent_telemetry.py` - read
   directly from each adapter, not guessed.
3. **Common Ground Comparison** (`common_ground`, token-level, SECONDARY to
   #1): `work_done_tokens = actual_input_tokens + actual_output_tokens +
   actual_reasoning_tokens`, `context_pressure_tokens = actual_input_tokens
   + actual_cache_read_tokens`, `billable_estimate_usd`. These still blend
   fields with uneven support across runtimes (see #2) - e.g. Claude never
   reports reasoning tokens, so its `work_done_tokens` is structurally
   lower than a runtime that does, regardless of actual effort. Prefer #1
   or `billable_estimate_usd` alone for cross-runtime comparison; use this
   section only to compare sessions within one runtime.
4. **Provider-Native Totals** (`provider_native_latest_snapshot_totals` /
   `provider_native_all_snapshot_totals`, preserved raw evidence):
   input/cache-creation/cache-read/output/reasoning/total tokens exactly as
   each provider's own log reported them. **Never compare these raw
   `actual_*` columns across runtimes** - see #2 for why a `0` can mean
   either "genuinely zero" or "this provider doesn't report this field."
   Audit/debug and single-runtime trend-watching only.
5. **Telemetry Health & Quality** checks (see below).

### Key Data Interpretation Principles
1. **Provider-native fields are not comparable across runtimes** - not just
   `actual_reasoning_tokens` (Claude never reports it; Codex/Antigravity
   do) but also `actual_cache_creation_tokens` (Antigravity never reports
   it via either extraction path; Claude/Cline do) and `actual_cache_read_tokens`
   (Claude records it on every turn via prompt caching; Antigravity's
   heuristic DB fallback maps a different protobuf field to it at only
   medium confidence). A `0` in one of these columns for one runtime and a
   real number for another does not mean "this runtime did less of that
   kind of work" - it means the two providers' logs don't expose the same
   concepts. See `provider_reporting_mode` above before drawing any
   conclusion from these columns.
2. **Claude Cache-Read Multiplication**: Anthropic prompt caching
   (`claude_log`) records `cache_read_input_tokens` on every single turn.
   In long multi-turn sessions, cache-read tokens accumulate to hundreds of
   millions or billions of tokens; they represent context window re-reads
   and must not be confused with fresh input tokens or new work done.
3. **Cumulative Session Snapshots**: `agent-sessions.csv` preserves
   historical cumulative session snapshots for multi-pass runs sharing the
   same `session_id`. Do not sum duplicate `session_id` rows directly;
   `summarize_agent_telemetry.py`'s default mode (`deduplicated_latest`)
   selects the latest snapshot per session for deduplicated totals. Pass
   `--include-snapshots` only for debugging.
4. **User-Configured Default Model Labels**: When `model_label` is omitted
   during session recording, default labels are automatically assigned by
   runtime (`antigravity` → `gemini-3.6-flash-medium`, `claude`/`claude-code`
   → `claude-sonnet-5-medium`, `codex` → `codex-5.5-medium`). These reflect
   the user's default runtime configuration.

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

# Actual token telemetry goes to agent-sessions.csv, not operator-runs.csv -
# see "Recording an agent session" below. operator-runs.csv carries no
# actual_*/total_tokens/estimated_cost_usd columns (removed - every row
# ever recorded had them blank, and structurally most rows can't honestly
# attribute a shared session's token total back to one command).
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
`record_agent_session.py --manual --actual-input-tokens ...` (for a
session row - `operator-runs.csv` carries no `actual_*` columns at all,
see "Two CSVs" above) - a first-class supported path, not a fallback of
last resort. `actual_*` token fields stay blank only when extraction was
never run or no reliable telemetry source exists for that session -
never invented.

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

`total_tokens` sums the five `actual_*` fields. `estimated_cost_usd` prefers a runtime-REPORTED cost
(e.g. Cline's own `totalCost`, passed straight through) over a
pricing-table estimate; an unrecognized `model_label` yields a blank cost,
never a failure - same contract as `finalize_operator_run.py`.

A non-`--manual` append is **refused** (not silently written) if its
`actual_*` fields are byte-identical to the same `session_id`'s most
recent existing row - nothing new was captured since that snapshot, most
likely because no conversation turns happened between two closeouts run
back-to-back. Pass `--allow-duplicate-snapshot` to write it anyway (e.g.
purely for its own `objective`/`linked_operator_run_ids`). `--manual`
rows are never subject to this check - a manually-entered value is
user-asserted, not re-derived from a log snapshot that could repeat.

## Validating the CSVs

```sh
python .agents/scripts/check_operator_csv.py
python .agents/scripts/check_operator_csv.py --diff-guard --run-id <run_id>

python .agents/scripts/check_operator_csv.py --sessions
python .agents/scripts/check_operator_csv.py --sessions --diff-guard --session-run-id <session_run_id>
```

**Multiple appends in one working tree, no commit needed between them.**
The diff-guard compares the working tree against the last git commit
(`HEAD` by default) and rejects any *removed or modified* row relative to
it, plus requires the target row to actually be present - but it does not
require the target row to be the *only* new row. Closing out several
queue-backed runs (or several no-queue passes) in one session commonly
means appending 2-3 rows to the same CSV before the next commit; each
append's own diff-guard call still passes as long as nothing already-
committed was deleted or changed. You do not need to commit after every
single append just to keep the next one's guard call happy - commit
whenever it's otherwise convenient (end of the pass, end of the session),
not once per row.

## Rules

1. `case_id`/`command_name` must come from the catalog in
   `operator_telemetry_common.py` - do not hand-invent a new case without
   adding it there first.
2. Only read-only commands may be measured; `measure_operator_outputs.py`
   refuses to run any argv containing a `qa_manage.py` mutating verb.
3. Append one row per completed measurement/session only - never rewrite an
   existing row, in either CSV. `finalize_operator_run.py`,
   `record_agent_session.py`, and `check_operator_csv.py [--sessions]
   --diff-guard` all enforce this. `operator-runs.csv` carries no
   `actual_*`/`total_tokens`/`estimated_cost_usd` columns at all
   (removed) precisely because several rows commonly share one long
   session, and a session's cumulative total cannot be honestly
   attributed back to any single command within it - that question
   belongs to `agent-sessions.csv`, its own table, exclusively (see "Two
   CSVs" above).
   **Uncommitted vs. committed rows are not the same case**: a row you just
   appended in the working tree, not yet committed, is still a draft - if a
   field turns out to be objectively wrong (e.g. a `model_label` that
   doesn't match the runtime's own logged model), correct it in place
   before committing, the same way you'd fix a typo before publishing.
   Once a row has been committed, treat it as historical - don't rewrite it
   casually for a later-noticed issue; append a correction/superseding row
   instead (or, for a genuine repair across many rows, a clearly-labeled
   one-off migration pass, not a silent edit).
4. Real names/projects/output text never go in either CSV, run notes
   template, or any committed file under this directory - only under
   gitignored `tmp/telemetry/`. No raw agent/session logs are ever stored
   in the repo - `extract_agent_telemetry.py --out` writes only small
   numeric-summary JSON, conventionally under `tmp/telemetry/`.
5. Every real pass records one mandatory closing telemetry row (see
   AGENTS.md's "Start Here" section) - not optional instrumentation -
   and WHICH CSV depends on whether the pass had a queue `run_id`:
   - Queue-backed intake run → one `operator-runs.csv` row
     (`completed_run_review`, tied to that `run_id`).
   - No-queue direct-note/conversational rollup pass (no `run_id` to tie
     `completed_run_review` to) → one `agent-sessions.csv` row
     (`record_agent_session.py`) instead. An `operator-runs.csv` row is
     optional here and measures only whichever single command you ran,
     never a substitute for the session-level row.
   Never invent actual token numbers to fill an `agent-sessions.csv` row
   faster: leave `actual_*` fields blank unless you have real agent-log
   data for that pass (`extract_agent_telemetry.py` or manual entry from
   the runtime's own reporting) - the deterministic byte/char/token
   estimate columns on `operator-runs.csv` rows are always populated
   regardless (that table has no `actual_*` fields to leave blank in the
   first place).
