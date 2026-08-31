# Workspace Layout

Full Drive folder layout and document conventions for the M1/M2/Project
Knowledge/PM Case Library/QA Department Standards lanes. See
[README.md](../README.md) for the top-level orientation this document
expands on.

## People Registry

`05_People_Management/_people_registry` is the single workspace-wide people
Sheet — one row per person (internal and client-side), covering everyone M1
or M2 might need to look up: role/side, project(s), hire date, PR history,
M1 manager, Worker ID, aliases, and notes. See
`google-workspace/people-registry.md` for the full column list. Neither M1's nor M2's own outputs duplicate this
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
`.agents/skills/qa-management-roles/references/google-workspace/m1-layout.md`
for the full rule.

## M2 Project Layout

M2 is organized by project context across a 3-layer information architecture:

- **Layer 1 — Evidence and Measurements**: facts, observations, measurements,
  source logs, and history (`qa_process_metrics`, `individual_metrics`,
  `process_checklist`, M2 1:1 records, `evidence_log`).
- **Layer 2 — M2 Decisions and Current-State Records**: interpretation, risk,
  judgment, action, and formal decision gates (`project_metrics`,
  `project_risk` [living 2-tab workbook: `Summary` + `Risk Items`],
  `individual_risk`, `m2_input` [formal decision gate], `action_items`,
  project and individual development plans).
- **Layer 3 — Executive Views**: designed for one-glance senior management
  reading (`_project_registry`, `_people_registry`, optional
  `_m2_risk_registry`, executive status reports). Layer 3 is generated
  mechanically from Layer 2 and must never become a competing source of truth.

### Living vs. Dated Document Matrix

| Layer | Document | Storage Mode | Lifecycle Rule |
| :--- | :--- | :--- | :--- |
| **Layer 3** | `_project_registry` | **Living Sheet** | Recomputed mechanically by `refresh_project_registry.py` |
| **Layer 3** | `status_report` | **Dated Doc** | New file per reporting period (`status_report_YYYY-MM-DD`) |
| **Layer 2** | `project_metrics` | **Living Sheet** | Updated in place (1 row per composite identity `(Project, Metric Key, Role / Stream)`) |
| **Layer 2** | `project_risk` | **Living 2-Tab Sheet** | Updated in place (`Summary` + `Risk Items` tabs) |
| **Layer 2** | `m2_input` | **Living Doc** | Append-only rounds (dated sections from top to bottom) |
| **Layer 1** | `evidence_log` | **Append-only Sheet/CSV** | Pure historical log (never overwrite old rows) |
| **Layer 1** | `qa_process_metrics` | **Periodic Sheet** | Append-only rows per sprint/period |

### Workspace-Wide Registries

Two workspace-wide Sheets sit directly under `20_M2_Project_Management`:

