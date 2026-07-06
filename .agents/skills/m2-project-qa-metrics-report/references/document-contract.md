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
2. Project development plans and project risk summaries.
3. Workbook status rows and 1to1 analysis findings.
4. Individual metrics only when project-level metrics are absent.

## Normalization

- Keep one metric per row.
- Use `Все хорошо`, `Пока нормально`, `Обратить внимание`, or `Unknown` for `Уровень внимания` when possible.
- Use `Есть данные`, `Есть данные (частично)`, `Нет данных`, or `N/A` for `Статус данных` when possible.
- Preserve exact dates and source names in `Evidence / источник`.

## Rule

Do not mix project-level and individual-level metrics in one output file unless the user explicitly asks for a combined document and a combined template exists.
