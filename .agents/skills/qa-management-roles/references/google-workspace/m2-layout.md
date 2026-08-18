# M2 Project-Based Layout

Scope: the M2 (`20_M2_Project_Management`) folder shape, `private`/`shared`
document locations, the 3-layer information architecture, and the `_project_registry`
dashboard. Load this module for any skill that creates or updates a final M2
project-management output. Person/operational registries (`_people_registry`,
`_skill_invocations`, etc.) live in their own modules — see
[people-registry.md](people-registry.md) and
[operational-registries.md](operational-registries.md).

Treat `20_M2_Project_Management` as a project-context workspace, not as a flat
report dump.

## Information Architecture (3 Layers)

1. **Layer 1 — Evidence and Measurements**: facts, observations, measurements,
   source logs, and history:
   - `team_shared\qa_process_metrics` — project/team QA-process measurements;
   - `people\<Person>\individual_metrics` — observable person/project contribution facts;
   - `private\process_checklist` — outsource QA-process maturity checks;
   - `private\people\<Person>\<Person> 1to1` — longitudinal per-person meeting records;
   - `private\evidence_log` — append-only trace of source facts and downstream updates.
2. **Layer 2 — M2 Decisions and Current-State Records**: interpretation, risk,
   judgment, action, and formal decision gates:
   - `private\project_metrics` — curated project outcome proxies and canonical context;
   - `private\project_risk` — living 2-tab workbook (`Summary` + `Risk Items`);
   - `private\people\<Person>\individual_risk` — private people/project risk view;
   - `private\m2_input` — formal decision gate (dated rounds of questions/answers);
   - `private\action_items` — dated actions, owners, and follow-ups;
   - `private\project_development_plan` and `people\<Person>\individual_development_plan`.
3. **Layer 3 — Executive Views**: designed for one-glance management reading:
   - `_project_registry` — 13-column master Sheet (one row per active project);
   - `_people_registry` — staffing, roles, and placement directory;
   - optional `_m2_risk_registry` — generated M2-private cross-project risk rollup;
   - executive status reports generated from Layer 2.

Layer 3 is generated mechanically from Layer 2. It must never become a competing
source of truth.

## Living vs. Dated Document Matrix

| Layer | Document | Storage Mode | Lifecycle Rule |
| :--- | :--- | :--- | :--- |
| **Layer 3** | `_project_registry` | **Living Sheet** | Recomputed mechanically by `refresh_project_registry.py` |
| **Layer 3** | `status_report` | **Dated Doc** | New file per reporting period (`status_report_YYYY-MM-DD`) |
| **Layer 2** | `project_metrics` | **Living Sheet** | Updated in place (1 row per composite identity `(Project, Metric Key, Role / Stream)`) |
| **Layer 2** | `project_risk` | **Living 2-Tab Sheet** | Updated in place (`Summary` + `Risk Items` tabs) |
| **Layer 2** | `m2_input` | **Living Doc** | Append-only rounds (dated sections from top to bottom) |
| **Layer 1** | `evidence_log` | **Append-only Sheet/CSV** | Pure historical log (never overwrite old rows) |
| **Layer 1** | `qa_process_metrics` | **Periodic Sheet** | Append-only rows per sprint/period |

## Standard Project Folder Shape

Final M2 tabular and narrative outputs go under:

`20_M2_Project_Management\<Project>\...`

- `private\project_risk` Google Sheet, with CSV fallbacks `Templates\светофор_рисков_проекта.csv`
  (for `Summary` tab) and `Templates\project_risk_items.csv` (for `Risk Items` tab) —
  living 2-tab workbook capturing 1-row-per-project executive summary and itemized risk register.
- `private\process_checklist` Google Sheet, with CSV fallback `process_checklist.csv`
  — the 12-section outsource QA process-maturity checklist (see
  `m2-project-process-checklist`, based on `Templates\аутсорс_чек_лист_qa.csv`).
  A living record, not a dated snapshot; confirmed gaps route into
  `project_risk`'s `Риск QA process` column rather than living only here.
- `private\project_development_plan` Google Doc, with Markdown fallback
- `private\project_metrics` Google Sheet, with CSV fallback `project_metrics.csv`
  — M2-only dashboard for the project (see `Templates\метрики_проекта_qa.md`
  §2). Holds canonical context keys (`Статус проекта`, `Engagement outlook`,
  `Цель клиента / Ценность QA`, `Фокус M2`, `Статус согласования (Alignment)`,
  `Сигнал capacity`), outcome proxies, and `Вклад в проект: <Имя>` rows with composite identity
  `(Project, Metric Key, Role / Stream)`. Never share this with QA engineers whose data appears in it.
- `team_shared\qa_process_metrics` Google Sheet, with CSV fallback
  `qa_process_metrics.csv` — project-wide QA-process facts (Fixed core of 4 rows:
  Production quality signal, Release / regression signal, QA process visibility,
  Automation health; plus optional project-specific metrics). Filled in by the project
  team / M2 extraction. Append-only by sprint/period.
