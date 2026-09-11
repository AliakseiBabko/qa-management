# M2 QA Process Metrics Schema

Scope: `qa_process_metrics` Sheet schema, the three-tier row discipline (Baseline 3 / Core 6 / Extended), the sprint-per-column layout, and source priority for QA process metrics.

## Schema — `qa_process_metrics`

**Wide layout: three fixed columns, then one column per sprint** (changed
2026-09-09). Until then this was a long 7-column table with a `Период`
column and one row per (metric, period), so a single metric's history was
scattered down the sheet as unrelated-looking rows, and the one reading
this artifact exists to support (did this number move?) was the one it
couldn't give. The columns now are:

`Метрика`, `Пояснение`, `Owner`, `<спринт 1>`, `<спринт 2>`, ...

- **Row identity is `Метрика` alone.** The rows are fixed and few: 3
  Baseline, up to 6 Core, plus whatever Extended rows the project's
  tooling actually supports. The sheet grows sideways, never downward.
- **A new sprint is a new column appended on the right**, in sprint
  order, never inserted out of order. Nothing earlier is overwritten;
  re-running for a sprint that already has a column updates that
  column's cells. This replaces the old append-a-row dedup on (Проект,
  Метрика, Период) — the dedup key is now (Метрика, sprint column).
- **The column header is the sprint id with its dates**, short form:
  `2026-S14 (19.08-01.09)`. Its canonical long form is
  `2026-S14 (2026-08-19..2026-09-01)`, and both come from the `Ритм
  спринтов` row in `project_metrics`, which is still required before the
  first sprint column can be written.
- **No `Проект` column.** The Sheet lives in one project's folder and
  carries the project in its filename when published to the department
  folder; repeating the same project name down every row of a wide table
  is noise.
- **No `Период` column.** The column header is the period.
- **No `Тренд` column.** Reading a row left to right *is* the trend, and
  a verdict column that has to be recomputed on every update is a
  maintenance cost with no reader. The trend discipline itself survives
  as a reading rule, below.
- **Group label rows** carry a bracketed label in `Метрика` and nothing
  else, in this fixed order: `[Базовые метрики: каждый спринт,
  обязательны на любом проекте]`, `[Автоматизация: заводится, если на
  проекте есть автотесты]`, `[Дефекты]`. Baseline is always first —
  those three rows are the ones every project can fill, and they belong
  where they get seen, not below a block of automation rows a manual
  project will leave empty.

**Every tier is collected per sprint** (changed 2026-09-09; Core and
Extended used to be collected per calendar month while only Tier 0 was
per sprint). One column per sprint means one cadence for the whole sheet:
Core rows are snapshots or counters (autotest count, pass rate of the
sprint's last run, open-bug count at sprint end, leakage found during the
sprint) and take a sprint boundary as readily as a month boundary. The
monthly unit survives where it belongs, in **reporting**: a sprint
belongs to the calendar month its **end date** falls in, so an M2 monthly
review aggregates whichever sprints closed inside that month (usually
1-3), and one sprint is never split across two months. On a project with
no sprints (`Ритм спринтов = Нет спринтов (Kanban)`), the columns are
calendar months instead, noted in `Пояснение`.

**Trend is read across columns, not stored.** For any numeric row,
compare the latest column against the **rolling average of the previous
three sprints**, not the single previous one, with ±20% as the stable
band — a holiday week or one oversized scope otherwise reads as a real
swing. Below three sprints of history there is no trend to read yet. What
is known about a swing's cause (vacation, scope change, release crunch,
environment downtime) goes in `Пояснение`.

If `project_metrics`'s `Статус проекта` row is `Не активен`, freeze this
Sheet entirely — don't add a new sprint column, don't chase the team for
data covering inactive sprints. Resume once `Статус проекта` goes back to
`Активен`. This is different from the uncollectable-metric rule below
(that's about one metric not fitting the project; this is about the whole
process being on hold).

When creating this Sheet, leave every sprint cell empty but **write a
real `Пояснение` for every row** — what the metric means, why it matters
on this specific project, and where to actually find the data (Jira/CI
dashboard/TestRail/other TMS, or an explicit "no tool yet" when that's the
truth) — tailored to what's already known about the project's tooling
from its source docs, not generic boilerplate. Without this, whoever the
Sheet gets shared with has no way to know what's being asked of them.

A sprint column is never a bare date or "date filled in": it always names
the sprint and its range, from the project's own `Ритм спринтов`. Same
rule on every project so periods stay comparable within a project — Tier
0 values are never compared across projects at all.

If a Tier 1 or Extended metric can't be collected for 3 sprints running,
remove its row entirely rather than leaving a chronically empty one (Tier
0 rows are exempt: they stay, blank with a reason) — a single sprint's
gap is normal, a repeated one means the metric doesn't fit this project's
available tooling.

