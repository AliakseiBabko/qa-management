---
name: m2-project-status-report
description: Create a short chat-ready M2 project status report for a requested period, including regular weekly/status updates saved as Google Docs when API access is available, and on-demand status summaries. Use when the user asks for current status, last-week status, project status update, or a text ready to copy into a chat based on available QA/project evidence.
---

# M2 Project Status Report

Use this skill for one output family only:

- short project status report text; saved regular reports use Google Docs when API access is available

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Read `../qa-management-roles/references/m2-role-rules.md`.
4. Identify project, audience, report type, and period:
   - regular report
   - on-demand report
   - requested project, or all projects if explicitly requested
   - absolute start/end dates for relative periods such as "last week"
4. If the project is not specified and cannot be inferred from context, ask for the project unless the user clearly wants a multi-project status.
5. Review available evidence for the requested period first, then use older artifacts only for context.

## Source Order

1. Existing status reports for the same project.
2. Project development plans and plan-progress notes.
3. Project QA metrics and individual QA metrics that affect the project picture.
4. Project risk summaries.
5. Workbook status rows, strategy-chat notes, 1to1 analysis findings, transcripts, or source extracts.
6. Source documents under `00_Source_Docs` and extracted copies under `80_Exports/source_extracts`.

For DOCX/XLSX sources, prefer existing extracted files under `G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD\<Project>\...`. If no suitable extract exists, use `.agents/scripts/qa_source_extract.py`.

## Workflow

1. Build a short evidence-backed status for the requested period.
2. Focus on what changed, what matters now, and what happens next.
3. Include metrics or risk levels only when they add useful management signal.
4. Separate current facts from plans, risks, and missing evidence.
5. Keep the report concise enough to paste into a chat without editing.
6. If the report is regular, save it using the contract naming rules.

## Chat Text Shape

Default structure:

```text
<Project> status, <period>

Done / changed:
- ...

Risks / blockers:
- ...

Next steps:
- ...
```

Optional sections when evidence supports them:

- Metrics / quality
- Feedback / communication
- Help needed

## Guardrails

- Do not invent progress, blockers, feedback, dates, metrics, or ownership.
- Do not write a long analytical report; this skill produces a short status update.
- Do not expose sensitive internal details unless needed for the management action.
- Do not duplicate full risk, metrics, or development-plan reports. Summarize only what is useful for status.
- If available evidence for the requested period is weak, say that directly and state which sources were missing.
