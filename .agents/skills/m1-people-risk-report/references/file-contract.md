# File Contract

Primary Google Workspace output is a single **living** people-risk
traffic-light Google Sheet in `10_M1_People_Management`, with local CSV
fallback. Use the template below as the schema contract. When Google API
access is available, read and validate the header row before writing.

## Template

`<repo-root>\Templates\светофор_рисков.csv`

## Output

`10_M1_People_Management\Светофор рисков` Google Sheet — one canonical,
living Sheet, no date in the title.

Local CSV fallback: `G:\My Drive\QA_Management\10_M1_People_Management\Светофор рисков.csv`

This stays at the `10_M1_People_Management` root — it's a workspace-wide,
cross-person document, not per-person content, so it does not move into
any `<Person>\` subfolder (see `google-workspace-rules.md`, M1
Person-Based Layout).

## Source Inputs

- per-person `1to1` Sheets/CSVs under `10_M1_People_Management\<Person>\`
  (see `m1-people-1to1-file`)
- structured findings from `qa-1to1-analysis`
- explicit manager notes

## Schema

- `Сотрудник`
- `Дата обновления` — ISO `YYYY-MM-DD`, the date this row's content last
  actually changed. Carries the freshness signal that used to live in the
  filename before this became a living document.
- `Риск с нашей стороны (мы недовольны)`
- `Риск со стороны сотрудника (он недоволен)`
- `Комментарии`
- `План действий`

## Risk Level Scale

- Use only `Низкий`, `Средний`, or `Высокий` in both risk columns — a
  3-level scale, same as M2's `project_risk` (see
  `m2-project-risk-report`'s document-contract). Do not use `Критический`
  or any other level; a row still on the older 4-level scale (e.g. from a
  pre-Google-API-access CSV) needs remapping to this scale, not carried
  forward as-is — an acute, already-materialized situation is still
  `Высокий`, just without a separate tier above it.
- Pair the level with a short direction/trend note in the same cell (e.g.
  `Высокий, рост` / `Средний, стабильный` / `Низкий, снижение`) — matches
  the style already used in real rows on this Sheet.

## Rule

Never edit the template file itself (`Templates\светофор_рисков.csv`) —
copy it once to create the living Sheet if one doesn't exist yet, then
update that Sheet in place from then on.

## Versioning

- Living canonical file: edit rows in place as a person's risk status
  changes, same discipline as M2's `project_risk`/`project_metrics` — not
  the dated-snapshot pattern (`_vN` suffix, never-overwrite) used
  elsewhere in this repo for genuinely point-in-time artifacts.
- Do not create a new dated Sheet/CSV per review. If the user explicitly
  wants a point-in-time archival export (e.g. for a formal reporting
  event), create one as a clearly-labeled one-off — that's the exception,
  not the default working pattern.
- A stray pre-Google-API-access CSV left over from before this Sheet
  existed (e.g. an old dated `светофор_рисков_YYYY-MM-DD.csv`) is not a
  version of this Sheet to reconcile with — it's leftover local-fallback
  staging from before Drive access was set up. Confirm with the user
  before archiving/deleting it rather than assuming it holds data this
  Sheet is missing.
