# M2 Project-Based Layout

Scope: the M2 (`20_M2_Project_Management`) folder shape, `private`/`shared`
document locations, and the `_project_registry` dashboard. Load this
module for any skill that creates or updates a final M2 project-management
output. Person/operational registries (`_people_registry`,
`_skill_invocations`, etc.) live in their own modules — see
[people-registry.md](people-registry.md) and
[operational-registries.md](operational-registries.md).

Treat `20_M2_Project_Management` as a project-context workspace, not as a flat
report dump. Final M2 tabular outputs should go under:

`20_M2_Project_Management\<Project>\...`

Standard project folder shape:

- `private\project_risk` Google Sheet, with CSV fallback `project_risk.csv`
- `private\process_checklist` Google Sheet, with CSV fallback `process_checklist.csv`
  — the 12-section outsource QA process-maturity checklist (see
  `m2-project-process-checklist`, based on `Templates\аутсорс_чек_лист_qa.csv`).
  A living record, not a dated snapshot; confirmed gaps route into
  `project_risk`'s `Риск QA process` column rather than living only here.
- `private\project_development_plan` Google Doc, with Markdown fallback
- `private\project_metrics` Google Sheet, with CSV fallback `project_metrics.csv`
  — M2-only dashboard for the project (see `Templates\метрики_проекта_qa.md`
  §2). Holds: `Горизонт совместной работы`, `Бизнес-риск продукта
  клиента`, one `Вклад в проект: <Имя>` row per person (no aggregated
  team row — every row stays visible individually at this level), and
  `Качество QA-процесса` (M2's read of `qa_process_metrics`). Never share
  this with the QA engineers whose data appears in it, even once
  folder-level sharing exists for other artifacts.
- `team_shared\qa_process_metrics` Google Sheet, with CSV fallback
  `qa_process_metrics.csv` — project-wide QA-process facts (Defect Escape
  Rate, Automation Coverage, test-run counts, etc. — see
  `Templates\метрики_проекта_qa.md` §3). Filled in by the project team, not
  M2 — do not guess values into it; create empty skeleton rows with a real
  `Пояснение` instruction instead. Append-only by calendar month.
- `private\evidence_log` Google Sheet, with CSV fallback `evidence_log.csv`
- `people\<Person>\shared\individual_development_plan` Google Doc, with Markdown fallback
- `people\<Person>\shared\individual_metrics` Google Sheet, with CSV fallback
- `private\people\<Person>\individual_metrics_internal` Google Sheet, with CSV
  fallback — M2-only, never shared with the employee (see
  `m2-individual-qa-metrics-report`'s references/internal-variant.md).
- `private\m2_input\` — folder holding one M2-only Google Doc, `m2_input`: M2's
  own dated rounds of questions/answers ahead of each project-level
  rollup (see `m2-role/m2-project-rollups.md` Project-Level Rollups and
  `Templates\m2_input.md`). One Doc per project, not a file per cycle —
  rounds are dated sections appended to it. (No longer holds a metrics
  Sheet — that moved into `project_metrics`, see above.)
- `private\status_reports` for saved project status Google Docs / Markdown fallback

Do not create a project-local `source_docs` folder. `90_Storage\Reference\Source_Documents\<Project>`
is already the canonical source layer — a per-project copy has no automated
way to stay in sync with it and will just go stale (this happened once
already: a one-off script copied a project's source files into
`20_M2_Project_Management\<Project>\source_docs`, and it was never kept
current or repeated for any other project). Reference `90_Storage\Reference`
directly instead of copying from it.

Do not create a project-local `archive` folder either. Superseded generated
outputs (e.g. a Sheet retired in favor of a Doc of the same name) go to the
single workspace-wide archive tree instead:

`90_Storage\Retired\20_M2_Project_Management\<Project>\...`

This keeps one place to look for retired artifacts rather than two, and
mirrors the live `20_M2_Project_Management\<Project>` shape so it stays easy
to find.

Keep `_project_registry` in `20_M2_Project_Management` as a top-level,
one-row-per-project "war room" dashboard — the airplane view across every
project M2 owns, sourced from each project's `project_metrics` (see
`Templates\метрики_проекта_qa.md` §4). Columns: `Проект`, `People`,
`Статус`, `Горизонт совместной работы`, `Бизнес-риск продукта клиента`,
`Наименьший вклад в проект`, `Качество QA-процесса`.

`Статус` mirrors `project_metrics`'s `Статус проекта` row
(`Templates\метрики_проекта_qa.md` §1.0) — exactly two values, `Активен`
or `Не активен`, no third "paused" state. It's manual-only: no script sets
or clears it, no scheduled cadence flips it back; it changes only when M2
edits `project_metrics` directly. Because `Не активен` projects are
excluded from the rebuilt registry entirely (see below), a project's
`Статус` cell in the live registry is effectively always `Активен` — the
column exists for schema consistency with `project_metrics`, not because
`Не активен` rows are ever visible here.

`Наименьший вклад в проект` is the one column that isn't a direct copy —
`project_metrics` can have several `Вклад в проект: <Имя>` rows, but the
registry collapses them to one column per project. **Never average them.**
Averaging "Позитивный, Позитивный, Смешанный, Негативный" destroys exactly
the signal this dashboard exists to surface. Take the worst status present
(Негативный → Смешанный → Позитивный, worst first) and name whoever is at
that level, e.g. `Смешанный (<Имя>)` — two people tied at the
worst level both get named. If the whole team shares one status, just
state it with no name attached (there's no one specific person to flag).

Active projects only — a project not currently active, for whatever
reason (client-driven pause, official stop/cancellation), gets excluded
from the live registry rather than kept and marked inactive in place;
inactive projects don't belong in a dashboard meant for current attention.
Mechanism: set `Статус проекта` to `Не активен`
(`Templates\метрики_проекта_qa.md` §1.0), rerun
`refresh_project_registry.py` - excludes the project automatically, no
manual deletion. Keep the project folder in place as history/current
record; add a closure or status summary to `project_risk`/
`project_development_plan` first if the reason is worth recording.
Flipping the status back to `Активен` (reactivation, or correcting a
mistaken flip) brings the project back into the registry on the next
refresh.
Columns are `Проект`, `People`,
`Статус`, and the four dashboard metrics — no aliases, source-docs pointer,
or folder-navigation link; those don't belong in a summary dashboard.

For broad cross-project KT, status, or management sessions:

- split extracted facts by project first;
- update each relevant project folder separately;
- append the source and routed outputs to the project `evidence_log`;
- retire aggregate KT/batch outputs under `90_Storage\Retired\20_M2_Project_Management`
  as evidence rather than treating them as final documents.

Use living canonical project files for current state. Use append-only rows/tabs
for history and evidence. Create dated versions only for formal reporting
snapshots, monthly reports, externally shared documents, or explicit user
requests.
