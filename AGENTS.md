# QA Management - Workspace Agent Policy

This file is the workspace-level policy for AI agents working in this repository.

## Purpose

This repository stores QA-management agent infrastructure for both:

- `M1` people-management workflows
- `M2` project-management workflows

Business data and generated outputs live in:

`G:\My Drive\QA_Management`

## Skill Location

Local skills live under:

```text
.agents/skills/
```

Current canonical skills:

| Skill | Role | Outcome | Canonical source |
|-------|------|---------|------------------|
| `qa-1to1-analysis` | Common | Shared structured analysis from a QA 1to1 transcript for both M1 and M2, including topic classification, evidence extraction, and people/project signal separation | `.agents/skills/qa-1to1-analysis/SKILL.md` |
| `qa-management-roles` | Common | Shared M1/M2/M3/M4 role boundaries and role rules, including M1 people-management goals and M2 project-management/business-value rules | `.agents/skills/qa-management-roles/SKILL.md` |
| `m1-people-1to1-file` | M1 | Individual person file in `G:\My Drive\QA_Management\10_M1_People_Management` based on `Templates/1to1.csv` from this repo | `.agents/skills/m1-people-1to1-file/SKILL.md` |
| `m1-people-risk-report` | M1 | Dated people risk traffic-light file in `G:\My Drive\QA_Management\10_M1_People_Management` based on `Templates/светофор_рисков.csv` from this repo | `.agents/skills/m1-people-risk-report/SKILL.md` |
| `m2-people-1to1-file` | M2 | Individual person file in `G:\My Drive\QA_Management\20_M2_Project_Management` based on `Templates/1to1.csv` from this repo | `.agents/skills/m2-people-1to1-file/SKILL.md` |
| `m2-project-risk-report` | M2 | Project risk traffic-light file | `.agents/skills/m2-project-risk-report/SKILL.md` |
| `m2-project-qa-metrics-report` | M2 | Project-level QA metrics file | `.agents/skills/m2-project-qa-metrics-report/SKILL.md` |
| `m2-individual-qa-metrics-report` | M2 | Individual QA metrics file within project scope | `.agents/skills/m2-individual-qa-metrics-report/SKILL.md` |
| `m2-project-development-plan` | M2 | Project-level development-plan file | `.agents/skills/m2-project-development-plan/SKILL.md` |
| `m2-individual-development-plan` | M2 | Individual development-plan file within project scope | `.agents/skills/m2-individual-development-plan/SKILL.md` |
| `m1-monthly-report` | M1 | Monthly M1 KPI/bonus report CSV based on monthly report workbook structure and evidence-backed people-management data | `.agents/skills/m1-monthly-report/SKILL.md` |
| `m2-monthly-report` | M2 | Monthly M2 KPI/bonus report CSV based on monthly report example structure and evidence-backed project-management data | `.agents/skills/m2-monthly-report/SKILL.md` |

Load only the skill needed for the current outcome. Do not preload other role skills.

## Repository Contents

- `.agents/skills`: local skills and skill-local scripts
- `Templates`: canonical CSV templates
- `.agents/skills/qa-1to1-analysis/references`: shared 1to1 topic, risk, and wording rules
- `.agents/skills/qa-management-roles/references`: shared M1/M2 role boundaries and management rules
- `README.md`: repo overview

## Data Root

Use `G:\My Drive\QA_Management` as the data root unless the user points to a different dataset location.

Expected data folders under that root:

- `00_Source_Docs`: durable source documents and reference materials
- `01_Recordings`: raw meeting recordings
- `02_Transcripts_Inbox`: raw transcript intake
- `03_Transcripts_Processed`: transcripts that have already been analyzed or moved out of intake
- `10_M1_People_Management`: M1 person files and people risk snapshots
- `20_M2_Project_Management`: M2 project-management outputs
- `80_Exports`: exported packages, shares, or generated external copies
- `90_Archive`: archived legacy folders and backups

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
- Each report-generation skill should target one expected output document format.

## Multi-Agent Convention

This repository is intended to be usable by Codex, Antigravity, and Claude Code through the same shared skill files under `.agents/skills/`.
Keep runtime differences limited to invocation notes inside the skills.
