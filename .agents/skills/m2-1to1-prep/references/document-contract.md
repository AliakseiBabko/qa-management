# Document Contract — M2 1to1 Prep

Scope: Role-specific M2 1:1 question-prep output structure and source prioritization.

This skill adapts the shared framework in `../../1to1-prep-core/references/prep-core-rules.md` for M2 project management.

## Purpose

Use this reference for M2's pre-1to1 question-prep output.

## Expected Output

Primary output is chat-ready Markdown text, structured as:

```text
1to1 prep — <Person> (<Project>), <date if given>

Метрики/факты:
- ...

Развитие:
- ...

Проект (только если применимо):
- ...
```

Omit any section with nothing in it rather than leaving it with a placeholder line.

## Versioning & Storage

- Transient chat text by default; no persistent file is created.
- If the user asks to save the prep, write it as a Google Doc named `1to1_prep_<YYYY-MM-DD>` in `20_M2_Project_Management\<Project>\private\people\<Person>\`. Do not overwrite a prior date's prep.
- Non-mutation: Do not write prep questions into `individual_development_plan`, `individual_metrics`, or `project_risk` — those get updated from what the 1to1 actually produces.

## Source Priority

See `../SKILL.md`, Source Order:
1. `individual_metrics` (blank rows and workload caveats)
2. `individual_development_plan` (open items and next steps)
3. `project_metrics` (`Вклад в проект: <Person>` caveats and provisional ratings)
4. `m2_input` (unanswered preliminary analysis questions answerable by this engineer)
5. `individual_risk` (private risk signals reframed neutrally; never quoted)
6. `qa_process_metrics` (blank process metrics owned by this person)
7. Newcomer support checks (`../../qa-management-roles/references/newcomer-support-rules.md`)

## Rule

Do not produce project-level status or risk content here. If the user actually wants project-status prep instead of person-1to1 prep, redirect to `m2-project-status-report` or `m2-project-risk-report`.
