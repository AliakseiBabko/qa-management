---
name: m1-people-risk-report
description: Create or update the M1 people risk traffic-light Google Sheet, with CSV fallback, from QA people-management evidence. Use when reviewing or updating people-risk status in the QA Management Google Drive workspace, based on `Templates\светофор_рисков.csv` in this repository.
---

# M1 People Risk Report

Use this skill for one output family only:

- the living people-risk traffic-light Google Sheet (`Светофор рисков`) in `10_M1_People_Management`, with local CSV fallback

## Required Start

1. Read `../qa-management-roles/references/google-workspace-rules.md`.
2. Read `references/file-contract.md`.
3. Read the existing `Светофор рисков` Sheet — this is a living document updated in place, not a dated snapshot; always read current state before writing.
4. Read the relevant person Sheets/files in `10_M1_People_Management\<Person>\` and/or structured findings from `qa-1to1-analysis`.

## Workflow

0. For the actual write, use `.agents\scripts\update_m1_risk_row.py` rather than hand-rolling a Sheets API call — it handles existing-row lookup vs. new-row, `Дата обновления` bookkeeping, and the risk-scale validation below in one place. Dry-run by default; `--apply` writes.
1. Use `Templates\светофор_рисков.csv` from this repository only when the `Светофор рисков` Sheet doesn't exist yet.
2. One row per employee. Update that person's existing row in place when their risk status changes — do not append a duplicate row for someone already on the Sheet.
3. Keep the schema stable:
   - `Сотрудник`
   - `Дата обновления` — when this row was last reviewed/changed; this is what carries the "as of" freshness signal now that the Sheet itself isn't dated.
   - `Риск с нашей стороны (мы недовольны)`
   - `Риск со стороны сотрудника (он недоволен)`
   - `Комментарии`
   - `План действий`
4. Calibrate people-side and company-side risk for people management, not project management.
5. Set `Дата обновления` to the actual date the row's content changed — do not touch it when only reading/reviewing, and do not backdate or leave it stale after a real edit.
6. Use only the 3-level scale (`Низкий`/`Средний`/`Высокий`) in both risk columns — see `references/file-contract.md`, Risk Level Scale. A row still carrying an older `Критический` value needs remapping to `Высокий`, not left as-is.

## Guardrails

- Do not write project-level risk here.
- Do not change template columns unless the user requests schema work.
- Do not create a new dated Sheet/CSV per review — this is a living
  document (`Светофор рисков`, no date in the title), same versioning
  discipline as `project_risk`/`project_metrics` on the M2 side, not the
  per-snapshot pattern used elsewhere in this repo. A dated snapshot is
  only for a genuinely archival export the user explicitly asks for.
