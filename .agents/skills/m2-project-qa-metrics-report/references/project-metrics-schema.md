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

Columns in `Templates\метрики_проекта_qa.csv`:
`Проект`, `Период`, `Метрика`, `Role / Stream`, `Показатель`, `Baseline`,
`Target`, `Evidence Status`, `Data Confidence`, `Пояснение`, `Owner`, `Тренд`.

Composite row identity:
```text
(Project, Metric Key, Role / Stream)
```
Project-wide rows use `Role / Stream = Project-wide`.

### Canonical Context Keys:

0. **`Статус проекта`** — `Активен` or `Не активен`. Exactly two states.
   When `Не активен`: excludes project from `_project_registry`, freezes
   `project_risk` level, and stops new periods in `qa_process_metrics`.
1. **`Engagement outlook`** — structured: `YYYY-MM-DD [Contractual] — <Continuation Outlook> (<Confidence>)`.
2. **`Цель клиента / Ценность QA`** — stated client objective with alignment flag.
3. **`Фокус M2`** — internal technical and delivery value focus.
4. **`Статус согласования (Alignment)`** — `Согласовано`, `В процессе калибровки`, or `Расхождение ожиданий`.
   **Expectation Gap Rule**: `Расхождение ожиданий` requires an `m2_input` question or an action item.
   It creates an active project-risk item only when credible impact exists on delivery, trust, staffing,
   or contract continuation.
5. **`Сигнал capacity`** — delivery/staffing early-warning signal.
6. **`Outcome proxy: <name>`** — 1 to 3 operational business outcome proxies (e.g. `Regression duration`,
   `Production leakage per release`, `Blocker discovery ratio`, `Onboarding speed`, `Estimated rework avoided`).
7. **`Вклад в проект: <Person>`** — private person attribution judgment (`Позитивный`, `Смешанный`, `Негативный`).

### Outcome Proxies and Epistemic Fields:

- **`Evidence Status`**: `observed`, `estimated`, `projected`, `assumption-based`.
- **`Data Confidence`**: `Высокая`, `Средняя`, `Низкая`.
- **`Baseline`**, **`Target`**, **`Показатель`** (Current): track measurable movement over `Период`.
- **Zero-Denominator Rule**: if denominator is zero (e.g. 0 releases in period), record as factual
  text `No releases in period`. Do not divide by zero or render `0%`.
- **`Not applicable` vs. `No data yet`**: `Not applicable` indicates the metric is out of scope for the
  project; `No data yet` indicates it is in scope but uncollected.

## Rule

Do not mix project-level and individual-level metrics in one output file
unless the user explicitly asks for a combined document and a combined
template exists. The `Вклад в проект: <Имя>` rows inside `project_metrics`
are the sanctioned exception — they're M2's project-level conclusions
derived from individual data, not raw individual-level rows.
