# File Contract

## Template

`<repo-root>\Templates\1to1.csv`

## Target

Primary Google Workspace target:

`20_M2_Project_Management\<Project>\private\people\<Person Name>\<Person Name> 1to1` Google Sheet

CSV fallback target (same canonical private folder):

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\private\people\<Person Name>\<Person Name> 1to1.csv`

The 1to1 file is M2-private: it stays under the project's `private\people\<Person Name>\`
folder and is never placed in the employee-facing `people\<Person Name>\shared\` folder.

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
