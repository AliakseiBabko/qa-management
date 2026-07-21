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

## M1 Person-Based Layout

Treat `10_M1_People_Management` as a person-based workspace, mirroring how
`20_M2_Project_Management` is project-based — the M2 layout splits by
project, M1 splits by person. Final per-person M1 outputs go under:

`10_M1_People_Management\<Person>\...`

Standard per-person folder shape:

- `1to1` Google Sheet, CSV fallback `1to1.csv` — see `m1-people-1to1-file`.
  Titled just `1to1`, not `<Person> 1to1` — the person is already the
  enclosing folder name, so repeating it in the file title is redundant
  (same convention as M2's `people\<Person>\shared\individual_metrics`, not
  `<Person> individual_metrics`).
- `OKR к Perfomance review <DD.MM.YY>` Google Doc, one per Performance
  Review cycle, with Markdown fallback — see
  `m1-individual-development-plan`. This is also M1's version of a
  "personal development plan" — there is no separate narrative
  development-plan Doc for M1 team members the way M2 has a distinct
  `individual_development_plan`; the OKR Doc is the one artifact that
  plays both roles here, per the real company OKR process.
- `salary_review_self_feedback_<DD.MM.YY>` Google Doc, when applicable —
  see `salary-review-prep`.
- `1to1_prep_<YYYY-MM-DD>` Google Doc — only when the user explicitly asks
  to save a 1to1 prep; see `m1-1to1-prep`. Not created by default.

