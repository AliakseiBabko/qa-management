# File Contract

## Template

`<repo-root>\Templates\светофор_рисков.csv`

## Output Pattern

`G:\My Drive\QA_Management\10_M1_People_Management\светофор_рисков_YYYY-MM-DD.csv`

## Source Inputs

- per-person `* 1to1.csv` files
- structured findings from `qa-1to1-analysis`
- explicit manager notes

## Rule

Never edit the template directly. Create or update a dated snapshot.

## Versioning

- Do not overwrite an existing dated final snapshot by default.
- If the target `YYYY-MM-DD` file already exists, create the next versioned file with a `_vN` suffix, for example `_v2` or `_v3`.
- Update an existing dated snapshot in place only when the user explicitly asks for revision.
