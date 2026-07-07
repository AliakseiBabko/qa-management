# Document Contract

Primary final output is a Google Sheet in `20_M2_Project_Management`, with local
CSV fallback. Preserve the CSV template columns as the Sheet schema.

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

## Versioning

- Do not overwrite an existing final project development-plan document by default.
- If the target project/date file already exists, create the next versioned file with a `_vN` suffix before `.csv`, for example `_v2` or `_v3`.
- Update an existing project development-plan document in place only when the user explicitly asks for revision.

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
- Include topology/context initiatives when they are needed for project control: clarify streams, real team size, DC/PM ownership, vendor/intermediary chain, client path, tender/contract horizon, security/location constraints, or feedback route.
- If the project needs better visibility before detailed improvement work is possible, create a visibility initiative with an owner, date, and expected artifact instead of inventing downstream actions.
- If QA value or project-side trust is under question, include an initiative that proves QA business value through metrics, accepted improvements, defect/risk prevention, or client/team feedback.

## Rule

Do not mix project-level and individual-level development plans in one output file unless the user explicitly asks for a combined document and a combined template exists.
