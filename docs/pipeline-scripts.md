# Pipeline Scripts

Full reference for the extraction/generation/operational scripts under
`.agents/scripts/` — what actually runs day to day, plus the legacy
first-pass tools kept only for historical context. See
[README.md](../README.md) for the top-level orientation this document
expands on.

## Source extraction

Use the dependency-free extractor when Office source documents need to be converted into
analysis-friendly Markdown, CSV, and JSON files:

```powershell
python .agents\scripts\qa_source_extract.py
```

Default input:

`G:\My Drive\QA_Management\00_Inbox`

Default output:

`G:\My Drive\QA_Management\90_Storage\_System\extracts\source\YYYY-MM-DD`

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

## M2 batch generation (legacy first-pass tool)

`generate_m2_outputs.py` (stays in `.agents\scripts\` — the current pipeline
imports functions from it) was one of the original bulk-migration tools for
turning raw extracted source docs into the first version of each project's
folder. It is not the day-to-day pipeline anymore — see "Current pipeline
scripts" further down for what actually runs now. It is safer to invoke
standalone than the other original migration tools were (removed from this
repo — see Git history if the one-off migration logic is ever needed again;
they were one-off/historical by construction, hardcoded with real project
data, and not meant to be rerun against current live project folders at
all), but still only produces rough first-pass output that needs the
current templates applied on top.

After extraction, generate first-pass M2 CSV outputs with:

```powershell
python .agents\scripts\generate_m2_outputs.py
```

Default input:

`G:\My Drive\QA_Management\90_Storage\_System\extracts\source\YYYY-MM-DD`

Default output:

`G:\My Drive\QA_Management\20_M2_Project_Management\generated_from_source_YYYY-MM-DD`

The generator preserves source evidence and writes draft CSVs for project risks, project metrics,
individual QA metrics, project development plans, and individual development plans.

Reorganizing generated or KT-derived M2 data into project folders (creating
project folders, project-local CSV fallbacks, Google Sheets, and an M2
project registry) was previously a one-off migration/setup script from
before the current per-project folder shape existed; it has been removed
from this repo since its logic was hardcoded around a specific real past
migration batch. Recreate it fresh if a similar one-off migration is ever
needed again, rather than reusing hardcoded historical data.

## Current pipeline scripts

These are what actually runs day to day, once a project's folder already exists:

- `management_dialogue.py` — project-local wrapper around the shared,
  dependency-free coordinator in `C:\Users\User\Documents\ai-skills\scripts\`,
  with plans and state stored in private `C:\Users\User\Documents\ai-management\management\`.
  Any `--unresolved` entry puts the dialogue into `waiting_for_user`; `next`
  is rejected until a user decision is recorded.

- `link_management_adapters.py` — project-local wrapper that recreates the
  machine-local junction to the canonical private
  `ai-management/skills/qa-management-roles` skill after a fresh clone.
  multi-model implementation-plan dialogue. `init` creates a state file for a
  canonical plan and agent rotation; `next` writes a targeted model brief with
  plan hash, acceptance criteria, unresolved items, and decisions;
  `complete-turn` records saved artifacts, changed files, revision hashes,
  validation evidence, and open questions; `decision`, `user-input`, `verify`,
  `close`, and `status` manage control points. It does not call model APIs,
  inject prompts into GUI sessions, or bypass subscription limits.

- `show_project_state.py` — read-only dump of a project's canonical
  documents (`--project <Name>`) and/or the two workspace-wide registries
  (`--registries`). Creates nothing, even for a typo'd/missing project name
  (reports it as missing rather than creating a stray folder, unlike the
  sync scripts' `find_or_create_folder`). Run this first, before manually
  reading Sheets/Docs one at a time, whenever a conversational update needs
  to see current state. `--summary` (alone, or with `--project`) skips the
  full dump and prints a one-liner per project instead — People count, risk
  level + updated date (`Дата обновления` — `project_risk` is a living
  one-row-per-project Sheet, not a dated snapshot series), evidence_log's
  most recent entry date — cheap
  triage before deciding a full dump is even warranted (e.g. a strategy
  chat that reads as mostly non-QA staffing/contract content). In the full
  dump, `evidence_log` defaults to the last 10 rows (`--evidence-tail N` to
  change, `0` for the full log) — it's an append-only audit trail that only
  grows, and most conversational updates only need what happened recently.
  Targeted reads (Phase 3) allow querying specific docs: `--document <Name>`,
  `--person <Name>`, `--since YYYY-MM-DD` (filter rows by date), and `--limit N`
  (truncate rows/paragraphs). Passing `--json` emits a strict JSON envelope
  instead of plain text, trapping errors safely and buffering output for
  programmatic consumption.
- `search_workspace.py` — Phase 5 deterministic query interface over the
  private workspace mirror. Read-only by definition; supports literal-path
  `search` across `HEAD` (or any valid `--ref`) and first-parent traversal
  `history` search, joining matches to exact source queue runs and export
  manifests. Constrained entirely to the defined canonical root paths (`.md`
  and `.csv`) and `_source_text/blobs/v1/*.txt` source files. No vector/FTS
  indexes or model calls; powered entirely by `git --literal-pathspecs grep`.
  See `.agents/references/search-cookbook.md` (Phase 12) for worked
  examples — "where was X last mentioned", "what changed since date",
  canonical-only vs. source-only search, one run by run-id, and when to
  prefer `show_project_state.py` instead (live Drive vs. the mirror's last
  committed snapshot). See `.agents/references/operator-prompts.md`
  (Phase 15A) for ready-made prompts covering `recommend-next`, gate
  answers, project-knowledge search, inbox cleanup, and qa-retro.
- `migrate_m2_visibility_layout.py` — one-time, idempotent Drive migration
  for the M2 permission-boundary layout. `audit` is read-only and reports
  planned moves plus unrecognized artifacts; `apply` creates only the
  required `private`, `team_shared`, and per-person `shared` folders and
  moves unambiguous canonical artifacts while preserving file IDs. It never
  changes sharing permissions and never moves an unknown file.
- `migrate_project_risk_schema.py` — migration script for converting legacy
  single-tab `project_risk` spreadsheets and fallback CSV tables to the living
  2-tab schema (`Summary` tab with 14 columns + `Risk Items` tab with 20 columns).
  Defaults safely to `--dry-run` (read-only audit with before/after diff summary);
  requires explicit `--apply` flag to write changes. Supports both Google Drive
  and local directory trees (`--local-dir <path>`). Idempotent: already compliant
  worksheets are detected and preserved without modification.
- `migrate_qa_process_metrics_layout.py` — one-time, idempotent Drive
  migration turning every project's long `qa_process_metrics` Sheet (a
  `Период` column, one row per (metric, period)) into the wide
  sprint-per-column layout: `Метрика`, `Пояснение`, `Owner`, then one
  column per sprint. Defaults to a dry run; `--apply` writes into the same
  spreadsheet, so file IDs, links, and sharing survive. Carries over every
  `Пояснение`, `Owner`, and non-empty `Показатель` (a period earns a column
  only if something was actually measured in it), keeps any non-canonical
  metric row under its own group label, and prints - never silently drops -
  text found in the removed `Тренд` column. `--period-label "OLD=NEW"`
  renames or merges old period stamps into one column header. Rerunning it
  on an already-wide sheet only refreshes boilerplate `Пояснение` wording
  the layout change made stale, leaving M2's own appended findings intact.
  Applied across all 9 projects on 2026-09-09.
- `m2_workspace_layout.py` — not a script to run; canonical mapping from M2
  document roles to visibility folders. Readers use canonical-first,
  legacy-compatible lookup during migration; writers create only in the
  canonical visibility folder.
- `project_knowledge_workspace_layout.py` — not a script to run; canonical
  folder layout for the Project Knowledge lane (`30_Project_Knowledge`,
  Phase 13.1). Deliberately simpler than `m2_workspace_layout.py` - no
  private/team_shared/people visibility split, since this lane is private
  by default with sharing handled as an explicit, one-off action outside
  this layout. Reuses `m2_workspace_layout.py`'s generic Drive helpers
  (`drive_query`, `find_child_folder`, `ensure_child_folder`) rather than
  duplicating them. `find_*` functions never create anything; `ensure_*`
  functions create what's missing (a project folder is only created when a
  source is actually being processed into it, never by a read command).
- `pm_case_workspace_layout.py` — not a script to run; canonical folder
  layout for the PM Case Library (`40_PM_Case_Library`). The simplest of
  the three layout modules - flat, no per-project subfolder at all, since
  this lane is deliberately cross-project (real cases from any project
  land in one shared, theme-organized library). Reuses
  `m2_workspace_layout.py`'s generic Drive helpers the same way
  `project_knowledge_workspace_layout.py` does. `find_root`/`find_document`
  never create anything - the root folder and both documents are created
  only when a real case is actually being logged for the first time, never
  speculatively.
- `qa_dept_standards_workspace_layout.py` — not a script to run; canonical
  folder layout for QA Department Standards (`50_QA_Department_Standards`).
  Same flat shape as `pm_case_workspace_layout.py` - no per-project
  subfolder, two documents directly under the root
  (`qa_department_standards`, `m2_lessons_learned`). `find_root`/
  `find_document` never create anything - both are created only when a
  real entry is actually being logged for the first time, never
  speculatively.
- `resolve_drive_path.py` — read-only lookup: resolves a local path under
  the user's Google Drive-for-Desktop mirror (`G:\My Drive\QA_Management\...`)
  to its real Drive file/folder (`id`, `mimeType`, `webViewLink`), walking
  the same folder tree by name that `qa_manage.compute_source_file_hash`
  already uses internally. Exists because `.gdoc`/`.gsheet`/`.gslides`
  placeholders in that mirror have no readable bytes on disk at all - a
  direct file read fails with an I/O error even though the file looks
  normal - so this is the way to get from "a local path the user pasted or
  dropped in 00_Inbox" to something the Docs/Sheets API (or an export URL)
  can actually open, with no browser automation involved.
- `read_google_doc.py` — read-only: prints (or saves) a Google Doc's full
  plain text, given either a local Drive-mirror path (`.gdoc`, resolved the
  same way `resolve_drive_path.py` does) or a raw Docs document ID
  (`--id`). Flattens both paragraphs and table cells — a real gap in some
  of this repo's other ad hoc Docs-API text extractors, which only handle
  paragraphs. Exists so reading an arbitrary project doc (an ops runbook,
  a knowledge base, anything not already covered by `show_project_state.py`'s
  specific document set) doesn't mean re-deriving the
  `documents().get()` → text-flattening logic from scratch each time.
- `migrate_workspace_root_layout.py` — legacy-to-current source lifecycle migration.
  `audit` is read-only; `apply` fails closed if any item lacks a queue-backed
  disposition. It moves active sources to `00_Inbox`, processed originals to
  `90_Storage/Processed_Sources`, non-intake references to `90_Storage/Reference`,
  and internal generated folders from `80_Exports` to `90_Storage/_System`, preserving
  Drive IDs and permissions. Unqueued items require an explicit runtime
  `--override <item-id>=inbox|archive|reference`.
- `workspace_root_layout.py` — not a script to run; pure root-folder
  disposition and destination rules shared by the migration and tests.
- `migrate_workspace_storage_layout.py` — one-time consolidation from the
  former `30_Reference`, `_System`, and `90_Archive` roots into
  `90_Storage`. `audit` is read-only; `apply` renames/moves folders while
  preserving Drive IDs and updates only `_intake_queue.Current source`,
  leaving immutable source identity untouched.
- `pipeline_common.py` — not a script to run; shared helpers other scripts
  should import instead of re-inlining them: `get_services()`
  (`load_credentials` + `build_services`); `get_people_registry_sheet()`
  (resolves `05_People_Management/_people_registry` — every script that
  reads/writes the people registry should use this instead of its own
  `find_sheet_in_folder` call, so a future schema change has one place to
  fix); `reformat_sheet()` (recomputes column widths/row heights for one
  Sheet right after a write — `format_all_sheets.py` is otherwise the only
  thing that keeps row height in sync with edited content, so a script that
  writes without calling this leaves stale, clipped row heights behind);
  `log_skill_invocation()` (appends a row to `_skill_invocations`, the
  workspace-wide log of which skill(s) actually handled a given source —
  see `google-workspace/operational-registries.md` — use this instead of a raw Sheets write
  so `source_type` stays validated against the canonical list);
  `get_last_round_status()` (reads
  an m2_input Doc and reports the latest round's date and whether its
  "Ответ и общие соображения M2" section is still empty — used by
  `show_project_state.py --summary` to flag a pending round without opening
  the Doc); and the two intent-based entry points for writing to m2_input —
  `add_questions()` (auto-routes to opening a fresh round or extending the
  current pending one, whichever the doc calls for) and `add_answer()`
  (writes into the current pending round, raises if none is pending). Use
  these two, not the lower-level `append_doc_round()`/
  `append_to_pending_round()` they're built on — picking between those two
  manually produced a real bug once on a real project: appending answer
  content with the wrong one landed it before the empty answer heading and
  made `get_last_round_status()` wrongly read the round as still pending.
- `docs_editing.py` — importable safe Google Docs `batchUpdate` primitives
  (for any skill/ad hoc script that edits a Doc outside
  `pipeline_common.py`'s own m2_input-specific helpers), plus a CLI over
  those primitives covering both read-only verification and the
  recurring write shapes (add a dated update to an existing section,
  correct one paragraph in place, append a Change Log line) so a
  knowledge-base/case-library edit almost never needs its own bespoke
  inline script:
  ```
  python docs_editing.py headings --id <doc_id> [--levels HEADING_1,HEADING_2]
  python docs_editing.py find --id <doc_id> --text "<substring>"
  python docs_editing.py end-index --id <doc_id>
  python docs_editing.py append-section --id <doc_id> --heading "<exact heading text>" --text-file <path> [--style STYLE] [--dry-run]
  python docs_editing.py replace-paragraph --id <doc_id> --prefix "<unique leading text>" --text-file <path> [--style STYLE] [--dry-run]
  python docs_editing.py append-end --id <doc_id> --text-file <path> [--dry-run]
  python docs_editing.py insert-at --id <doc_id> --index <n> --text-file <path> [--style STYLE] [--dry-run]
  ```
  Exists because verifying a heading structure or a just-written passage
  previously meant a full `read_google_doc.py` export - real cost on this
  workspace's larger Docs (some run past 300K characters) when only a few
  lines were actually needed - and because the write shapes above
  previously meant writing, running, and (on Windows) getting a fresh
  approval for a new one-off inline Python script nearly every single
  time a Project Knowledge/PM Case Library pass needed to add or correct
  one passage; this collapses that into one already-known, already-tested
  command. Every subcommand calls the same single `documents().get()` a
  full export would use, but prints only a compact, truncated preview -
  never the full document body. `--text-file` (never inline `--text`)
  sidesteps shell-quoting problems entirely for multi-paragraph or
  Cyrillic content - write the content with the `Write` tool first, then
  pass its path. Every write subcommand supports `--dry-run` to preview
  the exact insertion point and a text preview without calling the API.
  Use `read_google_doc.py` instead when an actual full-text read/export is
  what's needed.
  `list_headings()`/`find_paragraph_containing()`/`document_end_index()`/
  `find_paragraph_by_prefix()`/`section_end_index()` are the underlying
  read-only inspection functions (find a section's boundaries via its
  exact heading text - same-or-broader-level heading ends the section,
  correctly skipping nested sub-headings; locate a passage to correct,
  either by substring or by a uniquely-matching leading prefix - the
  latter raises instead of guessing when the prefix is ambiguous; find the
  true end-of-document insertion point) - importable directly, same as
  the write helpers below. `DocEdit` + `safe_batch_insert_text()` (built
  on the pure, directly-testable `build_batch_insert_requests()`) is the
  fix for a real corruption incident: pass insertions in any order,
  indexed against one earlier `documents().get()` snapshot, and it always
  sorts them descending by index before building the `batchUpdate`
  request list — a lower-index insert applied before a higher-index one
  silently invalidates the higher one's precomputed (now-stale) index,
  and its text lands mid-word/mid-paragraph inside whatever the first
  insert just added, exactly what happened once on a real document. Every
  inserted range also gets an explicit `updateParagraphStyle` (never left
  to inherit from whatever paragraph happens to sit at the insertion
  point — the same heading-inheritance gotcha
  `pipeline_common._insert_blocks` already guards against, generalized
  here). `delete_and_reinsert()` is the repair primitive for exactly that
  corruption shape: delete a misplaced range and re-insert the corrected
  text elsewhere in one call, ordered the same safe way - the CLI's
  `replace-paragraph` is this primitive plus `find_paragraph_by_prefix()`
  wired together as one command. Prefer the CLI (or these primitives)
  over hand-writing `batchUpdate` request lists in a one-off script.
- `markdown_to_docs.py` — importable Markdown → Google Docs engine: the
  supported Markdown subset (headings, paragraphs with `**bold**`,
  bullet/numbered lists, tables, fenced code, images), `parse()` into
  blocks, the Docs append primitives, `create_or_reset_doc()`,
  `render_blocks()`, and the dry-run helpers `block_counts()`/
  `print_outline()`. Every insert goes at the document's current end
  index, one batch per block, so no edit's index is ever computed against
  a state a later edit already shifted. Not a CLI — use
  `publish_markdown_doc.py` (generic) or `publish_perf_report.py`
  (performance sessions). Images embed only by uploading to Drive and
  granting `anyone/reader`, so `share=False` refuses rather than sharing
  silently.
- `publish_markdown_doc.py` — publish any local Markdown file as a Google
  Doc in a named folder: `--folder-id`, or `--folder-path` for a path
  under the workspace root (resolved by name, like `resolve_drive_path.py`),
  or `--doc-id` to replace an existing Doc's body instead of creating a
  second copy. `--dry-run` prints the parsed outline without touching the
  API; `--share-images` is required before any embedded image is uploaded
  and link-shared (without it an image block is a hard error, since
  feedback/report documents are text). Used by the Assessments &
  Interviews skills, which author their report as reviewable local
  Markdown first. For a *targeted* edit inside an existing Doc — append
  one section, replace one paragraph — use `docs_editing.py` instead; this
  script only ever writes a whole document.
- `publish_perf_report.py` — the performance-session bridge on top of
  `markdown_to_docs.py`: takes a session directory (`<session>/report.md`
  plus its chart PNGs), prechecks that every referenced chart exists,
  defaults the Doc title from the session name, and refuses to publish
  images under `--no-share`. `--dry-run`, `--folder-id`, `--doc-id` as
  above.
- `publish_department_artifacts.py` — publish this M2's per-project
  artifacts into the department's shared folder (the `QA Common` shared
  drive, folder `M2 / DC Projects AQA`), one `<Project>_<Surname>` folder
  per active project. Writes Drive **shortcuts**, never moves or copies:
  the pipeline resolves these documents by their path under
  `20_M2_Project_Management/<Project>/`, so a move breaks every script
  that walks that tree and a copy goes stale on the next skill write. A
  shortcut only opens if its *target* is shared, so publishing also
  grants `reader` to the department groups — both steps together, and
  `--unpublish` reverses both. `ARTIFACTS` is deliberately limited to
  `project_development_plan`, `project_metrics` and `qa_process_metrics`;
  the audience is the whole QA/AQA department, so adding `project_risk`,
  `individual_*`, `m2_input` or `evidence_log` is a disclosure decision,
  not a config tweak. Closed projects are skipped by name
  (`CLOSED_PROJECTS`) because `_project_registry` has no binary status
  column to derive that from. Default is a dry run; `--apply` writes,
  `--verify` audits that every shortcut resolves and is department-readable.
  All Drive calls pass `supportsAllDrives` — without it a create against
  the shared drive fails with a bare 404.
- `assessment_workspace_layout.py` — pure layout rules for
  `60_Assessments_And_Interviews` (find/ensure the lane root, a session
  *type* folder, a person folder; `find_session_document`, `find_index`,
  `session_document_name`, `INDEX_COLUMNS`). Type-first, per-session,
  append-only: `<root>/<type folder>/<Person>/<YYYY-MM-DD>_<role> - <Person>`,
  because the session type owns the assessment criteria and the output
  form. `find_*` never creates anything; `ensure_*` creates only what a
  real session being processed needs. Same shape and same reuse of
  `m2_workspace_layout`'s Drive helpers as
  `qa_dept_standards_workspace_layout.py`.
- `ai_adoption_workspace_layout.py` - pure layout rules for
  `55_AI_Adoption` (find/ensure the lane root and its `reviews/`
  subfolder; `find_document` for the workspace-level knowledge base
  documents - the three tiers plus the Russian derived edition of tier 3, whose
  source is recorded in `DERIVED_EDITIONS`;
  `review_document_name`/`parse_review_document_name`, and
  `find_reviews`, which returns a project's reviews newest-first so a
  review pass can cite the previous one). Two shapes in one lane: a fixed
  set of workspace-level documents at the root, and an open-ended
  per-project, per-session review family under `reviews/`, named
  `<Project>_ai_adoption_review_<YYYY-MM-DD>` and never rewritten.
  `find_*` never creates anything; `ensure_*` creates only what a real
  review or processed source needs. Same shape and same reuse of
  `m2_workspace_layout`'s Drive helpers as
  `qa_dept_standards_workspace_layout.py`.
- `validate_repo.py` — mechanical consistency validation of this repo's
  convention-mirrored files (the `repo-maintenance` checklist automated):
  AGENTS.md skill table ↔ `.agents/skills/`, README/docs ↔ `.agents/scripts/`,
  `document_graph.yaml` node/alias/script/source integrity, source-type
  lists in sync between `pipeline_common.py` and
  `google-workspace/operational-registries.md`, and `Templates/` references resolving. Exit
  1 on drift; run before committing any structural change.
- `refresh_all_timeline_views.py` — one command that rebuilds every
  derived timeline view after an `action_items`/`_m1_timeline` edit:
  `refresh_timeline_registry.py` (`_timeline`), `sync_timeline_to_calendar.py
  --apply` (the "QA Management Timeline" Google Calendar), and
  `refresh_timeline_looker_view.py` (`_timeline_looker_view`, feeding the
  Data Studio report). Exists because running only one of the three left
  stale views behind on a real item; always use this instead of the
  individual scripts.
- `sync_timeline_to_calendar.py` — projects `_timeline`/`_m1_timeline`
  into the "QA Management Timeline" Google Calendar (regenerated wholesale;
  never edit the calendar directly). Normally invoked via
  `refresh_all_timeline_views.py`.
- `refresh_timeline_looker_view.py` — rebuilds `_timeline_looker_view`,
  the flattened Sheet the Looker Studio report reads. Normally invoked via
  `refresh_all_timeline_views.py`.
- `check_sensitive_data.py` — guard for AGENTS.md's no-sensitive-data
  rule. Scans the whole **commit candidate** — everything that would become
  public if you committed and pushed right now — for real person/project
  names pulled live from `_people_registry`/`_project_registry`: every
  tracked file as staged in the index, every tracked file's working-tree
  version, and untracked non-gitignored files, anywhere in the repository
  rather than only under `.agents/`. Index and working tree are scanned
  separately on purpose: a value can be staged and then removed from the
  working copy, and a working-tree-only scan would call that dirty
  candidate clean. Skips `.git/`, gitignored paths (including `.local/`),
  and binary files. Deletions are not skipped wholesale: a *staged*
  deletion contributes no candidate blob, but an *unstaged* deletion is
  still in the index, so its staged content is still scanned — that is
  what would ship on a commit right now. Symlinks and junctions are never
  followed out of the repository (a staged symlink's blob is still read as
  text, without dereferencing it). Repository-relative **paths** are
  scanned too, since a filename can leak a name a clean file body does
  not. Registry lookup is strictly read-only — a missing registry
  folder/Sheet, or a watch list that comes back empty, is a clear failure
  (exit 2), never something it creates or waves through. **Fails closed:**
  a failed `git ls-files`, a non-git `--repo`, or a truncated
  `cat-file --batch` stream exits 2 rather than reporting "no findings" —
  an unreadable repository must never look like a clean one. Output is
  metadata only: path, line number, and index/worktree/untracked. A path
  hit prints *no path* (the path is the value), only an ordinal. No stable
  per-value hash is emitted — against a registry of a few hundred names a
  truncated hash is trivially dictionary-matched back. `--repo <path>`
  scans a different checkout. A cheap net, **not** proof of safety — it matches
  only registered names as literal substrings, so company names, emails,
  phone numbers, unregistered identifiers, and paraphrased first-party
  material still need a human read against AGENTS.md. Run manually before
  committing; it is not wired into a git hook or CI.
- `check_cascade_closure.py` — deterministic half of the cascading-update
  chain: reads `.agents/document_graph.yaml` (the machine-readable version
  of `m2-role/m2-cascading-updates.md` and `m2-role/m2-project-rollups.md`'s Cascading Updates / Project-Level Rollups fan-out)
  and prints the downstream checklist for a set of touched documents —
  `--touched individual_metrics,evidence_log` offline, or `--from-log N` to
  check the last N `_skill_invocations` rows' `Documents touched`. Exit 1
  while any downstream node is unaccounted for. It only computes *which*
  documents to visit; whether each one actually changes (and what to write)
  stays agent judgment — every open item must be resolved explicitly as
  either an update or a stated "no change needed", never by silence. Run it
  at the end of any intake that routed a source into project documents. A
  new document type or dependency means editing `document_graph.yaml` in
  the same commit as the skill that introduces it.
- `commit_workspace_state.py` — data-side git history: exports every
  canonical Google Sheet/Doc under the Drive root (skipping `90_Storage`,
  `01_Recordings`, and non-native files) into the local private mirror repo
  (`~/Documents/qa-drive-mirror`, auto-initialized) and commits. Two layers
  per document: diffable (CSV per Sheet tab, Markdown/text per Doc) and
  restorable (`.xlsx`/`.docx`, plus `.values.json` for every Sheet — the
  values-only layer works even for manually-created files the `drive.file`
  scope can't export). `_manifest.json` maps restore-layer paths to live
  file IDs. After document export, it automatically calls `export_source_text.py` to
  extract and commit the text of any pending queue source. An extraction failure skips
  global pruning (leaving stale files) to guarantee partial snapshots safely fail
  verification instead of pretending to be complete. After each commit the full history
  is packed into a single-file bundle at `90_Storage\Backups\mirror.bundle`
  on Drive (disaster recovery: `git clone mirror.bundle`). Run with `-m` describing
  the pass at the end of any pass that wrote canonical documents; a no-op
  when nothing changed. One commit per pass = the whole cascade rolls back
  as one unit. The mirror holds real names and real source text: never inside this public repo,
  never a public remote. Full export (walking the entire Drive tree) remains
  the **default** - every run prints per-file export timing/counts (folders
  scanned, files considered/exported/skipped-unchanged, retries, slowest
  files); pass `--stats-out <path>` to also dump that as JSON (opt-in, not
  written by default; local output only, may contain real Drive path names).
  `_manifest.json` entries also carry a non-volatile Drive fingerprint
  (`drive_path`, `mimeType`, `headRevisionId`, `modifiedTime`) alongside the
  existing `fileId`/`name`/`kind` - old entries without these fields remain
  valid. **Phase 14B**: `--scoped --run-id <run-id>` is an opt-in mode for
  routine single-project/single-person/workspace-only-bookkeeping runs -
  it exports only that run's scope (via `scope_resolver.py`) plus
  workspace-root/lane-root bookkeeping and source-text, instead of walking
  the whole tree. It never prunes or overwrites anything outside that
  scope (out-of-scope `_manifest.json` entries and files are carried
  forward byte-for-byte); it fails closed (exits 1, full export
  recommended) if the scope, a lane, or a folder can't be resolved, or if
  `_manifest.json` is missing/malformed. Multi-project rollups and
  periodic audits should keep using full export - measured speedup there
  is minor since most of the lane is in scope anyway. Run one full export
  once after adopting `--scoped` (and anytime `90_Storage` isn't the only
  thing that changed outside the pipeline) so the manifest scoped mode
  carries forward from stays trustworthy.
- `scope_resolver.py` — Phase 14B: given a run_id, resolves its queue-declared
  scope (via the same `enumerate_run_scopes()` helper `qa_manage.py review`/
  `complete` trust) to the Drive lane(s)/folder prefixes a scoped
  `commit_workspace_state.py --scoped` export must cover. Pure queue/graph
  logic - no Drive calls. Fails closed (returns a refusal reason) rather
  than ever silently narrowing scope; warns (without blocking) when a run
  touches more than a handful of distinct project/person scopes, since
  scoped mode saves little there.
- `export_source_text.py` — invoked by `commit_workspace_state.py` or manually via CLI.
  Extracts text from file-backed sources (`.txt`, `.md`, `.docx`) of eligible types
  (`qa_1to1`, `strategy_chat`, `meeting_transcript`, `people_case_chat`). Uses a
  `_source_text_manifest.json` tracking file and content-addressed blobs
  (`_source_text/blobs/v1/<sha256>.txt`). `Source text version 1` is strictly required
  for newly processed eligible sources; legacy and `historical` sources undergo optional
  best-effort backfill. It supports strict `--json` output.

- `mirror_common.py` — not a script to run; shared helper enforcing the private mirror
  safety boundary. Validates requested paths against the public repo and Drive root,
  and restricts `git init` behavior. Used by `commit_workspace_state.py` and `qa_manage.py`.
- `rollback_from_mirror.py` — restores live documents to a state recorded
  in the mirror: `--history <path>` lists commits touching a document,
  then `--commit <sha> --path <restore-layer file>` (dry-run; `--apply`
  writes) pushes that commit's content back into the same live file ID —
  `.xlsx`/`.docx` via Drive conversion, `.values.json` via the Sheets API.
  A rollback is a change, not an erasure: log it (evidence_log +
  `_skill_invocations`, originals stay), run `check_cascade_closure.py` on
  the restored docs, then `commit_workspace_state.py` to record the
  post-rollback state.
- `qa_manage.py` — intake queue and run state machine (the durable-state
  layer; the agent keeps all judgment). **Default daily/operator command:
  `dashboard`** — run this first, before `scan`/`next`/`start`/`review`/
  `complete`, to see what needs attention. Read-only summary across the
  whole queue: runs needing the next agent action (grouped with the exact
  next command — `start` / `record-analysis` / `record-apply` /
  `resolve-edge` / `commit_workspace_state.py` / `complete`, decided by
  reusing `review`'s own evaluate-run logic), `blocked` runs with their
  reason, `finalizing` runs needing a `complete` retry, `integrity_issues`
  found by that same evaluation on finalizing/completed rows (bounded by
  `--limit`, default 20, so it stays cheap), plus a read-only `00_Inbox`
  file count (grouped by queue-known source type) and a
  `90_Storage/Processed_Sources` count by month. `--include-completed`/
  `--include-ignored` add optional listings; `--project`/`--person` filter
  to one scope. Never creates, writes, or mutates anything — it only calls
  the same find/read helpers `review` does. Once `dashboard` points at a
  run to process, **`guide <run-id>`** is the next step — read-only,
  deterministic "exactly what do I do for THIS run": identity (status,
  stage, source/current-source path, source type, route variant, scopes,
  source text version, snapshot SHA), the graph route's interpretation
  (skills, entry documents, declared scopes, whether the source is still
  in `00_Inbox`), a stage-specific checklist with exact command templates
  (missing scope fields for `needs_scope`; `record-analysis`; which entry
  documents still need `record-apply` and for which scope; which cascade
  edges still need `resolve-edge`, parsed straight out of `review`'s own
  evaluation; `commit_workspace_state.py` when closure is clean but the
  snapshot/invocation token isn't; `complete`; `resume --continue` for a
  blocked run; `mark-historical` for a `failed` run; `mark-superseded` when
  a pre-processing row's own `Reason` already flags it as superseded by a
  newer, completed run for the same source), and only the guardrails
  relevant to that stage (never a generic checklist dump). A completed run
  with no integrity problem gets "no operational action needed"; one with
  a real snapshot/invocation problem gets repair/audit guidance, never a
  mutation command — a completed run's Snapshot is treated as immutable.
  Reuses `review`/`evaluate_run` exclusively; never creates, writes, or
  mutates anything. When `guide` says a `discovered` run needs a
  source_type/variant/scope judgment call, **`classify <run-id>`** is a
  cheap read-only preview before `start` (`--max-preview-chars N` caps the
  returned excerpt, default 2000, to avoid token waste): reads `Current
  source` (falling back to `Source`) and reports deterministic format
  signals only, no AI/LLM call and no semantic judgment — line count,
  distinct speaker-like prefix count, Google-Chat-style header count,
  date/time marker count, email-header marker count. From those signals
  plus `document_graph.yaml` it lists unranked `candidate_routes`
  (source_type, variant, required scope, skills, entry documents, and the
  exact signal behind each one — never a single final choice) plus
  command templates: `guide`, one `start ...` per candidate, `ignore
  ...` when the row's own duplicate-detection `Reason` suggests it, and
  `mark-superseded ...` when it instead flags the row as superseded by a
  newer, already-completed run for the same rescanned source. Low/no
  signal means "manual classification required" and the full routed
  source-type list, not a guess. Never picks a route, never calls `start`,
  never writes anywhere, and never puts the preview text or full source
  content into the queue or this repo — only short operational summaries
  belong there; the classification decision, made after actually reading
  the source, stays with the agent. Working a specific project and want a
  shortlist instead of picking one `discovered`/`needs_scope` run by hand?
  **`recommend-next --project <Project> [--lane m2_project_management|
  project_knowledge|m1_people_management] [--focus <keyword>[,<keyword>...]]
  [--limit N]`** (Phase 15A) is a read-only convenience ranking, reusing
  `classify`'s own signal/candidate-route computation for every candidate
  it considers — never a decision. `discovered` rows are matched to the
  project by `Current source` path prefix (`00_Inbox/<Project>/...` —
  never by content, and never by the canonical `30_Project_Knowledge` lane
  path, since discovered sources live in `00_Inbox`); `needs_scope` rows
  use their already-declared `Project` field. `--lane` keeps only
  candidates whose `classify`-style candidate route(s) resolve to that
  lane via `document_graph.yaml` (explicit graph `lane`, else a
  project-scoped route defaults to `m2_project_management` and a
  person-scoped one to `m1_people_management`) — for `needs_scope` rows
  the lane comes from the already-chosen Source type/variant instead of
  re-deriving candidates. `--focus` is a ranking hint only (matches
  filename/preview/candidate-reason text) — it never infers a project/
  person scope and never changes which rows are eligible, only their
  order. Also cross-references each candidate's filename against
  `_people_registry` names and aliases (`match_person_registry()`) and
  surfaces any hits as `person_alias_matches` plus a small
  `score_breakdown["person_alias_match"]` bonus — again a ranking hint
  only, never a scope inference: it never sets or implies a project/person
  for the row, and matching is token-based (a shared distinctive word,
  typically a surname) rather than fuzzy, so it won't catch a shortened or
  transliterated first name alone (e.g. a nickname standing in for a
  formal given name) without a shared token elsewhere. Every candidate's `score_breakdown` is returned
  alongside the score so the ranking is never a black box; see the
  guardrails in its own JSON output and
  `.agents/references/operator-prompts.md` for ready-made prompts. Never
  calls `write_queue`, `start`, `archive-source`, `complete`, any
  Drive/Sheets write, mirror export, or telemetry append.
  Handing a run off to another agent
  session, or resuming one cold? **`pack <run-id>`** (`--max-preview-chars
  N`, same default) is one compact read-only handoff packet: identity
  (status/stage, `Source` vs `Current source`, source_type/variant,
  scopes, source hash, source text version, Snapshot SHA, disposition),
  `dashboard`'s category for this run, `guide`'s checklist/commands/
  guardrails, `review`'s evaluate_run summary (unresolved edges, entry
  problems, invocation/snapshot status), a `classify`-style signals+
  candidate_routes block only when the route isn't resolved yet, graph
  context (skills/entry docs/required scope, plus downstream closure
  expectations once at the closure stage), a capped source preview
  (`Current source` preferred, metadata-only for non-text files), and a
  short `agent_handoff` prose block naming what to read first, which
  skill(s) to load, the exact next command, and what not to do. Reuses
  `dashboard`/`guide`/`classify`/`review` exclusively; never creates,
  writes, or mutates anything, and never includes full source text — only
  the same capped preview `classify` returns. Once you know the exact
  command, the rest of this entry is the workflow that actually processes
  it. `scan` discovers sources into the
  workspace `_intake_queue` Sheet with (path, content-hash) identity:
  exact pairs are skipped, changed content at a known path becomes a
  superseding run, identical content at a new path is recorded as a
  duplicate. `next`/`status` are read-only. `start <run-id>` records the
  agent's classification, validated against the graph — canonical
  source_type, route variant, and explicit (project, person) scope tuples
  (`--scope "P|X"`, repeatable; never a Cartesian product; missing
  required scope becomes `needs_scope`, never a silent default).
  `record-analysis` (stage → apply) stores a short summary;
  `record-apply` (stage → closure) records a per-scope outcome for every
  route entry document (`updated` / `no_change`+reason /
  `not_applicable`+reason) — only updated entries seed the cascade;
  `resolve-edge` records closure outcomes via `closure_outcomes`'s shared
  validation; `block`/`resume [--continue]` handle gates and report the
  exact unfinished stage with everything already recorded. At closure,
  `archive-source <run-id>` moves the original from `00_Inbox` to a
  run-specific `90_Storage/Processed_Sources/YYYY/MM/<run-id>` folder,
  records its current path/disposition without changing immutable source
  identity, and requires a fresh workspace snapshot afterward. If a
  pre-processing `00_Inbox` source was intentionally edited after `scan`
  recorded it (e.g. manually adding speaker names/person-card details to a
  transcript before `start`), **`refresh-source-hash <run-id>`** explicitly
  recomputes the same short hash `scan` uses and, only if it actually
  differs, updates `Source hash` plus an appended `Reason` note and `Last
  mutation` — nothing else (never source_type/route/scope/status/stage/
  entries/outcomes/disposition). It refuses any run not in
  `discovered`/`needs_scope`/`ready`, an archived disposition, a path
  outside `00_Inbox`, or a file it can't hash the way `scan` would (not a
  plain-text extension, or undecodable as UTF-8) — so an accidental source
  replacement is never silently reconciled instead of surfaced; it never
  moves/archives/processes the file, and is never called automatically by
  `start`/`complete`. `guide`/`pack` surface a recommendation to run it
  when a pre-processing run's live file hash no longer matches the queue's
  recorded one. `complete` is
  a verification gate — requires stage=closure, valid entry outcomes and
  strict closure per every (project, person, variant) scope (a scope-less
  run is checked as the workspace scope — never zero iterations), the
  exact `run:<run-id>` token in `_skill_invocations`, and a clean mirror
  snapshot no older than the run's `Last mutation` (bumped by every queue
  transition; snapshot SHA persisted on the row). The terminal transition
  is two-phase via a retryable `finalizing` state: the *intended terminal
  representation* is committed to the mirror (verified commit, manifest
  updated, Drive bundle refreshed) before `completed` is written to the
  live queue, so a bookkeeping failure can never produce a false success
  or a stuck terminal row — and a half-finished terminal commit (dirt
  confined to the queue's own export files) is recovered idempotently on
  retry. Explicit scope args must name a declared tuple (a typo can't
  silently create a scope); `add-scope` declares one the analysis
  legitimately discovered. For a multi-scope run, `record-apply` and
  `resolve-edge` require an explicit `--project`/`--person` (a default
  would collapse into a wildcard). The other terminal states: `fail`;
  `mark-historical` (concrete `--evidence` required — an evidence_log row,
  a `_skill_invocations` date, a document revision, never a vague reason
  or unverified memory — asserts prior processing; also corrects a
  mistaken `fail`; reachable only from a pre-processing state, never once
  `processing`/`blocked` has actually started — "this predates the queue"
  stops being a truthful claim the moment work begins); `ignore`
  (`--category non_intake_course_material|reference_material|
  duplicate_data_quality|other --reason "..."` with a concrete reason
  required — a category alone is not a reason, optional `--evidence` —
  not an intake source at all, reachable only from pre-processing states);
  and `mark-superseded <old-run-id> --by-run <new-run-id> --reason "..."
  [--allow-path-change --path-change-evidence "..."]` for the specific case
  `scan` itself already names — an intentionally-edited-then-rescanned
  `00_Inbox` file whose earlier, never-started queue row now just sits
  stale next to the newer run that actually got processed. Reuses `ignored`
  rather than a new status; only reachable from a pre-processing state;
  requires `--by-run` to be an existing, `completed` run, and requires the
  old/new rows to share a recorded `Source`/`Current source` path unless
  `--allow-path-change` carries concrete `--path-change-evidence` too (a
  guard against a `--by-run` typo silently pairing unrelated runs).
  `classify`/`guide`/`pack` all proactively suggest it (never auto-apply it)
  once a pre-processing row's own `Reason` already flags this exact
  situation. Neither mutation moves or deletes the source file — a
  terminal-status queue row's (path, hash) identity already keeps `scan` from
  rediscovering it. Categorically non-intake, processed, generated,
  backup, and retired material lives under `90_Storage`, which is
  explicitly excluded from discovery and outside the only scanned root.
  All commands support `--json` for a strict programmatic contract:
  stdout is suppressed during execution, and exactly one JSON envelope containing
  the command status, structured data, warnings, and errors is
  emitted at the end. Transitions are validated against an explicit table
  (unit-tested in `.agents/tests`). The `review <run-id>` command provides a
  read-only evaluation of a run's closure/completion readiness (missing invocation
  evidence, snapshot problems, unresolved edges) without mutation.
  **`gates [--project <Name>] [--min-age-days N] [--limit N] [--json]`**
  (Phase 12) is a separate read-only M2 gate dashboard, distinct from the
  intake-queue commands above: every M2 project with a currently pending
  `m2_input` round (an open question blocking `project_risk`/
  `project_development_plan`, with `action_items` gated secondarily),
  sorted oldest first, with round age, addenda count, the first addendum's
  heading only (never the question/addendum text itself), and a
  deterministic `recommended_action` (`ask M2/user for answers` /
  `process existing source first`, when the project already has an open
  intake-queue run that might answer it / `no action yet`, for an
  effectively empty round / `manual review required` as the fallback).
  Never answers a question, writes a document, or records a closure
  outcome — pure Drive/Sheets reads (`find_folder_path`, `list_children`,
  `find_document`, `docs().get()`, `read_queue`). Use it to review what M2
  still owes an answer on, as opposed to `dashboard`'s "what does the
  intake queue need" — `dashboard` remains the default first entry point.
- `closure_outcomes.py` — persists per-edge cascade resolutions into the
  workspace `_closure_outcomes` Sheet (`record --run-id R --source A
  --target B --outcome X [--reason ...] [--project/--person/--variant]`,
  plus `list`). Outcomes are validated against the edge's kind in
  `document_graph.yaml` (direct→updated; judgment→updated/no_change+reason;
  gated→gated+reason/updated; script→regenerated) and are scope-aware —
  the same edge may resolve differently per project/person in one run.
  Records must carry the scope their edge endpoints have (`--project` /
  `--person` enforced against the graph's `scope:` fields).
  `check_cascade_closure.py --run-id R` is **strict**: every required edge
  needs a recorded outcome ("touched" alone no longer closes an edge),
  outcomes are filtered to one scope at a time (`--project`/`--person`/
  `--variant`; rows with empty scope fields apply anywhere, rows scoped
  elsewhere never do), stored rows are revalidated against the current
  graph on load, and for duplicate identities the latest row wins (so
  `gated` can later become `updated` append-only). Pure logic is
  unit-tested: `python -m unittest discover -s .agents/tests`.
- `prepare_retro.py` — read-only gatherer for the `qa-retro` improvement
  loop: finds the last `source_type=retro` row in `_skill_invocations`,
  prints every invocation row since it (flagging `feedback:` notes — the
  captured user corrections that are the loop's primary input), a
  cascade-closure check across that window (`find_direct_script_misses`
  — groups rows by project, unions each project's `Documents touched`
  across the whole window, and flags any `direct`/`script`-kind
  downstream edge left open anywhere in that project's window;
  `judgment`/`gated` edges are deliberately not auto-flagged, too noisy
  to be a useful signal), a telemetry-staleness check
  (`check_telemetry_staleness` — real queue-backed runs completed in the
  window vs whether operator-runs.csv/agent-sessions.csv got any row at
  all in that same window; coarse presence check, not per-run
  attribution, since operator-runs.csv rows never store which queue
  run_id they measured. Added after a real incident: the mandatory
  telemetry step silently stopped for 2+ weeks — 24 completed queue runs,
  zero operator-runs.csv rows — and no retro pass in between caught it,
  because nothing was comparing these two signals against each other),
  plus repo commits over the same window.
  Judgment (grouping, the once=trace / twice+=propose-an-edit threshold,
  drafting diffs, confirming a flagged candidate is a real omission) stays
  with the qa-retro skill; the retro logs its own `retro` row when done,
  which becomes the next run's window start. Pure logic is unit-tested:
  `python -m unittest discover -s .agents/tests`.
- `apply_person_card.py` — parses a person card (the Job Title/M-level/
  Prof.Level/Mentor/DC block M2 pastes in conversation) per the Person Card
  Intake mapping in `google-workspace/people-registry.md`, looks up `_people_registry`
  by email, and prints the computed Role/Internal rank/Notes plus a diff
  against any existing row. Dry-run by default; `--apply` adds a genuinely
  new row (an existing row's Name/Project(s) still need human judgment per
  the Project(s) rule, so those are never auto-written). Pass the card via
  `--file <path>`, not stdin/a heredoc — a Windows bash heredoc was found to
  silently drop the Cyrillic half of the name while building this script.
  For an existing person, also greps their currently-listed Project(s)'
  `individual_metrics`/`individual_development_plan` for a track/level
  mismatch against the card (see `m2-role/m2-metrics-attribution.md`, Вклад в проект
  Calibration) and prints a heads-up, not a resolution. Known gap: it only
  checks *current* Project(s) — someone recently moved off a project leaves
  their mismatch evidence behind in the old project's docs, invisible to
  this scan; a clean result isn't proof there's no mismatch for someone
  who's changed projects recently.
- `update_m1_risk_row.py` — mechanical write path for `m1-people-risk-report`:
  updates or adds one person's row in the living `Светофор рисков` Sheet
  (`10_M1_People_Management`). Input is a small labeled text block
  (`Сотрудник:`/`Риск с нашей стороны:`/etc., one per `--file`), same
  card-style input as `apply_person_card.py`. Only supplied fields change
  on an existing row (missing fields stay untouched); a new person needs
  all four content fields present. Validates both risk-level cells against
  the 3-level scale (`Низкий`/`Средний`/`Высокий`, no `Критический`) and
  refuses to write an invalid level. Sets `Дата обновления` to today
  automatically whenever a content field actually changes. Dry-run by
  default; `--apply` writes.
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
  for a project (`qa_process_metrics`, `individual_risk` per
  person, `m2_input`, and a placeholder `project_metrics` only if one
  doesn't exist yet). Structure only, no fabricated judgment — the actual
  `project_metrics` rows and `m2_input` rounds still need M2's real read
  of the project. Safe to rerun; every artifact is created only if
  missing, and an existing `project_metrics` is always left untouched.
  `qa_process_metrics` is scaffolded in its wide shape — the Baseline 3
  and Core 6 rows under their group labels, three fixed columns
  (`Метрика`, `Пояснение`, `Owner`) and one sprint column, named via
  `--sprint "2026-S14 (19.08-01.09)"` or left as a placeholder for the
  team to rename once `Ритм спринтов` is filled in.
- `format_all_sheets.py` — applies consistent formatting (wrap, alignment,
  column widths targeting ≤10 lines, widening profiled columns when their
  actual content needs more room) across every Sheet under both
  `10_M1_People_Management` and `20_M2_Project_Management` by default
  (`--root-folder-id` to target a different/specific folder instead,
  repeatable). Safe to rerun anytime after a schema change. `--dry-run`
  prints planned column widths per sheet without writing — worth using
  whenever the scope changes again. A single-sheet read timeout is a
  transient failure, not a real one; the script is idempotent, so just
  rerun it rather than chasing the one sheet by hand. Note that a Sheet with
  no entry in `PROFILES` gets the generic fallback treatment — grid-wide
  WRAP/LEFT/TOP, every border cleared, a grey bold row 1, content-derived
  widths and row heights — so any hand-designed workbook stored under those
  roots needs a `SKIP_SHEET_NAMES` entry, or the sweep will flatten it.
- `restore_sheet_formatting.py` — copies one tab's *formatting* (per-cell
  `userEnteredFormat`, column widths, row heights) from a `--source`
  spreadsheet onto a `--target` one, leaving values, formulas, and notes
  alone, so a target whose content has moved on since the source copy was
  taken keeps its newer content. The recovery path when `format_all_sheets.py`
  has flattened a hand-designed workbook and an untouched copy still exists
  outside the swept roots. Dumps the target's current formatting to a backup
  JSON before writing, and reports merge differences without acting on them
  unless `--merges` is passed (rewriting merges moves content between cells).
  Scope the fetch with `--max-col`/`--max-row`: asking for a full 999-row grid
  of formats can trip the HTTP client's decompression-ratio guard, and rows
  past the content usually only need their default formatting anyway.
  `--dry-run` reports the planned request count without writing.
- `qa_source_extract.py` — dependency-free DOCX/XLSX → Markdown/CSV
  extractor; check `90_Storage/_System/extracts/source/*/manifest.csv` for an
  existing extraction before re-running it on the same source file.
- `prepare_intake_review.py` — intake assistant: finds files in
  `00_Inbox` not
  yet in `evidence_log`, reuses an existing extraction by sha256 instead of
  re-extracting, classifies each by filename against `_project_registry`/
  `_people_registry`, appends `evidence_log` rows,
  and writes a review bundle to `90_Storage/_System/reviews/intake/YYYY-MM-DD.md`.
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
  `90_Storage/_System/reviews/intake/strategy_chats_YYYY-MM-DD.md`. Dedups by exact
  filename, not content — a new batch of messages must land in a new file,
  never appended into an already-logged one. Also stops at fact
  extraction; `--dry-run` previews without writing.
- `refresh_project_registry.py` — the one script safe to run mechanically
  with no judgment step: copies each project's already-curated
  `project_metrics` dashboard values into `_project_registry`, compacting
  executive text to short one- or two-sentence summaries while retaining
  detailed evidence in the source tables. It combines QA-process evidence
  and current-result evidence into one cautious analytical statement and
  derives privacy-safe
  `People requiring attention` flags from private `individual_risk` rows and
  keeps the client-goal column as a higher-level M2 hypothesis rather than a
  duplicate of QA operating metrics. The registry intentionally omits M2
  actions and a generic confidence column: actions remain in `action_items`,
  while uncertainty is stated in the analytical current-state cell. Its
  early-signal column is rendered as `signal -> plausible consequence`, using
  project-risk and person-risk evidence rather than copying raw risk notes.
  It reads the actual `Показатель` field in both legacy 7-column and current
  12-column `project_metrics` schemas; the registry itself omits the
  redundant `Owner` column because it is always M2.
  (worst-known-status for `Наименьший вклад в проект`, never averaged). A
  project whose `Статус проекта` is `Не активен` (the manual marker M2 sets
  in `project_metrics` — pause or permanent stop alike, see
  `Templates/метрики_проекта_qa.md` §1.0) is excluded from the rebuilt
  registry entirely, not copied through with that value. Safe to rerun
  anytime after a `project_metrics` update.
- `refresh_timeline_registry.py` — same mechanical spirit as
  `refresh_project_registry.py`, but for events instead of health: pulls
  every project's `action_items` rows still `Статус = Открыто` into the
  workspace-wide `_timeline` Sheet, sorted by due date, creating `_timeline`
  if it doesn't exist yet. Safe to rerun anytime after an `action_items`
  edit; see `.agents/skills/m2-timeline`.
- `refresh_m1_pr_calendar.py` — M1's analog to `refresh_project_registry.py`:
  recomputes the expected next-PR window for every person in
  `_people_registry` with a `Дата трудоустройства`/`Дата последнего PR` on
  record, writes the result to `_m1_pr_calendar` (sorted soonest-opening
  first) and applies the workspace's standard formatting to it every run
  (see `format_all_sheets.py`), no dry-run needed since it's pure
  recomputation, not a judgment call. Safe to rerun anytime after a
  `_people_registry` update; see `.agents/skills/m1-timeline`.
- `scan_open_questions.py` — same kind of mechanical front half as
  `prepare_intake_review.py`/`detect_strategy_chats.py`, but scanning
  `m2_input`/`project_risk`/`project_metrics` instead of raw source files:
  surfaces pending rounds, unactioned risk plans, and `Неизвестно` metric
  rows as candidate `action_items` rows, one bundle across all projects.
  Dedups by a `scan:<kind>:<key>` tag in `Источник` so a rerun only shows
  what's new. Stops at surfacing — turning a candidate into a real dated,
  owned action (e.g. deciding a metric gap needs a scheduled 1:1) is still
  a judgment step; read-only (print + bundle file) by default, `--write`
  appends the raw candidates directly into `action_items`.
- `rollup_individual_metrics_to_project.py` — **deprecated**, refuses to
  run. Superseded by M2 writing per-person `Вклад в проект: <Имя>` rows
  directly in `project_metrics` (see `Templates/метрики_проекта_qa.md` §1)
  and `refresh_project_registry.py` propagating those rows onward.
- `operator_telemetry_common.py` — not a script to run; Phase 11 shared
  schema for the operator-telemetry layer (see `.agents/telemetry/README.md`):
  the canonical CSV column list, the read-only measurement case catalog
  (`dashboard_overview`, `guide_discovered`, `classify_discovered`,
  `pack_discovered`, `completed_run_review`, `triage_overview`, `triage_one`,
  `search_current`, `search_history`, `show_project_state_targeted`,
  `show_project_state_full_project`), and the append/validate/diff-guard
  helpers the three scripts below share. Recording a `completed_run_review`
  (or equivalent) row after every real intake/rollup pass finishes is a
  mandatory closing step (see AGENTS.md's "Start Here" section), not just
  ad hoc measurement.
- `measure_operator_outputs.py` — runs one read-only case from the catalog
  above (or `--dry-run`s it, printing the redacted command with nothing
  executed) and measures its output footprint — elapsed time, stdout/stderr
  bytes, char count, a deterministic `chars / 4` token estimate, and a
  best-effort result/truncation count parsed from `--json` output. Refuses
  to run any `qa_manage.py` mutating verb. Writes a local run note under
  `tmp/telemetry/` (gitignored); `--append-csv` also appends a redacted row
  to `.agents/telemetry/operator-runs.csv`. A live `--target` (run id /
  project / query) is substituted only into the executed command — the
  committed row always keeps the `{target}` placeholder, never the real
  value. `--dual-write-central` (Phase 15, opt-in, requires `--append-csv`)
  additionally best-effort-mirrors the row into ai-telemetry's
  `command_runs` table via `central_telemetry_adapter.py` — see
  `.agents/telemetry/README.md`.
- `finalize_operator_run.py` — the enrichment step over
  `measure_operator_outputs.py --append-csv`: computes
  `reduction_ratio_vs_baseline` against an existing baseline row already in
  the CSV. Always appends exactly one new row and diff-guards afterward to
  confirm no other row changed. `operator-runs.csv` carries no
  `actual_*`/`total_tokens`/`estimated_cost_usd` columns (removed — every
  row ever recorded had them blank, and structurally most rows can't
  honestly attribute a shared session's token total back to one command;
  see `operator_telemetry_common.py`'s `CSV_HEADER` comment). This
  script's `estimate_cost()`/`compute_total_tokens()` functions are kept
  only because `record_agent_session.py` imports them for
  `agent-sessions.csv`, the real populated home for token/cost data.
- `check_operator_csv.py` — validates `.agents/telemetry/operator-runs.csv`:
  header match, required/numeric fields, enum values, duplicate `run_id`s,
  and a best-effort ASCII-only leak guard on the redacted-args/notes
  fields. `--diff-guard --run-id <id>` asserts the working CSV only added
  that one row versus `HEAD`.
- `extract_agent_telemetry.py` — best-effort actual-token extraction from
  local agent-runtime session logs, for `record_agent_session.py` (feeds
  `agent-sessions.csv`'s `actual_*` fields, not `operator-runs.csv`, which
  carries no such columns). Ported from the erp-web-tests
  benchmark-playwright-debugging skill's extractor, re-normalized to this
  repo's own `actual_*` CSV field names. Supports `claude`/`claude-code` (`~/.claude/projects/*/<session>.jsonl`,
  verified against this repo's own sessions), `codex`
  (`~/.codex/sessions/<Y>/<M>/<D>/rollout-*-<session>.jsonl`, including
  session_meta-linked continuation files — confirmed against a real Codex
  session log on this machine), `cline` (VSCode extension
  `taskHistory.json`), and `antigravity` (`agy` CLI, then a best-effort
  SQLite fallback — decoded plausible numbers from a real local `.db` file
  on this machine, but with no independent ground truth to confirm the
  field mapping, so lower-confidence than Claude/Codex). Antigravity may
  still require the manual-entry fallback depending on local installation
  or session shape — this
  raises a clear error pointing at `finalize_operator_run.py
  --actual-input-tokens ...` etc., a first-class supported path, not a
  workaround. Never writes raw log content anywhere, only small numeric
  summaries (to `--out`, conventionally under `tmp/telemetry/`).
- `record_agent_session.py` — appends one row to
  `.agents/telemetry/agent-sessions.csv`, the session-level counterpart to
  `operator-runs.csv`: since a session's token total can't be honestly
  attributed back to any one command within it (several `operator-runs.csv`
  rows commonly share one long session), session-wide usage gets its own
  table instead of backfilling those rows. Extracts via
  `extract_agent_telemetry.py`'s adapters (or accepts `--manual` entry),
  computes `total_tokens`/`estimated_cost_usd`, and defaults `confidence`
  from `extraction_method` (`claude_log`/`codex_log`/`cline_history`/
  `antigravity_cli` → high, `antigravity_db` → medium, manual → `manual`).
  Never touches `operator-runs.csv`; `--linked-operator-run-ids` entries
  not found there are a warning, not a failure. Same append-only/diff-guard
  model as the other CSV. Refuses (unless `--manual` or
  `--allow-duplicate-snapshot`) to append a row whose `actual_*` fields are
  byte-identical to the same `session_id`'s most recent existing row - a
  real incident produced 4 such rows in one 16-minute window (4 queue-run
  closeouts back-to-back with no new conversation turns between them),
  each individually accurate but indistinguishable from a bug on direct
  CSV review and adding zero new usage data.
- `record_task_outcome.py` — appends one row to
  `.agents/telemetry/task-outcomes.csv`, the pass-level derived closure and
  workload deliverable counterpart to `operator-runs.csv` and `agent-sessions.csv`:
  auto-extracts objective closure facts from `qa_manage.py review <run-id> --json`,
  `record-apply` entries, `closure_outcomes.py` edges, and private mirror source text
  blobs (`_source_text_manifest.json` keyed by `<run_id>:v1`). Primary mode `--from-run
  <run-id> --linked-session-run-id <session-row-id> --append-csv` runs as the final
  telemetry step after `complete`.
- `closeout_telemetry.py` — **the preferred entry point for closing out a
  completed queue-backed intake run's telemetry**: one command
  (`--run-id <id> --runtime <r> --session-id <id> [--model-label ...] [--commit]
  [--json]`) that runs `measure_operator_outputs.py --case completed_run_review`,
  `record_agent_session.py --from-run`, and `record_task_outcome.py --from-run
  --linked-session-run-id` in sequence, then all six validators
  (`check_operator_csv.py` × 3, `summarize_agent_telemetry.py --json`,
  `check_sensitive_data.py`, `git diff --check`), and reports every created row id.
  Refuses to run at all unless `qa_manage.py review <run-id>` is already `completed`;
  refuses to `--commit` if any validator failed (changes stay uncommitted with the
  exact next command printed instead). For a runtime whose adapter can't derive a
  task-scoped time window yet (only Claude/`claude-code` can today - see
  `record_agent_session.py`), records a whole-session agent-session row instead,
  with an explicit warning that it isn't task-scoped - never a silent
  mislabel. `--commit` stages only the three telemetry CSVs, never business
  documents, the queue, or the mirror. Manual step-by-step invocation of the three
  scripts above remains available for anything this wrapper doesn't cover.
- `central_telemetry_adapter.py` — Phase 14/15: not a CLI, a small
  importable module `record_agent_session.py`/`record_task_outcome.py`/
  `measure_operator_outputs.py` call when given `--dual-write-central`,
  best-effort-mirroring their already-local CSV row into the central,
  cross-project `ai-telemetry` database (`project_id=qa-management`,
  `source_system=native`) via that sibling repo's own native-write
  recording scripts. Also resolves a dual-written task row's central
  `linked_session_row_id` via a targeted read-only query, when the
  corresponding session was already dual-written. Fails soft by design -
  any central-write or link-lookup problem is a warning, never a failure
  of the local closeout that already succeeded. `closeout_telemetry.py`
  passes `--dual-write-central` by default (opt out with
  `--skip-central-write`); the three individual scripts default it off.
  See `.agents/telemetry/README.md`'s "This is legacy/local telemetry"
  section for the full picture.
- `record_telemetry.py` — Phase 17B: a thin wrapper, generated (not
  hand-edited) by the central `ai-telemetry` project's own wrapper
  generator from its canonical template, that subprocess-forwards to
  that project's own `record_*.py` scripts, with `--project-id=qa-management`
  baked in as the default. `current-session` is the kind to use at
  closeout for a no-queue pass's equivalent central row (auto-detects
  runtime/session with no extra flags in the common case, in place of
  manually passing `--dual-write-central`) — does not replace the
  mandatory local `record_agent_session.py --append-csv` row. See that
  project's own README, "Near-automatic current-session recording", for
  the full flag/kind list; this repo never edits this file by hand,
  regenerate it via the central project's own generator if the wrapper
  pattern itself changes.
- `summarize_agent_telemetry.py` — read-only telemetry analysis and quality
  reporting script for `.agents/telemetry/agent-sessions.csv`. Computes raw totals
  by runtime (deduplicating cumulative session snapshots by default) and derived
  comparative metrics (`model_work_estimate`, `context_pressure`, `billing_estimate`).
  Reports telemetry health checks: cumulative snapshot groups, blank token fields,
  legacy runtime aliases (`claude-code`), missing model labels or timestamps, and
  confidence breakdowns. Supports `--json`, `--runtime`, `--include-snapshots`, and `--verbose`.
- `setup_agent_adapters.py` — creates the machine-local skill-discovery
  adapter for Claude Code. `.agents/skills/` remains the single canonical
  skill source; Codex and Antigravity read it directly and need no adapter.
  Claude Code looks under `.claude/skills/`, so this script creates
  `.claude/skills` as a **link** to `.agents/skills` — a directory junction
  on Windows (no Administrator rights needed; a symlink would require
  elevation or Developer Mode) and a relative `../.agents/skills` symlink on
  POSIX. Nothing is copied or mirrored, so there is only ever one copy of a
  skill to edit. `python .agents/scripts/setup_agent_adapters.py` sets it up
  and is idempotent (an already-correct adapter is left alone);
  `--check` verifies it read-only and exits nonzero when the adapter is
  missing, dangling, misdirected, or a real directory/file. Setup never
  deletes, replaces, or overwrites an unexpected path — it refuses with the
  remediation to perform by hand. The adapter is machine-local and
  intentionally untracked (`.gitignore`), so a clean clone has no
  `.claude/skills` and `validate_repo.py` does not require one; run the setup
  script once per working copy that uses Claude Code.

- `confluence_client.py` — headless Confluence Cloud REST API client, no
  browser/interactive login required. Basic Auth with an Atlassian API
  token (`.local/atlassian/credentials.json` — email + token + base
  URL, same gitignored trust boundary as `.local/google/`, see AGENTS.md).
  `--page-id` fetches one page's title + body text (storage-format XHTML
  converted to plain text via a small stdlib-only extractor, no bs4/
  html2text dependency); `--children` lists a page/folder's direct
  children; `--cql` runs an arbitrary CQL search (e.g.
  `ancestor=<folder-id>` for every descendant page). Used as a library
  (`get_session`/`get_page`/`get_children`/`search_cql`/`storage_to_text`)
  by any pass that needs to pull a Confluence source instead of scraping
  it through a live browser session.

There is no automated observer/dispatcher watching inbox folders — every
sync above runs because M2 asked for it in conversation. See
`google-workspace/pipeline-architecture.md`.
