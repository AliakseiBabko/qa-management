---
name: m1-people-1to1-file
description: Create or update an individual QA engineer 1to1 CSV file for M1 people management. Use when turning transcript analysis into a per-person file in `G:\My Drive\QA_Management\10_M1_People_Management` based on `Templates/1to1.csv` from this repository.
---

# M1 People 1to1 File

Use this skill for one output family only:

- `G:\My Drive\QA_Management\10_M1_People_Management\<Person Name> 1to1.csv`

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
4. Write business-facing text in Russian by default unless the user explicitly requests another language.

## Guardrails

- Do not generate people risk traffic lights here.
- Do not mix project-level analysis into the per-person row beyond what helps explain the conversation.
- Do not reclassify the meeting topic differently from `qa-1to1-analysis` without explicit evidence.
