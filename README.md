# qa-management

Repository for QA-management agent infrastructure.

This repo stores:

- shared skill definitions under `.agents/skills/`
- canonical CSV templates under `Templates/`
- shared 1to1 analysis rules under `.agents/skills/qa-1to1-analysis/references/`
- shared M1/M2 role rules under `.agents/skills/qa-management-roles/references/`

Operational data and generated report files are managed in the QA Management Google Drive workspace:

`https://drive.google.com/drive/u/0/folders/1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`

Google Drive root folder ID:

`1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`

The desktop mirror / filesystem fallback is:

`G:\My Drive\QA_Management`

Current Drive layout:

- `00_Source_Docs/`: everything that came in about a project or the
  business, organized by type:
  - `01_Meeting_Transcripts/`: raw meeting transcripts
  - `02_Chats_and_Emails/`: raw chat/email exports
  - `03_Source_Documents/`: durable per-project source documents and
    company-wide reference material (project folders, homework corpus,
    assessment matrices, monthly report examples)
- `10_M1_People_Management/`: M1 person files and people risk snapshots
- `20_M2_Project_Management/`: project-based M2 project-management outputs
- `80_Exports/`: export packages and external copies
- `90_Archive/`: archived legacy folders and backups

No raw video/multimedia is stored in Drive — only transcripts and
documents. Some root-level folders were created outside this repo's
Google API scope (via Drive Desktop sync or manually), so they can't be
renamed/deleted through the API — Drive-side folder changes need to be
applied manually. See
`.agents/skills/qa-management-roles/references/google-workspace-rules.md`
for the full folder-mapping and Sharing Safety notes.

Final business outputs should prefer Google Sheets for tabular artifacts and Google Docs
for narrative/status artifacts when Google API access is available. Local CSV/Markdown
files remain valid as fallback, staging, source-extraction, and export artifacts.

## M2 Project Layout

M2 is organized by project context. Two workspace-wide Sheets sit directly
under `20_M2_Project_Management`:

- `_project_registry` — one row per **active** project, the top-level "war
  room" dashboard (Проект, People, Горизонт совместной работы, Бизнес-риск
  продукта клиента, Наименьший вклад в проект, Качество QA-процесса).
  Stopped projects are removed from this registry, not marked inactive.
- `_people_registry` — every person (the company and client-side) mentioned
  across projects, with role/side/confirmation status. See
  `google-workspace-rules.md` for the full column list.

Each project folder follows this shape:

```text
20_M2_Project_Management/<Project>/
├─ project_risk.gsheet
├─ project_development_plan.gsheet
├─ project_metrics.gsheet       # M2-only dashboard, see below — never shared with the team
├─ qa_process_metrics.gsheet    # engineer-filled, project-wide QA-process facts
├─ evidence_log.gsheet
├─ m2_input/
│  └─ m2_input.gdoc             # M2-only dated rounds of judgment/context
├─ people/<Person>/
│  ├─ individual_development_plan.gdoc   # employee-visible
│  ├─ individual_metrics.gsheet          # employee-visible
│  └─ individual_metrics_internal.gsheet # M2-only, never shared with the employee
└─ status_reports/
```

There is no per-project `source_docs/` or `archive/` folder — reference
`00_Source_Docs/03_Source_Documents/<Project>` directly, and retired artifacts go to the
single workspace-wide `90_Archive/20_M2_Project_Management/<Project>/`
tree instead of a local copy that would go stale.

**Employee-visibility boundary**: `individual_development_plan` and
`individual_metrics` are shared with/seen by the employee they're about.
`project_metrics`, `qa_process_metrics`'s aggregation, `individual_metrics_internal`,
and `m2_input` are M2-only and must never be shared with that boundary in
mind — see `google-workspace-rules.md`, Sharing Safety.

**Update chain**: `individual_metrics`/`individual_development_plan` (per
person) → `project_metrics` (per project) → `_project_registry` (across
all projects). A new source that changes something at the person level
should update the whole chain in the same pass — see `m2-role-rules.md`,
Cascading Updates. Metric definitions and which artifact each one belongs
in: `Templates/метрики_qa_по_проекту.md` (individual) and
`Templates/метрики_проекта_qa.md` (project/QA-process/dashboard).

Broad KT/session sources should be split by project before updating final files.
Use `evidence_log` as the append-only trace of which source changed which project
files — including conversational updates, not just automated syncs. Keep
aggregate KT outputs in `90_Archive`, not as canonical final documents.

## Source extraction

Use the dependency-free extractor when Office source documents need to be converted into
analysis-friendly Markdown, CSV, and JSON files:

```powershell
python .agents\scripts\qa_source_extract.py
```

Default input:

`G:\My Drive\QA_Management\00_Source_Docs`

