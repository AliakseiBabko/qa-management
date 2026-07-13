# Document Contract

Primary final output is a Google Sheet in `20_M2_Project_Management\<Project>`,
with local CSV fallback. Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the QA metrics document family: `project_metrics`
and `qa_process_metrics`. Both live at `20_M2_Project_Management\<Project>\`,
alongside `project_risk`, but they are two separate Sheets with different
owners and different audiences — never merge them into one file.

- **`project_metrics`** — M2-only dashboard for the project, the single
  place to see the whole picture of a project. M2 fills this in; never
  share it with the QA engineers whose data appears in it.
- **`qa_process_metrics`** — project-wide QA-process facts, filled in by
  the project team from their own tools. M2 does not collect this data or
  guess values into it.

## Templates

- `<repo-root>\Templates\метрики_проекта_qa.csv` — `project_metrics` Sheet
  column schema.
- `<repo-root>\Templates\qa_process_metrics.csv` — `qa_process_metrics`
  Sheet column schema.
- `<repo-root>\Templates\метрики_проекта_qa.md` — catalogue covering both
  artifacts and how to choose among their candidate metrics. Derived from
  `00_Source_Docs\M2_project_development_plan` and <Project>'s/<Project>'s
  actual content.
- `<repo-root>\Templates\метрики_qa_по_проекту.csv` / `.md`
  For individual QA metrics inside the project scope.

## Expected Output

One project-level metrics-oriented report format per skill invocation.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>`

## Versioning

- `generate_m2_outputs.py` (see README, "legacy first-pass tools") predates
  this dashboard schema and is not template-aware — it mechanically pulls
  `label: value` bullets from each source document's own Scorecard section.
  Any `project_metrics` content that traces back to that script (rather
  than the current 4-row-type dashboard built via `scaffold_project_dashboard.py`
  and real M2 judgment) is a raw source dump, not a compliant sheet — never
  treat it as already following this schema.
  `sync_m2_source_docs_to_sheets.py` uses this same extraction path for
  `project_metrics` — it only creates the sheet when one doesn't exist yet
  (a rough bootstrap) and never overwrites an existing one, specifically so
  rerunning it can't silently replace a real dashboard with extracted
  fragments again.
- Both `project_metrics` and `qa_process_metrics` are living Sheets,
  updated in place — same as `individual_metrics` and `project_risk`. Do
  not create dated `_vN` files for routine updates.
- `qa_process_metrics` is append-only by calendar month (see its Schema
  section below) — "updated in place" means updating the current month's
  rows, not overwriting prior months.
- Append source traceability to the project `evidence_log`.

## Schema — `project_metrics`

Columns: `Проект`, `Период`, `Метрика`, `Показатель`, `Пояснение`, `Owner`,
`Тренд` — same 7-column shape as `individual_metrics`. `Период` always
filled; `Показатель` is a clean fact/status, never a numeric-score-plus-word
mix; `Owner` always filled; `Пояснение` is achievement+gap prose, never a
raw file path (traceability lives in `evidence_log`).

Row types, all living in this one Sheet:

