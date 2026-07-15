# Document Contract

Primary output is a Google Doc draft, per PR cycle, with local Markdown
fallback. Drafted by/for the employee, with manager support — same
authorship pattern as OKR.

## Purpose

Use this reference for the salary-review self-feedback document family.

## Template

`<repo-root>\Templates\salary_review_self_feedback.md`

## Target

Depends on whether this is a team-member case or a self case:

- Team member (QA engineer, any grade) → same person folder their OKR Doc
  lives in: `10_M1_People_Management\<Person>\` (M1 team) or the project's
  `people\<Person>\` folder (M2 team, see `google-workspace-rules.md`).
- M1/M2 preparing their own → `_self_review\<Person>\` under whichever
  root matches their own grade (`10_M1_People_Management` for M1,
  `20_M2_Project_Management` for M2) — same root `m-self-review` uses.

Doc title: `salary_review_self_feedback_<DD.MM.YY>` (the PR date, same
convention as the OKR Doc title).

Local Markdown fallback naming pattern: `salary_review_self_feedback_<Person>_<DD.MM.YY>.md`.

## Versioning

- One dated Doc per PR cycle — this is a point-in-time submission, not a
  living document. Do not update a prior cycle's Doc in place.
- If a same-title Doc already exists for that date, ask before overwriting.

## Scope

- one person (team member or M1/M2 themselves)
- one PR cycle

## Source Priority

1. Existing salary-review self-feedback from the prior cycle, for
   continuity (not for carrying forward stale claims).
2. The person's OKR Doc — completed Key Results are the primary evidence
   source for "Рост ценности."
3. `project_metrics`'s `Вклад в проект` row, if the person is on a
   tracked project.
4. The person's `1to1` Sheet, for notable achievements or department
   contributions mentioned there.
5. Explicit input from the person/manager for anything not evidenced in
   this repository (billable hours, AI-assessment status, blocker
   checklist answers).

## Normalization

- Exclude routine, on-level tasks from "Рост ценности" — only what's
  beyond normal duties counts.
- Do not restate OKR content verbatim; summarize what it demonstrates
  about value growth instead.
- Leave a field blank with a stated reason ("not tracked in this repo,
  ask the person/RM") rather than guessing a number.
- The blocker pre-check section must reflect real answers, even negative
  ones — do not soften or omit a real blocker to make the draft look
  cleaner.

## Rule

Keep this skill scoped to salary-review self-feedback only. Do not use it
to draft OKR content, the Критерии оценки команды artifact, or a general
PR summary beyond what salary review specifically requires.
