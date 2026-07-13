# QA Management - Workspace Agent Policy

This file is the workspace-level policy for AI agents working in this repository.

## Purpose

This repository stores QA-management agent infrastructure for both:

- `M1` people-management workflows
- `M2` project-management workflows

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
| `qa-management-roles` | Common | Shared M1/M2/M3/M4 role boundaries and role rules, including M1 people-management goals and M2 project-management/business-value rules | `.agents/skills/qa-management-roles/SKILL.md` |
| `m1-people-1to1-file` | M1 | Individual person Google Sheet in `10_M1_People_Management`, with CSV fallback, based on `Templates/1to1.csv` from this repo | `.agents/skills/m1-people-1to1-file/SKILL.md` |
| `m1-people-risk-report` | M1 | Dated people risk traffic-light Google Sheet, with CSV fallback, based on `Templates/светофор_рисков.csv` from this repo | `.agents/skills/m1-people-risk-report/SKILL.md` |
| `m2-people-1to1-file` | M2 | Individual person Google Sheet in `20_M2_Project_Management`, with CSV fallback, based on `Templates/1to1.csv` from this repo | `.agents/skills/m2-people-1to1-file/SKILL.md` |
| `m2-project-risk-report` | M2 | Project risk traffic-light Google Sheet, with CSV fallback | `.agents/skills/m2-project-risk-report/SKILL.md` |
| `m2-project-qa-metrics-report` | M2 | Project-level QA metrics Google Sheet, with CSV fallback | `.agents/skills/m2-project-qa-metrics-report/SKILL.md` |
| `m2-individual-qa-metrics-report` | M2 | Individual QA metrics Google Sheet within project scope, with CSV fallback | `.agents/skills/m2-individual-qa-metrics-report/SKILL.md` |
| `m2-project-development-plan` | M2 | Project-level development-plan Google Sheet, with CSV fallback | `.agents/skills/m2-project-development-plan/SKILL.md` |
| `m2-individual-development-plan` | M2 | Individual development-plan Google Sheet within project scope, with CSV fallback | `.agents/skills/m2-individual-development-plan/SKILL.md` |
| `m2-project-status-report` | M2 | Short chat-ready project status report for a requested period; regular saved reports use Google Docs with Markdown fallback | `.agents/skills/m2-project-status-report/SKILL.md` |
| `m1-monthly-report` | M1 | Monthly M1 KPI/bonus Google Sheet, with CSV fallback, based on monthly report workbook structure and evidence-backed people-management data | `.agents/skills/m1-monthly-report/SKILL.md` |
| `m2-monthly-report` | M2 | Monthly M2 KPI/bonus Google Sheet, with CSV fallback, based on monthly report example structure and evidence-backed project-management data | `.agents/skills/m2-monthly-report/SKILL.md` |

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
- `10_M1_People_Management`: M1 person files and people risk snapshots
- `20_M2_Project_Management`: M2 project-management outputs
- `80_Exports`: exported packages, shares, or generated external copies
- `90_Archive`: archived legacy folders and backups

M2 project-management outputs are project-based. Each active project should have
its own folder under `20_M2_Project_Management`, for example:

```text
20_M2_Project_Management/<Project>/
├─ project_risk.gsheet
├─ project_development_plan.gsheet
├─ project_metrics.gsheet
├─ evidence_log.gsheet
├─ people/<Person>/
│  ├─ individual_development_plan.gsheet
│  └─ individual_metrics.gsheet
├─ status_reports/
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