0. **`Статус проекта`** — one row, `Активен` or `На паузе`. Manual-only:
   no script sets or clears `На паузе`, and there is no scheduled review
   that would — reactivation happens only when M2 explicitly changes it,
   which then flows through `refresh_project_registry.py`'s normal mirror
   on its next run. While `На паузе`: `project_risk`'s `Общий уровень
   риска` stays frozen at its last real value rather than being remapped
   onto the pause (a pause isn't a point on that scale); `qa_process_metrics`
   stops taking new monthly periods (see its Schema section below); and the
   project stays in `_project_registry` (a pause is not the "project
   stopped" case that rule is about). Every project gets this row, default
   `Активен`. See catalogue §1.0.
1. **`Горизонт совместной работы`** — one row. Expected end date of the
   engagement/current phase; where meaningful change could happen
   (contract end, vendor switch, tender). See catalogue §2.1.
2. **`Бизнес-риск продукта клиента (оценка M2)`** — one row, Низкий/
   Средний/Высокий. Risk that the client's own business fails to reach its
   goals and dissolves — independent of our performance (that's
   `project_risk`'s job). See catalogue §2.2.
3. **`Вклад в проект: <Имя>`** — one row per QA on the project, Позитивный/
   Смешанный/Негативный, showing the actual conclusion for that person.
   No aggregated team row — every individual row stays visible at this
   level; aggregation to one worst-case value only happens one level up,
   in `_project_registry`. Moved here from `individual_development_plan`
   because that Doc is visible to the employee it's about. See catalogue
   §2.3.
4. **`Качество QA-процесса`** — one row, Позитивный/Смешанный/Негативный.
   M2's synthesized read of `qa_process_metrics`, not a copy of it. Empty
   until `qa_process_metrics` has real data to read. See catalogue §2.4.

There is no automated `Команда: ...` statistical-rollup row (a mechanical
distribution of Core metrics across the team, e.g. "2/3 Соответствует") —
`rollup_individual_metrics_to_project.py` is deprecated and refuses to
run; `Вклад в проект: <Имя>` gives an actual judgment per person instead
of a mechanical distribution, so do not add rollup-style rows here.

Rows 1-2 and 4 are M2-only judgment. Revenue, client base, and churn are
cited as evidence inside row 2's `Пояснение` when known, not tracked as
separate rows. Rows 1-2 and 4 get a row on every project even when
`Показатель` is empty — the row set stays identical across projects so a
blank cell reads as "not available yet," not "M2 forgot this metric."
`Вклад в проект: <Имя>` rows are the exception — only add a row once
there's an actual conclusion to record for that person.

Removed entirely, and why:
- `Уровень внимания`, `Статус данных` — every row read a constant value,
  carried no information.
- `Следующее действие`, `Комментарии` — belong in
  `project_development_plan`'s Ближайшие шаги/Направления развития.
- Project-level risk-scorecard content (stability, delivery predictability,
  process maturity, overall risk level) — that's `project_risk`'s job;
  keeping it here duplicated it with a worse format.
- `Cost of quality avoided` — not something M2 estimates from outside; it
  depends on real `qa_process_metrics` data (Defect Escape Rate, Defect
  Density, Mean Time to Fix), and becomes a narrative M2 builds from that
  data for client conversations, not a row here.
- "Продуктовые метрики использования" (Activation Rate/MAU/DAU/...) — too
  granular for general business-context understanding; add point-in-time
  only if a specific project's QA scope actually covers that flow.

## Schema — `qa_process_metrics`

Same 7 columns. Append-only by calendar month: dedup on (Проект, Метрика,
Период); re-running for the same month updates that month's row, a new
month adds new rows. `Тренд` starts as a simple month-over-month
comparison once two months of history exist.

If `project_metrics`'s `Статус проекта` row is `На паузе`, freeze this
Sheet entirely — don't add a new `Период`, don't chase the team for data
covering paused months. Resume once `Статус проекта` goes back to
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

Full candidate metric list and per-metric collection instructions:
`Templates\метрики_проекта_qa.md` §3.

## Source Priority

1. Existing project metrics workbooks or extracted project metrics Markdown.
2. Business/project goals, client expectations, and success criteria.
3. Project development plans and project risk summaries.
4. Individual QA metrics when they explain project capacity, coverage, QA speed, defect quality, automation contribution, stakeholder visibility, blockers, overload, continuity, or role value.
5. Workbook status rows and 1to1 analysis findings.

## Source Extraction Strategy

- Before reading an original DOCX/XLSX file, check whether the source was already extracted under `G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD\<Project>\`.
- For extracted workbooks, start from the workbook JSON file. Use sheet names, row counts, column counts, `document_role`, source path, and preview rows to decide which CSV sheet files matter.
- For extracted workbooks with many sheets or many rows, do not read all CSV files end to end. First inspect the JSON manifest, then search candidate CSV files for metric labels, dates, scorecard sections, owners, blockers, trend words, or project-specific keywords.
- For extracted DOCX files, search headings and key phrases before reading long sections. Prefer sections that mention metrics, scorecard, plan progress, QA process, automation, manual testing, feedback, risks, blockers, owners, and review dates.
- If no suitable extract exists, run `.agents/scripts/qa_source_extract.py` with the source root and an output root under `G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`. Do not re-extract into a non-empty folder without `--overwrite` unless the user explicitly wants to refresh the extract.
- Preserve extracted source paths in `evidence_log`, not in `Пояснение` — neither table has an evidence/path column.
- If an extracted file is stale compared with the source document modified date, say so and decide whether the stale extract is sufficient or a refreshed extract is needed.

## Normalization

- Keep one metric per row.
- Each metric should answer a concrete management question and connect to project/business/QA value.
- Every candidate metric from the catalog is a row in `qa_process_metrics`
  for every project, always — do not select a "compact" subset and drop
  the rest (see `m2-role-rules.md`, Template Consistency). A metric that
  isn't currently a priority for this project, or has no data yet, still
  gets a row: leave `Показатель` blank and say why in `Пояснение`
  (including "not a priority for this project because ..." as a valid
  reason). Do not duplicate another reporting stream's row unless the
  duplicate answers a different management question.
- Validate metric fit before using standard delivery metrics. Closed tasks, moved tasks, story points, or sprint throughput are weak primary metrics when scope changes constantly, task sizes are not comparable, estimates are abstract, or there is no stable release cadence.
- Connect `project_metrics` to individual QA metrics where they materially affect the general project picture — that's exactly what the `Вклад в проект: <Имя>` rows do.
- Do not turn `project_metrics` into a person-performance table beyond the `Вклад в проект` rows it's explicitly designed to hold. Each person's conclusion must separate personal contribution from project/system constraints such as stream differences, seniority, access, scope, deadlines, requirements quality, and process maturity.

## Candidate Metric Catalog (`qa_process_metrics`)

Use this as a menu, not as a required checklist. Select metrics by project context, client pain, available evidence, and what decision the metric will support. Full definitions and "where to find it" guidance: `Templates\метрики_проекта_qa.md` §3.

### Project improvement / plan progress

- Progress against the project development plan: planned actions completed, accepted by project stakeholders, blocked, or postponed.
- Automation development progress: new automated coverage, stabilized tests, CI/CD/reporting integration, useful automation results for release decisions.
- Risk/problem management: visible project problems identified, owner assigned, mitigation started, current blocker age, next review date.
- Accepted project improvements: process changes, reporting improvements, test management changes, documentation/readiness improvements, stakeholder-approved QA proposals.

### QA process speed and predictability

- QA cycle time for feature/regression/retest flow.
- Time from build readiness to QA result.
- Retest turnaround time.
- Blocker age and environment/data waiting time.
- Deadline fit: testing completed inside agreed window, or reason for miss.

### Automation

- Automation coverage by critical flow/module.
- Number of automated tests added or maintained.
- Automation execution time.
- Pass rate.
- Flaky test count/rate and trend.
- Failed-test triage time.
- CI/CD/report availability and usefulness for release decisions.

### Manual testing

- Manual test coverage by feature, requirement, flow, or risk area.
- Number/scope of tested features per iteration.
- Test execution speed for planned scope.
- Escaped defects / missed bugs by severity.
- Defect quality: duplicates, invalid bugs, not-a-bug, feature requests misclassified as bugs, unclear bug reports.
- Regression readiness and completion for release-critical scope.

### Client/team value and communication

- Stakeholder visibility: which decision-makers or key stakeholders receive QA status, risks, metrics, or proposals.
- Feedback from client, PM, DC, QA Lead, or team; mark whether feedback is direct or indirect.
- Accepted QA recommendations and their project impact.
- QA contribution to project value: reduced risk, faster release decision, better quality signal, improved trust, reduced support/rework.

### Individual-input metrics for project aggregation

Use individual metrics only when they explain project capacity, coverage, or role value. For person-level reporting, use the individual QA metrics skill.

- Tests created/executed by person or stream.
- Testing speed and scope per iteration.
- Deadline fit for assigned QA scope.
- Defect quality and escaped defects connected to the person's scope.
- Stakeholder interaction level and accepted improvements initiated by the person.
- Automation contribution by person or stream: tests added, maintained, stabilized, or connected to reporting/CI.
- Individual blockers, overload, access gaps, or unclear ownership that affect project delivery, QA speed, or continuity.

## Rule

Do not mix project-level and individual-level metrics in one output file
unless the user explicitly asks for a combined document and a combined
template exists. The `Вклад в проект: <Имя>` rows inside `project_metrics`
are the sanctioned exception — they're M2's project-level conclusions
derived from individual data, not raw individual-level rows.
