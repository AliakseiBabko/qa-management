# Workspace Basics

Scope: the canonical Drive workspace, Sheets-vs-Docs output preference, and
the top-level folder map. Load this module for any skill that reads or
writes a final business-facing output in the Drive workspace.

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

- `00_Inbox`
- `10_M1_People_Management`
- `20_M2_Project_Management`
- `80_Exports` (optional; create only for an actual external package)
- `90_Storage` (`Reference`, `Processed_Sources`, `_System`, `Backups`, `Retired`)

No raw video/multimedia is stored in Drive — only transcripts and
documents.

`00_Inbox` is the only intake location. It is scanned recursively, but no
type subfolders are required: the agent classifies content during `start`.
An empty folder therefore means there are no unprocessed file sources.
A filename ending `_strategy`
  (e.g. `<Project>_strategy.txt`) is a project-level M2 strategy chat — a
  running, multi-month, multi-stakeholder planning/status channel for one
  project, distinct from a person-specific case chat or 1:1. See
  `m2-strategy-chat-analysis` for how these are processed. New messages for
  a project already on record go into a **new** file (e.g.
  `<Project>_strategy_2026-07-20.txt`), never appended into the existing
  one — `detect_strategy_chats.py` dedups by filename, so editing an
  already-logged file in place makes the new content invisible to it.

After successful processing, the original moves to
`90_Storage\Processed_Sources`; its immutable queue `Source` value and
content hash remain the audit identity. Durable non-intake references live
under `90_Storage\Reference`. Generated source extracts and review bundles live
under `90_Storage\_System`, never `80_Exports`. Create `80_Exports` only when an
explicit package or copy will actually be shared outside the management
workspace; otherwise the root is intentionally absent.

When only the root folder ID is known, locate child folders by name through the Drive API. If a required child folder is missing, ask before creating it unless the user explicitly requested setup.
