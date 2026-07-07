# File Contract

## Template

`<repo-root>\Templates\1to1.csv`

## Target

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\people\<Person Name>\<Person Name> 1to1.csv`

Primary Google Workspace target:

`20_M2_Project_Management\<Project>\people\<Person Name>\<Person Name> 1to1` Google Sheet

Use the CSV target only as local fallback or staging. Preserve `Templates\1to1.csv` as the schema contract.

## Columns

- `Date`
- `Topic`
- `Comments`
- `Results`
- `Assign`
- `Action plan`

## Update Rule

- Append a new row by default.
- Revise an old row only when the user explicitly asks for correction.
- Use the same schema as the M1 1to1 writer; only the destination folder and M2-oriented emphasis differ.
- Do not create `_vN` copies for this file family. The person file is an append-only longitudinal record, not a dated final snapshot.
- When Google API access is available, append to the existing Google Sheet. Read and validate the header row before appending.
