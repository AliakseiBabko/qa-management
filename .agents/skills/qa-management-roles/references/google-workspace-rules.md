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

- Use Google Sheets for tabular outputs that were previously CSV files: 1to1 records, risk traffic lights, QA metrics, development plans, and monthly KPI reports.
- Use Google Docs for narrative outputs: status reports, summaries, prose plans, or chat-ready reports saved as regular documents.
- Keep CSV templates in `<repo-root>\Templates` as schema contracts. Do not treat them as the preferred final storage format when Google API access is available.
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

- Use Google Docs for saved regular status reports and other narrative documents.
- Keep the body concise and business-facing; do not include internal evidence paths unless the user asks for evidence.
- Preserve versioning behavior by title.

## API Safety

- Use the smoke-test-proven Google APIs: Drive API, Sheets API, Docs API.
- Do not print credentials, token JSON, client secrets, or authorization URLs containing sensitive parameters unless needed for user action.
- Keep `.local\google\credentials.json` and `.local\google\token.json` out of git.
- If Google API access fails, fall back to writing the established local CSV/Markdown artifact under `G:\My Drive\QA_Management` and state that the Google API write failed.

## Source Extraction

Source extraction may continue to write Markdown, CSV, JSON, and manifests under `80_Exports\source_extracts`. Those files are intermediate analysis artifacts, not final business documents.