What stays at the `10_M1_People_Management` root, not inside any
`<Person>\` subfolder, because it's workspace-wide or about M1 themselves
rather than about one team member:

- `Светофор рисков` — living people-risk traffic-light Sheet covering the
  whole team at once, updated in place (no date in the title; see
  `m1-people-risk-report`).
- `m1_monthly_report_<Manager>_YYYY-MM` — M1's own monthly KPI/bonus
  report, not a per-person artifact (see `m1-monthly-report`).
- `_m1_timeline` — living workspace-wide Sheet of upcoming/overdue events
  across the whole team (see `m1-timeline`). Leading underscore marks it
  as a system/rollup artifact, same convention as `_people_registry`/
  `_project_registry`.
- `_m1_pr_calendar` — PR-only view, mechanically regenerated from
  `_people_registry`'s `Дата трудоустройства`/`Дата последнего PR` by
  `refresh_m1_pr_calendar.py` (see `m1-timeline`,
  `performance-review-rules.md`'s "Deriving the Expected Next PR Window").
  Never hand-edited — same generated-rollup discipline as `_m1_timeline`.
- `_self_review\<M1 name>\` — M1's own Performance Review self-prep, as
  the employee being reviewed by M3, not as the manager running PR for
  their team (see `m-self-review`, `salary-review-prep`). Kept under its
  own `_self_review\` namespace rather than directly as `<M1 name>\` so
  it's never confused with a team member's own folder, even when M1's own
  name would otherwise look like just another person folder at this root.

`find_person_roster()`-style logic (see `scan_m1_events.py`) should
enumerate `<Person>\` subfolders directly, excluding anything starting
with `_` — that's the team roster, not a name parsed out of a Sheet
title.

## M2 Project-Based Layout

Treat `20_M2_Project_Management` as a project-context workspace, not as a flat
report dump. Final M2 tabular outputs should go under:

`20_M2_Project_Management\<Project>\...`

Standard project folder shape:

- `privateproject_risk` Google Sheet, with CSV fallback `project_risk.csv`
- `privateprocess_checklist` Google Sheet, with CSV fallback `process_checklist.csv`
  — the 12-section outsource QA process-maturity checklist (see
  `m2-project-process-checklist`, based on `Templates\аутсорс_чек_лист_qa.csv`).
  A living record, not a dated snapshot; confirmed gaps route into
  `project_risk`'s `Риск QA process` column rather than living only here.
- `privateproject_development_plan` Google Doc, with Markdown fallback
- `privateproject_metrics` Google Sheet, with CSV fallback `project_metrics.csv`
  — M2-only dashboard for the project (see `Templates\метрики_проекта_qa.md`
  §2). Holds: `Горизонт совместной работы`, `Бизнес-риск продукта
  клиента`, one `Вклад в проект: <Имя>` row per person (no aggregated
  team row — every row stays visible individually at this level), and
  `Качество QA-процесса` (M2's read of `qa_process_metrics`). Never share
  this with the QA engineers whose data appears in it, even once
  folder-level sharing exists for other artifacts.
- `team_sharedqa_process_metrics` Google Sheet, with CSV fallback
  `qa_process_metrics.csv` — project-wide QA-process facts (Defect Escape
  Rate, Automation Coverage, test-run counts, etc. — see
  `Templates\метрики_проекта_qa.md` §3). Filled in by the project team, not
  M2 — do not guess values into it; create empty skeleton rows with a real
  `Пояснение` instruction instead. Append-only by calendar month.
- `privateevidence_log` Google Sheet, with CSV fallback `evidence_log.csv`
- `people\<Person>\shared\individual_development_plan` Google Doc, with Markdown fallback
- `people\<Person>\shared\individual_metrics` Google Sheet, with CSV fallback
- `private\people\<Person>\individual_metrics_internal` Google Sheet, with CSV
  fallback — M2-only, never shared with the employee (see
  `m2-individual-qa-metrics-report` document-contract, Internal Variant).
- `private\m2_input\` — folder holding one M2-only Google Doc, `m2_input`: M2's
  own dated rounds of questions/answers ahead of each project-level
  rollup (see `m2-role-rules.md` Project-Level Rollups and
  `Templates\m2_input.md`). One Doc per project, not a file per cycle —
  rounds are dated sections appended to it. (No longer holds a metrics
  Sheet — that moved into `project_metrics`, see above.)
- `private\status_reports` for saved project status Google Docs / Markdown fallback

Do not create a project-local `source_docs` folder. `90_Storage\Reference\Source_Documents\<Project>`
is already the canonical source layer — a per-project copy has no automated
way to stay in sync with it and will just go stale (this happened once
already: a one-off script copied a project's source files into
`20_M2_Project_Management\<Project>\source_docs`, and it was never kept
current or repeated for any other project). Reference `90_Storage\Reference`
directly instead of copying from it.

Do not create a project-local `archive` folder either. Superseded generated
outputs (e.g. a Sheet retired in favor of a Doc of the same name) go to the
single workspace-wide archive tree instead:

`90_Storage\Retired\20_M2_Project_Management\<Project>\...`

This keeps one place to look for retired artifacts rather than two, and
mirrors the live `20_M2_Project_Management\<Project>` shape so it stays easy
to find.

Keep `_project_registry` in `20_M2_Project_Management` as a top-level,
one-row-per-project "war room" dashboard — the airplane view across every
project M2 owns, sourced from each project's `project_metrics` (see
`Templates\метрики_проекта_qa.md` §4). Columns: `Проект`, `People`,
`Статус`, `Горизонт совместной работы`, `Бизнес-риск продукта клиента`,
`Наименьший вклад в проект`, `Качество QA-процесса`.

`Статус` (`Активен` / `На паузе`) mirrors `project_metrics`'s `Статус
проекта` row (`Templates\метрики_проекта_qa.md` §1.0) — manual-only, no
script sets or clears it, no scheduled cadence flips it back; it changes
only when M2 edits `project_metrics` directly, and the next
`refresh_project_registry.py` run just picks up that value like any other
mirrored field.

`Наименьший вклад в проект` is the one column that isn't a direct copy —
`project_metrics` can have several `Вклад в проект: <Имя>` rows, but the
registry collapses them to one column per project. **Never average them.**
Averaging "Позитивный, Позитивный, Смешанный, Негативный" destroys exactly
the signal this dashboard exists to surface. Take the worst status present
(Негативный → Смешанный → Позитивный, worst first) and name whoever is at
that level, e.g. `Смешанный (<Имя>)` — two people tied at the
worst level both get named. If the whole team shares one status, just
state it with no name attached (there's no one specific person to flag).

Active projects only — when a project is **officially stopped or
cancelled**, remove its row from the live registry rather than marking it
inactive in place; archived projects don't belong in a dashboard meant for
current attention. A **client-driven pause that hasn't been officially
ended** (e.g. a client-requested hold with an explicit "not a
cancellation") is not this case — it stays in the registry with `Статус` =
`На паузе` until M2 confirms it's actually stopped or reactivates it.
Columns are `Проект`, `People`,
`Статус`, and the four dashboard metrics — no aliases, source-docs pointer,
or folder-navigation link; those don't belong in a summary dashboard.

### `_people_registry`

Keep `_people_registry` in its own top-level folder, `05_People_Management`
(not nested under `10_M1_People_Management` or `20_M2_Project_Management`),
as a single workspace-wide Google Sheet (CSV fallback) covering **every**
person who comes up — Innowise employees under M1 management, M2-staffed
people, and client/vendor-side people across all projects. One person, one
row, regardless of which skill (M1 or M2) is the one touching them that day.

**History (2026-07-17 merge)**: this replaces two separate sheets,
`_m1_people_registry` (under `10_M1_People_Management`) and
`_m2_people_registry` (under `20_M2_Project_Management`), which duplicated
~10 of 13 columns between them with no principled rule for which sheet owned
which field. That let a field (e.g. `Name (EN)`) go missing in one sheet
while other fields for the same person got filled — a real bug, not a
hypothetical one. A dedicated top-level folder (rather than nesting the
merged sheet under either skill's folder) means a repo clone used for only
M1 or only M2 work still finds this registry without needing the other
skill's folder tree.

Columns:

- `Name (RU)`, `Name (EN)` — both, when the person has a known English-name
  form (useful since transcripts/chats mix scripts). First + last name only,
  no patronymic (patronymic goes in Notes if captured).
- `Email` — when known.
- `Side` — `Internal`, or `Client` / `Client — <company>` when the specific
  client-side or third-party vendor company is known (e.g. a client's own
  staff vs. a separate vendor supplying people on the same project). One
  column, not two — a person's affiliation and which company they're at is
  a single fact, and splitting it produced redundant-looking rows like
  `Internal, Internal` for every internal person.
- `Worker ID` — from an HRM worker-record card (see Person Card Intake,
  HRM Worker-Record Card shape below). Blank for client-side people — they
  have no Worker ID at all, not just an unknown one.
- `M1` — this person's current M1 manager, for internal people. Blank for
  client-side people, and for a person who is themselves a top-level M1
  with no manager on record.
- `Role` — M1 / M2 / M3 / M4 / HR / DC / QA / AQA / Team Lead / PM / Client
  stakeholder / Candidate / etc. Keep this to title/M-level/DC-status only —
  stream, tech stack, and secondary-project detail belong in `Project(s)` or
  `Notes`, not stuffed into `Role` (that drift is exactly what caused
  duplicate/conflicting Role text across the two now-merged sheets).
- `Internal rank` — the company's own internal level (Junior/Middle/Senior),
  for internal people only. This is distinct from a person's project-level
  grade fit (`Соответствие ожиданиям клиента (грейд)` in
  `individual_metrics`) — the two can differ, and neither substitutes for
  the other. Leave blank when not known; do not infer it from project-level
  grade.
- `Project(s)` — where the person is staffed/employed, comma-separated, or
  "all"/`Бенч` for company-wide roles or no current project. **Not** every
  project where they show up performing an M1/M2/DC duty for someone else's
  team — a person's main staffed project and a cross-project management hat
  they wear for other people are two different facts and must not be merged
  into one column. E.g. an AQA staffed on `<Project A>` who also acts as M2
  for a QA on `<Project B>` keeps `Project(s)` = `<Project A>`; the
  `<Project B>` M2 duty goes in `Notes`, naming the project(s) it covers.
  Multiple people commonly wear more than one hat (staffed role + M1/M2/DC
  duty elsewhere) — capture both, but don't let one overwrite or dilute the
  other.
- `Дата трудоустройства` — hire date (`YYYY-MM-DD`), for internal people
  only. Leave blank when not known; ask rather than guess — this is the
  anchor date for the probation-closing Performance Review (hire date + 3
  months, see `qa-management-roles/references/performance-review-rules.md`),
  so a wrong guess here silently mis-schedules a PR. Also the anchor
  `m1-timeline` and `m1-individual-development-plan` read from instead of
  re-deriving a date from transcripts each time.
- `Дата последнего PR` — the date of the person's most recently completed
  Performance Review (`YYYY-MM-DD`), internal people only. Blank means no
  PR has happened yet (still pre-probation-close), not "unknown" — do not
  fill it from a guess. M1 (or M2/M3 for their own PR) updates this cell
  right after a PR actually happens; `m1-timeline`'s cadence computation
  (expected next PR = this date + 6 months) depends on it staying current.
- `Первый коммерческий проект` — `Да` / `Нет`, whether this is the person's
  first-ever commercial (client-facing/production) project, distinct from
  hire date or internal rank — see `newcomer-support-rules.md` for the full
  detection and response rule. Ask rather than guess; leave blank only
  while genuinely unconfirmed.
- `Aliases / spelling variants` — alternate spellings/transliterations/STT
  mishearings confirmed for this person (e.g. a name transcribed three
  different ways across meeting recordings). Add to this column instead of
  burying an alias inside `Notes` prose, where a later Notes rewrite can
  silently drop it.
- `Notes` — anything uncertain, stated explicitly, including any
  cross-project management duty per the `Project(s)` rule above, citations,
  and confidence level on any estimated date.

No computed "next PR expected" column — `m1-timeline` already derives that
dynamically from `Дата последнего PR` + cadence rules
(`performance-review-rules.md`); storing it statically here would just go
stale.

### Person Card Intake

M2 sometimes hands over a person directly as a structured card rather than
via a transcript/chat, e.g.:

```
<Name (EN)>, <Имя (RU)>, <email>
Job Title - Data Engineer
M-level - P
Prof.Level - Senior
Mentor - No
DC - Yes
```

Map every field explicitly rather than re-deriving the mapping each time:

- Name (RU) / Name (EN) — from the given Russian/English (or transliterated)
  names directly.
- Email — as given.
- Side — `Internal` if the email domain matches the company's own domain
  (see `apply_person_card.py`'s `COMPANY_EMAIL_DOMAIN`); otherwise ask
  rather than guess.
- Role — `Job Title`, with `DC` prefixed if `DC - Yes` (e.g. `DC; Data
  Engineer`). Do not add `DC` to Role if the card says `DC - No`, even if
  the person is discussed alongside DC-shaped duties elsewhere. Separately,
  if `M-level` is a recognized internal management level (`M1`/`M2`/`M3`/
  `M4`), combine it into Role alongside Job Title too (e.g. `M3; DC
  Manager`), matching how existing M3 AQA rows are already written (`M3
  AQA`). If `M-level` is not one of those (e.g. `P`), its meaning isn't
  confirmed — leave Role alone and put it in Notes verbatim instead (see
  below); don't guess it belongs in Role.
- Internal rank — `Prof.Level` directly (Junior/Middle/Senior). This field
  already matches the `Internal rank` column's own scale.
- Project(s) — leave blank unless the card or its context states an actual
  staffed project; never infer it from which chat/project the card happened
  to arrive alongside (see the `Project(s)` rule above).
- `Первый коммерческий проект` — only if the card explicitly states it
  (e.g. a `First commercial project - Yes` line); do not infer it from
  `Prof.Level`, `M-level`, or the absence of prior `Project(s)` entries. If
  the card doesn't state it and the person is being staffed onto a project,
  ask rather than leave it silently blank — see `newcomer-support-rules.md`.
- Notes — `M-level` verbatim (only when it wasn't already folded into Role
  per above), flagged as unconfirmed in meaning; `Mentor` status in plain
  language; and a citation of the source (which chat/note the card came
  from).

If a card conflicts with an existing registry row for the same person (a
different Role, Side, or rank), treat it as a correction — the card is
direct, first-party information from M2, stronger evidence than an inferred
role from a transcript — but still fix every document that repeated the old
fact (see the Template Consistency note in `m2-role-rules.md`).

If a card's `Job Title` (e.g. AQA Engineer) conflicts with how that person's
actual on-project work reads in `individual_metrics`/`individual_development_plan`
(e.g. a fully manual scope), don't treat it as a contradiction to resolve
by picking a side — see `m2-role-rules.md`'s Вклад в проект Calibration,
client-driven scope-vs-track mismatch, which is very likely the actual
explanation.

When processing a transcript/chat and a role is unclear or contradicts this
registry, ask rather than guess — this registry exists specifically because
a wrong role guess (e.g. attributing a 1:1 to the wrong person's role) can
propagate into several documents before anyone notices.

#### HRM Worker-Record Card (Second Card Shape)

A different card shape also comes up: an HRM system export with fields
like `First Name`/`Last Name`/`Patronymic name`/`First Name (EN)`/`Last
Name (EN)`, `Worker ID`, `Hire date`/`Employment date`, and an
`Org. structure` block (`Unit`/`Division`/`Department`/`Team`/`Group`).
This has no email and doesn't always include the `Job Title`/`M-level`/
`Prof.Level`/`Mentor`/`DC` block the other card shape has — `apply_person_card.py`
does not parse this shape; map it by hand. Since the 2026-07-17 merge there
is only one `_people_registry` row per person, so this card shape and the
primary card shape both write into the same row — no cross-link bookkeeping
needed anymore.

- `Дата трудоустройства` — `Hire date` (same as `Employment date` in every
  case seen so far). Convert to ISO `YYYY-MM-DD` when writing — the card
  gives `DD.MM.YYYY`, but the registry's documented convention is ISO;
  don't carry the card's raw format through unconverted.
- Name (RU)/(EN) — first + last name, matching the existing column
  convention (no patronymic in the Name columns); put the patronymic and
  full official name in Notes instead.
- `Group: <Surname> Team` — identifies that person's current **M1** (e.g.
  `Group: Mitsko Team` means M1 = Митько). Cross-check against any M1
  already on record for this person (e.g. from a Workload sheet) rather
  than overwriting silently — the two sources confirming each other is
  itself worth noting in Notes. Prefer the most recent M1-leads roster
  (e.g. an `M1 Leads <date>.xlsx` source doc) over this card's own
  `M-level` field when they disagree — HRM's `M-level` can lag a real
  promotion/handoff by weeks; say so explicitly in Notes rather than
  silently picking one.
- `Worker ID` — its own column; blank for client-side people (they were
  never in HRM at all, not just missing this field).
- `Department` / other org-structure fields — not mapped to a dedicated
  registry column; record in Notes if useful context.
- If `Job Title`/`M-level`/`Prof.Level`/`Mentor`/`DC` are present on this
  card shape too, map those fields the same way as the primary card shape
  above.

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

`evidence_log` traceability is not just for automated sync-script runs.
Any update made conversationally — processing a transcript/chat dropped in
`00_Inbox`, applying M2's own answers from an `m2_input` round,
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

`source_type` canonical values (do not invent a new spelling of an
existing concept — check this list first): `strategy_chat`,
`meeting_transcript`, `m1_history`, `m2_conversation`, `qa_1to1`,
`admin_note`, `people_case_chat` (a person-specific incident chat under
`02_Chats_and_Emails`, e.g. a leaving-case thread — distinct from a
project-wide `strategy_chat`), `retro` (a `qa-retro` improvement-loop
pass over the log itself — its row is also the marker
`prepare_retro.py` slices the next window from). Three pre-classification
values — `raw_transcript`, `raw_chat`, `source_document` — are written
only by `prepare_intake_review.py` on newly-discovered files ("pending M2
review"); once a source is actually processed, its rows use one of the
real types above, never the raw label. If a genuinely new source shape
appears, add it here rather than picking an ad hoc value silently at the
point of use.

### `_skill_invocations`

Separate from `evidence_log` (which is per-project and answers "which live
documents changed because of this source"), `_skill_invocations` is a
single workspace-wide living Sheet at the Drive root (not nested under
`10_`/`20_`, same clone-independence reasoning as `_people_registry`) that
answers "what skill(s) actually got applied to this source" — across both
M1 and M2, so those patterns can be analyzed later (e.g. "which document
shapes reliably trigger which skill combo") instead of only living in
conversation history. Log a row every time a source document or
conversational request gets processed through one or more skills —
whether or not it ends up changing a canonical document (a first-contact
1to1-invite draft that produces no lasting document is still worth
logging, since the point is skill-trigger patterns, not just outcomes).

Use `pipeline_common.log_skill_invocation()` rather than hand-rolling the
Sheets write — it validates `source_type` against the same canonical list
above and reformats the Sheet after writing. Columns: `Date`, `Source`,
`Source type`, `Project` (blank if not project-scoped), `Person` (blank if
not about one person), `Skills applied` (comma-separated skill folder
names, e.g. `qa-1to1-analysis, m2-1to1-apply` — list every skill actually
applied, not just the first one that seems to fit, same discipline as
`evidence_log`'s `routed_to`), `Documents touched` (blank if none),
`Notes`.

When the processing pass belongs to an intake-queue run (`qa_manage.py`),
`Notes` must also carry the exact run token `run:<run-id>` — `complete`
verifies the token's presence, and substring/source-path matching is
deliberately not accepted (an old invocation row for the same source must
not satisfy a new run).

`Notes` additionally carries the improvement loop's raw material: when
the user corrects or overrides something during a pass (wording, routing,
a judgment call), capture it in that pass's row as a note prefixed
`feedback:` naming the target, e.g. `feedback: m2-1to1-apply — routed X
only to individual_metrics, user also wanted m2_input`. Keep it abstract
enough for pattern-matching (the skill/rule and the shape of the miss),
one `feedback:` note per distinct correction. `qa-retro` groups these
notes across passes and proposes a rule change once the same shape
repeats — a correction that only lives in conversation history is
invisible to that loop.

### `_closure_outcomes`

Workspace-wide append-only Sheet at the Drive root: one row per resolved
cascade edge per intake run — `Run ID`, `Timestamp`, `Project`, `Person`,
`Route variant`, `Source node`, `Target node`, `Edge kind`, `Outcome`,
`Reason`, `Actor`. Written via `closure_outcomes.py record` (never a raw
Sheets write — it validates the outcome against the edge's kind in
`document_graph.yaml`: `direct`→`updated`; `judgment`→`updated`/`no_change`
(+reason); `gated`→`gated` (+reason)/`updated`; `script`→`regenerated`).
The same edge may resolve differently for two projects/people in one run —
that's what the scope columns are for. `check_cascade_closure.py --run-id`
reads these rows, so "no change needed" becomes a recorded, checkable fact
instead of a sentence in a chat reply. Until the intake queue mints
canonical run ids, use `<date>-<source-slug>`.

### `_intake_queue`

Workspace-wide Sheet at the Drive root: one row per intake run, managed
only through `qa_manage.py` (scan/next/start/record-analysis/resolve-edge/
record-apply/resolve-edge/block/resume/complete/fail/historical) — never
edited by hand, and unlike the append-only logs its rows are updated in
place as a run moves through `discovered → needs_scope/ready → processing
(analysis→apply→closure) → finalizing → completed/failed/historical/
ignored`, with `blocked` as a parking state and `finalizing` as the
retryable verification-passed-but-bookkeeping-pending step. `historical`
asserts the source WAS processed pre-queue (evidence required); `ignored`
(categorized: course material / reference material / duplicate artifact)
asserts it is not intake at all and is reachable only from
pre-processing states — never conflate the two. `historical` is the terminal state for sources processed
before the queue existed (evidence required — pre-queue history is not a
failure); `failed` may be corrected to `historical` when migration
evidence turns up. Source identity is (path, content hash): changed
content at a known path is rediscovered as a superseding run, identical
content at a new path is recorded as a duplicate. `start` records the
agent's classification with explicit (project, person) scope tuples —
never a Cartesian product, never a silent default (`needs_scope` instead).
`record-apply` records a per-scope outcome for every route entry document
(`updated` / `no_change`+reason / `not_applicable`+reason); only updated
entries seed the cascade. `complete` is a verification gate: entry
outcomes valid per scope, strict closure per scope, the exact
`run:<run-id>` token in `_skill_invocations`, and a clean mirror snapshot
not older than the run's last mutation. Its exact SHA is persisted on the row,
and `complete` validates that this specific business snapshot SHA contains the
exported text blob for any `Source text version 1` run. The terminal queue state
itself is exported to the mirror as a follow-up commit. The `review <run-id>` command provides a read-only evaluation of
a run's completion readiness (missing invocation evidence, snapshot problems,
unresolved edges) without mutating the queue. All `qa_manage.py` commands support
a strict `--json` contract (suppressing normal stdout and emitting exactly one
JSON envelope at the end) for programmatic agent integration. Rows hold operational
metadata and short summaries only — never transcript content or analysis bodies.
The queue's `Run ID` is the canonical run id used in `_closure_outcomes`,
`_skill_invocations` notes, and mirror commit messages.

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
status reports, risk narratives, summaries) or into a chat message drafted
for the user to send to a colleague/stakeholder (see
`chat-message-style-rules.md` for that case specifically) — not to code,
file paths, or literal evidence citations.

- Do not use an em dash / long dash ("—") as word-joining punctuation in
  any generated prose. It reads as AI-generated and undermines text meant
  to sound natural, especially colleague-facing chat messages. Use a
  comma, period, semicolon, parentheses, or restructure the sentence
  instead.
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
- Real data read from the Drive API (names, emails, project specifics)
  stays in conversation/generated Drive output — never write it back into
  this repository's own tracked files (skills, references, templates,
  scripts, commit messages) as an "example" or "for context." See
  `AGENTS.md`, "No Sensitive Data In This Repository."
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
  `90_Storage\Retired`).
- The Sheets API read-request quota is 60/min per user/project. Any script
  that iterates every Sheet in the workspace (`format_all_sheets.py`) costs
  at least 2 read calls per sheet (`spreadsheets().get` +
  `values().get`) and will exceed that quota well before finishing once the
  workspace has more than ~30 sheets — this is expected at current workspace
  size, not a sign something is broken. A 429 here is a rate limit, not a
  real failure: back off and retry (see `call_with_retry` in
  `format_all_sheets.py`) rather than treating the run as failed. If a
  one-off script or manual API call hits the same 429 without retry logic,
  just rerun it — formatting/read-only scripts are safe to rerun and pick up
  whatever didn't complete.

## Sharing Safety

The M2 tree uses folders as explicit permission boundaries:

- Share `team_shared\` only with the QA engineers assigned to that project.
  It contains team-editable project facts, currently `qa_process_metrics`.
- Share `people\<Person>\shared\` only with that person. It contains their
  `individual_development_plan` and `individual_metrics`.
- Never share the project root, `private\`, `people\<Person>\`, or any parent
  folder. `private\` contains M2 judgment, evidence, risks, internal metrics,
  1to1 history, and status drafts.
- Inherited access cannot be corrected by making a child look private. A
  private artifact found below a shared folder is a structural violation:
  move it to `private\` before continuing.
- Folder names are not a substitute for a permission audit. Sharing
  automation must verify the target folder, intended audience, and absence
  of private descendants before adding permissions.

## Docs API Editing

- When updating an existing Doc's content in bulk, clear the whole body
  (`deleteContentRange` over the full range) and reinsert with fresh
  paragraph styles, rather than patching pieces in place.
- If you do patch just one heading's text via `deleteContentRange` +
  `insertText`, its paragraph style resets to normal text — you must reapply
  `updateParagraphStyle` (e.g. `HEADING_2`) afterward, or the heading silently
  stops looking like a heading.

## Search Strategy

Do not grep recursively across the whole `G:\My Drive\QA_Management` mirror
to find mentions of a person or topic. This reads every file's raw bytes,
including multi-MB `.docx`/`.xlsx` source binaries and `.gdoc`/`.gsheet`
placeholder files whose real content lives in the cloud, not the local
pointer file (grepping them finds nothing anyway, since the local file is
just a JSON stub) — a real attempt at this timed out well before finishing
on a single-name search.

Instead:

1. Check `_people_registry` first — its `Project(s)`/`Notes` columns
   usually already point at the person's project and known source docs.
2. Then look directly in the conventional location this repo already
   documents: `<Person> case chat.txt` / `<Person> case at <Project>.txt`
   under `00_Inbox`, that project's
   `<Project>_strategy.txt`, or `01_Meeting_Transcripts` — the naming
   convention already tells you where to look; don't blind-search first.
3. If a genuinely broad text search across Drive is still needed, use the
   Drive API's `fullText contains` query (server-side indexed, and it
   covers native Google Docs/Sheets content) instead of a local filesystem
   grep over the mirror.
4. Don't introduce a new tagging/indexing layer to solve this — the
   existing naming conventions and registries already serve that purpose.

## Source Extraction

Source extraction writes Markdown, CSV, JSON, and manifests under `90_Storage\_System\extracts\source`. Those files are intermediate analysis artifacts, not final business documents.

When asked to analyze a `.docx` or `.xlsx` source file, use
`.agents\scripts\qa_source_extract.py` (its `extract_docx`/`extract_xlsx`
functions can be imported and called directly on a single file, without
running the full CLI) rather than reaching for a separate library — it
reads `.xlsx`/`.docx` straight from the zip/XML package with no external
dependencies, which is what already made analyzing an internal assessment
matrix workbook and a project's source docs work without needing to
install anything.

Before extracting, check whether the file has already been processed:
look for its path (and `sha256`, via `sha256_file()`) in an existing
`manifest.csv`/`manifest.json` under `90_Storage\_System\extracts\source\*`. A
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
