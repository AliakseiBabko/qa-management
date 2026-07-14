---
name: m1-monthly-report
description: Create or update an M1 monthly KPI report as a Google Sheet, with CSV fallback, from real people-management evidence, the M1 monthly report workbook structure, 1to1 outputs, risk reports, HR/RM/project notes, or explicit manager facts. Use when preparing monthly M1 bonus/KPI reporting, checking which M1 obligations/KPIs can be supported, identifying missing evidence, or turning M1 monthly-report source data into a spreadsheet.
---

# M1 Monthly Report

Use this skill for one output family only:

- M1 monthly KPI report Google Sheet, with CSV fallback

Default source example:

`G:\My Drive\QA_Management\00_Source_Docs\M1_monthly_report.xlsx`

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Read `../qa-management-roles/references/m1-role-rules.md`.
4. Identify the target M1 manager and reporting month.
5. Read the smallest relevant evidence set:
   - existing M1 monthly report workbook or extracted CSV
   - M1 1to1 files
   - people risk snapshot
   - team members' current-cycle OKR Docs (`m1-individual-development-plan`) — evidence for the `Работа с ОКР` obligation row
   - HR/RM notes
   - assessment, PR, interview, onboarding, security, FTE, timesheet, team-size, and project-start evidence
6. Ask questions only for fields required to complete the requested report and not present in the evidence.

## Workflow

1. Preserve the two-section report structure:
   - Section 1: base obligations, no bonus accrual
   - Section 2: KPI / bonus / penalty rows
2. For every row, fill only source-backed cells.
3. Leave unsupported cells blank.
4. Ask missing-data questions before finalizing when the requested report requires those cells.
5. Use `Да` only when there is direct evidence that the obligation/KPI happened in the reporting period.
6. Use `Нет` only when the source explicitly says it did not happen, or the user confirms it.
7. Leave `Completed (Да/Нет)` blank when the status is unknown.
8. Preserve the 2D CSV layout from `Templates\m1_monthly_report.csv`; do not convert it into a normalized table.
9. For the `Работа с ОКР` row, use `Да` only when there is direct evidence
   that OKR work actually happened in the reporting month for the team —
   a new-cycle OKR Doc was drafted/approved, an existing one was closed out
   with results, or Key Result statuses were updated (per the ≥2-week
   cadence in `m1-individual-development-plan`'s process rules). A team
   member simply having an OKR Doc from a prior month with no activity in
   the reporting month is not evidence for that month.

## Guardrails

- Do not infer bonus eligibility from vague activity.
- Do not calculate bonus totals from unsupported counts.
- Do not reuse a previous month as evidence for a new month unless the source explicitly applies to the requested month.
- Do not treat template/example comments as facts.
- Keep business-facing text in Russian unless the user asks otherwise.
