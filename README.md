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

- `00_Inbox/`: the single recursive intake folder. Drop transcripts,
  chats, emails, spreadsheets, or other source files here without manually
  classifying them. Empty means there is no unprocessed file intake.
  Everyday discovery scans this folder only.
- `05_People_Management/`: `_people_registry` — the single workspace-wide
  people Sheet, covering everyone (M1-managed, M2-staffed, client-side)
  regardless of which skill is looking at it. Deliberately not nested under
  `10_` or `20_` so a repo clone used for only M1 or only M2 work still
  finds it — see M1/M2 Person and Project Layout below.
- `10_M1_People_Management/`: person-based (`<Person>/` subfolder per
  team member) — see M1 Person Layout below
- `20_M2_Project_Management/`: project-based M2 project-management outputs
- `80_Exports/` (optional): created only when an explicit immutable package
  or copy is prepared for external sharing; internal extracts do not belong here
- `90_Storage/`: the single non-actionable storage root:
  - `Reference/`: durable source and training/reference material
  - `Processed_Sources/`: originals already processed by the intake pipeline
  - `_System/`: generated extracts and review bundles
  - `Backups/`: private-mirror recovery bundle
  - `Retired/`: retired outputs and legacy folders
  This root is explicitly excluded from source discovery; moving a file
  here means it is no longer part of the active intake backlog.

No raw video/multimedia is stored in Drive - only transcripts and
documents. Folder moves use the Drive API so file IDs, links, revisions,
and existing permissions are preserved. See
`.agents/skills/qa-management-roles/references/google-workspace-rules.md`
for the full folder-mapping and Sharing Safety notes.

Final business outputs should prefer Google Sheets for tabular artifacts and Google Docs
for narrative/status artifacts when Google API access is available. Local CSV/Markdown
files remain valid as fallback, staging, source-extraction, and export artifacts.

## People Registry

`05_People_Management/_people_registry` is the single workspace-wide people
Sheet — one row per person (internal and client-side), covering everyone M1
or M2 might need to look up: role/side, project(s), hire date, PR history,
M1 manager, Worker ID, aliases, and notes. See `google-workspace-rules.md`
for the full column list. Neither M1's nor M2's own outputs duplicate this
data — `_m1_pr_calendar`, `individual_metrics`, etc. all read from it.

## M1 Person Layout

M1 is organized by person, mirroring how M2 is organized by project. Each
team member gets their own folder:

```text
10_M1_People_Management/
├─ <Person>/
│  ├─ 1to1.gsheet                              # per-person longitudinal record
│  ├─ OKR к Perfomance review <DD.MM.YY>.gdoc   # one per PR cycle; also M1's version of a "personal development plan"
│  ├─ salary_review_self_feedback_<DD.MM.YY>.gdoc  # when applicable
│  └─ 1to1_prep_<YYYY-MM-DD>.gdoc               # only if the user asks to save a prep
├─ Светофор рисков.gsheet              # living, workspace-wide, covers the whole team at once
├─ m1_monthly_report_<Manager>_YYYY-MM.gsheet  # M1's own KPI report, not per-person
├─ _m1_timeline.gsheet                 # living rollup of upcoming/overdue events
├─ _m1_pr_calendar.gsheet              # generated PR-only view, from _people_registry
└─ _self_review/<M1 name>/             # M1's own PR self-prep, as the employee being reviewed
```

Root-level files (risk snapshots, M1's monthly report, `_m1_timeline`,
`_m1_pr_calendar`) stay
at the root because they're workspace-wide or about M1 themselves, not
about one team member — see
`.agents/skills/qa-management-roles/references/google-workspace-rules.md`,
M1 Person-Based Layout, for the full rule.

## M2 Project Layout

M2 is organized by project context. Two workspace-wide Sheets sit directly
under `20_M2_Project_Management`:

- `_project_registry` — one row per **active** project, the top-level "war
  room" dashboard (Проект, People, Горизонт совместной работы, Бизнес-риск
  продукта клиента, Наименьший вклад в проект, Качество QA-процесса).
  Stopped projects are removed from this registry, not marked inactive.
