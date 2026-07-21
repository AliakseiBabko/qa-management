# Document Contract

Primary output for a **regular** report is chat-ready text for the
project's own strategy chat — that's where real weekly reports on these
projects actually get posted (see SKILL.md, Destination). A saved Google
Doc in `20_M2_Project_Management\<Project>\private\status_reports` (local Markdown
fallback) is for when the user explicitly wants a kept/archival copy, not
the default path for a routine update. On-demand reports are returned in
chat by default.

## Purpose

Use this reference for short M2 project status reports.

## Expected Output

A short text status update that can be copied into a project, strategy, or management chat.

Use Markdown/plain text. Do not use CSV for this report family.

## Target Folder

For saved regular reports:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\private\status_reports`

Suggested naming pattern:

`status_<Project>_YYYY-MM-DD.md`

For multi-project reports:

`status_multi-project_YYYY-MM-DD.md`

## Versioning

- Save every regular report with project name and report date.
- Do not overwrite an existing final status report by default.
- If the target report already exists, create the next versioned file with a `_vN` suffix before `.md`, for example `_v2` or `_v3`.
- On-demand reports are returned in chat by default. Save them only when the user asks to save, or when the user explicitly calls it a regular report.

## Period Rules

- Resolve relative periods to absolute dates using the current date.
- "Last week" means the previous Monday-Sunday calendar week unless the user gives a different convention.
- "Current status" means status as of the current date, based on the requested period plus the latest available relevant evidence.
- State the period in the title, but match the convention to what the
  report actually is — real reporters use both, don't force one:
  - a period summary (a week/sprint of accumulated work) → a date range,
    e.g. `2026-06-29 - 2026-07-05` or `Статус <Project> за 29.06-05.07`.
  - a point-in-time snapshot (status as of today/this sync) → a single
    date, e.g. `Статус <Project> на 05.07.2026` or
    `Weekly Status Report (05/07/2026)`.

## Source Rules

- Start from evidence inside the requested period.
- Use older project artifacts only to explain baseline, plan, owner, or unresolved carry-over risk.
- Prefer extracted source files over original DOCX/XLSX when available:
  `G:\My Drive\QA_Management\_System\extracts\source\YYYY-MM-DD\<Project>\...`
- For large extracts, inspect manifests/JSON previews first, then search for relevant dates, project names, status labels, blockers, risks, metrics, owners, and next actions.
- If no suitable extract exists for DOCX/XLSX, run `.agents/scripts/qa_source_extract.py` before reading the source directly.
- Keep evidence traceable internally, but do not clutter the chat-ready status with source paths unless the user asks for evidence.

## Content Rules

Include only sections supported by evidence:

1. `Done / changed`
2. `Metrics / quality`
3. `Risks / blockers`
4. `Feedback / communication`
5. `Next steps`
6. `Help needed`
7. `Расширение / Upsell` — an actual diagnostic signal (see
   `presale-upsell-rules.md`, Diagnostic Markers) or a real conversation/
   pitch already in motion (POC proposed, pilot period discussed, a
   specific service from the menu raised). Include the status of any
   active pitch (raised informally / POC proposed / pilot in progress /
   client decision pending). Omit the section entirely rather than
   filling it with generic upsell language when there's no real signal
   this period.

For a project with more than one QA, structure the report per-person/
per-stream instead of one flat set of these sections (see SKILL.md, Chat
Text Shape) — real multi-person reports on this team (e.g. one person
across Payments/Credit Card/Mobile streams on one project; another across
BA/UI-UX/Engineering/QA streams on a different project) break down by
stream before anything cross-cutting. A flat report across several
unrelated people's work reads
as muddled and buries who owns what.

Keep each section short:

- one to three bullets per section
- concrete facts, owners, dates, and next actions where known
- no long background narrative

## M2 Focus

A project status report should show:

- project movement since the previous report
- quality and QA-process signal
- risk/blocker movement
- plan progress
- stakeholder/client communication
- staffing or continuity issues when they affect project delivery
- expansion/upsell opportunity, when a real one exists (see
  `presale-upsell-rules.md`)
- next management action

## Missing Evidence

If data for the requested period is missing, write a short status anyway only if there is enough reliable context. Add a brief line such as:

`Data note: no fresh project metrics/status rows found for the period; status is based on latest available risk/plan evidence.`

Do not fill gaps with assumptions.

## Language

Use Russian by default for business-facing status text unless the user asks for another language. Preserve normal English project terms and metric names when they are part of the working vocabulary.
