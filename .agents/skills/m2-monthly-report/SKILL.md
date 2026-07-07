---
name: m2-monthly-report
description: Create or update an M2 monthly KPI report as a Google Sheet, with CSV fallback, from project-management evidence, the M2 monthly report example workbook structure, M2 project metrics, development plans, risk reports, staffing/status data, client feedback, or explicit manager facts. Use when preparing monthly M2 bonus/KPI reporting, checking which M2 obligations/KPIs can be supported, identifying missing evidence, or turning M2 monthly-report source data into a spreadsheet.
---

# M2 Monthly Report

Use this skill for one output family only:

- M2 monthly KPI report Google Sheet, with CSV fallback

Default source example:

`G:\My Drive\QA_Management\00_Source_Docs\M2_monthly_report.xlsx`

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Read `../qa-management-roles/references/m2-role-rules.md`.
4. Identify the target M2 manager and reporting month.
5. Treat `M2_monthly_report.xlsx` as an example/calculator unless the user explicitly says it is the real report for that manager/month.
6. Read the smallest relevant evidence set:
   - project metrics
   - project and individual development plans
   - project risk reports
   - staffing/onboarding/offboarding evidence
   - client feedback and status-thread evidence
   - release, upsale, rate, paid, timesheet, security, FTE, and project-count evidence
7. Ask questions only for fields required to complete the requested report and not present in the evidence.

## Workflow

1. Preserve the two-section report structure:
   - Section 1: base obligations, no bonus accrual
   - Section 2: KPI / bonuses / penalties
2. For every row, fill only source-backed cells.
3. Leave unsupported cells blank.
4. Ask missing-data questions before finalizing when the requested report requires those cells.
5. Use `Да` only when there is direct evidence for the reporting period.
6. Use `Нет` only when the source explicitly says the case did not happen, or the user confirms it.
7. Leave `Completed (Да/Нет)` blank when the status is unknown.
8. Preserve the 2D CSV layout from `Templates\m2_monthly_report.csv`; do not convert it into a normalized table.

## Guardrails

- Do not use the example person names, projects, amounts, or comments from `M2_monthly_report.xlsx` as facts.
- Do not infer successful release, upsale, direct client access, positive feedback, or project improvement without direct evidence.
- Do not calculate totals from unsupported counts.
- Do not convert project risks into penalties unless the source explicitly maps them to a KPI/penalty row.
- Do not add example/calculator comments from the workbook into a real report unless independently supported by actual evidence.
- Keep business-facing text in Russian unless the user asks otherwise.
