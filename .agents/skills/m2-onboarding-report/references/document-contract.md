# Document Contract

Primary output is chat-ready text for the project's own strategy chat —
same convention as `m2-project-status-report`'s regular reports. A saved
Google Doc (local Markdown fallback) is only for when the user explicitly
wants a kept/archival copy.

## Purpose

Use this reference for the two onboarding milestone reports: Start report
and Final onboarding report.

## Expected Output

Short chat-ready text, Markdown/plain text. Do not use CSV for this
report family.

## Target Folder

If a copy is saved:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\private\status_reports`

Suggested naming:

`onboarding_start_<Project>_<Person>_YYYY-MM-DD.md`
`onboarding_final_<Project>_<Person>_YYYY-MM-DD.md`

## Versioning

- Do not overwrite an existing saved report by default; add a `_vN`
  suffix if the target file already exists.
- Each report is a one-time event artifact, not a living document — no
  in-place updates once sent, unlike `project_metrics`/`project_risk`.

## Source Rules

- Start report: kickoff notes, Sales handoff, interview notes, the
  onboarding checklist.
- Final report: the closed checklist, prior weekly onboarding-block
  updates, 1:1 notes from the onboarding period, and this project's
  `pk_knowledge_base` (if any) for the technical description.
- Never fabricate a contract term, legend detail, security setup fact, or
  technical-description item — state the gap instead of guessing.

## Missing Evidence

If a required field for either template has no evidence, write the field
as `[нет данных]` or a short explicit gap note rather than omitting the
field silently or inventing a plausible value — both templates are used
as checklists as much as reports, and a silently-dropped field defeats
that.

## Language

Russian by default, same convention as `m2-project-status-report`.
Preserve standard English terms (CI/CD, Acceptance Criteria, etc.) as-is.