- `_project_registry` — one row per **active** project, the 13-column top-level
  "war room" dashboard:
  1. `Проект` (120 px) — Project name
  2. `People` (150 px) — Staffing with workstream tags (e.g. `<Person 1> (AQA), <Person 2> (Manual)`)
  3. `Engagement outlook` (140 px) — Structured: `<date> [Contractual] — <Outlook> (<Confidence>)`
  4. `Цель клиента / Ценность QA` (160 px) — Stated client objective with alignment flag
  5. `Текущий результат` (180 px) — Composite outcome (`Baseline [status] → Current [status] → Target [status]`)
  6. `Общий уровень риска` (90 px) — `Низкий` / `Средний` / `Высокий` (color-coded badge)
  7. `Ранний сигнал / Прогноз` (200 px) — Composite from top active risk item (`RSK-ID: <Statement> [<Prediction Status>]`)
  8. `Качество QA-процесса` (110 px) — Fixed-core process rating with data-confidence label
  9. `People requiring attention` (120 px) — Mechanically derived candidate signal (appends `[Stale: review required]` if underlying private risk is >30d unreviewed; `—` if none; strictly preserves privacy)
  10. `Действие M2` (140 px) — Primary mitigation action (and Upsell / Expansion tags when value is proven)
  11. `Уверенность в данных` (110 px) — Synthesized confidence with breakdown (`Executive: Med (Out: High, Risk: Low)`)
  12. `Owner` (80 px) — Action accountability owner
  13. `Следующий review` (80 px) — Next review date (`YYYY-MM-DD`)

  Total layout allocation is 1,680 px, maintaining a 100 px buffer within the nominal 1,780 px screen budget.
  A project not currently active (`project_metrics`'s `Статус проекта` is `Не активен`) is excluded from this registry.
- `_timeline` — generated rollup of every project's open `action_items`
  rows, sorted by date; the one place to see what's due today/tomorrow/this
  week across all projects. Never edited directly — refresh it with
  `refresh_timeline_registry.py` after changing a project's `action_items`.
  See `.agents/skills/m2-timeline`.

Project completeness is expected to be uneven under the incremental-fill
model (see `m2-role/m2-project-rollups.md`, Project-Level Rollups) — a freshly-scaffolded
project with mostly `Неизвестно` rows and an unanswered `m2_input` round
isn't a data-quality bug, it's the normal state before M2 has answered that
round.

### Folder Layout & Google Drive Access Control (ACL) Boundaries

Each project folder follows this shape:

```text
20_M2_Project_Management/<Project>/
├── private/                              <-- Unshared (M2/M3 only)
│   ├── project_risk.gsheet               <-- Living 2-tab workbook (Summary + Risk Items)
│   ├── process_checklist.gsheet
│   ├── project_development_plan.gdoc
│   ├── project_metrics.gsheet            <-- Living Sheet with composite identity
│   ├── evidence_log.gsheet               <-- Append-only source & routing log
│   ├── action_items.gsheet
│   ├── m2_input/m2_input.gdoc            <-- Formal decision gate (dated rounds)
│   ├── status_reports/
│   └── people/<Person>/                  <-- Unshared (M2 private 1:1s & risks)
│       ├── individual_risk.gsheet
│       └── <Person> 1to1.gsheet
├── team_shared/                          <-- Shared only with this project's QA team
│   └── qa_process_metrics.gsheet
└── people/<Person>/                      <-- Shared explicitly with <Person> (Viewer/Editor)
    ├── individual_development_plan.gdoc
    └── individual_metrics.gsheet
```

> [!CAUTION]
> **Drive ACL Safety Rule:** The `<Project>` root and `<Project>/private/` MUST NOT inherit permissions from `<Project>/people/<Person>/`. Sharing `<Project>/people/<Person>/` with an employee gives them access only to their own folder, never to sibling folders or the private root.

There is no per-project `source_docs/` or `archive/` folder - reference
`90_Storage/Reference/Source_Documents/<Project>` directly, and retired artifacts go to the
single workspace-wide `90_Storage/Retired/20_M2_Project_Management/<Project>/`
tree instead of a local copy that would go stale.

**Visibility boundaries**: share only `team_shared/` with the project's QA
team and only `people/<Person>/` with that person. Never share the
project root, `private/`, or `people/<Person>/` sibling folders. `qa_process_metrics` is the
team-editable factual input; its synthesized conclusion lives in the M2-only
`private/project_metrics`. See `google-workspace/api-sharing-editing.md`, Sharing Safety.

**Update chain**: `individual_metrics`/`individual_development_plan` (per
person) → `project_metrics` (per project) → `_project_registry` (across
all projects). A new source that changes something at the person level
should update the whole chain in the same pass — see `m2-role/m2-cascading-updates.md`,
Cascading Updates. Metric definitions and which artifact each one belongs
in: `Templates/метрики_qa_по_проекту.md` (individual) and
`Templates/метрики_проекта_qa.md` (project/QA-process/dashboard).

**Project Risk Workbook**: `project_risk` is one living Google Sheet with two tabs:
- `Summary` tab (mirrored locally by `Templates/светофор_рисков_проекта.csv`): 1-row-per-project executive summary with key risk ID and prediction status.
- `Risk Items` tab (mirrored locally by `Templates/project_risk_items.csv` fallback): itemized risk register with full lifecycle (`Severity`, `First Signal Date`, `Expected Impact Date`, `Materialization Date`, `Closed Date`, `Prediction Status`, `Migration State`).

**Migration Boundary**: Phase 1 is a repository documentation and graph-contract change only. Live Google Drive folders, permissions, and business data are not modified during this phase.

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

**Outstaff Delivery milestone reports**: for a project following the
department's Outstaff Delivery process standard (logged in
`qa_department_standards`), four skills draft the process's other
chat-ready milestone artifacts alongside `m2-project-status-report`'s
regular/onboarding-block reports: `m2-onboarding-report` (Day-1 start
report, final onboarding report), `m2-offboarding-report` (stop
retrospective), `m2-replacement-report` (the five staged Replacement
posts: launch, screening, CV review, interview feedback, close-out), and
`m2-shadow-onboarding-report` (weekly shadow-onboarding block, kickoff/
independent-work milestone notices). All four are `status_reports`-family
output, same folder/save convention as `m2-project-status-report`.

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
`google-workspace/operational-registries.md` and `document_graph.yaml`'s `lanes:` mapping).
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

## PM Case Library Layout

A fourth lane, distinct from all three above: `40_PM_Case_Library`, a flat,
cross-project, personal-reference collection of real management
situations (client/team/stakeholder behavior, what was tried, what
happened, the takeaway) — organized by pattern, not by project, so
similar situations across different projects/clients can be compared
side by side.

```
40_PM_Case_Library/
  pm_case_index                         (Sheet - one row per logged case)
  pm_case_library                       (Doc - the living case library,
                                          organized by theme)
```

No per-project subfolder — unlike the M1/M2/Project Knowledge lanes, this
one is intentionally flat (see `pm_case_workspace_layout.py`). Personal
reference only for v1 (not shared with other M2s). Two skills:
`pm-case-knowledge-roles` (shared judgment — what counts as a case, the
M1/M2/Project-Knowledge boundary, the same theme/H3-threshold and
Change-Log-one-liner structural rules as Project Knowledge's knowledge
bases) and `pm-case-knowledge-intake` (writes the two documents).