Default output:

`G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`

The extractor does not modify source documents. It writes a `manifest.csv` and project-level
subfolders with DOCX text as Markdown and XLSX sheets as CSV. These are intermediate
analysis artifacts, not the preferred final business output format.

## Google API Smoke Test

Use the smoke test before replacing CSV outputs with Google Sheets or Google Docs updates.
It creates temporary files in one folder, writes and reads test content, and trashes the
temporary files by default.

Prerequisites:

- Google Cloud project: `qa-manage-integration`
- Enabled APIs: Google Drive API, Google Sheets API, Google Docs API
- OAuth Desktop client JSON downloaded to `.local/google/credentials.json`
- Python packages:

```powershell
python -m pip install google-api-python-client google-auth google-auth-oauthlib
```

Run with a harmless test folder ID:

```powershell
python .agents\scripts\google_api_smoke_test.py --folder-id <GOOGLE_DRIVE_FOLDER_ID>
```

If IT provides a service account instead of OAuth Desktop credentials, share the
test folder with the service account email and run:

```powershell
python .agents\scripts\google_api_smoke_test.py --auth service-account --credentials .local\google\service-account.json --folder-id <GOOGLE_DRIVE_FOLDER_ID>
```

Add `--keep-files` if you want to inspect the created Sheet and Doc manually.

## M2 batch generation (legacy first-pass tools)

