# M2 QA Process Metrics Schema

Scope: `qa_process_metrics` Sheet schema, Core (6-metric) discipline, and source priority for QA process metrics.

## Schema — `qa_process_metrics`

Same 7 columns. Append-only by calendar month: dedup on (Проект, Метрика,
Период); re-running for the same month updates that month's row, a new
month adds new rows. `Тренд` starts as a simple month-over-month
comparison once two months of history exist.

If `project_metrics`'s `Статус проекта` row is `Не активен`, freeze this
Sheet entirely — don't add a new `Период`, don't chase the team for data
covering inactive months. Resume once `Статус проекта` goes back to
`Активен`. This is different from the 2+ month uncollectable-metric rule
below (that's about one metric not fitting the project; this is about the
whole process being on hold).

When creating this Sheet, leave every `Показатель` empty but **write a
real `Пояснение` for every row** — what the metric means, why it matters
on this specific project, and where to actually find the data (Jira/CI
dashboard/TestRail/other TMS, or an explicit "no tool yet" when that's the
truth) — tailored to what's already known about the project's tooling
from its source docs, not generic boilerplate. Without this, whoever the
Sheet gets shared with has no way to know what's being asked of them.

`Период` is always the last completed calendar month, stated as such
(e.g. "июнь 2026"), not "date filled in" — same rule on every project so
periods are comparable.

If a metric can't be collected for 2+ months running, remove it from the
Sheet entirely rather than leaving a chronically empty row — a single
month's gap is normal, a repeated one means the metric doesn't fit this
project's available tooling.

`Owner` should be a named person, not a generic "QA team" — if the
project has more than one QA, split rows across actual names by who has
access/role fit; seeing your own name in a row is what actually gets it
filled in.

Full Core + Extended metric list and per-metric collection instructions:
`Templates\метрики_проекта_qa.md` §2 (fixed a stale §3 cross-reference
here — §3 is `_project_registry`, not this catalog).

## Source Priority

1. Existing project metrics workbooks or extracted project metrics Markdown.
2. Business/project goals, client expectations, and success criteria.
3. Project development plans and project risk summaries.
4. Individual QA metrics when they explain project capacity, coverage, QA speed, defect quality, automation contribution, stakeholder visibility, blockers, overload, continuity, or role value.
5. Workbook status rows and 1to1 analysis findings.

## Normalization

- Keep one metric per row.
- Each metric should answer a concrete management question and connect to project/business/QA value.
- `qa_process_metrics` has two tiers, not one flat catalog (changed
  2026-07-17 — the old "every candidate is a mandatory row" rule produced
  15+ rows per project, most permanently blank, which real project
  feedback (<Project>, see `Templates\метрики_проекта_qa.md` §2 History)
  showed teams can't realistically fill):
  - **Core (6 metrics)** — always a row on every project, same
    blank-with-reason discipline as everything else under Template
    Consistency (see `m2-role/m2-metrics-calibration.md`). Full list and collection method:
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
  - **Extended catalog** — optional, menu not checklist. See
    `extended-metrics-catalog.md` — load it only when the project already
    has a working data source for one of those metrics.
- Validate metric fit before using standard delivery metrics. Closed tasks, moved tasks, story points, or sprint throughput are weak primary metrics when scope changes constantly, task sizes are not comparable, estimates are abstract, or there is no stable release cadence.
- Connect `project_metrics` to individual QA metrics where they materially affect the general project picture — that's exactly what the `Вклад в проект: <Имя>` rows do.
- Do not turn `project_metrics` into a person-performance table beyond the `Вклад в проект` rows it's explicitly designed to hold. Each person's conclusion must separate personal contribution from project/system constraints such as stream differences, seniority, access, scope, deadlines, requirements quality, and process maturity.
