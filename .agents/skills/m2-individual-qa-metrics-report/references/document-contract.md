# Document Contract

Primary final output is a Google Sheet in
`20_M2_Project_Management\<Project>\people\<Person>`, with local CSV fallback.
Preserve the CSV template columns as the Sheet schema.

This table is deliberately short and self-explanatory: every row should be
readable on its own, with no column whose meaning needs an explanation
elsewhere. Anything that needs explaining — why a metric matters, what
"attention" means for this person, what to do about a bad number, additional
context — belongs in the individual development plan, not in this table.

## Purpose

Use this reference for the individual QA metrics document family.

## Template

`<repo-root>\Templates\метрики_qa_по_проекту.csv` — Sheet column schema.

`<repo-root>\Templates\метрики_qa_по_проекту.md` — catalog of standard
individual metrics and how to measure each one (quantitative formula or
qualitative 3-level definition).

## Choosing metrics from the catalog

- Collect every Core metric from the catalog wherever it's at all possible.
  The Core set uses the same name and the same calculation method on every
  project and every person — that's what makes people and projects
  comparable. Don't substitute a similar-but-different local metric for a
  Core one without a real reason; if a Core metric genuinely can't be
  collected on this project, skip it rather than replace it with something
  that looks similar but isn't computed the same way.
- Additional (non-Core) metrics: pick from the catalog whatever the project
  actually has data for. Do not invent a unique metric per person.
- If a whole category has nothing collectible on this project, skip the
  category entirely rather than inventing a number to fill it. Do not add a
  row for a metric that has no data source — if it can't be collected, it
  doesn't belong in this table at all, regardless of how relevant it might
  seem.
- Prefer what's already in the tracker/CI without extra manual bookkeeping —
  a metric that needs manual counting every time will not get maintained.
- For quantitative metrics, always state the formula/source in `Пояснение` —
  a number with no explanation of where it came from is not usable.
- Fix definitions up front and do not revise them after the fact (do not
  drop flaky tests from the denominator, do not change the critical-flow
  list retroactively) — otherwise the metric can be gamed.
- Do not use metrics the catalog explicitly excludes: goals mislabeled as
  metrics ("Готовность к следующему scope"), or things nobody could define
  how to measure ("Технический рост", "Проактивность"/"Коммуникация" as a
  bare number, raw test count with no coverage link, unanchored reaction
  time). If one of these matters for the person, it belongs in
  `Фокус развития` in the individual development plan, not as an
  `individual_metrics` row.
- Every row in this table is implicitly worth attention by virtue of being
  here — there is no separate "importance" or "attention level" field, and
  no "not important" metrics belong in this table in the first place. If a
  metric needs a note about why it currently matters more or less, put that
  in the individual development plan.
- Do not put next steps, action items, or free-form commentary in this
  table. Those go in the individual development plan's `План действий` /
  `Фокус развития` sections instead — this table only records what the
  metric is and what it currently shows.

## Expected Output

One individual metrics-oriented report format.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\people\<Person>`

Suggested naming pattern:

`метрики_qa_<Project>_<Person>_YYYY-MM-DD.csv`

## Versioning

- `individual_metrics` is an append-only history of snapshots, not a
  single overwritten row per metric — each sync/update adds the current
  date's rows alongside prior dates rather than replacing them. This is
  what makes `Тренд` meaningful: without kept history there is nothing to
  compare the current value against.
- Deduplicate on (`Проект`, `Сотрудник`, `Дата`, `Метрика`) — re-running on
  the same date updates that date's row in place; a new date adds new rows.
- Append source traceability to the project `evidence_log`.
- If a predecessor's differently-structured metrics data already exists for
  a person when this schema is first applied, preserve it as a same-folder
  copy (e.g. `individual_metrics_predecessor_<date>`) rather than deleting
  it or moving it to the archive — it stays as in-place historical
  reference until there's a reason to archive it properly.

## Scope

- one QA engineer
- inside one project or project-set context

## Schema

Use exactly the columns in `Templates\метрики_qa_по_проекту.csv` — 8 columns,
nothing more:

1. `Проект`
2. `Сотрудник`
3. `Дата` — date of this snapshot (a single date, not a range/period).
4. `Роль / stream` — leave empty when the project has no streams; keep the
   column so the schema stays usable across projects that do have them.
5. `Метрика` — name from the catalog.
6. `Показатель` — the actual fact/count/ratio (e.g. `24 завершённых задачи`,
   `6 багов, 0 невалидных`), not a 1-5 rating.
7. `Пояснение` — not just "where the number came from," but the achievement
   and the gap: what's already working, and specifically what's missing to
   reach a better value. This applies to qualitative Core metrics too, e.g.
   `Соответствие ожиданиям клиента (грейд): Требует поддержки — уверенно
   тестирует новые фичи, но пока не расследует production-инциденты без
   помощи lead'а`. Do not put a raw source file path here; that
   traceability already lives in `evidence_log`. For
   `Соответствие ожиданиям клиента (грейд)` specifically, do not restate the
   `Перформанс` number as the explanation — it's a volume/velocity number,
   not seniority fit; use feedback and task-complexity/autonomy evidence
   instead. For `Обратная связь клиента/команды`, name who the
   feedback is actually from (client vs. team vs. self-report) — do not
   default to "тимлид" on a project that has no team lead role.
   `Вклад в проект` is not a row in this table — it lives in
   `project_metrics` instead, since this Sheet is visible to the employee
   it's about and that conclusion is M2's private judgment.
