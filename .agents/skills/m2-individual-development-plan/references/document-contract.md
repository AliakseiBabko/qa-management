# Document Contract

## Purpose

Use this reference for the individual development-plan document family.

## Template

`<repo-root>\Templates\план_развития_qa_по_проекту.csv`

## Expected Output

One individual development-plan-oriented report format.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management`

Suggested naming pattern:

`план_развития_qa_<Project>_<Person>_YYYY-MM-DD.csv`

## Versioning

- Do not overwrite an existing final individual development-plan document by default.
- If the target project/person/date file already exists, create the next versioned file with a `_vN` suffix before `.csv`, for example `_v2` or `_v3`.
- Update an existing individual development-plan document in place only when the user explicitly asks for revision.

## Scope

- one QA engineer
- inside one project or project-set context

## Schema

Use exactly the columns in `Templates\план_развития_qa_по_проекту.csv`:

1. `Проект`
2. `Сотрудник`
3. `Роль / stream`
4. `Период`
5. `Review cycle`
6. `Цель на период`
7. `Фокус развития`
8. `Почему важно`
9. `Действие сотрудника`
10. `Поддержка менеджера`
11. `Срок`
12. `Критерий успеха`
13. `Текущий прогресс`
14. `Следующий review`
15. `Evidence / источник`

## Source Priority

1. Existing individual development plan.
2. Project goals, business context, and what the project needs from the person.
3. Individual metrics file.
4. Person workbook rows and 1to1 analysis findings.
5. Project development plan only for context.

## Normalization

- Tie each focus item to the project role the person needs to grow into: ownership, visibility, responsibility, authority, trust, client/team entry point, or process/module ownership.
- If project expectations exceed the person's current level, state the project need and manager support explicitly instead of framing the gap only as personal underperformance.
- If the person's value must be demonstrated to defend QA stake, include concrete evidence-producing actions: useful metrics, accepted process proposals, visible risk prevention, automation/reporting usefulness, or client/team feedback.
- If project context blocks progress, such as vague requirements, weak documentation, access/security limits, unstable deadlines, or unclear ownership, put the manager support/escalation in the plan.

## Rule

Keep the plan project-contextual and person-specific. If a focus item is actually a project process initiative, move it to the project development-plan skill.

Each focus item should state what it gives the project/client/business or how it grows the person's project role.
