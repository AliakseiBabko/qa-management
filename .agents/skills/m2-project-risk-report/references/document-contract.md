# Document Contract

## Purpose

Use this reference for the project-risk document family.

## Template

`<repo-root>\Templates\светофор_рисков_проекта.csv`

## Expected Output

One project-risk traffic-light document per reporting snapshot.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management`

Suggested naming pattern:

`светофор_рисков_проекта_YYYY-MM-DD.csv`

## Schema

Use exactly the columns in `Templates\светофор_рисков_проекта.csv`:

1. `Проект`
2. `Период / snapshot date`
3. `Общий уровень риска`
4. `Риск delivery`
5. `Риск QA process`
6. `Риск staffing / continuity`
7. `Риск communication / client`
8. `Evidence / источники`
9. `Комментарии`
10. `План действий`
11. `Owner`
12. `Следующий review`

## Inputs

- QA 1to1 findings
- project transcripts
- delivery/process notes
- staffing or project context data
- extracted source corpus under `G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`

## Evidence Rules

- Prefer direct project evidence over general impressions.
- Keep people-performance concerns out of the project-risk file unless they create explicit project continuity, delivery, or client risk.
- Put source names or dated meetings in `Evidence / источники`.
- Use `Unknown` for any risk dimension that is not supported by the evidence.
- State why the risk matters and what future harm it can cause.

## Rule

Keep this skill scoped to one project-risk document format only.
