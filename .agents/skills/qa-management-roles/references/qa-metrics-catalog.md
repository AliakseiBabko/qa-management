# QA Metrics Catalog

A single map of the QA metrics this workspace collects, across three
tiers. This file does not own any Sheet schema or column definitions —
those live in `Templates\метрики_проекта_qa.md` (project-level:
`project_metrics`, `qa_process_metrics`, `_project_registry`) and
`Templates\метрики_qa_по_проекту.md` (`individual_metrics`). Use this file
to see the whole picture and to decide which tier a given signal belongs
in; use the Templates files for the actual definition, formula, and
"where to find it" instructions before writing a value anywhere.

## Governing Principle

Metrics — Core or optional, project-level or individual — are diagnostic
signals for M2 review, 1:1s, retrospectives, and project-risk decisions.
They are inputs to a judgment M2 makes, not automatic performance
verdicts. See `m2-role/m2-metrics-calibration.md`, Metrics Are Signals, Not Verdicts, for
the full statement of this principle, including:

- never add an optional metric to every project by default — add one only
  when the project already has a recurring data source and there is a
  concrete management question it answers
- if data is missing, record the gap explicitly instead of fabricating or
  silently estimating a value
- RCA (root cause analysis) is required before attributing production
  leakage to a person (see `m2-role/m2-metrics-attribution.md`, Production Bug Leakage
  Attribution)

## 1. Core Minimum Project QA-Process Metrics (mandatory, project-level)

Exactly 6 rows, always present on every project in `qa_process_metrics`
(blank-with-reason when data isn't collected yet — see `m2-role/m2-metrics-calibration.md`,
Template Consistency). Full definitions and collection method:
`Templates\метрики_проекта_qa.md` §2 Core.

- Покрытие (грубая оценка) — automation coverage
- Количество автотестов (тренд) — number of automated tests
- Pass rate последнего прогона
- Ощущение по flaky-тестам
- Снимок открытых/известных багов — known open bugs snapshot
- Production bug leakage (Баги, утекшие в прод)

## 2. Optional Project/Release Quality Metrics (project-level, tooling-gated)

Add a row only when the project already has a real incident-tracking
source (incident tracker, PagerDuty/Opsgenie/Jira Service Management, a
status page, or a genuinely-maintained manual incident log) — never as a
blank placeholder "for later." Full definitions and collection method:
`Templates\метрики_проекта_qa.md` §2 Extended, "Релизы и инциденты".

- Incident-free releases
- Incident rate
- Customer-impacting incidents
- Downtime
- MTTA (Mean Time to Acknowledge)
- MTTR (Mean Time to Restore/Resolve)
- Repeat incident rate
- Reopened incident rate
- Pre-prod vs prod defect ratio
- Weighted production incident score
- Release success thresholds

## 3. Optional Individual QA Contribution Metrics (person-level, tooling-gated)

Add a row only when the project has comparable data for it — same
collection method, same unit, across whoever gets a row. Full definitions
and collection method: `Templates\метрики_qa_по_проекту.md`, "Личный
вклад".

- Test documentation created/updated
- Test cases executed
- Valid bugs raised
- Prod leakage attributable after RCA — note: only once an RCA has
  actually traced the leaked defect to this person with evidence; never
  an automatic personal verdict, and never justified merely by this
  person being the only QA on the project (see `m2-role/m2-metrics-attribution.md`,
  Production Bug Leakage Attribution)

## What This File Is Not

This is not a fourth schema to keep in sync by hand. It does not
redefine a metric's formula, its `Показатель`/`Пояснение` wording, or its
Sheet column — that would create two sources of truth that can drift.
When a metric's definition changes, change it in the owning Templates
file (§2 of `метрики_проекта_qa.md` or the relevant section of
`метрики_qa_по_проекту.md`) and update this file's list only if a metric
is added, removed, or moves tier.