- `_timeline` — generated rollup of every project's open `action_items`
  rows, sorted by date; the one place to see what's due today/tomorrow/this
  week across all projects. Never edited directly — refresh it with
  `refresh_timeline_registry.py` after changing a project's `action_items`.
  See `.agents/skills/m2-timeline`.

Project completeness is expected to be uneven under the incremental-fill
model (see `m2-role-rules.md`, Project-Level Rollups) — a freshly-scaffolded
project with mostly `Неизвестно` rows and an unanswered `m2_input` round
isn't a data-quality bug, it's the normal state before M2 has answered that
round.

Each project folder follows this shape:

```text
20_M2_Project_Management/<Project>/
├─ private/                      # M2-only; never share this folder
│  ├─ project_risk.gsheet
│  ├─ process_checklist.gsheet
│  ├─ project_development_plan.gdoc
│  ├─ project_metrics.gsheet
│  ├─ evidence_log.gsheet
│  ├─ action_items.gsheet
│  ├─ m2_input/m2_input.gdoc
│  ├─ status_reports/
│  └─ people/<Person>/
│     ├─ individual_metrics_internal.gsheet
│     └─ <Person> 1to1.gsheet
├─ team_shared/                  # share only with this project's QA team
│  └─ qa_process_metrics.gsheet
├─ people/<Person>/
│  └─ shared/                    # share only with this person
│     ├─ individual_development_plan.gdoc
│     └─ individual_metrics.gsheet
```

There is no per-project `source_docs/` or `archive/` folder - reference
`90_Storage/Reference/Source_Documents/<Project>` directly, and retired artifacts go to the
single workspace-wide `90_Storage/Retired/20_M2_Project_Management/<Project>/`
tree instead of a local copy that would go stale.

**Visibility boundaries**: share only `team_shared/` with the project's QA
team and only `people/<Person>/shared/` with that person. Never share the
project root, `private/`, or `people/<Person>/`. `qa_process_metrics` is the
team-editable factual input; its synthesized conclusion lives in the M2-only
`private/project_metrics`. See `google-workspace-rules.md`, Sharing Safety.

**Update chain**: `individual_metrics`/`individual_development_plan` (per
person) → `project_metrics` (per project) → `_project_registry` (across
all projects). A new source that changes something at the person level
should update the whole chain in the same pass — see `m2-role-rules.md`,
Cascading Updates. Metric definitions and which artifact each one belongs
in: `Templates/метрики_qa_по_проекту.md` (individual) and
`Templates/метрики_проекта_qa.md` (project/QA-process/dashboard).

