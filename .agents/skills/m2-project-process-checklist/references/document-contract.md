# Document Contract

Primary final output is a living Google Sheet per project in
`20_M2_Project_Management\<Project>`, with local CSV fallback. Preserve
the CSV template rows/columns as the Sheet schema.

## Purpose

Use this reference for the outsource process-maturity checklist document
family: a per-project, ongoing record of which of the 12 process areas
from the "QA чек-лист для аутсорс проектов" article are in place, missing,
or explicitly not applicable, and why.

## Template

`<repo-root>\Templates\аутсорс_чек_лист_qa.csv`

A parallel `.xlsx` copy convention is referenced by the source article
(`90_Storage\Reference\Source_Documents\Аутсорс чек-лист QA.xlsx`) — treat
this repo's CSV/Sheet as the canonical machine-readable version; if a
project already has the `.xlsx` copy filled in locally, transcribe it into
the Sheet rather than maintaining both.

## Expected Output

One `process_checklist` Google Sheet per project (living, not a dated
snapshot).

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>`

Local CSV fallback filename: `process_checklist.csv`.

## Versioning

- Living canonical file: edit rows in place as project process changes
  (a missing item gets set up, an agreed exception changes) rather than
  creating dated copies.
- `scaffold_project_dashboard.py`-style scaffolding, if extended to this
  file, should create an empty checklist (template rows, blank status
  columns) for a project if one doesn't exist yet, and never overwrite an
  existing one.

## Schema

Use exactly the columns in `Templates\аутсорс_чек_лист_qa.csv`:

1. `№` — fixed item number (`1.1`-`12.1`), matching the 12-section
   structure. Never renumber.
2. `Раздел` — the fixed section name (Требования и документация, Роли и
   ответственность, Инфраструктура и окружение, Коммуникация, Тестовая
   документация и инструменты, Качество и виды тестирования, Процессы
   разработки, Баги и дефекты, Регрессионное тестирование, Релизы и
   итерации, Управление изменениями, Quality Gates).
3. `Пункт` — the fixed question text.
4. `Применимо к проекту` — `Да` / `Нет` / `Не применимо`.
5. `Статус` — `Есть` / `Отсутствует` / `Частично`.
6. `Обоснование (если Нет / Не применимо)` — required whenever `Статус`
   isn't a clean `Есть` — see `outsource-operating-principles.md` before
   writing this.
7. `Согласовано с М2 и командой` — `Да` + date, or blank if not actually
   agreed yet. Never mark agreement that hasn't happened.
8. `Owner` — who owns closing the gap, if it's being closed. Blank is
   acceptable only for an accepted, no-action-needed exception.
9. `Дата` — target/follow-up date, if applicable.
10. `Комментарии` — free text, including any agreement reached through M2
    worth preserving (see `outsource-operating-principles.md`, Practical
    Reminders).

## Inputs

- Direct observation/conversation with the project team (BA presence,
  environment setup, workflow definitions, etc.).
- Existing `project_risk`/`project_metrics` — a known QA-process gap
  already logged there should be cross-checked against this checklist
  rather than duplicated blind.
- The project's own `.xlsx` copy of the checklist, if one was kept
  locally during onboarding (see Template above).

## Evidence Rules

- Every non-`Есть` status needs a real, specific reason — "not tracked" is
  not a reason; "fixed 3-month scope, revisit if extended" is.
- Do not infer `Согласовано с М2 и командой = Да` from the fact that a
  gap seems obviously reasonable — it needs an actual conversation.
- When a gap is judged a real risk, log it in `project_risk`'s `Риск QA
  process` column (see `m2-project-risk-report`) — this Sheet is the
  evidence, not the risk judgment itself.

## Rule

Keep this skill scoped to the process-checklist document family only. Do
not use it to write project-risk judgments (`m2-project-risk-report`) or
project development-plan actions (`m2-project-development-plan`) directly
— route confirmed gaps there instead of expanding this Sheet's columns to
hold that content.
