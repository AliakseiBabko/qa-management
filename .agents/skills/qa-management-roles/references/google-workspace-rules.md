# Google Workspace Rules

Use this reference for QA-management skills that create or update final business-facing outputs.

## Canonical Workspace

- Google Drive root folder: `https://drive.google.com/drive/u/0/folders/1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`
- Google Drive root folder ID: `1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`
- Desktop mirror / filesystem fallback: `G:\My Drive\QA_Management`
- Local OAuth credentials: `.local\google\credentials.json`
- Local OAuth token cache: `.local\google\token.json`

Treat Google Drive as the canonical business workspace when Google API access is available. Treat `G:\My Drive\QA_Management` as the local mirror, source-file intake, and fallback path.

## Output Preference

- Use Google Sheets for genuinely tabular outputs that were previously CSV files: 1to1 records, risk traffic lights, QA metrics, and monthly KPI reports.
- Use Google Docs for narrative outputs: status reports, summaries, project and individual development plans, or chat-ready reports saved as regular documents.
- Development plans (`project_development_plan`, `individual_development_plan`) are Google Docs, not Sheets. They read as headed prose — business context, current state, a plan broken into review horizons, open decisions, risks — not one row per initiative. Forcing them into Sheet rows duplicates the same context paragraph into every row or drops it; a Doc holds it once.
- Keep CSV templates in `<repo-root>\Templates` as schema contracts for the Sheet-based families only. Do not treat them as the preferred final storage format when Google API access is available.
- It is acceptable to stage local CSV/Markdown files when needed for review, extraction, or API upload. Mark them as intermediate or fallback artifacts.

## Folder Mapping

Use the same folder names under the Google Drive root as the local mirror:

- `00_Source_Docs`
- `01_Recordings`
- `02_Transcripts_Inbox`
- `03_Transcripts_Processed`
- `10_M1_People_Management`
- `20_M2_Project_Management`
- `80_Exports`
- `90_Archive`

When only the root folder ID is known, locate child folders by name through the Drive API. If a required child folder is missing, ask before creating it unless the user explicitly requested setup.

## M2 Project-Based Layout

Treat `20_M2_Project_Management` as a project-context workspace, not as a flat
report dump. Final M2 tabular outputs should go under:

`20_M2_Project_Management\<Project>\...`

Standard project folder shape:

- `project_risk` Google Sheet, with CSV fallback `project_risk.csv`
- `project_development_plan` Google Doc, with Markdown fallback
- `project_metrics` Google Sheet, with CSV fallback `project_metrics.csv`
- `evidence_log` Google Sheet, with CSV fallback `evidence_log.csv`
- `people\<Person>\individual_development_plan` Google Doc, with Markdown fallback
- `people\<Person>\individual_metrics` Google Sheet, with CSV fallback
- `status_reports` for saved project status Google Docs / Markdown fallback
- `source_docs` for project-local source document copies or references
- `archive` for superseded generated outputs and project-local historical batches (including a Sheet retired in favor of a Doc of the same name)

Keep `_project_registry` in `20_M2_Project_Management` as the active project
index with project names, aliases, people, and source locations.

For broad cross-project KT, status, or management sessions:

- split extracted facts by project first;
- update each relevant project folder separately;
- append the source and routed outputs to the project `evidence_log`;
- archive aggregate KT/batch outputs as evidence rather than treating them as
  final documents.

Use living canonical project files for current state. Use append-only rows/tabs
for history and evidence. Create dated versions only for formal reporting
snapshots, monthly reports, externally shared documents, or explicit user
requests.

## Naming And Versioning

- Preserve existing skill naming patterns, but use Google file titles instead of local filenames.
- For tabular outputs, omit `.csv` from the Google Sheet title unless the user explicitly wants the suffix preserved.
- For Google Docs outputs, omit `.md` from the title.
- Do not overwrite existing final dated/monthly documents by default.
- If a same-title final document exists in the target Drive folder, create the next `_vN` title, for example `_v2` or `_v3`.
- Personal 1to1 Sheets are append-only longitudinal records. Update the existing person Sheet by appending a row unless the user explicitly asks for correction.

## Sheet Rules

- Preserve the template column order and meaning exactly.
- For 2D monthly report templates, preserve the workbook-like layout rather than normalizing into a database table.
- Prefer one Google Sheet per final report artifact unless the user asks for a consolidated workbook.
- When updating an existing Sheet, read the header/layout first and validate that it matches the expected template before writing.
- If the layout does not match the expected template, stop and ask whether to migrate, append anyway, or create a new version.

## Docs Rules

- Use Google Docs for saved regular status reports, development plans, and other narrative documents.
- Keep the body concise and business-facing; do not include internal evidence paths unless the user asks for evidence, except for development plans, which keep a short "Источники / Evidence" section for traceability (matching how the real source plans are already written).
- Update the living Doc in place for development plans; Google Docs version history preserves prior revisions, so do not create a new dated Doc for routine updates.
- Reviewer feedback on a plan belongs in native Google Docs comments anchored to the relevant paragraph, not as an appended text block or a separate column.
- Preserve versioning behavior by title.

## API Safety

- Use the smoke-test-proven Google APIs: Drive API, Sheets API, Docs API.
- Do not print credentials, token JSON, client secrets, or authorization URLs containing sensitive parameters unless needed for user action.
- Keep `.local\google\credentials.json` and `.local\google\token.json` out of git.
- If Google API access fails, fall back to writing the established local CSV/Markdown artifact under `G:\My Drive\QA_Management` and state that the Google API write failed.

## Source Extraction

Source extraction may continue to write Markdown, CSV, JSON, and manifests under `80_Exports\source_extracts`. Those files are intermediate analysis artifacts, not final business documents.
