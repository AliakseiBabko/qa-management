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
- `10_M1_People_Management`
- `20_M2_Project_Management`
- `80_Exports`
- `90_Archive`

No raw video/multimedia is stored in Drive — only transcripts and
documents.

`00_Source_Docs` is organized by type, not by project — a fresh chat
export or meeting transcript often isn't yet clear which project it
belongs to, so type is the more stable first split:

- `00_Source_Docs\01_Meeting_Transcripts` — 1:1s, dailies, demos, KT
  calls, shadowing calls, client/project syncs.
- `00_Source_Docs\02_Chats_and_Emails` — exported/combined chat and email
  history: people cases, HR/feedback threads, status messages,
  escalations, client/team correspondence.
- `00_Source_Docs\03_Source_Documents` — durable per-project source
  documents and company-wide reference material: `<Project>\` folders,
  the M2 homework corpus (`M2_role_vision`, `M2_personal_development_plan`,
  `M2_project_development_plan`), assessment matrices, monthly report
  examples.

Once a raw file in `01_Meeting_Transcripts` or `02_Chats_and_Emails` has
been read and its facts extracted into the relevant Sheets/Docs, move it
into `03_Source_Documents\<Project>\` if it's durable project reference
material, or to `90_Archive` if it's not needed for near-term reference —
there is no separate "processed" holding tier; `evidence_log` is what
records that a source was used and where.

Root-level folders were created outside this app's Drive API scope (via
Drive Desktop sync or manually), so the app cannot rename, move, or
delete them — this table describes the target structure; the user applies
the actual Drive changes manually. Do not assume Drive already matches
this table without checking.

When only the root folder ID is known, locate child folders by name through the Drive API. If a required child folder is missing, ask before creating it unless the user explicitly requested setup.

## M2 Project-Based Layout

Treat `20_M2_Project_Management` as a project-context workspace, not as a flat
report dump. Final M2 tabular outputs should go under:

`20_M2_Project_Management\<Project>\...`

Standard project folder shape:

- `project_risk` Google Sheet, with CSV fallback `project_risk.csv`
- `project_development_plan` Google Doc, with Markdown fallback
- `project_metrics` Google Sheet, with CSV fallback `project_metrics.csv`
  — M2-only dashboard for the project (see `Templates\метрики_проекта_qa.md`
  §2). Holds: `Горизонт совместной работы`, `Бизнес-риск продукта
  клиента`, one `Вклад в проект: <Имя>` row per person (no aggregated
  team row — every row stays visible individually at this level), and
  `Качество QA-процесса` (M2's read of `qa_process_metrics`). Never share
  this with the QA engineers whose data appears in it, even once
  folder-level sharing exists for other artifacts.
- `qa_process_metrics` Google Sheet, with CSV fallback
  `qa_process_metrics.csv` — project-wide QA-process facts (Defect Escape
  Rate, Automation Coverage, test-run counts, etc. — see
  `Templates\метрики_проекта_qa.md` §3). Filled in by the project team, not
  M2 — do not guess values into it; create empty skeleton rows with a real
  `Пояснение` instruction instead. Append-only by calendar month.
- `evidence_log` Google Sheet, with CSV fallback `evidence_log.csv`
- `people\<Person>\individual_development_plan` Google Doc, with Markdown fallback
- `people\<Person>\individual_metrics` Google Sheet, with CSV fallback
- `people\<Person>\individual_metrics_internal` Google Sheet, with CSV
  fallback — M2-only, never shared with the employee (see
  `m2-individual-qa-metrics-report` document-contract, Internal Variant).
- `m2_input\` — folder holding one M2-only Google Doc, `m2_input`: M2's
  own dated rounds of questions/answers ahead of each project-level
  rollup (see `m2-role-rules.md` Project-Level Rollups and
  `Templates\m2_input.md`). One Doc per project, not a file per cycle —
  rounds are dated sections appended to it. (No longer holds a metrics
  Sheet — that moved into `project_metrics`, see above.)
- `status_reports` for saved project status Google Docs / Markdown fallback

Do not create a project-local `source_docs` folder. `00_Source_Docs\<Project>`
is already the canonical source layer — a per-project copy has no automated
way to stay in sync with it and will just go stale (this happened once
already: a one-off script copied <Project>'s source files into
`20_M2_Project_Management\<Project>\source_docs`, and it was never kept
current or repeated for any other project). Reference `00_Source_Docs`
directly instead of copying from it.

Do not create a project-local `archive` folder either. Superseded generated
outputs (e.g. a Sheet retired in favor of a Doc of the same name) go to the
single workspace-wide archive tree instead:

`90_Archive\20_M2_Project_Management\<Project>\...`

This keeps one place to look for retired artifacts rather than two, and
mirrors the live `20_M2_Project_Management\<Project>` shape so it stays easy
to find.

Keep `_project_registry` in `20_M2_Project_Management` as a top-level,
one-row-per-project "war room" dashboard — the airplane view across every
project M2 owns, sourced from each project's `project_metrics` (see
`Templates\метрики_проекта_qa.md` §4). Columns: `Проект`,
`People`, `Горизонт совместной работы`, `Бизнес-риск продукта клиента`,
`Наименьший вклад в проект`, `Качество QA-процесса`.

`Наименьший вклад в проект` is the one column that isn't a direct copy —
`project_metrics` can have several `Вклад в проект: <Имя>` rows, but the
registry collapses them to one column per project. **Never average them.**
Averaging "Позитивный, Позитивный, Смешанный, Негативный" destroys exactly
the signal this dashboard exists to surface. Take the worst status present
(Негативный → Смешанный → Позитивный, worst first) and name whoever is at
that level, e.g. `Смешанный (<Имя>)` — two people tied at the
worst level both get named. If the whole team shares one status, just
state it with no name attached (there's no one specific person to flag).

Active projects only — when a project stops (temporarily or permanently),
remove its row from the live registry rather than marking it inactive in
place; archived projects don't belong in a dashboard meant for current
attention. Columns are `Проект`, `People`, and the four dashboard metrics —
no aliases, status flag, source-docs pointer, or folder-navigation link;
those don't belong in a summary dashboard.

Keep `_people_registry` in `20_M2_Project_Management` as a single workspace-wide
Google Sheet (CSV fallback), covering people affiliated with both the company
and clients across all projects — not a per-project list, since roles like
M1/M2/HR/DC often span multiple projects and a per-project copy would drift
out of sync. Columns:

- `Name (RU)`, `Name (EN)` — both, when the person has a known English-name
  form (useful since transcripts/chats mix scripts).
- `Email` — when known.
- `Side` — `the company`, or `Client` / `Client — <company>` when the specific
  client-side or third-party vendor company is known (e.g. a client's own
  staff vs. a separate vendor supplying people on the same project). One
  column, not two — a person's affiliation and which company they're at is
  a single fact, and splitting it produced redundant-looking rows like
  `the company, the company` for every the company person.
- `Role` — M1 / M2 / M3 / M4 / HR / DC / QA / AQA / Team Lead / PM / Client
  stakeholder / Candidate / etc. Project-scoped detail (stream, specialty)
  can go in the same cell, e.g. "AQA, stream SOLO".
- `Internal rank` — the company-internal level (Junior/Middle/Senior), for
  the company people only. This is distinct from a person's project-level
  grade fit (`Соответствие ожиданиям клиента (грейд)` in
  `individual_metrics`) — the two can differ, and neither substitutes for
  the other. Leave blank when not known; do not infer it from project-level
  grade.
- `Project(s)` — comma-separated, or "all" for company-wide roles (HR, DC).
- `Notes` — anything uncertain, stated explicitly.

`Aliases / STT variants`, `Status`, and `Confirmed by M2` were removed —
this table exists to log people who come up in discussions or calls, not to
track their lifecycle or verification state, and alias-matching in
transcripts doesn't need a dedicated column to work.

When processing a transcript/chat and a role is unclear or contradicts this
registry, ask rather than guess — this registry exists specifically because
a wrong role guess (e.g. attributing a 1:1 to the wrong person's role) can
propagate into several documents before anyone notices.

For broad cross-project KT, status, or management sessions:

- split extracted facts by project first;
- update each relevant project folder separately;
- append the source and routed outputs to the project `evidence_log`;
- archive aggregate KT/batch outputs under `90_Archive\20_M2_Project_Management`
  as evidence rather than treating them as final documents.

Use living canonical project files for current state. Use append-only rows/tabs
for history and evidence. Create dated versions only for formal reporting
snapshots, monthly reports, externally shared documents, or explicit user
requests.

`evidence_log` traceability is not just for automated sync-script runs.
Any update made conversationally — processing a transcript/chat dropped in
`00_Source_Docs\01_Meeting_Transcripts`/`02_Chats_and_Emails`, applying M2's own answers from an `m2_input` round,
analyzing a source file on request (e.g. a grade/assessment matrix) — must
also get an `evidence_log` row, with the same columns as an automated sync:
`date, source, source_type, project, routed_to, notes`. When the source is
the conversation itself rather than a file (e.g. M2's answers in a
preliminary-analysis round), use a descriptive `source` value (e.g. "M2
conversation 2026-07-08 — risk level & rollup answers") and a `source_type`
like `m2_conversation`. List every document actually touched in
`routed_to`, comma-separated, not just the first one. The point is that
`evidence_log` should answer "which live documents changed because of this
source" for every source, automated or conversational — a log that only
covers automated syncs is misleading about what actually changed.

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

## Language Rules

Apply this to any prose written into a final output (development plans,
status reports, risk narratives, summaries) — not to code, file paths, or
literal evidence citations.

- Base language is Russian. Write full sentences in Russian; do not build a
  clause out of one Russian verb followed by an English noun phrase.
  - Bad: "Ввести lightweight bug tracking rule." / "Подготовить account-level
    quality summary."
  - Good: "Ввести лёгкое правило учёта багов." / "Подготовить сводку качества
    на уровне аккаунта."
- Keep English only for things that do not have a natural standalone Russian
  name: tool/platform names (Jira, Confluence, Playwright, Cucumber, Allure,
  ReportPortal, AWS, Node.js), acronyms (QA, AQA, CI/CD, API, MVP, OKR, KPI,
  SLA, TMS, DoR, DoD, PM, BA, M1/M2/M3), and proper nouns (project names,
  stream names, product names, people's names).
- Do not use English for ordinary words that have a normal Russian
  equivalent, even if the word is common in spoken IT English: quality,
  value, risk, gap, state/status, summary, readiness, coverage (покрытие),
  bug (баг), sprint (спринт), regression (регрессия), checklist (чек-лист),
  framework (фреймворк), onboarding (онбординг), feedback (обратная связь),
  escalation (эскалация). Prefer the settled Russian IT loanword
  (баг/спринт/фреймворк/чек-лист/онбординг/эскалация/пайплайн) over the raw
  English word when one is already standard in this corpus.
- When rewriting or normalizing an existing document, preserve meaning,
  owners, dates, and numbers exactly; only change the wording style.

## API Safety

- Use the smoke-test-proven Google APIs: Drive API, Sheets API, Docs API.
- Do not print credentials, token JSON, client secrets, or authorization URLs containing sensitive parameters unless needed for user action.
- Keep `.local\google\credentials.json` and `.local\google\token.json` out of git.
- If Google API access fails, fall back to writing the established local CSV/Markdown artifact under `G:\My Drive\QA_Management` and state that the Google API write failed.
- The OAuth client only has `drive.file` scope: it can read metadata for any
  file (via `drive.metadata.readonly`), but can only rename/move/trash files
  it created itself through this API. Any file created another way — by hand
  in the Drive UI, by Drive Desktop sync, or by a different tool/OAuth
  client — will fail with `appNotAuthorizedToFile` on any write attempt. This
  is expected, not a bug to retry around: tell the user exactly which file
  and ask them to rename/move/delete it manually in the Drive UI instead.
- Always scope Drive `files.list` queries by parent (`'<parent_id>' in
  parents and name = '...'`). A bare `name = '...'` query with no parent
  filter matches same-named folders/files anywhere in the whole Drive, which
  can look like a duplicate-folder problem when the match is actually
  correctly nested somewhere else entirely (e.g. already filed under
  `90_Archive`).

## Sharing Safety

As of 2026-07-08, no folder-level Drive sharing is configured for
`20_M2_Project_Management` — everything under it is currently only as
private as the whole tree is. Documents marked "employee-facing"
(`individual_development_plan`, `individual_metrics`) and documents marked
"M2-only" (`m2_input`, `individual_metrics_internal`) live side by side in
the same `people\<Person>\` folder purely by naming convention right now,
not by actual access control.

When sharing with an employee is eventually set up:

- Share the specific `individual_development_plan` Doc and `individual_metrics`
  Sheet directly with that person — never the `people\<Person>\` folder, the
  project folder, or any parent folder. Drive supports sharing an individual
  file without exposing its parent folder; use that, not folder-level
  sharing, for anything containing more than one person's or one
  visibility-level's content.
- Never share `m2_input` or `individual_metrics_internal` with anyone. If a
  sharing request or automation ever proposes folder-level or bulk sharing
  inside `20_M2_Project_Management`, stop and flag it explicitly instead of
  proceeding — a wrong folder-level share would expose every person's
  M2-only content project-wide, not just the intended file.
- Naming something "internal" or placing it in a person's folder does not
  make it private. Until sharing is actually configured, treat every
  document in this workspace as equally exposed and do not rely on file
  naming as a substitute for real access control when advising the user.

## Docs API Editing

- When updating an existing Doc's content in bulk, clear the whole body
  (`deleteContentRange` over the full range) and reinsert with fresh
  paragraph styles, rather than patching pieces in place.
- If you do patch just one heading's text via `deleteContentRange` +
  `insertText`, its paragraph style resets to normal text — you must reapply
  `updateParagraphStyle` (e.g. `HEADING_2`) afterward, or the heading silently
  stops looking like a heading.

## Source Extraction

Source extraction may continue to write Markdown, CSV, JSON, and manifests under `80_Exports\source_extracts`. Those files are intermediate analysis artifacts, not final business documents.

When asked to analyze a `.docx` or `.xlsx` source file, use
`.agents\scripts\qa_source_extract.py` (its `extract_docx`/`extract_xlsx`
functions can be imported and called directly on a single file, without
running the full CLI) rather than reaching for a separate library — it
reads `.xlsx`/`.docx` straight from the zip/XML package with no external
dependencies, which is what already made analyzing `Assessment matrix AQA
the company.xlsx` and the <Project> source docs work without needing to
install anything.

Before extracting, check whether the file has already been processed:
look for its path (and `sha256`, via `sha256_file()`) in an existing
`manifest.csv`/`manifest.json` under `80_Exports\source_extracts\*`. A
matching `source_file` + `sha256` means the extraction is already
available at that row's `extract_file` — reuse it instead of
re-extracting. A matching path with a different `sha256` means the file
changed since the last extraction and should be re-extracted.

## Pipeline Architecture

There is no automated observer/dispatcher watching inbox folders. Every sync
this repo does — extraction (`qa_source_extract.py`), intake review
(`prepare_intake_review.py`), Sheet/Doc sync
(`sync_m2_source_docs_to_sheets.py`, `sync_m2_plans_to_docs.py`), formatting
(`format_all_sheets.py`), and the registry refresh
(`refresh_project_registry.py`) — runs because M2 asked for it in
conversation, not because a file landed in an inbox folder. Treat "drop a
chat/email in an inbox folder and it gets processed" as the intent behind
this pipeline, not as something already wired up.

`prepare_intake_review.py` is the mechanical front half of that intent —
classify what's new and log it — but it stops at exactly the same judgment
boundary as everything else here: it does not decide what a new file means
for a project, only that the file exists and (when classifiable) which
project it probably belongs to. Reading the flagged files and deciding
whether they change the picture enough to warrant an `m2_input` round is
still a conversational step.

The one piece that is safe to run mechanically without a human judgment step
is `refresh_project_registry.py` — it copies each project's already-curated
`project_metrics` dashboard rows (Горизонт/Бизнес-риск/Вклад в
проект/Качество QA-процесса) into `_project_registry`, worst-case not
averaged, with no interpretation of its own. `rollup_individual_metrics_to_project.py`
is deprecated (see README, "Current pipeline scripts") — it computed a
statistical `Команда: ...` distribution row that `project_metrics` no
longer has any place for; `refresh_project_registry.py` is its replacement
as "the mechanical step," not a rollup of `individual_metrics` at all.
Everything upstream of `project_metrics` itself — deciding what's shareable
vs. `m2_input`-only, drafting plan/risk language, weighing one person's read
of a project against another's, and writing `project_metrics` in the first
place — is a judgment step, and should stay conversational until there's a
long track record showing those judgment calls are stable and repeatable
enough to encode.
