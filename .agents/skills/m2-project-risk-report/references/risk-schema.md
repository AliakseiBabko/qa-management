# M2 Project Risk Schema

Scope: `project_risk` Sheet purpose, template, expected output, versioning, and row schema.

Primary final output is a Google Sheet in `20_M2_Project_Management\<Project>`,
with local CSV fallback. Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the project-risk document family.

## Template

`<repo-root>\Templates\светофор_рисков_проекта.csv`

## Expected Output

One project-risk traffic-light document per reporting snapshot.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>`

Suggested naming pattern:

`светофор_рисков_проекта_YYYY-MM-DD.csv`

## Versioning

- `generate_m2_outputs.py` (see README, "legacy first-pass tools") is not
  template-aware: it mechanically pulls `label: value` bullets out of each
  source document's own Scorecard section into whatever columns happen to
  line up, without synthesizing a single project-level voice per column —
  this is where rows like a `Риск staffing / continuity` cell literally
  reading `Owner: X. Owner: Y. Owner: Z.` come from. Its `project_risk`
  output is a raw source dump, not a compliant row — never treat it as
  already following this schema. When applying this schema to a project for
  the first time (or fixing a row that reads like disconnected fragments
  instead of one coherent risk assessment per column), back up the old row
  as `project_risk_predecessor_<date>` and write a real synthesized row from
  the evidence, the same way this has already been done for other projects.
  `sync_m2_source_docs_to_sheets.py` uses this same extraction path — it
  only creates `project_risk` when one doesn't exist yet (a rough
  bootstrap) and never overwrites an existing one, specifically so rerunning
  it can't silently replace a real synthesized row with fragments again.
- Use the living project-local `project_risk` file for current state, and append
  source traceability to the project `evidence_log`.
- Do not overwrite an existing formal dated project-risk snapshot by default.
- If the target snapshot-date file already exists, create the next versioned file with a `_vN` suffix before `.csv`, for example `_v2` or `_v3`.
- Update an existing project-risk snapshot in place only when the user explicitly asks for revision.

## Schema

Use exactly the columns in `Templates\светофор_рисков_проекта.csv`:

1. `Проект`
2. `Период / snapshot date`
3. `Общий уровень риска`
4. `Риск delivery`
5. `Риск QA process`
6. `Риск staffing / continuity`
7. `Риск communication / client`
8. `Комментарии`
9. `План действий`
10. `Owner` — an actual accountable owner (a person or M2 itself), not left
    blank. Every project's `Owner` cell was empty before 2026-07-08; treat a
    blank `Owner` as an incomplete row, not an acceptable default.
11. `Следующий review`

`Evidence / источники` was removed from this schema: it only ever held raw
source file paths, which is exactly the pattern already excluded from
`individual_development_plan` for the same reason — a bare list of paths
tells the reader nothing, and that traceability already lives in
`evidence_log`. Do not reintroduce a raw-path evidence column here.
