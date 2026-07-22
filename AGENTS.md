# QA Management - Workspace Agent Policy

This file is the workspace-level policy for AI agents working in this repository.

## Purpose

This repository stores QA-management agent infrastructure for both:

- `M1` people-management workflows
- `M2` project-management workflows

## No Sensitive Data In This Repository

This repository is **public**. It holds abstract skill logic, templates,
and scripts only — never real business data. Before writing or editing
any file here (skills, references, templates, scripts, README/AGENTS
content, commit messages), check that it contains none of:

- a real person's name (employee, client, candidate — first name alone
  included, if it identifies someone in context), in any script
- a real company name — including this tool's own operating company; use
  `Internal`/`the company` generically (see Company context below)
- a real client/project codename
- a real email address, phone number, or other contact detail
- verbatim content copied from a real transcript, chat, 1:1, risk
  narrative, or similar first-party source, even as an "example"
- any other detail that identifies a specific real person, team, or
  engagement

Development-tool and API-provider names/domains (e.g. the AI coding
agents named in Multi-Agent Convention below, Google Workspace APIs) are
allowed when needed for technical documentation or commit attribution —
including `Co-Authored-By` trailers. The prohibition covers real
employer, client, engagement, employee, and other business identities,
plus personal contact details.

If a rule or example needs illustrating, use a placeholder
(`<Person>`/`<Имя>`, `<Project>`, `<email>`) or describe the pattern in
the abstract ("a real example seen on this kind of team looks like...")
instead of naming the actual instance. This applies to commit messages
too, not just file content — a redacted file with an identifying commit
message defeats the point.

Real names, real project data, and any other company-specific detail
belong **only** in the corporate Google Drive workspace referenced below
— principally `_people_registry` for who's who, and each project's own
folder for project-specific facts. Skills should read/write that data via
the Drive API at runtime, never hardcode it here.

