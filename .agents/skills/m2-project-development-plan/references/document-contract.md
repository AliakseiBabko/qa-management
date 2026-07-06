# Document Contract

## Purpose

Use this reference for the development-plan document family.

## Templates

- `<repo-root>\Templates\план_развития_проекта.csv`
  For project-level development planning.
- `<repo-root>\Templates\план_развития_qa_по_проекту.csv`
  For individual development plans inside the project scope.

## Expected Output

One project-level development-plan-oriented report format per skill invocation.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management`

Suggested naming pattern:

`план_развития_проекта_<Project>_YYYY-MM-DD.csv`

## Schema

Use exactly the columns in `Templates\план_развития_проекта.csv`:

1. `Проект`
2. `Период`
3. `Review cycle`
4. `Краткое резюме`
5. `Текущее состояние`
6. `Фокус / initiative`
7. `Почему важно`
8. `Действие`
9. `Ответственный`
10. `Срок`
11. `Критерий успеха`
12. `Риск если не сделать`
13. `Следующий review`
14. `Evidence / источник`

## Source Priority

1. Existing project development plan.
2. Business/project context, client expectations, strategy-chat statuses, and project goals.
3. Project risk summary.
4. Project metrics.
5. Workbook status/context rows.
6. Individual plans only when they reveal a project-level capability or continuity gap.

## Normalization

- Keep one initiative per row.
- Put repeated executive summary/current-state text in each row only if CSV consumption requires standalone rows; otherwise keep it concise.
- Use exact review dates when provided by the source.
- Each initiative should answer: what project/business problem it solves, what value it brings, how success is measured, and where progress will be synchronized.

## Rule

Do not mix project-level and individual-level development plans in one output file unless the user explicitly asks for a combined document and a combined template exists.
