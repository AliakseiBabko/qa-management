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
   - Need to find new/unprocessed source files? —
     `.agents\scripts\prepare_intake_review.py` (transcripts/chats/source
     documents) or `.agents\scripts\detect_strategy_chats.py`
     (`_strategy` chats specifically).
   - Just routed a source into project documents? —
     `.agents\scripts\check_cascade_closure.py --touched <docs>` (or
     `--from-log 1`) expands `.agents\document_graph.yaml` and flags every
     downstream document not yet accounted for. Don't end an intake pass
     with it still reporting OPEN items — resolve each as an update or an
     explicit "no change needed".
   - Then record the pass in the data-side history:
     `.agents\scripts\commit_workspace_state.py -m "<skill>: <source>"` —
     exports the workspace's canonical documents into the local private
     mirror repo (`~/Documents/qa-drive-mirror`, real data, never public)
     and commits, so the whole pass can be diffed or rolled back as one
     unit later (`rollback_from_mirror.py`). Harmless when nothing
     changed.
   - Writing a new one-off inspection/update script anyway? Reuse
     `.agents\scripts\pipeline_common.py`'s `get_services()` instead of
     re-inlining `load_credentials`/`build_services` boilerplate.
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

- `00_Source_Docs`: durable source documents and reference materials
- `01_Recordings`: raw meeting recordings
- `02_Transcripts_Inbox`: raw transcript intake
- `03_Transcripts_Processed`: transcripts that have already been analyzed or moved out of intake
- `10_M1_People_Management`: person-based, `<Person>\` subfolder per team member (1to1, OKR, salary-review self-feedback); the living `Светофор рисков` sheet, `_m1_timeline`, and M1's own monthly report stay at the root — see `google-workspace-rules.md`, M1 Person-Based Layout
- `20_M2_Project_Management`: M2 project-management outputs
- `80_Exports`: exported packages, shares, or generated external copies
- `90_Archive`: archived legacy folders and backups

M2 project-management outputs are project-based. Each active project should have
its own folder under `20_M2_Project_Management`, for example:

```text
20_M2_Project_Management/<Project>/
├─ project_risk.gsheet
├─ project_development_plan.gdoc
├─ project_metrics.gsheet
├─ evidence_log.gsheet
├─ people/<Person>/
│  ├─ individual_development_plan.gdoc
│  └─ individual_metrics.gsheet
├─ status_reports/
├─ action_items.gsheet
├─ source_docs/
└─ archive/
```

Use `_project_registry.gsheet` / `_project_registry.csv` in
`20_M2_Project_Management` to track active project names, aliases, people, and
source locations. For broad cross-project sources, split extracted facts by
project first, update each project folder separately, then archive the aggregate
source/output as evidence.

Archived legacy locations:

- `90_Archive/VSCode_Settings_Backup`: former top-level `.vscode`
- `90_Archive/03_Projects_DC_old_empty_placeholder`: preserved old empty DC placeholder

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
