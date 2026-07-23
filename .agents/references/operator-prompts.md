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

## Routine Shortcut Contract

When a prompt says "process", "audit", "clean up", or "close out", the
agent must follow the repository's current scripts, skills, and
state-machine contracts from `AGENTS.md`/`README.md` without the prompt
restating every step. In particular:

- Use `dashboard`/`guide`/`classify`/`pack`/`recommend-next` as the
  read-only entry points when they fit the task.
- If `guide`/`pack` reports an intentional pre-processing source-hash
  mismatch, use `refresh-source-hash <run-id>` before `start`.
- Load the owning skill(s) for the selected source type and follow their
  workflow, quality gate, and lane-boundary rules.
- Close queue-backed intake runs through the explicit workflow:
  `record-analysis`, per-scope `record-apply`, `resolve-edge`,
  `archive-source`, mirror snapshot, `complete`, and the mandatory
  `completed_run_review` telemetry row.
- For no-queue passes, record the mandatory `agent-sessions.csv` row
  instead of pretending a `completed_run_review` row exists.
- Inspect the mirror changed-files list for unrelated Drive drift before
  treating the pass as done.

These steps are not copied into every prompt below; they are inherited by
reference. If a prompt conflicts with the repository contract, the
repository contract wins.

## Process the next Project Knowledge source for `<Project>`

> Process the next Project Knowledge source for `<Project>`. Use
> `recommend-next --project <Project> --lane project_knowledge` to choose
> a candidate, read the source before `start`, classify from content, and
> follow the Routine Shortcut Contract.

## Process this specific source: `<path or filename>`

> Process `00_Inbox/<Project>/<file>` as the next source (Project
> Knowledge or M1/M2, whichever the content indicates). Classify from
> content, not filename, and follow the Routine Shortcut Contract. [any
> focus/context notes]

## Process this Project Knowledge document for `<Project>`

> Process `00_Inbox/<Project>/<file>` as a Project Knowledge source.
> Confirm the exact source_type from content, update the durable knowledge
> base and QA docs only where the source changes them, and follow the
> Routine Shortcut Contract. [any focus/context notes]

## Answer the M2 gate for `<Project>`

> Run `gates --project <Project>`, read the pending round's questions,
> and record my answer(s) as an `m2_conversation` pass. Follow the
> Routine Shortcut Contract for no-queue/rollup telemetry and snapshot
> verification.

## I edited an inbox transcript to add speaker names/details

> I manually added speaker names/emails/person-card details to
> `00_Inbox/<Project>/<file>` after it was scanned, so its recorded
> `Source hash` no longer matches. Before processing, run
> `refresh-source-hash <run-id>` to reconcile the hash explicitly (it only
> touches `Source hash` + an audit note + `Last mutation`, and refuses
> anything past a pre-processing state or outside `00_Inbox`) - do not
> hand-edit the queue row, and do not assume the mismatch away.

## Search project knowledge for `<topic>`

> Search `30_Project_Knowledge/<Project>/` for "`<topic>`" and summarize
> what's already captured, including any open questions.

## Clean up 00_Inbox (excluding `<lane-in-progress-folder>`)

> Run a controlled cleanup audit for `00_Inbox`, excluding `<folder>`.
> Report before moving anything; only move terminal, evidence-backed
> files. Follow the Routine Shortcut Contract; cleanup is not business
> intake.

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
