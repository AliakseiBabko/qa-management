# M2 Individual Risk (private)

Scope: the private `individual_risk` Sheet — when and how to use it,
separate from the shared `individual_metrics`. Load only when actually
writing or updating this Sheet.

`individual_risk` is a second, separate Sheet per person —
`private\people\<Person>\individual_risk`, separated from the
employee-facing `individual_metrics` but never shared with that employee
(see `google-workspace/api-sharing-editing.md`, Sharing Safety). It exists
because M2 sometimes has a real, evidence-based read that isn't ready — or
isn't appropriate — to put in front of the employee: a subjective doubt
about whether an improvement is durable, a concern surfaced by someone
else (a 1:1, a client aside) that hasn't been confirmed enough to act on,
a perspective that conflicts with what's already recorded in the shared
table. This is not a place to invent concerns — every entry still needs
real evidence, same as the shared table; the difference is readiness/
appropriateness to share, not evidence quality.

## Schema And Shape (2026-08-05 redesign)

Same living, one-row-per-person shape as M1's `Светофор рисков`
(`m1-people-risk-report/references/file-contract.md`) and M2's own
`project_metrics`/`project_risk` — **not** an append-only log. A person
gets exactly **one row**, updated in place as the read changes. Do not
append a second row for the same person the way `evidence_log` or a
transcript-derived dated-entry table would — this table's whole point is
"what's the current picture," not a timeline of everything that was ever
said.

Columns (see `Templates\individual_risk.csv`):

- `Проект`
- `Сотрудник`
- `Дата обновления` — ISO `YYYY-MM-DD`, the date this row's content last
  actually changed. Do not touch it when only reading/reviewing.
- `Риск с нашей стороны (мы недовольны)` — Низкий/Средний/Высокий (same
  3-level scale as `project_risk`/`Светофор рисков` — no `Критический`).
  Pair the level with a short direction/trend note in the same cell (e.g.
  `Средний, рост`), matching `Светофор рисков`'s convention.
  Risk that WE are unhappy with something about this person's work/
  situation on the project.
- `Риск со стороны сотрудника (он недоволен)` — same 3-level scale. Risk
  that THEY are unhappy, disengaging, or at risk of leaving/underperforming
  for reasons on their side.
- `Комментарии` — the synthesis: what's actually going on, in enough
  detail that the row is legible months later without re-reading every
  source. This is where multiple perspectives (M2's own read, an
  unconfirmed second-hand signal, the person's own self-report, an HR or
  Sales aside) get combined into one coherent picture — pair each fact
  with its source/confidence when it matters (self-report vs. independently
  confirmed vs. M2's own observation), the same discipline
  `m2-project-risk-report/references/risk-evidence-rules.md` applies to
  `project_risk`'s comments.
- `План действий` — concrete next step(s), not `"следить за ситуацией"`
  with no owner/date.

## Update Discipline

- One row per person, always. Update the existing row's `Дата обновления`,
  risk cells, `Комментарии`, and `План действий` together when new
  evidence changes the picture — never leave `Дата обновления` stale next
  to freshly-changed content, and never bump it without real new content
  (matches `m1-people-risk-report`'s own rule).
- A person with genuinely no signal yet (no 1:1, nothing reported) still
  gets a row with `Проект`/`Сотрудник` filled and everything else blank
  rather than no row at all — same blank-with-reason discipline as every
  other current-state table in this workspace (see
  `m2-role/m2-metrics-calibration.md`, Template Consistency). Do not
  invent a value from nothing.
- Do not feed this table into the automated `project_metrics` rollup
  script — it only reads the shared `individual_metrics` Core set.
  Anything from here that should influence `project_risk` or
  `project_development_plan` goes through the normal `m2_input` two-phase
  gate (see `m2-role/m2-project-rollups.md`, Project-Level Rollups): raise
  it as a preliminary-analysis question, wait for M2's answer, then apply
  it — the same discipline as any other project-level rollup input, not a
  shortcut around it.
- When something recorded here becomes solid enough to share, promote a
  sanitized version of it into `individual_metrics` or
  `individual_development_plan`'s `Фокус развития` — do not just widen
  access to this Sheet.

## History

Named `individual_metrics_internal` before 2026-08-05, with a
`Проект/Сотрудник/Дата/Сторона/Метрика/Показатель/Пояснение/Тренд` schema
mirroring `individual_metrics` plus a `Сторона` column, and an
append-one-row-per-signal discipline. Renamed and reshaped on explicit
user feedback: the append-only log shape read like `evidence_log`, not
like a risk read a manager could scan in one glance the way
`project_risk`/`Светофор рисков` can — multi-perspective content (the
original reason for `Сторона`) still fits, just folded into `Комментарии`
prose (with source attribution per fact) instead of a repeating row key.