8. `Тренд` — filled once there is at least one prior date to compare
   against; leave blank on the first-ever snapshot for a metric.

## Internal Variant

`individual_metrics_internal` is a second, separate Sheet per person —
`people\<Person>\individual_metrics_internal`, same folder as the
employee-facing `individual_metrics` but never shared with that employee
(see `google-workspace-rules.md` Sharing Safety). It exists because M2
sometimes has a real, evidence-based read that isn't ready — or isn't
appropriate — to put in front of the employee: a subjective doubt about
whether an improvement is durable, a concern surfaced by someone else (a
1:1, a client aside) that hasn't been confirmed enough to act on, a
perspective that conflicts with what's already recorded in the shared
table. This is not a place to invent concerns — every row still needs real
evidence, same as the shared table; the difference is readiness/
appropriateness to share, not evidence quality.

Schema: same 8 columns as `individual_metrics`, plus one —
`Сторона` inserted after `Дата`: who this read belongs to (`M2`, `M1`,
`клиент`, `команда`, `QA-инженер` for self-report) — because this table
exists specifically to hold multiple, sometimes-disagreeing perspectives
side by side rather than collapsing them into one voice the way the shared
table does.

Same append-only/dedup mechanics as `individual_metrics`
(`Проект`/`Сотрудник`/`Дата`/`Метрика` as the dedup key, now also scoped by
`Сторона` since the same metric can carry different reads from different
sides on the same date).

Do not feed this table into the automated `project_metrics` rollup script —
it only reads the shared `individual_metrics` Core set. Anything from here
that should influence `project_risk` or `project_development_plan` goes
through the normal `m2_input` two-phase gate (see `m2-role-rules.md`
Project-Level Rollups): raise it as a preliminary-analysis question, wait
for M2's answer, then apply it — the same discipline as any other
project-level rollup input, not a shortcut around it.

When something recorded here becomes solid enough to share, promote a
sanitized version of it into `individual_metrics` or
`individual_development_plan`'s `Фокус развития` — do not just widen access
to this Sheet.

## Source Priority

1. Existing individual metrics workbook or extracted individual metrics Markdown.
2. Project goals and expected role/value for the person.
3. Person sheet from the project workbook.
4. Individual development plan when it contains progress or capability evidence.
5. Project-level context only for interpreting the person's role and constraints.

## Normalization

- Validate that the metric reflects the person's real project role and constraints.
- Do not use closed tasks, moved tasks, story points, or sprint throughput as primary person-level metrics when scope, task size, estimates, or release cadence are unstable.
- If the person is constrained by project context, such as vague requirements, missing process, overload, access limits, unclear QA ownership, or senior-level expectations for a junior QA, note that in the individual development plan (not in this table) and choose metrics that separate personal contribution from project constraints.
- Core metrics feed the project-level `project_metrics` rollup automatically (see that skill's contract) precisely because they use a shared name and calculation method — this is the mechanism that connects individual and project metrics, so do not rename or redefine a Core metric locally even if a project-specific variant would read more naturally.
- Keep person-level conclusions scoped to contribution and constraints. Do not imply project-level health from one person unless that person's role or stream materially affects the overall project picture.

## Rule

Use row-level evidence. If a person's work is constrained by project context, that context belongs in the individual development plan, not as a justification for lowering a metric value without support.
