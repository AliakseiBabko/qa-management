# File Contract

Primary Google Workspace output is a dated people-risk traffic-light Google Sheet
in `10_M1_People_Management`, with local CSV fallback. Use the template below
as the schema contract. When Google API access is available, apply the same
versioning rule to the Google Sheet title and validate the header row before
writing.

## Template

`<repo-root>\Templates\светофор_рисков.csv`

## Output Pattern

`G:\My Drive\QA_Management\10_M1_People_Management\светофор_рисков_YYYY-MM-DD.csv`

This stays at the `10_M1_People_Management` root — it's a workspace-wide,
cross-person snapshot, not per-person content, so it does not move into
any `<Person>\` subfolder (see `google-workspace-rules.md`, M1
Person-Based Layout).

## Source Inputs

- per-person `1to1` Sheets/CSVs under `10_M1_People_Management\<Person>\`
  (see `m1-people-1to1-file`)
- structured findings from `qa-1to1-analysis`
- explicit manager notes

## Rule

Never edit the template directly. Create or update a dated snapshot.

## Versioning

- Do not overwrite an existing dated final snapshot by default.
- If the target `YYYY-MM-DD` file already exists, create the next versioned file with a `_vN` suffix, for example `_v2` or `_v3`.
- Update an existing dated snapshot in place only when the user explicitly asks for revision.
