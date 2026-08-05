# M2 Project Risk Schema

Scope: `project_risk` Sheet purpose, template, expected output, versioning, and row schema.

Primary final output is a Google Sheet in `20_M2_Project_Management\<Project>`,
with local CSV fallback. Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the project-risk document family.

## Template

`<repo-root>\Templates\светофор_рисков_проекта.csv`

## Expected Output

One living project-risk Sheet per project — not a dated snapshot series.
Exactly one row per project, updated in place as the risk read changes
(same shape/discipline as `project_metrics`, M1's `Светофор рисков`, and
the person-level `individual_risk`, see `m2-individual-qa-metrics-report/
references/internal-variant.md`).

Target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\private`

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
  instead of one coherent risk assessment per column), write a real
  synthesized row from the evidence directly into the project's one current
  row — do not create a `project_risk_predecessor_<date>` backup file
  first; that dated-backup pattern belonged to the old per-snapshot model
  and has no place in a living, one-row document (a bad prior row just
  gets corrected in place, the same as any other stale cell). `sync_m2_source_docs_to_sheets.py`
  uses this same extraction path — it only creates `project_risk` when one
  doesn't exist yet (a rough bootstrap) and never overwrites an existing
  one, specifically so rerunning it can't silently replace a real
  synthesized row with fragments again.
- **One row per project, always.** Update that project's existing row in
  place when the risk read changes — never append a second dated row for
  a project already on the Sheet, even for a routine no-change review.
  `Дата обновления` carries the freshness signal; there is no separate
  snapshot-date key. Append source traceability to the project
  `evidence_log`, not a new row here.
- Do not create a dated snapshot file/tab per review. If the user
  explicitly wants a point-in-time archival export (e.g. for a formal
  reporting event), create one as a clearly-labeled one-off — that is the
  exception, not the default working pattern.

## Schema

Use exactly the columns in `Templates\светофор_рисков_проекта.csv`:

1. `Проект`
2. `Дата обновления` — ISO or `DD.MM.YYYY` (match what's already in the
   Sheet), the date this row's content last actually changed. Do not
   touch it when only reading/reviewing, and do not backdate or leave it
   stale after a real edit.
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
