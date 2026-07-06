---
name: m2-people-1to1-file
description: Create or update an individual QA engineer 1to1 CSV file for M2 project management. Use when turning shared QA 1to1 transcript analysis into a per-person file in `G:\My Drive\QA_Management\20_M2_Project_Management` based on `Templates/1to1.csv` from this repository.
---

# M2 People 1to1 File

Use this skill for one output family only:

- `G:\My Drive\QA_Management\20_M2_Project_Management\<Person Name> 1to1.csv`

## Required Start

1. Start from structured findings from `qa-1to1-analysis`, or analyze the transcript directly if needed.
2. Read `references/file-contract.md`.
3. Read the existing person file if it exists.

## Workflow

1. Use `Templates/1to1.csv` from this repository only when the person file does not exist yet.
2. Write or update one row with:
   - `Date`
   - `Topic`
   - `Comments`
   - `Results`
   - `Assign`
   - `Action plan`
3. Preserve historical rows unless the user explicitly asks to revise one.
4. Keep the row useful for project-management follow-up while preserving people-management facts that explain the project context.
5. Write business-facing text in Russian by default unless the user explicitly requests another language.

## Guardrails

- Do not generate project risk, metrics, or development-plan reports here.
- Do not change the shared `1to1.csv` schema.
- Do not reclassify the meeting topic differently from `qa-1to1-analysis` without explicit evidence.
