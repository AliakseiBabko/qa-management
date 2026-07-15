# Document Contract

Two output shapes: a dated `критерии_оценки_команды` Google Sheet (CSV
fallback) per PR cycle, and a chat-only self-review prep summary saved as
a Doc only on request.

## Purpose

Use this reference for M1's/M2's own Performance Review self-prep
artifacts — distinct from the team-facing M1 skills (see SKILL.md intro).

## Target Root

This skill covers both M1 and M2 (both are reviewed by M3 on the same
cadence), so the target root depends on which grade is being reviewed:

- M1 → `10_M1_People_Management\_self_review\<M1 name>\`
- M2 → `20_M2_Project_Management\_self_review\<M2 name>\`

Ask if it's ambiguous which grade the user is — do not guess from context
alone, since the two roots differ.

## Template

`<repo-root>\Templates\критерии_оценки_команды.csv`

## Expected Output

### Критерии оценки команды

One dated Google Sheet per PR cycle:

Title: `критерии_оценки_команды_<DD.MM.YY>` (the PR date this scoring is
for, same date format as the OKR Doc title convention in
`m1-individual-development-plan`).

Local CSV fallback naming pattern: `критерии_оценки_команды_<Manager>_<DD.MM.YY>.csv`.

### Self-review prep summary

Chat text, structured as:

```text
Self-review prep — <M1/M2 name>, PR <date if given>

OKR (прошедший цикл):
- ...

Критерии оценки команды: <X>/34 (<Y>%) — <эффективна / не эффективна / не полностью посчитано>

Открытые PGROWTH-таски:
- ...
```

No default persistent artifact for the summary — save as a Doc named
`self_review_prep_<DD.MM.YY>` under the same `_self_review\<Person>\`
folder only if the user explicitly asks.

## Versioning

- `критерии_оценки_команды` is a dated snapshot, one per PR cycle — do not
  update a prior cycle's Sheet in place. This matches how
  `светофор_рисков` snapshots work, and differs from `_m1_timeline`/OKR
  Docs, which are living/updated-in-place.
- If a same-title Sheet already exists for that date (a rerun same day),
  ask before overwriting rather than silently replacing it.

## Schema

Use exactly the columns in `Templates\критерии_оценки_команды.csv`:

1. `#` — metric number (1-17), matches `team-criteria-rules.md`. Never
   renumber.
2. `Метрика` — the metric name, as given in `team-criteria-rules.md`.
3. `Период сбора` — the collection window (3 months unless the metric
   states 6 months).
4. `Ответственный за сбор` — `Лид команды` for every metric except #1
   (`M+1`).
5. `Метод сбора` — as given in `team-criteria-rules.md`; note where this
   repo has partial evidence (project_metrics, _people_registry) vs. where
   the number must come from an external system.
6. `Макс баллов` — fixed per metric (see `team-criteria-rules.md`).
7. `Балл` — the actual score. Blank (not `0`) when unknown.
8. `Комментарий / evidence` — the source of the number (a link, a person's
   name, a project_metrics row reference) — same evidence discipline as
   `evidence_log`.

## Source Priority

1. Existing `критерии_оценки_команды` snapshot from the prior PR cycle —
   for continuity/comparison, not for carrying forward stale numbers.
2. `project_metrics`'s `Вклад в проект` rows (metric 4) and
   `_people_registry`'s `Role`/`Internal rank` (metrics 6, 12) — the only
   metrics with in-repo partial evidence.
3. Explicit numbers the user provides for every other metric.
4. The person's own OKR Doc and PGROWTH task state, for the self-review
   prep summary.

## Rule

Keep this skill scoped to the M-self-review document family only. Do not
use it to draft team members' OKR/1to1/monthly-report content — those stay
in `m1-individual-development-plan`/`m1-1to1-prep`/`m1-monthly-report`.