`Owner` should be a named person, not a generic "QA team" — if the
project has more than one QA, split rows across actual names by who has
access/role fit; seeing your own name in a row is what actually gets it
filled in.

Column schema template: `Templates\qa_process_metrics.csv` (also the CSV
fallback). Full Baseline + Core + Extended metric list and per-metric
collection instructions: `Templates\метрики_проекта_qa.md` §2.

## Source Priority

1. Existing project metrics workbooks or extracted project metrics Markdown.
2. Business/project goals, client expectations, and success criteria.
3. Project development plans and project risk summaries.
4. Individual QA metrics when they explain project capacity, coverage, QA speed, defect quality, automation contribution, stakeholder visibility, blockers, overload, continuity, or role value.
5. Workbook status rows and 1to1 analysis findings.

## Normalization

- Keep one metric per row.
- Each metric should answer a concrete management question and connect to project/business/QA value.
- `qa_process_metrics` has three tiers, not one flat catalog (two tiers
  from 2026-07-17 — the old "every candidate is a mandatory row" rule
  produced 15+ rows per project, most permanently blank, which real
  project feedback (<Project>, see `Templates\метрики_проекта_qa.md` §2
  History) showed teams can't realistically fill; a Baseline tier below
  Core added 2026-09-07, because even the Core 6 assume tooling — a test
  repo, a CI run, a bug tracker — that not every project has, while a
  ticket count and a git log are available everywhere):
  - **Baseline / Tier 0 (3 metrics)** — the unconditional floor,
    never removable and always the top rows: tickets per sprint, story
    points per sprint, and AQA git activity per sprint. Full definitions:
    `Templates\метрики_проекта_qa.md` §2.1. Project-wide sums only; the
    per-person cut of the same three lives in `individual_metrics`. Their
    absolute values are not comparable across projects or people — they
    answer whether this team's own dynamics changed under the same
    parameters, nothing more, and they never become a standalone
    `_project_registry` verdict.
  - **Core / Tier 1 (6 metrics)** — expected wherever the project has any
    source for them, with the same blank-with-reason discipline under
    Template Consistency (see `m2-role/m2-metrics-calibration.md`).
    Downgraded 2026-09-07 from unconditionally mandatory: Tier 0 is now
    the mandatory floor, and the 3-sprints-blank removal rule applies to
    this tier, not to Tier 0. Full list and collection method:
    `Templates\метрики_проекта_qa.md` §2 Core. Two of the six are
    collected by the QA engineer running `Templates\qa_repo_metrics_prompt.md`
    against their own project's test repo with whatever coding agent
    they have access to — not a manual count. One of the six —
    **Production bug leakage (Баги, утекшие в прод)** — is separate from
    the "known open bugs" snapshot row: it captures defects found
    after release/in production/by users/client/business/product owner,
    not the current defect count. Classify each finding where possible
    (QA leakage / requirement-or-product gap / environment-data-config
    issue / known accepted risk / unclear-needs-triage) and record a
    qualitative value with evidence when an exact count isn't known: no
    data / no confirmed leakage / confirmed cases exist, count unknown /
    N confirmed cases. It rolls up into `project_metrics`'s `Качество
    QA-процесса` and `_project_registry` the same as any other Core
    metric — it does not become an `individual_metrics` row unless the
    source directly attributes responsibility to a named person and that
    attribution is evidence-backed (see `m2-role/m2-metrics-attribution.md`, Production Bug
    Leakage Attribution).
  - **Extended / Tier 2 catalog** — optional, menu not checklist. See
    `extended-metrics-catalog.md` — load it only when the project already
    has a working data source for one of those metrics.
- Validate metric fit before using standard delivery metrics. Closed
  tasks, moved tasks, story points, and sprint throughput are weak as
  **level** metrics — an absolute count means nothing when scope changes
  constantly, task sizes are not comparable, estimates are abstract, or
  there is no stable release cadence, and it must never be compared
  across projects or people. They are valid as **trend** metrics inside
  one project's own history, which is exactly the job Tier 0 gives them
  (revised 2026-09-07; the earlier version of this rule read as a blanket
  ban and was used to justify projects with no metrics at all). Keep the
  method of collection fixed once chosen, or the trend is measuring the
  method rather than the work.
- Connect `project_metrics` to individual QA metrics where they materially affect the general project picture — that's exactly what the `Вклад в проект: <Имя>` rows do.
- Do not turn `project_metrics` into a person-performance table beyond the `Вклад в проект` rows it's explicitly designed to hold. Each person's conclusion must separate personal contribution from project/system constraints such as stream differences, seniority, access, scope, deadlines, requirements quality, and process maturity.