**Not a primary intake lane** — unlike the M1/M2/Project-Knowledge
source types, a case has no `source_type` of its own and never enters
`qa_manage.py`'s queue/classify/guide/pack pipeline directly. It is a
secondary, occasional output that `qa-1to1-analysis`/`m2-1to1-apply`,
`m2-strategy-chat-analysis`, `m2-status-meeting-intake`, and
`project-knowledge-intake` each route to when their own real pass
surfaces a case-shaped situation that doesn't belong in their own
document — most passes route nothing, and that's the normal outcome, not
a gap.

## QA Department Standards Layout

A fifth lane, distinct from all four above: `50_QA_Department_Standards`,
a flat, personal-reference pair of documents. Not per-project (unlike
Project Knowledge) and not a situation log (unlike the PM Case Library) —
this is the current-state answer to "what does the department expect
right now" (tools, process requirements, standing direction), plus a
separate personal log of the user's own management lessons learned.

```
50_QA_Department_Standards/
  qa_department_standards               (Doc - current department
                                          tools/process/direction,
                                          topic-organized, updated in
                                          place — not append-only)
  m2_lessons_learned                     (Doc - personal, append-only
                                          retrospective log)
```

No per-project subfolder — flat, same as the PM Case Library (see
`qa_dept_standards_workspace_layout.py`). Personal reference only, not
shared. Two skills: `qa-department-standards-roles` (shared judgment —
what counts as a real entry, the boundary vs Project
Knowledge/PM-Case-Library/M1/M2, the topic-organized-vs-append-only
structural split between the two documents) and
`qa-department-standards-intake` (writes both documents).

**Not a primary intake lane** — like the PM Case Library, this has no
`source_type` of its own and never enters `qa_manage.py`'s
queue/classify/guide/pack pipeline directly. It fires as a secondary,
occasional output of `m2-status-meeting-intake`, `m2-strategy-chat-analysis`,
and `m2-admin-note-intake` when their own real pass surfaces a genuine
department-wide standards change, or as a standalone pass on direct
M3/department-head relay or a direct request to log a lesson learned —
most passes route nothing, and that's the normal outcome, not a gap.

## Assessments & Interviews Layout

A sixth lane: `60_Assessments_And_Interviews`, per-session evaluation
documents about one named person. Not current-state (unlike M1/M2) and
not a reference library (unlike the PM Case Library or QA Department
Standards) — each document is the record of one meeting that already
happened, so a new session never rewrites an earlier session's document.

Type-first, then person, because the session *type* owns both the
assessment criteria and the output form: an internal grade assessment is
scored against our own competency matrix, a client interview against that
client's own questions and the CV they received.

```
60_Assessments_And_Interviews/
  internal_assessments/
    <Person>/
      2026-08-28_assessment_feedback - <Person>   (Doc)
      2026-08-28_transcript - <Person>            (Doc, optional)
  external_interviews/
    <Person>/
      2026-09-02_interview_feedback - <Person>    (Doc)
  other_interviews/                               (mock/screening/internal
                                                    role interviews — no
                                                    owning skill, no scored
                                                    verdict)
  _assessment_index                               (Sheet - one row per
                                                    processed session)
```

Names come from `assessment_workspace_layout.session_document_name()` —
never hand-built. `find_*` never creates a folder; `ensure_*` creates only
what a real session needs, so an unused type folder never appears.
Reports are authored as local Markdown first and published with
`publish_markdown_doc.py`; a re-publish of the same session replaces that
document's body (`--doc-id`) rather than adding a second copy.

Three skills: `interview-assessment-roles` (lane boundary, evidence
discipline — including the unaided-vs-led distinction that drives every
verdict — storage/indexing, privacy), `internal-assessment-feedback`
(matrix + transcript in, publishable grade feedback out), and
`external-interview-feedback` (CV + transcript in, client-interview
debrief out).

**A primary intake lane, but with no downstream cascade.** It owns two
`source_type` values — `assessment_transcript` and
`external_interview_transcript` — and its own entry documents, but no
edge into any M1/M2 document. A gap found in a session becomes a
development-plan item, a PM case, or a department standard only through a
separate, judged pass into that lane's own skill; making it a required
cascade target would turn every assessment into a mandatory edit of
someone's development plan.

Raw video/audio never lands here — transcripts and documents only, same
rule as the rest of the workspace.

## Visual Evidence Drop

`00_Inbox/_Visual_Drop/` is a special subfolder for raw screenshot dumps
with arbitrary filenames, plus optional rough context notes such as
`visual_context.md` or `visual_context_notes.txt` (project, related
meeting/source, person, groups, what to extract).
Image files aren't in `qa_manage.py`'s `SCAN_EXTS`, so they never get
auto-queued - they sit inert until an agent organizes them via the
`visual-evidence-intake` skill into a renamed/grouped bundle under
`00_Inbox/<Project>/visual-bundle-<topic>/` with a preserved
original-filename-to-new-filename mapping. Screenshots can be sidecar
visual evidence for an already-processed transcript or document, but they
do not replace the text source. See
`.agents/skills/visual-evidence-intake/SKILL.md`.
