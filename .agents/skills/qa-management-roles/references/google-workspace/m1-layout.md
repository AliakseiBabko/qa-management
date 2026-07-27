# M1 Person-Based Layout

Scope: the M1 (`10_M1_People_Management`) folder shape, per-person artifact
locations, and what stays at the workspace root. Load this module for any
skill that creates or updates a final M1 people-management output.

Treat `10_M1_People_Management` as a person-based workspace, mirroring how
`20_M2_Project_Management` is project-based — the M2 layout splits by
project, M1 splits by person. Final per-person M1 outputs go under:

`10_M1_People_Management\<Person>\...`

Standard per-person folder shape:

- `1to1` Google Sheet, CSV fallback `1to1.csv` — see `m1-people-1to1-file`.
  Titled just `1to1`, not `<Person> 1to1` — the person is already the
  enclosing folder name, so repeating it in the file title is redundant
  (same convention as M2's `people\<Person>\shared\individual_metrics`, not
  `<Person> individual_metrics`).
- `OKR к Perfomance review <DD.MM.YY>` Google Doc, one per Performance
  Review cycle, with Markdown fallback — see
  `m1-individual-development-plan`. This is also M1's version of a
  "personal development plan" — there is no separate narrative
  development-plan Doc for M1 team members the way M2 has a distinct
  `individual_development_plan`; the OKR Doc is the one artifact that
  plays both roles here, per the real company OKR process.
- `salary_review_self_feedback_<DD.MM.YY>` Google Doc, when applicable —
  see `salary-review-prep`.
- `1to1_prep_<YYYY-MM-DD>` Google Doc — only when the user explicitly asks
  to save a 1to1 prep; see `m1-1to1-prep`. Not created by default.

What stays at the `10_M1_People_Management` root, not inside any
`<Person>\` subfolder, because it's workspace-wide or about M1 themselves
rather than about one team member:

- `Светофор рисков` — living people-risk traffic-light Sheet covering the
  whole team at once, updated in place (no date in the title; see
  `m1-people-risk-report`).
- `m1_monthly_report_<Manager>_YYYY-MM` — M1's own monthly KPI/bonus
  report, not a per-person artifact (see `m1-monthly-report`).
- `_m1_timeline` — living workspace-wide Sheet of upcoming/overdue events
  across the whole team (see `m1-timeline`). Leading underscore marks it
  as a system/rollup artifact, same convention as `_people_registry`/
  `_project_registry`.
- `_m1_pr_calendar` — PR-only view, mechanically regenerated from
  `_people_registry`'s `Дата трудоустройства`/`Дата последнего PR` by
  `refresh_m1_pr_calendar.py` (see `m1-timeline`,
  `performance-review-rules.md`'s "Deriving the Expected Next PR Window").
  Never hand-edited — same generated-rollup discipline as `_m1_timeline`.
- `_self_review\<M1 name>\` — M1's own Performance Review self-prep, as
  the employee being reviewed by M3, not as the manager running PR for
  their team (see `m-self-review`, `salary-review-prep`). Kept under its
  own `_self_review\` namespace rather than directly as `<M1 name>\` so
  it's never confused with a team member's own folder, even when M1's own
  name would otherwise look like just another person folder at this root.

`find_person_roster()`-style logic (see `scan_m1_events.py`) should
enumerate `<Person>\` subfolders directly, excluding anything starting
with `_` — that's the team roster, not a name parsed out of a Sheet
title.
