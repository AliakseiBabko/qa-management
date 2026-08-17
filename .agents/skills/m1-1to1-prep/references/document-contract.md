# Document Contract — M1 1to1 Prep

Scope: Role-specific M1 1:1 question-prep output structure and source prioritization.

This skill adapts the shared framework in `../../1to1-prep-core/references/prep-core-rules.md` for M1 people management.

## Purpose

Use this reference for M1's pre-1to1 question-prep output.

## Expected Output

Primary output is chat-ready Markdown text, structured as:

```text
1to1 prep — <Person>, <date if given>

Открытые риски:
- ...

Открытые OKR:
- ...

Последующие шаги:
- ...
```

Omit any section with nothing in it rather than leaving it with a placeholder line.

## Versioning & Storage

- Transient chat text by default; no persistent file is created.
- If the user asks to save the prep, write it as a Google Doc named `1to1_prep_<YYYY-MM-DD>` in `10_M1_People_Management\<Person>\` (create the person subfolder if needed). Do not overwrite a prior date's prep.
- Non-mutation: Do not write into the people-risk Sheet, the person's 1to1 Sheet, their OKR Doc, or `_m1_timeline` from this skill — those get updated from what the 1to1 actually produces.

## Source Priority

See `../SKILL.md`, Source Order:
1. `светофор_рисков.csv` (primary driver: `Риск с нашей стороны`, `Риск со стороны сотрудника`)
2. `План действий` from the same risk row
3. Most recent row's `Assign`/`Action plan` in `10_M1_People_Management\<Person>\1to1`
4. Overdue Key Results in current-cycle OKR Doc (`m1-individual-development-plan`)
5. Open rows in `_m1_timeline` (`m1-timeline`)
6. Recent `qa-1to1-analysis` transcript findings
7. `_project_registry` Column 9 (`People requiring attention` / `[Stale: review required]` candidate signals)
8. Newcomer support checks (`../../qa-management-roles/references/newcomer-support-rules.md`)
9. Off-scope stress follow-ups (`../../qa-management-roles/references/off-scope-stress-rules.md`)

## Rule

Do not produce project-level content here. If the user actually wants project-focused 1to1 prep instead, redirect to `m2-1to1-prep`.
