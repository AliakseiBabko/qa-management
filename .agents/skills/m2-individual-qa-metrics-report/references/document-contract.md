# Document Contract

Primary final output is a Google Sheet in
`20_M2_Project_Management\<Project>\people\<Person>`, with local CSV fallback.
Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the individual QA metrics document family.

## Template

`<repo-root>\Templates\метрики_qa_по_проекту.csv`

## Expected Output

One individual metrics-oriented report format.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\people\<Person>`

Suggested naming pattern:

`метрики_qa_<Project>_<Person>_YYYY-MM-DD.csv`

## Versioning

- Use the living project-local person file `individual_metrics` for metric
  snapshots, and append source traceability to the project `evidence_log`.
- Do not overwrite an existing formal dated individual QA metrics document by default.
- If the target project/person/date file already exists, create the next versioned file with a `_vN` suffix before `.csv`, for example `_v2` or `_v3`.
- Update an existing individual QA metrics document in place only when the user explicitly asks for revision.

## Scope

- one QA engineer
- inside one project or project-set context

## Schema

Use exactly the columns in `Templates\метрики_qa_по_проекту.csv`:

1. `Проект`
2. `Сотрудник`
3. `Период`
4. `Роль / stream`
5. `Метрика`
6. `Показатель / score`
7. `Уровень внимания`
8. `Тренд`
9. `Статус данных`
10. `Evidence / источник`
11. `Следующее действие`
12. `Комментарии`

## Source Priority

1. Existing individual metrics workbook or extracted individual metrics Markdown.
2. Project goals and expected role/value for the person.
3. Person sheet from the project workbook.
4. Individual development plan when it contains progress or capability evidence.
5. Project-level context only for interpreting the person's role and constraints.

## Normalization

- Validate that the metric reflects the person's real project role and constraints.
- Do not use closed tasks, moved tasks, story points, or sprint throughput as primary person-level metrics when scope, task size, estimates, or release cadence are unstable.
- If the person is constrained by project context, such as vague requirements, missing process, overload, access limits, unclear QA ownership, or senior-level expectations for a junior QA, state that in `Комментарии` and choose metrics that separate personal contribution from project constraints.
- If metrics are not currently collectible, mark the data status clearly, explain why, and set the next collection/review action instead of inventing a score.
- Mark when an individual metric should feed the project-level metrics view because it affects capacity, coverage, QA cycle time, defect quality, escaped defects, automation contribution, stakeholder visibility, accepted improvements, blockers, overload, or continuity risk.
- Keep person-level conclusions scoped to contribution and constraints. Do not imply project-level health from one person unless that person's role or stream materially affects the overall project picture.

## Rule

Use row-level evidence. If a person's work is constrained by project context, state that in `Комментарии` rather than lowering the person-level score without support.