**Process checklist**: `.agents/skills/m2-project-process-checklist`
maintains `process_checklist` — a living, 22-question/12-section record of
outsource QA process maturity (requirements/docs, roles, environment,
communication, test docs/tooling, quality/test types, dev process, bugs,
regression, releases, change management, Quality Gates), based on
`Templates/аутсорс_чек_лист_qa.csv`. A missing item is not automatically a
project risk — the skill's `references/outsource-operating-principles.md`
(from the "Роль М2 на аутсорс проекте" / "Особенности работы на аутсорс
проектах" articles) covers when a gap is a reasonable trade-off under
fixed scope/timeline vs. a real gap, and lists when QA should escalate to
M2. A gap judged a real risk gets logged into `project_risk`'s `Риск QA
process` column, not left to live only in the checklist.

**Presale / upsell**: `qa-management-roles/references/presale-upsell-rules.md`
covers M2's account-growth responsibility — diagnostic markers for a QA/AQA
resourcing gap, automation-readiness criteria (project stage, duration,
team size, regression volume), the upsell problem/benefit framework, the
productized service menu (test-case writing, smoke/critical execution, UI/
API automation, CI/CD integration, plus accessibility/security add-ons),
and the escalation path (Head of QA / presale lead) for building a real
pitch. `project_development_plan` carries this as its own "Возможности
расширения (Upsell)" section (§4, see `Templates/план_развития_проекта.md`)
and `m2-project-status-report` as an optional section — both only when a
real diagnostic signal or conversation exists, never as generic
service-menu filler.

Broad KT/session sources should be split by project before updating final files.
Use `evidence_log` as the append-only trace of which source changed which project
files — including conversational updates, not just automated syncs. Keep
aggregate KT outputs in `90_Storage/Retired`, not as canonical final documents.

## Project Knowledge Layout

A third lane, separate from M1 people-management and M2 project-management
reporting: `30_Project_Knowledge\<Project>\`, for building project
understanding — learning/onboarding, not management reporting. A project
can enter this lane with poor or entirely missing formal documentation;
knowledge gets built gradually from whatever sources actually exist
(1:1s, meetings, chats, presentations, documents, owner notes). A formal
knowledge-transfer session (`project_knowledge_transcript`) is one
possible input, never a prerequisite for starting a knowledge base.

```
30_Project_Knowledge/<Project>/
  source_index                          (Sheet - one row per processed source)
  knowledge_base/
    <Project>_knowledge_base            (Doc - living knowledge base)
  summaries/
    <source-slug>_summary               (Doc - one per processed source)
  qa_docs/
    performance_test_plan               (Doc)
    test_plan                           (Doc)
    test_strategy                       (Doc)
```

Private by default — no `private`/`team_shared`/`people/<Person>/shared`
split like the M2 lane has (see `project_knowledge_workspace_layout.py`).
Sharing an individual Doc is a deliberate, one-off action taken outside
automation, not a folder move. Google Docs for the knowledge
base/summaries/QA docs, Google Sheets only for `source_index` — no
Obsidian/Notion/local wiki, no Google Slides in this phase (a later phase
may generate slides from a reviewed brief; nothing does that yet).

Four source types: `project_knowledge_transcript`, `project_knowledge_document`,
`project_knowledge_chat`, `project_knowledge_notes` (see
`google-workspace-rules.md` and `document_graph.yaml`'s `lanes:` mapping).
Two skills: `project-knowledge-roles` (shared judgment rules — gradual
accumulation, durable-vs-one-off distinction, open questions, the M1/M2
boundary, QA docs as downstream-not-automatic products) and
`project-knowledge-intake` (the source-triggered pass).

**Relationship to the operator commands:** this lane reuses the normal
intake pipeline unchanged. `qa_manage.py scan`/`triage`/`classify`/`guide`/
`pack` all work the same way for a `project_knowledge_*` source as for an
M1/M2 one — `classify` adds these source types as unranked candidates
alongside the M1/M2 ones wherever the same format signals fire (transcript/
chat-shaped sources), never a final choice and never an inferred project
name; `guide`/`pack` surface each route's `route_description` the same way
they do for M1/M2 routes. `qa_manage.py gates` stays M2-only (no
`m2_input`-style two-phase gate exists in this lane yet), and `dashboard`/
`triage` have no `--lane` filter yet — both list every lane's rows
together. `search_workspace.py` includes `30_Project_Knowledge` in its
canonical roots; `show_project_state.py --lane project_knowledge` reads
this lane's Drive state live (`--registries`/`--summary`/`--person` are
M2-only concepts and are rejected for this lane).

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
  committed snapshot).
- `migrate_m2_visibility_layout.py` — one-time, idempotent Drive migration
  for the M2 permission-boundary layout. `audit` is read-only and reports
  planned moves plus unrecognized artifacts; `apply` creates only the
  required `private`, `team_shared`, and per-person `shared` folders and
  moves unambiguous canonical artifacts while preserving file IDs. It never
  changes sharing permissions and never moves an unknown file.
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
  see `google-workspace-rules.md` — use this instead of a raw Sheets write
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
- `validate_repo.py` — mechanical consistency validation of this repo's
  convention-mirrored files (the `repo-maintenance` checklist automated):
  AGENTS.md skill table ↔ `.agents/skills/`, README ↔ `.agents/scripts/`,
  `document_graph.yaml` node/alias/script/source integrity, source-type
  lists in sync between `pipeline_common.py` and
  `google-workspace-rules.md`, and `Templates/` references resolving. Exit
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
- `check_sensitive_data.py` — grep-based guard for AGENTS.md's
  no-sensitive-data rule: scans added lines in the current git diff under
  `.agents/` for real person/project names pulled live from
  `_people_registry`/`_project_registry`. A cheap net, not proof of
  safety — it only matches registered names as literal substrings; company
  names, emails, and paraphrased content still need a human read. Run
  manually before committing changes under `.agents/`.
- `check_cascade_closure.py` — deterministic half of the cascading-update
  chain: reads `.agents/document_graph.yaml` (the machine-readable version
  of `m2-role-rules.md`'s Cascading Updates / Project-Level Rollups fan-out)
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
  never a public remote.
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
  blocked run; `mark-historical` for a `failed` run), and only the guardrails
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
  command templates: `guide`, one `start ...` per candidate, and `ignore
  ...` when the row's own duplicate-detection `Reason` suggests it. Low/no
  signal means "manual classification required" and the full routed
  source-type list, not a guess. Never picks a route, never calls `start`,
  never writes anywhere, and never puts the preview text or full source
  content into the queue or this repo — only short operational summaries
  belong there; the classification decision, made after actually reading
  the source, stays with the agent. Handing a run off to another agent
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
  identity, and requires a fresh workspace snapshot afterward. `complete` is
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
  stops being a truthful claim the moment work begins); and `ignore`
  (`--category non_intake_course_material|reference_material|
  duplicate_data_quality|other --reason "..."` with a concrete reason
  required — a category alone is not a reason, optional `--evidence` —
  not an intake source at all, reachable only from pre-processing states).
  Neither mutation moves or deletes the source file — a terminal-status
  queue row's (path, hash) identity already keeps `scan` from
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
  captured user corrections that are the loop's primary input) plus repo
  commits over the same window. Judgment (grouping, the once=trace /
  twice+=propose-an-edit threshold, drafting diffs) stays with the
  qa-retro skill; the retro logs its own `retro` row when done, which
  becomes the next run's window start.
- `apply_person_card.py` — parses a person card (the Job Title/M-level/
  Prof.Level/Mentor/DC block M2 pastes in conversation) per the Person Card
  Intake mapping in `google-workspace-rules.md`, looks up `_people_registry`
  by email, and prints the computed Role/Internal rank/Notes plus a diff
  against any existing row. Dry-run by default; `--apply` adds a genuinely
  new row (an existing row's Name/Project(s) still need human judgment per
  the Project(s) rule, so those are never auto-written). Pass the card via
  `--file <path>`, not stdin/a heredoc — a Windows bash heredoc was found to
  silently drop the Cyrillic half of the name while building this script.
  For an existing person, also greps their currently-listed Project(s)'
  `individual_metrics`/`individual_development_plan` for a track/level
  mismatch against the card (see `m2-role-rules.md`, Вклад в проект
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
  for a project (`qa_process_metrics`, `individual_metrics_internal` per
  person, `m2_input`, and a placeholder `project_metrics` only if one
  doesn't exist yet). Structure only, no fabricated judgment — the actual
  `project_metrics` rows and `m2_input` rounds still need M2's real read
  of the project. Safe to rerun; every artifact is created only if
  missing, and an existing `project_metrics` is always left untouched.
- `format_all_sheets.py` — applies consistent formatting (wrap, alignment,
  column widths targeting ≤5 lines) across every Sheet under both
  `10_M1_People_Management` and `20_M2_Project_Management` by default
  (`--root-folder-id` to target a different/specific folder instead,
  repeatable). Safe to rerun anytime after a schema change. `--dry-run`
  prints planned column widths per sheet without writing — worth using
  whenever the scope changes again. A single-sheet read timeout is a
  transient failure, not a real one; the script is idempotent, so just
  rerun it rather than chasing the one sheet by hand.
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
  `project_metrics` dashboard values into `_project_registry`
  (worst-known-status for `Наименьший вклад в проект`, never averaged). Safe
  to rerun anytime after a `project_metrics` update.
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
  mandatory closing step (see AGENTS.md's intake-workflow bullet), not just
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
  value.
- `finalize_operator_run.py` — the enrichment step over
  `measure_operator_outputs.py --append-csv`: merges actual token telemetry
  (CLI flags or a `--telemetry-json` file), computes `total_tokens` and
  `estimated_cost_usd` when the model/pricing is known, and computes
  `reduction_ratio_vs_baseline` against an existing baseline row already in
  the CSV. Always appends exactly one new row and diff-guards afterward to
  confirm no other row changed.
- `check_operator_csv.py` — validates `.agents/telemetry/operator-runs.csv`:
  header match, required/numeric fields, enum values, duplicate `run_id`s,
  and a best-effort ASCII-only leak guard on the redacted-args/notes
  fields. `--diff-guard --run-id <id>` asserts the working CSV only added
  that one row versus `HEAD`.
- `extract_agent_telemetry.py` — best-effort actual-token extraction from
  local Claude Code session logs (`~/.claude/projects/*/<session>.jsonl`)
  for `finalize_operator_run.py --telemetry-json`. Codex/Antigravity log
  locations were not verified on this machine and raise a documented
  `NotImplementedError` pointing at the manual-entry fallback
  (`finalize_operator_run.py --actual-input-tokens ...` etc.) — manual token
  entry is a first-class supported path, not a workaround, and does not
  block using the rest of Phase 11.

There is no automated observer/dispatcher watching inbox folders — every
sync above runs because M2 asked for it in conversation. See
`google-workspace-rules.md`, Pipeline Architecture.

## Status Reports

Short chat-ready M2 project status reports are handled by:

- `.agents/skills/m2-project-status-report`

Regular reports should be saved as Google Docs under each project's
`20_M2_Project_Management/<Project>/private/status_reports`
when Google API access is available. Local Markdown fallback path:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\private\status_reports`

Use project name and report date in the filename.

## Department Traffic Light (Foreign Tracker)

Filling M2's own row block on the department's shared "Auto staff.
Светофор проектов" outstaff tracker (`00_Inbox`,
tab `Outstaff`) — a document owned by the department, not generated by this
workspace — is handled by:

- `.agents/skills/m2-department-traffic-light`

## Timeline / Action Items

Per-project events, deadlines, and follow-ups (meetings, status-report
commitments, clarifications owed) plus a cross-project "what's due when"
view are handled by:

- `.agents/skills/m2-timeline`

Each project keeps a living `action_items` Google Sheet (CSV fallback
`action_items.csv`, template `Templates/action_items.csv`). Run
`refresh_timeline_registry.py` after editing one to update the
workspace-wide `_timeline` rollup. `show_project_state.py --summary` also
flags overdue/due-soon items per project without opening either Sheet.

`scan_open_questions.py` finds candidate action items already implied by
other documents — a pending `m2_input` round, a `project_risk` action plan,
a `Неизвестно` row in `project_metrics` — across every project in one pass,
so open questions don't have to be tracked by memory. It's read-only by
default (prints + writes a bundle to
`90_Storage/_System/reviews/open_questions/YYYY-MM-DD.md`); `--write` appends
candidates straight into `action_items`. Its wording/date/owner are
mechanical placeholders — see `m2-timeline` SKILL.md for how to turn a raw
candidate (e.g. an unclear benchmark status) into a real scheduled action
(e.g. a 1:1 to clarify it) before logging it for real.

M1's people-side counterpart — Performance Review dates, OKR cycle
closures, and monthly-report deadlines — is handled by:

- `.agents/skills/m1-timeline`

Unlike `m2-timeline`, this is a single flat `_m1_timeline` Google Sheet
directly under `10_M1_People_Management` (CSV fallback `_m1_timeline.csv`,
template `Templates/m1_timeline.csv`) — M1's team is small enough that a
per-project-style Sheet-plus-rollup isn't needed. `scan_m1_events.py`
derives candidates mechanically: it reads every OKR Doc's title (`OKR к
Perfomance review DD.MM.YY`) to surface upcoming/overdue Performance
Reviews and people missing a current OKR, cross-checks that against an
expected-next-PR *window* computed from `_people_registry`'s `Дата
трудоустройства`/`Дата последнего PR` (real cadence: window opens at last
PR + 6 months, or hire date + 3 months for a first/probation-closing PR,
and closes 1 month later — see
`qa-management-roles/references/performance-review-rules.md`), and checks
`m1_monthly_report_<Manager>_YYYY-MM` presence to surface an overdue
monthly report. Same read-only-by-default / `--write` split as
`scan_open_questions.py`, writing its bundle to
`90_Storage/_System/reviews/open_questions/YYYY-MM-DD_m1.md`.

For a PR-only view (no other event types mixed in), `refresh_m1_pr_calendar.py`
generates `_m1_pr_calendar` (template `Templates/m1_pr_calendar.csv`) from
the same `_people_registry` data — one row per person with a computable
window, sorted soonest-first, `Статус` one of `Не скоро`/`В окне`/
`Просрочено`/`Нет данных`. Fully regenerated every run, like
`refresh_project_registry.py` on the M2 side — never hand-edited, so it
can't drift from `_people_registry` as a second source of truth. Also
reformatted (wrap/align/column widths) on every run, so it never needs a
separate manual formatting pass.

## Self-Review (M1/M2)

M1's and M2's own Performance Review self-prep — as the employee being
reviewed by M3, not as the manager running PR for their team — is handled
by:

- `.agents/skills/m-self-review`

Two outputs: a dated `критерии_оценки_команды` Google Sheet per PR cycle
(CSV fallback, template `Templates/критерии_оценки_команды.csv`, scoring
rules in the skill's `references/team-criteria-rules.md`), scoring the
manager's own team on 17 metrics out of 34 points (70%+ = effective team);
and a chat-ready self-review prep summary (own OKR recap, team score,
outstanding PGROWTH tasks). Stored under `_self_review\<Person>\` inside
whichever root the manager's own grade uses
(`10_M1_People_Management` for M1, `20_M2_Project_Management` for M2) —
distinct from the team-facing M1 skills above, which are about the
manager's team, not the manager themselves.

Salary review — which happens inside a PR for eligible employees — is a
separate skill since it applies to any employee, not just M1/M2:

- `.agents/skills/salary-review-prep`

Produces a dated `salary_review_self_feedback` Google Doc draft (template
`Templates/salary_review_self_feedback.md`): evidence-backed value growth
(excluding routine on-level work), AI-competency assessment status
(verified only by the named AI leads, never self-certified), and a
blocker pre-check (developmental dynamics, AI competency, bench status,
feedback, department engagement — see
`qa-management-roles/references/salary-review-rules.md`). Usable both for
M1 supporting a QA team member's own self-feedback and for M1/M2
preparing their own, alongside `m-self-review`.

## Monthly Reports

Monthly KPI report skills:

- `.agents/skills/qa-management-roles`
- `.agents/skills/m1-monthly-report`
- `.agents/skills/m2-monthly-report`

CSV templates:

- `Templates/m1_monthly_report.csv`
- `Templates/m2_monthly_report.csv`

Source examples:

- `G:\My Drive\QA_Management\90_Storage\Reference\Source_Documents\M1_monthly_report.xlsx`
- `G:\My Drive\QA_Management\90_Storage\Reference\Source_Documents\M2_monthly_report.xlsx`

The M1 workbook contains real report examples. The M2 workbook is treated as an example/calculator
unless explicitly provided as a real report for a target month.