`generate_m2_outputs.py` (stays in `.agents\scripts\` — the current pipeline
imports functions from it) and `.agents\scripts\legacy\reorganize_m2_project_workspace.py`
were the original bulk-migration tools for turning raw extracted source
docs into the first version of each project's folder. `.agents\scripts\legacy\process_remaining_intake.py`
is a similar one-off with hardcoded dates/people/rows from a specific past
intake batch. None of these are the day-to-day pipeline anymore — see
"Current pipeline scripts" further down for what actually runs now. The two
scripts under `.agents\scripts\legacy\` are one-off/historical by
construction (hardcoded paths, dates, or batches) and are not meant to be
rerun against current live project folders at all; `generate_m2_outputs.py`
is safer to invoke standalone but still only produces rough first-pass
output that needs the current templates applied on top.

After extraction, generate first-pass M2 CSV outputs with:

```powershell
python .agents\scripts\generate_m2_outputs.py
```

Default input:

`G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`

Default output:

`G:\My Drive\QA_Management\20_M2_Project_Management\generated_from_source_YYYY-MM-DD`

The generator preserves source evidence and writes draft CSVs for project risks, project metrics,
individual QA metrics, project development plans, and individual development plans.

To reorganize generated or KT-derived M2 data into project folders, use:

```powershell
python .agents\scripts\legacy\reorganize_m2_project_workspace.py
```

This script creates project folders, project-local CSV fallbacks, Google Sheets,
and an M2 project registry. It is a one-off migration/setup utility from
before the current per-project folder shape existed — do not rerun it.

## Current pipeline scripts

These are what actually runs day to day, once a project's folder already exists:

- `show_project_state.py` — read-only dump of a project's canonical
  documents (`--project <Name>`) and/or the two workspace-wide registries
  (`--registries`). Creates nothing, even for a typo'd/missing project name
  (reports it as missing rather than creating a stray folder, unlike the
  sync scripts' `find_or_create_folder`). Run this first, before manually
  reading Sheets/Docs one at a time, whenever a conversational update needs
  to see current state. `--summary` (alone, or with `--project`) skips the
  full dump and prints a one-liner per project instead — People count, risk
  level + snapshot date, evidence_log's most recent entry date — cheap
  triage before deciding a full dump is even warranted (e.g. a strategy
  chat that reads as mostly non-QA staffing/contract content).
- `pipeline_common.py` — not a script to run; shared helpers other scripts
  should import instead of re-inlining them: `get_services()`
  (`load_credentials` + `build_services`); `get_last_round_status()` (reads
  an m2_input Doc and reports the latest round's date and whether its
  "Ответ и общие соображения M2" section is still empty — used by
  `show_project_state.py --summary` to flag a pending round without opening
  the Doc); `append_doc_round()` to open a brand-new dated round at the end
  of the Doc; and `append_to_pending_round()` to add an addendum to a round
  that's still pending, inserted *before* the empty answer heading rather
  than after it. Using `append_doc_round()` for the latter case will make
  `get_last_round_status()` wrongly read the round as answered — this
  actually happened once (<Project>, 2026-07-13, see its evidence_log) before
  the dedicated function was added.
- `sync_m2_source_docs_to_sheets.py` — syncs source docs into `evidence_log`
  and `individual_metrics` Sheets (real append-only merge, not overwrite).
  `project_risk` and `project_metrics` are bootstrap-only: it creates a
  rough first-pass Sheet from mechanical extraction if one doesn't exist
  yet, but never touches either once a real one exists — both need M2's own
  synthesis (single coherent row/column per project, not a mechanical
  `label: value` pull from source docx), which this script structurally
  cannot produce.
- `sync_m2_plans_to_docs.py` — syncs `project_development_plan` and
  `individual_development_plan` as Google Docs (narrative documents, not
  Sheets).
- `scaffold_project_dashboard.py` — creates the missing M2-only artifacts
  for a project (`qa_process_metrics`, `individual_metrics_internal` per
  person, `m2_input`, and a placeholder `project_metrics` only if one
  doesn't exist yet). Structure only, no fabricated judgment — the actual
  `project_metrics` rows and `m2_input` rounds still need M2's real read
  of the project. Safe to rerun; every artifact is created only if
  missing, and an existing `project_metrics` is always left untouched.
- `format_all_sheets.py` — applies consistent formatting (wrap, alignment,
  column widths targeting ≤5 lines) across every Sheet under
  `20_M2_Project_Management`. Safe to rerun anytime after a schema change.
- `qa_source_extract.py` — dependency-free DOCX/XLSX → Markdown/CSV
  extractor; check `80_Exports/source_extracts/*/manifest.csv` for an
  existing extraction before re-running it on the same source file.
- `prepare_intake_review.py` — intake assistant: finds files in
  `01_Meeting_Transcripts`/`02_Chats_and_Emails`/`03_Source_Documents` not
  yet in `evidence_log`, reuses an existing extraction by sha256 instead of
  re-extracting, classifies each by project (folder-based under
  `03_Source_Documents`, filename-matched against `_project_registry`/
  `_people_registry` under the inbox folders), appends `evidence_log` rows,
  and writes a review bundle to `80_Exports/intake_review/YYYY-MM-DD.md`.
  Genuinely ambiguous files are left `UNCLASSIFIED` rather than guessed —
  route those manually. Stops there: does not touch `m2_input`,
  `project_risk`, `project_development_plan`, `project_metrics`, or status
  reports — read the bundle and start a normal preliminary-analysis round
  for anything that matters. Use `--dry-run` to preview without writing.
- `detect_strategy_chats.py` — the same kind of mechanical front half, but
  specifically for `<Project>_strategy*.txt` files (project-level M2
  strategy chats, see `m2-strategy-chat-analysis`): classifies by filename
  prefix, parses Google Chat's copy-paste message-header format to resolve
  the file's date range (a heuristic against file mtime — Google Chat
  headers carry no year and use relative weekday-only timestamps for
  recent messages), appends one `evidence_log` row per new file, and writes
  `80_Exports/intake_review/strategy_chats_YYYY-MM-DD.md`. Dedups by exact
  filename, not content — a new batch of messages must land in a new file,
  never appended into an already-logged one. Also stops at fact
  extraction; `--dry-run` previews without writing.
- `refresh_project_registry.py` — the one script safe to run mechanically
  with no judgment step: copies each project's already-curated
  `project_metrics` dashboard values into `_project_registry`
  (worst-known-status for `Наименьший вклад в проект`, never averaged). Safe
  to rerun anytime after a `project_metrics` update.
- `rollup_individual_metrics_to_project.py` — **deprecated**, refuses to
  run. Superseded by M2 writing per-person `Вклад в проект: <Имя>` rows
  directly in `project_metrics` (see `Templates/метрики_проекта_qa.md` §1)
  and `refresh_project_registry.py` propagating those rows onward.

There is no automated observer/dispatcher watching inbox folders — every
sync above runs because M2 asked for it in conversation. See
`google-workspace-rules.md`, Pipeline Architecture.

## Status Reports

Short chat-ready M2 project status reports are handled by:

- `.agents/skills/m2-project-status-report`

Regular reports should be saved as Google Docs under `20_M2_Project_Management/status_reports`
when Google API access is available. Local Markdown fallback path:

`G:\My Drive\QA_Management\20_M2_Project_Management\status_reports`

Use project name and report date in the filename.

## Monthly Reports

Monthly KPI report skills:

- `.agents/skills/qa-management-roles`
- `.agents/skills/m1-monthly-report`
- `.agents/skills/m2-monthly-report`

CSV templates:

- `Templates/m1_monthly_report.csv`
- `Templates/m2_monthly_report.csv`

Source examples:

- `G:\My Drive\QA_Management\00_Source_Docs\M1_monthly_report.xlsx`
- `G:\My Drive\QA_Management\00_Source_Docs\M2_monthly_report.xlsx`

The M1 workbook contains real report examples. The M2 workbook is treated as an example/calculator
unless explicitly provided as a real report for a target month.
