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

M2 is organized by project context. Two workspace-wide Sheets sit directly
under `20_M2_Project_Management`:

- `_project_registry` — one row per **active** project, the top-level "war
  room" dashboard (Проект, People, Горизонт совместной работы, Бизнес-риск
  продукта клиента, Наименьший вклад в проект, Качество QA-процесса).
  A project not currently active (temporary pause or permanent stop alike —
  `project_metrics`'s `Статус проекта` is exactly two values, `Активен` /
  `Не активен`, see `Templates/метрики_проекта_qa.md` §1.0) is excluded
  from this registry, not kept and marked inactive — set `Статус проекта`
  to `Не активен` and rerun `refresh_project_registry.py`.
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
│     ├─ individual_risk.gsheet
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
`private/project_metrics`. See `google-workspace/api-sharing-editing.md`, Sharing Safety.

**Update chain**: `individual_metrics`/`individual_development_plan` (per
person) → `project_metrics` (per project) → `_project_registry` (across
all projects). A new source that changes something at the person level
should update the whole chain in the same pass — see `m2-role/m2-cascading-updates.md`,
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