This strict rule applies to **this repository only**. The Drive workspace
itself is internal, shared only with the relevant management audience —
real names, personal/compensation history, performance judgments, and
reliability assessments about named colleagues are exactly what documents
like `project_risk`, `individual_*`, and the department traffic-light
tracker are for. Don't hedge, genericize, or hold back real judgment
content when writing into a Drive Sheet/Doc just because the same detail
would be unsafe here in the repo — the two have different audiences by
design, and treating Drive output with repo-level caution just adds
friction nobody asked for. Ordinary evidence-backed judgment still applies
(don't state something as fact without support); this is only about not
over-redacting real, sourced content meant for that audience.

If you ever find real data that leaked into this repo (an example,
a leftover reference, a stray script), don't just delete it going
forward — flag it, since it may also need scrubbing from git history
(`git log --all -p` still exposes it even after a file is fixed/deleted
in the current tree).

**Company context**: skills here assume a QA department inside an
outsource software development company, staffing engineers onto client
projects. `Side` values are `Internal` (this company's own staff) vs.
`Client` (client-side or third-party vendor people) — never the literal
company name. If you're adapting this repository for a real company,
`apply_person_card.py`'s `COMPANY_EMAIL_DOMAIN`/`COMPANY_SIDE_LABEL` are
the one place a real domain gets configured — and that file stays local/
private, not committed with a real value filled in.

Business data and generated outputs live in the QA Management Google Drive workspace:

`https://drive.google.com/drive/u/0/folders/1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`

Google Drive root folder ID:

`1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`

The desktop mirror / filesystem fallback is:

`G:\My Drive\QA_Management`

## Start Here (Before Manual Drive/Sheets/Docs Calls)

Before writing any ad hoc script to read or update Drive/Sheets/Docs content:

1. Check whether Google API access is already set up: `.local/google/credentials.json`
   and `.local/google/token.json` (see `README.md`, Google API Smoke Test). If both
   exist, the API pipeline is usable — don't assume CSV/Markdown fallback without
   checking first.
2. Read `README.md`'s **Current pipeline scripts** section before hand-rolling a new
   script. Most tasks map to an existing one:
   - Need to see a project's or the registries' current state? —
     `.agents\scripts\show_project_state.py --project <Name>` /
     `--registries`. Read-only, safe to run anytime, creates nothing. Add
     `--summary` for a cheap one-liner per project (People count, risk
     level, last evidence_log date) to triage before pulling a full dump.
     For programmatic targeted reads (Phase 3), use `--document <Name>`,
     `--person <Name>`, `--since YYYY-MM-DD`, and `--limit N` along with `--json`
     to emit a strict JSON envelope. Pass `--lane project_knowledge` (default
     `m2`) for a project under `30_Project_Knowledge` instead of
     `20_M2_Project_Management` - see the Project Knowledge lane below;
     `--registries`/`--summary`/`--person` are not supported for that lane.
   - Need to search the entire workspace or view historical changes? —
     `.agents\scripts\search_workspace.py search <query>` (current state) or
     `.agents\scripts\search_workspace.py history <query>` (first-parent commit traversal).
     It provides deterministic literal-path search across the canonical `.md`/`.csv` corpus
     and `_source_text` blobs using Git. Output can be limited by path, kind, run-id, or dates.
     Passing `--json` emits a strict JSON envelope buffering output for programmatic consumption.
     See `.agents\references\search-cookbook.md` (Phase 12) for worked recipes
     ("where was X last mentioned", "what changed since date", canonical-only vs.
     source-only, one run by run-id) and when to prefer
     `show_project_state.py` instead (live Drive state vs. the mirror's last
     committed snapshot, which can be stale). Unprocessed-inbox inspection
     (a source not yet processed) goes through `triage`/`triage-one`/
     `classify`/`pack` instead - `search_workspace.py` only sees what's
     already in the mirror.
   - Working on project understanding/onboarding rather than M1/M2
     management reporting? — the **Project Knowledge lane**
     (`30_Project_Knowledge\<Project>\`, Phase 13.1). Builds a project
     knowledge base gradually from whatever sources actually exist
     (transcripts, documents, chats, owner notes) - a formal
     knowledge-transfer session (`project_knowledge_transcript`) is one
     possible input, never a prerequisite; a project can start in this
     lane with poor/incomplete documentation. Reuses the normal intake
     queue/archive/mirror pipeline: `scan`/`triage`/`classify`/`guide`/
     `pack` all work unchanged (`route_description` surfaces for these
     routes the same way it does for M1/M2 ones); `dashboard`/`triage`
     have no `--lane` filter yet, and `qa_manage.py gates` stays M2-only
     (this lane has no `m2_input`-style two-phase gate). Four source
     types: `project_knowledge_transcript`, `project_knowledge_document`,
     `project_knowledge_chat`, `project_knowledge_notes`; skills
     `project-knowledge-roles` (shared rules) and
     `project-knowledge-intake` (source-triggered). Private by default
     (no shared/team_shared split) - sharing an individual Doc is a
     deliberate, one-off action outside automation. No Google Slides in
     this phase - presentation output is explicitly deferred to a later
     phase, not part of Phase 13.1.
   - Want to know what M2 still owes an answer on — pending `m2_input`
     rounds gating `project_risk`/`project_development_plan` across
     projects? — `.agents\scripts\qa_manage.py gates [--project <Name>]
     [--min-age-days N] [--json]` (Phase 12). Read-only, sorted oldest
     first: round age, addenda count, first addendum heading only (never
     question/addendum text), and a deterministic `recommended_action`.
     Never answers a question, writes a document, or records closure — this
     is a review command, not an intake-processing one; `dashboard` remains
     the default first entry point for intake-queue work.
   - Starting a session, or not sure what needs attention right now? —
     run `.agents\scripts\qa_manage.py dashboard` first, before `scan`,
     `next`, `start`, `review`, or `complete`. It's the default operator
     entry point: a read-only summary of every run needing the next agent
     action (grouped with the exact next command), blocked/finalizing
     runs, integrity issues on finalizing/completed runs (reusing
     `review`'s own evaluation, bounded by `--limit`), and a read-only
     `00_Inbox`/`90_Storage` file-count summary (add `--json` for the
     strict envelope). Never creates or mutates anything. Use it to decide
     *which* run/action needs attention.
   - `dashboard` pointed you at a run - what exactly do I do for it? —
     `.agents\scripts\qa_manage.py guide <run-id>` (add `--json` for the
     strict envelope). Read-only, one run at a time: identity (status,
     stage, source path, scopes, snapshot), the graph route's
     interpretation (skills/entry documents), a stage-specific checklist
     with exact command templates (the `start`/`add-scope` scope fields a
     `needs_scope` row is missing, `record-analysis`, which entry
     documents a `processing/apply` run still needs `record-apply` for,
     which edges a `processing/closure` run still needs `resolve-edge`
     for, `commit_workspace_state.py` when closure is clean but the
     snapshot/invocation token isn't, `complete`/`complete` retry,
     `resume --continue`, `mark-historical`), and only the guardrails relevant
     to that stage. Never creates or mutates anything. Use this once
     `dashboard` (or a direct find) has pointed you at a specific run;
     once you know the exact command, the full intake workflow below is
     how you actually process it.
   - `guide` says a `discovered` run needs a source_type/variant/scope
     judgment call before `start` - want a cheap read-only preview first? —
     `.agents\scripts\qa_manage.py classify <run-id>` (add `--json` for the
     strict envelope; `--max-preview-chars N` caps the returned excerpt,
     default 2000). Reads `Current source` (falling back to `Source`),
     reports deterministic format signals only - no AI/LLM call, no
     semantic judgment: line count, distinct speaker-like prefix count,
     Google-Chat-style header count, date/time marker count, email-header
     marker count. From those signals plus `document_graph.yaml` it lists
     unranked `candidate_routes` (source_type, variant, required scope,
     skills, entry documents, and the exact signal behind each one) and
     command templates (`guide`, one `start ...` per candidate, `ignore
     ...` when the row's own duplicate-detection Reason suggests it). It
     never picks a final route, never calls `start`, never writes
     anywhere, and never puts the preview text or full source content into
     the queue or this repo - the classification decision, made after
     actually reading the source, stays with the agent.
   - Handing a run off to another agent session (or resuming one cold)? —
     `.agents\scripts\qa_manage.py pack <run-id>` (add `--json` for the
     strict envelope; `--max-preview-chars N` caps the source preview,
     default 2000). One compact read-only packet combining identity
     (status/stage, `Source` vs `Current source`, source_type/variant,
     scopes, source hash, source text version, Snapshot SHA,
     disposition), `dashboard`'s category for this run, `guide`'s
     checklist/commands/guardrails, `review`'s evaluate_run summary
     (unresolved edges, entry problems, invocation/snapshot status), a
     `classify`-style signals+candidate_routes block *only* when the
     route isn't resolved yet, graph context (skills/entry docs/required
     scope, plus downstream closure expectations once at the closure
     stage), a capped source preview (`Current source` preferred), and a
     short `agent_handoff` block naming what to read first, which skill(s)
     to load, the exact next command, and what not to do. Reuses
     `dashboard`/`guide`/`classify`/`review` exclusively; never creates,
     writes, or mutates anything, and never includes full source text -
     only the same capped preview `classify` returns.
   - Cleaning up the `00_Inbox` backlog itself (not processing a specific
     source right now)? — `.agents\scripts\qa_manage.py triage
     [--category discovered|needs_scope|blocked|all] [--limit N]
     [--project P] [--person X]` (add `--json`). Read-only overview built
     from the same dashboard/classify helpers: every backlog candidate
     with its recommended command and the exact terminal-action commands
     (`ignore`/`mark-historical`) `TRANSITIONS` actually allows from its
     status - never a suggestion to auto-apply one, and never an inference
     from filename/extension alone. Drill into one with `qa_manage.py
     triage-one <run-id>` for source access/age, `classify`-style signals
     and candidate routes, a capped preview, and the same allowed-action
     commands, all for a single run. Both are strictly read-only - the
     only way to actually change a run's state is the explicit `ignore`
     (`--category C --reason "..." [--evidence "..."]`, required reason,
     only reachable from `discovered`/`needs_scope`/`ready`) or
     `mark-historical` (`--evidence "..."`, required concrete evidence -
     not a vague reason or memory - only reachable from a pre-processing
     state or as a correction of a mistaken `fail`; invalid once
     `processing`/`blocked` has actually started) command below, one run
     at a time. Neither moves or deletes the source file - a
     terminal-status queue row already keeps `scan` from rediscovering it.
   - Processing a new source (picked via `dashboard`/`guide`/`classify`/
     `pack`, or found directly)? —
     the intake workflow runs through
     `.agents\scripts\qa_manage.py` (state machine; you keep the
     judgment): `scan` → `next` → read the source → `start <run-id>
     --source-type ... [--variant] [--scope "Project|Person" ...]` →
     apply the listed skills → `record-analysis --summary` →
     `record-apply` per scope (`--updated`/`--no-change`/
     `--not-applicable`, reasons required) → `resolve-edge` per cascade
     edge → `archive-source <run-id>` →
     `commit_workspace_state.py -m "...[<run-id>]"` → `complete`.
     `archive-source` moves the original from `00_Inbox` to a run-specific
     `90_Storage/Processed_Sources` folder while preserving Drive identity;
     the snapshot must be created after this move.
     Put the exact token `run:<run-id>` in the `_skill_invocations`
     Notes and the run id in the mirror commit message. The `commit_workspace_state.py`
     pass also automatically extracts and commits the source text into the private mirror.
     Full export (walking the entire tree, skipping only `90_Storage`/`01_Recordings` as
     before) remains the **default** and prints per-file export timing/counts every run;
     pass `--stats-out <path>` to also dump those stats as JSON. **Phase 14B:**
     `--scoped --run-id <run-id>` is an opt-in mode for routine single-project/
     single-person/workspace-only-bookkeeping runs - it exports only that run's scope
     (`scope_resolver.py`, reusing the same `enumerate_run_scopes()` `review`/`complete`
     trust) plus workspace-root/lane-root bookkeeping and source-text, never touching or
     pruning anything outside that scope. It fails closed (exits 1, telling you to re-run
     without `--scoped`) if the scope, a lane, or a folder can't be resolved, or if the
     mirror's `_manifest.json` is missing/malformed. Multi-project rollups and periodic
     audits should keep using full export - scoping barely helps there since most of the
     lane is already in scope. Run one full export once after adopting `--scoped` (and
     after any manual Drive edit or folder-layout change) so the manifest scoped mode
     carries forward from stays trustworthy.
     `complete` verifies the invocation evidence, per-scope closure, and requires verification
     of the exact business snapshot SHA from the queue's `Snapshot` column. For `Source text version 1`
     runs, it also verifies that the exact snapshot SHA contains the exported text blob.
     After `complete` (or after any conversational rollup pass that ends with its own
     `commit_workspace_state.py` snapshot - an M2 answer pass, a repo-maintenance fix, etc.),
     record one telemetry row: `.agents\scripts\measure_operator_outputs.py --case
     completed_run_review --run-id <run-id> --append-csv` (or `--case pack_discovered`/
     `--case search_current`, whichever command you actually used to review the finished
     pass). This is a closing step for every real intake/rollup pass, not optional
     instrumentation - see `.agents\telemetry\README.md`. The row stores only redacted
     command labels and counts (byte/char/deterministic token estimates); it never stores
     real output, source text, or names - actual token fields stay blank unless you have
     real agent-log telemetry for that pass (`extract_agent_telemetry.py`), never invented.
   - Need to find new/unprocessed source files? —
     `.agents\scripts\prepare_intake_review.py` (transcripts/chats/source
     documents) or `.agents\scripts\detect_strategy_chats.py`
     (`_strategy` chats specifically) — or `qa_manage.py scan`, which
     also creates queue rows.
   - Just routed a source into project documents? —
     `.agents\scripts\check_cascade_closure.py --touched <docs>` (or
     `--from-log 1`) expands `.agents\document_graph.yaml` and flags every
     downstream document not yet accounted for. Record each edge's
     resolution with `closure_outcomes.py record --run-id <date>-<slug>
     ... --outcome updated|no_change|gated|regenerated` (reason required
     for no_change/gated), then re-run the closure check with
     `--run-id` — it must report CLOSED before the pass ends.
   - Then record the pass in the data-side history:
     `.agents\scripts\commit_workspace_state.py -m "<skill>: <source>"` —
     exports the workspace's canonical documents into the local private
     mirror repo (`~/Documents/qa-drive-mirror`, real data, never public)
     and commits, so the whole pass can be diffed or rolled back as one
     unit later (`rollback_from_mirror.py`). The mirror automatically stores exact,
     content-addressed text representations of source chats and transcripts, which means it
     contains real conversation text and must remain strictly private. Harmless when nothing
     changed. Before treating the commit as done, check the "Changed files" list the
     script prints (or `git -C ~/Documents/qa-drive-mirror status`/`diff`)
     against what this pass was actually supposed to touch, and report
     anything outside that scope as unrelated Drive drift instead of
     silently committing it - standing practice (qa-retro, 2026-07-21),
     not something to be asked for on each individual pass.
   - Writing a new one-off inspection/update script anyway? Reuse
     `.agents\scripts\pipeline_common.py`'s `get_services()` instead of
     re-inlining `load_credentials`/`build_services` boilerplate.
   - Want to know whether the operator commands above (`dashboard`, `guide`,
     `classify`, `pack`, `triage`, `search_workspace`,
     `show_project_state --document`) actually save output/tokens versus an
     older full-read workflow, or just recording that a real pass happened?
     — Phase 11's telemetry layer, `.agents\telemetry\README.md`.
     `.agents\scripts\measure_operator_outputs.py --case <case_id>
     [--dry-run]` runs one read-only case and measures elapsed time,
     byte/char counts, and a deterministic token estimate (never the real
     output); `--append-csv` records a redacted row in
     `.agents\telemetry\operator-runs.csv`. Cases include
     `dashboard_overview`, `guide_discovered`, `classify_discovered`,
     `pack_discovered`, `completed_run_review` (`qa_manage.py review`),
     `triage_overview`/`triage_one`, `search_current`/`search_history`,
     `show_project_state_targeted`/`show_project_state_full_project`.
     `finalize_operator_run.py` enriches a row with actual token telemetry
     (only if you have real agent-log data - never invented) and a
     baseline reduction ratio; `check_operator_csv.py` validates the CSV
     and diff-guards a specific append. Recording a row after every real
     intake/rollup pass is a mandatory closing step (see the intake
     workflow above) - not optional instrumentation. This does not change
     which command is the default entry point — `dashboard` still is — it
     only measures/records the existing workflow.
3. Only fall back to raw filesystem exploration (`find`/`Glob`) under
   `G:\My Drive\QA_Management` for genuinely new source files that haven't been
   classified yet — not for inspecting already-canonical project documents, which
   are Google Sheets/Docs and can't be read as plain files anyway (they'll error
   with "Invalid request code" if you try).

## Skill Location

Local skills live under:

```text
.agents/skills/
```

Current canonical skills:

| Skill | Role | Outcome | Canonical source |
|-------|------|---------|------------------|
| `qa-1to1-analysis` | Common | Shared structured analysis from a QA 1to1 transcript for both M1 and M2, including topic classification, evidence extraction, and people/project signal separation | `.agents/skills/qa-1to1-analysis/SKILL.md` |
| `m2-strategy-chat-analysis` | M2 | Analysis of a project-level "_strategy" chat export (running, multi-month, multi-stakeholder planning/status channel for one project) into project-scoped facts, routed via the normal M2 cascading-update/rollup chain | `.agents/skills/m2-strategy-chat-analysis/SKILL.md` |
| `m2-admin-note-intake` | M2 | Short pasted-inline (not file-based) conversation snippets about chat access/membership, chat/project naming ambiguity, and structured person-info cards | `.agents/skills/m2-admin-note-intake/SKILL.md` |
| `m2-1to1-apply` | M2 | Routes a QA 1:1 transcript's already-analyzed (via `qa-1to1-analysis`) findings through the M2 cascading-update chain into individual/project documents and `m2_input` | `.agents/skills/m2-1to1-apply/SKILL.md` |
| `qa-management-roles` | Common | Shared M1/M2/M3/M4 role boundaries and role rules, including M1 people-management goals and M2 project-management/business-value rules | `.agents/skills/qa-management-roles/SKILL.md` |
| `m1-people-1to1-file` | M1 | Individual person Google Sheet inside `10_M1_People_Management\<Person>\`, with CSV fallback, based on `Templates/1to1.csv` from this repo | `.agents/skills/m1-people-1to1-file/SKILL.md` |
| `m1-1to1-prep` | M1 | Scoped question list for an upcoming M1 1to1 with a specific QA engineer, driven by that person's current people-risk signals | `.agents/skills/m1-1to1-prep/SKILL.md` |
| `m2-1to1-prep` | M2 | Scoped question list for an upcoming M2 1to1 with a specific QA engineer on one of M2's projects | `.agents/skills/m2-1to1-prep/SKILL.md` |
| `m2-status-meeting-intake` | M2 | Multi-project M2/M3 status-review meeting transcript split per project and routed through the normal m2_input/action_items/evidence_log chain | `.agents/skills/m2-status-meeting-intake/SKILL.md` |
| `m1-people-risk-report` | M1 | Living people risk traffic-light Google Sheet (`Светофор рисков`), with CSV fallback, based on `Templates/светофор_рисков.csv` from this repo | `.agents/skills/m1-people-risk-report/SKILL.md` |
| `m1-individual-development-plan` | M1 | Individual OKR Google Doc per Performance Review cycle, with Markdown fallback, based on `Templates/okr_m1.md` from this repo | `.agents/skills/m1-individual-development-plan/SKILL.md` |
| `m1-timeline` | M1 | Workspace-wide `_m1_timeline` Google Sheet (Performance Reviews computed from real PR cadence, OKR cycle closures, monthly-report deadlines, follow-ups) plus the generated `_m1_pr_calendar` PR-only view, with CSV fallback | `.agents/skills/m1-timeline/SKILL.md` |
| `m-self-review` | Common (M1/M2) | M1's/M2's own Performance Review self-prep: dated `критерии_оценки_команды` team-scoring Google Sheet (CSV fallback) plus a chat-ready self-review prep summary | `.agents/skills/m-self-review/SKILL.md` |
| `salary-review-prep` | Common | Salary-review self-feedback Google Doc draft (evidence-backed value growth, AI-competency status, blocker pre-check) for a team member or for M1/M2 themselves, based on `Templates/salary_review_self_feedback.md` | `.agents/skills/salary-review-prep/SKILL.md` |
| `m2-people-1to1-file` | M2 | Individual person Google Sheet in `20_M2_Project_Management`, with CSV fallback, based on `Templates/1to1.csv` from this repo | `.agents/skills/m2-people-1to1-file/SKILL.md` |
| `m2-project-risk-report` | M2 | Project risk traffic-light Google Sheet, with CSV fallback | `.agents/skills/m2-project-risk-report/SKILL.md` |
| `m2-project-process-checklist` | M2 | Living per-project outsource QA process-maturity checklist Google Sheet (12 sections), with CSV fallback, based on `Templates/аутсорс_чек_лист_qa.csv` | `.agents/skills/m2-project-process-checklist/SKILL.md` |
| `m2-project-qa-metrics-report` | M2 | Project-level QA metrics Google Sheet, with CSV fallback | `.agents/skills/m2-project-qa-metrics-report/SKILL.md` |
| `m2-individual-qa-metrics-report` | M2 | Individual QA metrics Google Sheet within project scope, with CSV fallback | `.agents/skills/m2-individual-qa-metrics-report/SKILL.md` |
| `m2-project-development-plan` | M2 | Project-level development-plan Google Doc (narrative, synced via `sync_m2_plans_to_docs.py`), with Markdown fallback | `.agents/skills/m2-project-development-plan/SKILL.md` |
| `m2-individual-development-plan` | M2 | Individual development-plan Google Doc within project scope (employee-visible), with Markdown fallback | `.agents/skills/m2-individual-development-plan/SKILL.md` |
| `m2-project-status-report` | M2 | Short chat-ready project status report for a requested period; regular saved reports use Google Docs with Markdown fallback | `.agents/skills/m2-project-status-report/SKILL.md` |
| `m2-department-traffic-light` | M2 | Fills M2's own row block on the department's shared (foreign, not workspace-generated) "Auto staff. Светофор проектов" outstaff tracker from real source documents | `.agents/skills/m2-department-traffic-light/SKILL.md` |
| `m2-timeline` | M2 | Per-project `action_items` Google Sheet (events, deadlines, follow-ups) and the workspace-wide `_timeline` rollup, with CSV fallback | `.agents/skills/m2-timeline/SKILL.md` |
| `m1-monthly-report` | M1 | Monthly M1 KPI/bonus Google Sheet, with CSV fallback, based on monthly report workbook structure and evidence-backed people-management data | `.agents/skills/m1-monthly-report/SKILL.md` |
| `m2-monthly-report` | M2 | Monthly M2 KPI/bonus Google Sheet, with CSV fallback, based on monthly report example structure and evidence-backed project-management data | `.agents/skills/m2-monthly-report/SKILL.md` |
| `qa-retro` | Common | Improvement-loop retro pass: turns repeated friction/feedback since the last retro (via `prepare_retro.py` over `_skill_invocations`) into proposed skill/reference/graph edits, presented as diffs for user review | `.agents/skills/qa-retro/SKILL.md` |
| `repo-maintenance` | Common | Consistency checklist for any structural change to this repo (skill/script/template/document-type/dependency), keeping AGENTS.md, README, `document_graph.yaml`, and source-type lists in sync in the same commit | `.agents/skills/repo-maintenance/SKILL.md` |
| `project-knowledge-roles` | Project Knowledge | Shared rules for the Project Knowledge lane (`30_Project_Knowledge`) - gradual knowledge accumulation from diverse sources, durable-vs-one-off distinction, open questions, M1/M2 boundary, QA docs as downstream products | `.agents/skills/project-knowledge-roles/SKILL.md` |
| `project-knowledge-intake` | Project Knowledge | Source-triggered intake for `project_knowledge_transcript`/`document`/`chat`/`notes`: summary (where appropriate), `pk_source_index` row, `pk_knowledge_base` update, optional QA-doc update | `.agents/skills/project-knowledge-intake/SKILL.md` |

Load only the skill needed for the current outcome. Do not preload other role skills.

## Repository Contents

- `.agents/skills`: local skills and skill-local scripts
- `Templates`: canonical CSV templates used as schemas for Google Sheets or local CSV fallback
- `.agents/skills/qa-1to1-analysis/references`: shared 1to1 topic, risk, and wording rules
- `.agents/skills/qa-management-roles/references`: shared M1/M2 role boundaries and management rules
- `README.md`: repo overview

## Data Root

Use the Google Drive root folder ID `1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc` as the canonical business workspace when Google API access is available. Use `G:\My Drive\QA_Management` as the local mirror and fallback data root unless the user points to a different dataset location.

Expected data folders under that root:

- `00_Inbox`: the only intake folder; recursively scanned, and empty means there are no unprocessed files
- `10_M1_People_Management`: person-based, `<Person>\` subfolder per team member (1to1, OKR, salary-review self-feedback); the living `Светофор рисков` sheet, `_m1_timeline`, and M1's own monthly report stay at the root — see `google-workspace-rules.md`, M1 Person-Based Layout
- `20_M2_Project_Management`: M2 project-management outputs
- `80_Exports` (optional): created only when an explicit immutable package/copy is prepared for external sharing
- `90_Storage`: the single non-actionable storage root, containing `Reference`,
  `Processed_Sources`, `_System`, `Backups`, and `Retired`
  It is explicitly excluded from source discovery; moving a file here means it
  is no longer part of the active intake backlog.

M2 project-management outputs are project-based. Each active project should have
its own folder under `20_M2_Project_Management`, for example:

```text
20_M2_Project_Management/<Project>/
├─ private/
│  ├─ project_risk.gsheet
│  ├─ process_checklist.gsheet
│  ├─ project_development_plan.gdoc
│  ├─ project_metrics.gsheet
│  ├─ evidence_log.gsheet
│  ├─ action_items.gsheet
│  ├─ m2_input/m2_input.gdoc
│  ├─ status_reports/
│  └─ people/<Person>/individual_metrics_internal.gsheet
├─ team_shared/qa_process_metrics.gsheet
└─ people/<Person>/shared/
   ├─ individual_development_plan.gdoc
   └─ individual_metrics.gsheet
```

Share only `team_shared/` with the project QA team and only a specific
`people/<Person>/shared/` folder with that person. Never share the project
root or `private/`.

Use `_project_registry.gsheet` / `_project_registry.csv` in
`20_M2_Project_Management` to track active project names, aliases, people, and
source locations. For broad cross-project sources, split extracted facts by
project first, update each project folder separately, then archive the aggregate
source/output as evidence.

Archived legacy locations:

- `90_Storage/Retired/VSCode_Settings_Backup`: former top-level `.vscode`
- `90_Storage/Retired/03_Projects_DC_old_empty_placeholder`: preserved old empty DC placeholder

## General Rules

- Start from the smallest relevant evidence source.
- Do not invent unsupported facts.
- Keep final business-facing text concrete and evidence-based.
- Use Russian as the default language for business-facing analysis and generated outputs unless the user explicitly requests another language.
- Preserve English terms, definitions, and citations when they are part of the source or normal working vocabulary.
- Preserve established template schemas and filename conventions unless the user requests a schema change.
- Prefer Google Sheets for final tabular business outputs and Google Docs for final narrative/status outputs. Use local CSV/Markdown in `G:\My Drive\QA_Management` only as fallback, staging, or source-extraction output when Google API access is unavailable or not requested.
- For M2, route final tabular outputs into the relevant project folder. Do not keep cross-project KT or batch files as canonical final documents; use them only as intermediate evidence that feeds project-local files.
- Each report-generation skill should target one expected output document format.
- Do not overwrite existing final dated/monthly documents by default. If a final document already exists for the same snapshot date or reporting month, create the next `_vN` file, for example `_v2`, `_v3`, unless the user explicitly asks to revise the existing file in place.
- Personal 1to1 files are append-only longitudinal records, not versioned snapshot documents. Preserve old rows and revise an old row only when the user explicitly asks for correction.

## Multi-Agent Convention

This repository is intended to be usable by Codex, Antigravity, and Claude Code through the same shared skill files under `.agents/skills/`.
Keep runtime differences limited to invocation notes inside the skills.
