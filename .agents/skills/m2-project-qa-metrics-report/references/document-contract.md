# Document Contract

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

`G:\My Drive\QA_Management\20_M2_Project_Management`

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
4. Workbook status rows and 1to1 analysis findings.
5. Individual metrics only when project-level metrics are absent.

## Normalization

- Keep one metric per row.
- Use `Все хорошо`, `Пока нормально`, `Обратить внимание`, or `Unknown` for `Уровень внимания` when possible.
- Use `Есть данные`, `Есть данные (частично)`, `Нет данных`, or `N/A` for `Статус данных` when possible.
- Preserve exact dates and source names in `Evidence / источник`.
- Each metric should answer a concrete management question and connect to project/business/QA value.
- Validate metric fit before using standard delivery metrics. Closed tasks, moved tasks, story points, or sprint throughput are weak primary metrics when scope changes constantly, task sizes are not comparable, estimates are abstract, or there is no stable release cadence.
- When standard delivery metrics are weak, prefer metrics that answer the real project question: QA value, escaped defects, defect severity, blocker discovery, regression stability, automation usefulness, process maturity, client/team trust, accepted QA improvements, or risk reduction.
- If metrics are missing because the project is in active risk mitigation, onboarding, overload, or instability, set `Статус данных` to `Нет данных` or `Есть данные (частично)`, explain the reason, and put a concrete next collection/review action.
- Do not treat short-term absence of metrics as failure by itself; treat prolonged absence of metrics or feedback on an active project as a visibility risk.

## Rule

Do not mix project-level and individual-level metrics in one output file unless the user explicitly asks for a combined document and a combined template exists.
