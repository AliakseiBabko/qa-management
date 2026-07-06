---
name: m1-monthly-report
description: Create or update an M1 monthly KPI report CSV from real people-management evidence, the M1 monthly report workbook structure, 1to1 outputs, risk reports, HR/RM/project notes, or explicit manager facts. Use when preparing monthly M1 bonus/KPI reporting, checking which M1 obligations/KPIs can be supported, identifying missing evidence, or turning M1 monthly-report source data into a CSV.
---

# M1 Monthly Report

Use this skill for one output family only:

- M1 monthly KPI report CSV

Default source example:

`G:\My Drive\QA_Management\00_Source_Docs\M1_monthly_report.xlsx`

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/m1-role-rules.md`.
3. Identify the target M1 manager and reporting month.
4. Read the smallest relevant evidence set:
   - existing M1 monthly report workbook or extracted CSV
   - M1 1to1 files
   - people risk snapshot
   - HR/RM notes
   - assessment, PR, interview, onboarding, security, FTE, timesheet, team-size, and project-start evidence
5. Ask questions only for fields required to complete the requested report and not present in the evidence.

## Workflow

1. Preserve the two-section report structure:
   - Section 1: base obligations, no bonus accrual
   - Section 2: KPI / bonus / penalty rows
2. For every row, fill only source-backed cells.
3. Leave unsupported cells blank.
4. Put each missing-data question in `Missing Data Question` when a row cannot be completed from evidence.
5. Use `Да` only when there is direct evidence that the obligation/KPI happened in the reporting period.
6. Use `Нет` only when the source explicitly says it did not happen, or the user confirms it.
7. Leave `Completed (Да/Нет)` blank when the status is unknown.

## Guardrails

- Do not infer bonus eligibility from vague activity.
- Do not calculate bonus totals from unsupported counts.
- Do not reuse a previous month as evidence for a new month unless the source explicitly applies to the requested month.
- Do not treat template/example comments as facts.
- Keep business-facing text in Russian unless the user asks otherwise.