- `private\evidence_log` Google Sheet, with CSV fallback `evidence_log.csv`
- `people\<Person>\individual_development_plan` Google Doc, with Markdown fallback
- `people\<Person>\individual_metrics` Google Sheet, with CSV fallback
- `private\people\<Person>\individual_risk` Google Sheet, with CSV
  fallback — M2-only, never shared with the employee. Living, one-row-per-
  person current-state record.
- `private\people\<Person>\<Person> 1to1` Google Sheet — longitudinal 1:1 record.
- `private\m2_input\` — folder holding one M2-only Google Doc, `m2_input`: M2's
  own dated rounds of questions/answers ahead of each project-level rollup
  (formal decision gate; see `Templates\m2_input.md`).
- `private\action_items` Google Sheet — dated actions, owners, and follow-ups.
- `private\status_reports` for saved project status Google Docs / Markdown fallback

## Google Drive Access Control (ACL) Boundaries

```text
20_M2_Project_Management/<Project>/
├── private/                              <-- Unshared (M2/M3 only)
│   ├── project_metrics
│   ├── project_risk
│   ├── m2_input
│   ├── evidence_log
│   ├── action_items
│   ├── process_checklist
│   ├── project_development_plan
│   ├── status_reports/
│   └── people/<Person>/                  <-- Unshared (M2 private 1:1s & risks)
│       ├── individual_risk
│       └── 1to1
├── team_shared/                          <-- Shared only with this project's QA team
│   └── qa_process_metrics
└── people/<Person>/                      <-- Shared explicitly with <Person> (Viewer/Editor)
    ├── individual_development_plan
    └── individual_metrics
```

> [!CAUTION]
> **Drive ACL Safety Rule:** The `<Project>` root and `<Project>/private/` MUST NOT inherit permissions from `<Project>/people/<Person>/`. Sharing `<Project>/people/<Person>/` with an employee gives them access only to their own folder, never to sibling folders or the private root.

Do not create a project-local `source_docs` folder. `90_Storage\Reference\Source_Documents\<Project>`
is already the canonical source layer — reference `90_Storage\Reference` directly instead of copying.

Do not create a project-local `archive` folder either. Superseded generated
outputs go to `90_Storage\Retired\20_M2_Project_Management\<Project>\...`.

## Executive Workspace Registry (`_project_registry`)

Keep `_project_registry` in `20_M2_Project_Management` as a top-level,
one-row-per-project "war room" dashboard — the airplane view across every active
project M2 owns, sourced mechanically from each project's `project_metrics` and
`project_risk`.

### 13 Columns and Layout Pixel Budget (1,680 px allocated within 1,780 px display budget):

1. `Проект` (120 px) — Project name
2. `People` (150 px) — Staffing with workstream tags (e.g. `<Person 1> (AQA), <Person 2> (Manual)`)
3. `Общий уровень риска` (130 px) — `Низкий` / `Средний` / `Высокий` (color-coded badge)
4. `Текущее состояние QA / результат (оценка M2)` (350 px) — One analytical statement combining QA-process evidence, current delivery facts, and evidence gaps
5. `Engagement outlook` (180 px) — Structured: `<date> [Contractual] — <Outlook> (<Confidence>)`
6. `Цель клиента / Ценность QA (гипотеза M2)` (260 px) — Higher-level hypothesis about the client's product goal and the value/role of our QA team
7. `Ранний сигнал / Прогноз` (280 px) — Composite from top active risk item (`RSK-ID: <Statement> [<Prediction Status>]`)
8. `People requiring attention` (160 px) — Mechanically derived candidate signal
9. `Действие M2` (280 px) — Primary mitigation action
10. `Уверенность в данных` (120 px) — Synthesized confidence with breakdown
11. `Следующий review` (100 px) — Next review date (`YYYY-MM-DD`)

### Top-Risk Selection & Confidence Synthesis

- **Top-Risk Selection**: deterministic priority by: (1) highest Severity (`Высокий` > `Средний` > `Низкий`), (2) earliest Expected Impact Date, (3) `Detected Late` over `Detected Early`, (4) latest `Last Changed` timestamp. Excludes `Closed` items and `Migration State = Legacy`.
- **Confidence Synthesis**: ordered `Высокая` > `Средняя` > `Низкая`. Missing defaults to `Низкая`. Synthesized confidence = $\min(\text{outcome\_conf}, \text{risk\_conf})$ when both affect conclusion.
- **Active Projects Only**: `project_metrics`'s `Статус проекта` row (`Активен` or `Не активен`) controls inclusion. `Не активен` excludes the project from the rebuilt registry automatically.

## Update Conventions & Cross-Project Intake

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

## Migration Boundary

Phase 1 is a repository documentation and graph-contract change only. Live Google Drive
folders, permissions, and business data are not modified during this phase.
