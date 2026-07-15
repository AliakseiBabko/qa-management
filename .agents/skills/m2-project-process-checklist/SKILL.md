---
name: m2-project-process-checklist
description: Create or update the per-project outsource QA process-maturity checklist Google Sheet, with CSV fallback, based on `Templates/аутсорс_чек_лист_qa.csv`. Use when onboarding a new project, doing a periodic process-health check, or deciding whether a missing process element (requirements, QA environment, bug lifecycle, Definition of Done, Quality Gates, etc.) is an acceptable trade-off or a real project risk.
---

# M2 Project Process Checklist

Use this skill for one output family only:

- per-project outsource process-maturity checklist Google Sheet, with CSV fallback

This tracks the 12-category checklist from the internal "QA чек-лист для
аутсорс проектов" article — requirements/docs, roles, infrastructure,
communication, test docs/tooling, quality/test types, dev process, bugs,
regression, releases/iterations, change management, Quality Gates. It is a
living per-project record, kept up to date throughout the engagement, not
a one-time onboarding form.

## Required Start

1. Read `references/document-contract.md`.
2. Read `references/outsource-operating-principles.md` — required before judging any gap, since a missing item is not automatically a risk on an outsource project.
3. Read `../qa-management-roles/references/google-workspace-rules.md`.
4. Read `../qa-management-roles/references/m2-role-rules.md`.
5. Read the project's existing checklist Sheet if one exists, plus `project_risk` and `project_metrics` for context already on record.

## Workflow

1. Use `Templates/аутсорс_чек_лист_qa.csv` as the schema — 22 fixed
   questions across 12 sections. Do not renumber, merge, or drop a
   question even if it looks inapplicable; mark it `Не применимо` with a
   reason instead (same Template Consistency discipline as every other
   schema in this repo — see `m2-role-rules.md`).
2. For each item, fill: `Применимо к проекту`, `Статус` (`Есть` /
   `Отсутствует` / `Частично`), and — for anything not a clean `Есть` — a
   real `Обоснование` (why it's missing/not applicable, not just "N/A").
   Read `outsource-operating-principles.md` before writing this: a gap
   that's a reasonable trade-off under fixed scope/timeline reads
   differently than a gap with no such justification.
3. `Согласовано с М2 и командой` — every exception needs actual sign-off,
   per the source article's own rule ("решение согласуется с М2 и
   командой проекта"). Leave blank and flag it if this hasn't actually
   happened yet — do not mark agreement that didn't occur.
4. Set `Owner` and `Дата` for any item that needs follow-up action, not
   just a status.
5. When a gap is judged a real risk (not an acceptable trade-off per
   `outsource-operating-principles.md`), route it into `project_risk`'s
   `Риск QA process` column (see `m2-project-risk-report`) rather than
   leaving it to live only in this checklist — this Sheet tracks process
   state, `project_risk` tracks what that state means for the engagement.
6. Update the living Sheet in place as project process matures or changes
   — this is not a dated snapshot family (see Versioning in
   document-contract.md).

## Guardrails

- Do not treat every `Отсутствует`/`Не применимо` row as a project risk by
  default — judge it against `outsource-operating-principles.md` first.
- Do not let a checklist gap alone lower an individual's `Вклад в проект`
  judgment — process-maturity gaps are usually project/PM-level, per
  `m2-role-rules.md`'s Вклад в проект Calibration.
- Do not skip a question's `Обоснование` just because the status is "not
  applicable" — every non-`Есть` status needs a stated reason.
- Do not use this Sheet as the QA-process risk assessment itself — that's
  `project_risk`. This Sheet is the evidence; `project_risk` is the
  judgment.
- Do not create a new dated snapshot per review — update the one living
  Sheet in place, same as `project_metrics`'s living-file convention (see
  `google-workspace-rules.md`, M2 Project-Based Layout).
