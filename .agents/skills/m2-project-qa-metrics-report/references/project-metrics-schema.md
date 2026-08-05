# M2 Project Metrics Schema

Scope: `project_metrics` Sheet purpose, templates, expected output, versioning, and row schema.

Primary final output is a Google Sheet in `20_M2_Project_Management\<Project>`,
with local CSV fallback. Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the QA metrics document family: `project_metrics`
and `qa_process_metrics`. Both live at `20_M2_Project_Management\<Project>\`,
alongside `project_risk`, but they are two separate Sheets with different
owners and different audiences — never merge them into one file.

- **`project_metrics`** — M2-only dashboard for the project, the single
  place to see the whole picture of a project. M2 fills this in; never
  share it with the QA engineers whose data appears in it.
- **`qa_process_metrics`** — project-wide QA-process facts, filled in by
  the project team from their own tools. M2 does not collect this data or
  guess values into it.

## Templates

- `<repo-root>\Templates\метрики_проекта_qa.csv` — `project_metrics` Sheet
  column schema.
- `<repo-root>\Templates\qa_process_metrics.csv` — `qa_process_metrics`
  Sheet column schema.
- `<repo-root>\Templates\метрики_проекта_qa.md` — catalogue covering both
  artifacts and how to choose among their candidate metrics. Derived from
  `90_Storage\Reference\Source_Documents\M2_project_development_plan` and real project content.
- `<repo-root>\Templates\метрики_qa_по_проекту.csv` / `.md`
  For individual QA metrics inside the project scope.
- `qa-management-roles\references\qa-metrics-catalog.md` — cross-cutting
  map of all three metric tiers (Core project QA-process, optional
  project/release quality, optional individual contribution) and the
  signals-not-verdicts principle they share; points back here for actual
  definitions rather than duplicating them.

## Expected Output

One project-level metrics-oriented report format per skill invocation.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>`

## Versioning

- `generate_m2_outputs.py` (see README, "legacy first-pass tools") predates
  this dashboard schema and is not template-aware — it mechanically pulls
  `label: value` bullets from each source document's own Scorecard section.
  Any `project_metrics` content that traces back to that script (rather
  than the current 4-row-type dashboard built via `scaffold_project_dashboard.py`
  and real M2 judgment) is a raw source dump, not a compliant sheet — never
  treat it as already following this schema.
  `sync_m2_source_docs_to_sheets.py` uses this same extraction path for
  `project_metrics` — it only creates the sheet when one doesn't exist yet
  (a rough bootstrap) and never overwrites an existing one, specifically so
  rerunning it can't silently replace a real dashboard with extracted
  fragments again.
- Both `project_metrics` and `qa_process_metrics` are living Sheets,
  updated in place — same as `individual_metrics` and `project_risk`. Do
  not create dated `_vN` files for routine updates.
- `qa_process_metrics` is append-only by calendar month (see
  `qa-process-metrics-schema.md`'s Schema section) — "updated in place"
  means updating the current month's rows, not overwriting prior months.
- Append source traceability to the project `evidence_log`.

## Schema — `project_metrics`

Columns: `Проект`, `Период`, `Метрика`, `Показатель`, `Пояснение`, `Owner`,
`Тренд` — same 7-column shape as `individual_metrics`. `Период` always
filled; `Показатель` is a clean fact/status, never a numeric-score-plus-word
mix; `Owner` always filled; `Пояснение` is achievement+gap prose, never a
raw file path (traceability lives in `evidence_log`).

Row types, all living in this one Sheet:

0. **`Статус проекта`** — one row, `Активен` or `Не активен`. Exactly two
   states, never a third "paused" value in between - a temporary
   client-driven pause and an official stop/cancellation are both recorded
   as `Не активен`; the reason and its detail belong in this row's
   `Пояснение` and in `project_risk`/`project_development_plan`, not in a
   separate enum value. Manual-only: no script sets or clears `Не активен`,
   and there is no scheduled review that would - reactivation (or simply
   correcting a mistaken flip) happens only when M2 explicitly changes it
   back to `Активен`, which then flows through
   `refresh_project_registry.py`'s normal mirror on its next run. While
   `Не активен`: `project_risk`'s `Общий уровень риска` stays frozen at its
   last real value rather than being remapped onto the inactivity (it isn't
   a point on that scale); `qa_process_metrics` stops taking new monthly
   periods (see its Schema section below); and `refresh_project_registry.py`
   excludes the project from the rebuilt registry automatically - no manual
   row deletion or folder move needed, the project's live documents stay in
   place. Every project gets this row, default `Активен`. See catalogue
   §1.0.
1. **`Горизонт совместной работы`** — one row. Expected end date of the
   engagement/current phase; where meaningful change could happen
   (contract end, vendor switch, tender). See catalogue §2.1.
2. **`Бизнес-риск продукта клиента (оценка M2)`** — one row, Низкий/
   Средний/Высокий. Risk that the client's own business fails to reach its
   goals and dissolves — independent of our performance (that's
   `project_risk`'s job). See catalogue §2.2.
3. **`Вклад в проект: <Имя>`** — one row per QA on the project, Позитивный/
   Смешанный/Негативный, showing the actual conclusion for that person.
   No aggregated team row — every individual row stays visible at this
   level; aggregation to one worst-case value only happens one level up,
   in `_project_registry`. Moved here from `individual_development_plan`
   because that Doc is visible to the employee it's about. See catalogue
   §2.3.
4. **`Качество QA-процесса`** — one row, Позитивный/Смешанный/Негативный.
   M2's synthesized read of `qa_process_metrics`, not a copy of it. Empty
   until `qa_process_metrics` has real data to read. See catalogue §2.4.

There is no automated `Команда: ...` statistical-rollup row (a mechanical
distribution of Core metrics across the team, e.g. "2/3 Соответствует") —
`rollup_individual_metrics_to_project.py` is deprecated and refuses to
run; `Вклад в проект: <Имя>` gives an actual judgment per person instead
of a mechanical distribution, so do not add rollup-style rows here.

Rows 1-2 and 4 are M2-only judgment. Revenue, client base, and churn are
cited as evidence inside row 2's `Пояснение` when known, not tracked as
separate rows. Rows 1-2 and 4 get a row on every project even when
`Показатель` is empty — the row set stays identical across projects so a
blank cell reads as "not available yet," not "M2 forgot this metric."
`Вклад в проект: <Имя>` rows are the exception — only add a row once
there's an actual conclusion to record for that person.

Removed entirely, and why:
- `Уровень внимания`, `Статус данных` — every row read a constant value,
  carried no information.
- `Следующее действие`, `Комментарии` — belong in
  `project_development_plan`'s Ближайшие шаги/Направления развития.
- Project-level risk-scorecard content (stability, delivery predictability,
  process maturity, overall risk level) — that's `project_risk`'s job;
  keeping it here duplicated it with a worse format.
- `Cost of quality avoided` — not something M2 estimates from outside; it
  depends on real `qa_process_metrics` data (Defect Escape Rate, Defect
  Density, Mean Time to Fix), and becomes a narrative M2 builds from that
  data for client conversations, not a row here.
- "Продуктовые метрики использования" (Activation Rate/MAU/DAU/...) — too
  granular for general business-context understanding; add point-in-time
  only if a specific project's QA scope actually covers that flow.

## Rule

Do not mix project-level and individual-level metrics in one output file
unless the user explicitly asks for a combined document and a combined
template exists. The `Вклад в проект: <Имя>` rows inside `project_metrics`
are the sanctioned exception — they're M2's project-level conclusions
derived from individual data, not raw individual-level rows.
