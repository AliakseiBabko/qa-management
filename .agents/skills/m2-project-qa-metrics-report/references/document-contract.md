# Document Contract

Primary final output is a Google Sheet in `20_M2_Project_Management\<Project>`,
with local CSV fallback. Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the QA metrics document family.

## Templates

- `<repo-root>\Templates\метрики_проекта_qa.csv`
  For project-level QA metrics.
- `<repo-root>\Templates\метрики_qa_по_проекту.csv`
  For individual QA metrics inside the project scope.

## Expected Output

One project-level metrics-oriented report format per skill invocation.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>`

Suggested naming pattern:

`метрики_проекта_qa_<Project>_YYYY-MM-DD.csv`

## Versioning

- Do not overwrite an existing final project QA metrics document by default.
- If the target project/date file already exists, create the next versioned file with a `_vN` suffix before `.csv`, for example `_v2` or `_v3`.
- Update an existing project QA metrics document in place only when the user explicitly asks for revision.

## Schema

Use exactly the columns in `Templates\метрики_проекта_qa.csv`:

1. `Проект`
2. `Период`
3. `Метрика`
4. `Показатель / score`
5. `Уровень внимания`
6. `Тренд`
7. `Статус данных`
8. `Evidence / источник`
9. `Owner`
10. `Следующее действие`
11. `Комментарии`

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
- Preserve extracted source paths in `Evidence / источник`, for example `80_Exports/source_extracts/2026-07-06/<Project>/xlsx/Метрики проекта/Метрики проекта__Метрики проекта.csv`.
- If an extracted file is stale compared with the source document modified date, say so and decide whether the stale extract is sufficient or a refreshed extract is needed.

## Normalization

- Keep one metric per row.
- Use `Все хорошо`, `Пока нормально`, `Обратить внимание`, or `Unknown` for `Уровень внимания` when possible.
- Use `Есть данные`, `Есть данные (частично)`, `Нет данных`, or `N/A` for `Статус данных` when possible.
- Preserve exact dates and source names in `Evidence / источник`.
- Each metric should answer a concrete management question and connect to project/business/QA value.
- Prefer a compact project-specific metric set, usually 3-5 metrics, that works for both client/project stakeholders and internal M2 visibility. Do not duplicate another reporting stream unless the duplicate row answers a different management question.
- When the main need is to show how the team is improving the project, use progress against the project development plan as a metric: planned improvement, current state, movement since last review, blocker, accepted result, and next step.
- Validate metric fit before using standard delivery metrics. Closed tasks, moved tasks, story points, or sprint throughput are weak primary metrics when scope changes constantly, task sizes are not comparable, estimates are abstract, or there is no stable release cadence.
- When standard delivery metrics are weak, prefer metrics that answer the real project question: QA value, escaped defects, defect severity, blocker discovery, regression stability, automation usefulness, process maturity, client/team trust, accepted QA improvements, or risk reduction.
- If metrics are missing because the project is in active risk mitigation, onboarding, overload, or instability, set `Статус данных` to `Нет данных` or `Есть данные (частично)`, explain the reason, and put a concrete next collection/review action.
- Do not treat short-term absence of metrics as failure by itself; treat prolonged absence of metrics or feedback on an active project as a visibility risk.
- Connect project metrics to individual QA metrics where they materially affect the general project picture. Use individual signals to explain project capacity, coverage, speed, quality, visibility, risk, and role value.
- Do not turn the project metrics report into a person-performance table. Aggregated project conclusions must separate personal contribution from project/system constraints such as stream differences, seniority, access, scope, deadlines, requirements quality, and process maturity.
- If individual metrics are the main source for a project-level row, state the aggregation basis in `Комментарии` and mark `Статус данных` as `Есть данные (частично)` unless the coverage across people/streams is complete.

## Candidate Metric Catalog

Use this as a menu, not as a required checklist. Select metrics by project context, client pain, available evidence, and what decision the metric will support.

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

Do not mix project-level and individual-level metrics in one output file unless the user explicitly asks for a combined document and a combined template exists.
