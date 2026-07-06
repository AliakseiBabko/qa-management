# Document Contract

## Purpose

Use this reference for the individual QA metrics document family.

## Template

`<repo-root>\Templates\метрики_qa_по_проекту.csv`

## Expected Output

One individual metrics-oriented report format.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management`

Suggested naming pattern:

`метрики_qa_<Project>_<Person>_YYYY-MM-DD.csv`

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

## Rule

Use row-level evidence. If a person's work is constrained by project context, state that in `Комментарии` rather than lowering the person-level score without support.
