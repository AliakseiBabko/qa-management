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

- `00_Source_Docs/`: durable source documents and reference materials
- `01_Recordings/`: raw meeting recordings
- `02_Transcripts_Inbox/`: raw transcript intake
- `03_Transcripts_Processed/`: processed transcripts
- `10_M1_People_Management/`: M1 person files and people risk snapshots
- `20_M2_Project_Management/`: project-based M2 project-management outputs
- `80_Exports/`: export packages and external copies
- `90_Archive/`: archived legacy folders and backups

Final business outputs should prefer Google Sheets for tabular artifacts and Google Docs
for narrative/status artifacts when Google API access is available. Local CSV/Markdown
files remain valid as fallback, staging, source-extraction, and export artifacts.

## M2 Project Layout

M2 is organized by project context. The active project registry lives in:

`G:\My Drive\QA_Management\20_M2_Project_Management\_project_registry.csv`

and as a Google Sheet in the same Drive folder.

Each project folder follows this shape:

```text
20_M2_Project_Management/<Project>/
├─ project_risk.gsheet
├─ project_development_plan.gsheet
├─ project_metrics.gsheet
├─ evidence_log.gsheet
├─ people/<Person>/
│  ├─ individual_development_plan.gsheet
│  └─ individual_metrics.gsheet
├─ status_reports/
├─ source_docs/
└─ archive/
```

Broad KT/session sources should be split by project before updating final files.
Use `evidence_log` as the append-only trace of which source changed which project
files. Keep aggregate KT outputs in archive, not as canonical final documents.

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

## M2 batch generation

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
python .agents\scripts\reorganize_m2_project_workspace.py
```

This script creates project folders, project-local CSV fallbacks, Google Sheets,
and an M2 project registry. Treat it as a migration/setup utility, not as a
daily intake processor.

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
