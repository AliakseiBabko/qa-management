# Operator Prompts (Phase 15A)

Short, reusable prompts for routine requests, so a session can start with
one line instead of re-deriving the request shape each time. Placeholders
(`<Project>`, `<run-id>`, `<Person>`, `<topic>`, `<path>`) stand in for
real values - never write a real name/project into this committed file,
only into what you type locally.

Each prompt states **who decides what** - a shortcut compresses the
*prompt*, not the *judgment*. `recommend-next`'s ranking is a convenience
shortlist, never a `start` decision - read the source before starting
anything, same as `classify` already requires.

## Process the next Project Knowledge source for `<Project>`

> Run `recommend-next --project <Project> --lane project_knowledge`,
> confirm the top candidate makes sense (read `score_breakdown`, don't
> just trust rank order), then process it end to end: classify from
> content (not filename), `start`, apply the project-knowledge-intake
> skill, and close it out with the existing explicit workflow
> (`record-analysis`/`record-apply`/`resolve-edge`, snapshot, `complete`,
> telemetry).

## Process this specific source: `<path or filename>`

> Process `00_Inbox/<Project>/<file>` as the next source (Project
> Knowledge or M1/M2, whichever the content indicates). Classify from
> content, not filename. [any focus/context notes]

## Answer the M2 gate for `<Project>`

> Run `gates --project <Project>`, read the pending round's questions,
> and record my answer(s) as an `m2_conversation` pass.

## Search project knowledge for `<topic>`

> Search `30_Project_Knowledge/<Project>/` for "`<topic>`" and summarize
> what's already captured, including any open questions.

## Clean up 00_Inbox (excluding `<lane-in-progress-folder>`)

> Run a controlled cleanup audit for `00_Inbox`, excluding `<folder>`.
> Report before moving anything; only move terminal, evidence-backed
> files.

## Run the qa-retro improvement loop

> Run the qa-retro skill's improvement-loop pass against recent pipeline
> work.

## A note on `recommend-next --focus`

`--focus <keyword>[,<keyword>...]` only re-ranks candidates already
matched by `--project`/`--lane` - it never infers a project/person scope
and never changes which rows are eligible. Use it to surface a source
likely to be about a specific topic (e.g. `--focus performance,NFR`)
without it silently widening or narrowing what's actually considered.

## Final closure is still the explicit workflow (for now)

There is no `finish-run` shortcut yet (a later phase) - once a run's
analysis/apply is done and closure is clean, still close it out with the
explicit sequence: `archive-source` (if not already archived), a scoped
or full `commit_workspace_state.py` snapshot, `complete`, then the
mandatory closing telemetry row (`completed_run_review` for a queue-backed
run, or an `agent-sessions.csv` row via `record_agent_session.py` for a
no-queue direct-note/rollup pass - see `.agents/telemetry/README.md`).
