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
- `05_People_Management/`: `_people_registry` — the single workspace-wide
  people Sheet, covering everyone (M1-managed, M2-staffed, client-side)
  regardless of which skill is looking at it. Deliberately not nested under
  `10_` or `20_` so a repo clone used for only M1 or only M2 work still
  finds it — see M1/M2 Person and Project Layout below.
- `10_M1_People_Management/`: person-based (`<Person>/` subfolder per
  team member) — see M1 Person Layout below
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
├─ project_risk.gsheet
├─ process_checklist.gsheet     # living outsource QA process-maturity checklist (12 sections)
├─ project_development_plan.gsheet
├─ project_metrics.gsheet       # M2-only dashboard, see below — never shared with the team
├─ qa_process_metrics.gsheet    # engineer-filled, project-wide QA-process facts
├─ evidence_log.gsheet
├─ m2_input/
│  └─ m2_input.gdoc             # M2-only dated rounds of judgment/context
├─ action_items.gsheet          # living list of dated events/deadlines/follow-ups
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

`G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`

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

## Department Traffic Light (Foreign Tracker)

Filling M2's own row block on the department's shared "Auto staff.
Светофор проектов" outstaff tracker (`00_Source_Docs\03_Source_Documents`,
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
`80_Exports/open_questions_review/YYYY-MM-DD.md`); `--write` appends
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
`80_Exports/open_questions_review/YYYY-MM-DD_m1.md`.

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

- `G:\My Drive\QA_Management\00_Source_Docs\M1_monthly_report.xlsx`
- `G:\My Drive\QA_Management\00_Source_Docs\M2_monthly_report.xlsx`

The M1 workbook contains real report examples. The M2 workbook is treated as an example/calculator
unless explicitly provided as a real report for a target month.
