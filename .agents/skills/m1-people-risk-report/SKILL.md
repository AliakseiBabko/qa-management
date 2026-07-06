---
name: m1-people-risk-report
description: Create or update the M1 people risk traffic-light CSV from QA people-management evidence. Use when generating dated files like `G:\My Drive\QA_Management\10_M1_People_Management\светофор_рисков_YYYY-MM-DD.csv` from `Templates\светофор_рисков.csv` in this repository.
---

# M1 People Risk Report

Use this skill for one output family only:

- `G:\My Drive\QA_Management\10_M1_People_Management\светофор_рисков_YYYY-MM-DD.csv`

## Required Start

1. Read `references/file-contract.md`.
2. Read one representative existing snapshot when available.
3. Read the relevant person files in `G:\My Drive\QA_Management\10_M1_People_Management` and/or structured findings from `qa-1to1-analysis`.

## Workflow

1. Copy `Templates\светофор_рисков.csv` from this repository when creating a new dated snapshot.
2. Fill one row per employee.
3. Keep the schema stable:
   - `Сотрудник`
   - `Риск с нашей стороны (мы недовольны)`
   - `Риск со стороны сотрудника (он недоволен)`
   - `Комментарии`
   - `План действий`
4. Calibrate people-side and company-side risk for people management, not project management.

## Guardrails

- Do not write project-level risk here.
- Do not change template columns unless the user requests schema work.
