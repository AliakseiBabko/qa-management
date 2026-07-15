---
name: m1-people-1to1-file
description: Create or update an individual QA engineer 1to1 Google Sheet, with CSV fallback, for M1 people management. Use when turning transcript analysis into a per-person longitudinal record in the QA Management Google Drive workspace based on `Templates/1to1.csv` from this repository.
---

# M1 People 1to1 File

Use this skill for one output family only:

- `1to1` Google Sheet inside `10_M1_People_Management\<Person>\`, with local CSV fallback

## Required Start

1. Start from structured findings from `qa-1to1-analysis`, or analyze the transcript directly if needed.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Read `references/file-contract.md`.
4. Read the existing person Sheet/file if it exists.

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
- Do not title the Sheet `<Person> 1to1` — the person is already the enclosing folder name (`10_M1_People_Management\<Person>\`), so the Sheet itself is just `1to1` (matches the M2 per-project convention: content-type-named files inside person-named folders, not the reverse).
