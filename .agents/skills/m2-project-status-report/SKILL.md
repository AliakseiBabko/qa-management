---
name: m2-project-status-report
description: Create a short chat-ready M2 project status report for a requested period - posted into the project's own strategy chat (the most common real destination), saved as a Google Doc under status_reports, or returned on-demand in conversation. Use when the user asks for current status, last-week status, project status update, or a text ready to copy into a chat based on available QA/project evidence.
---

# M2 Project Status Report

Use this skill for one output family only:

- short project status report text, matched to how real weekly reports on
  these projects actually get delivered (see Destination below) - not a
  long analytical document

This skill and `m2-strategy-chat-analysis` are two directions of the same
loop: a status written here often gets posted into the project's own
`_strategy` chat, and a later batch of that same chat is exactly what
`m2-strategy-chat-analysis` reads back in. Writing a clear, evidence-backed
status now is also writing next month's raw material for that skill.

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, `../qa-management-roles/references/google-workspace/search-source-extraction.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-role-basics.md`
   (business-value framing) and
   `../qa-management-roles/references/m2-role/m2-communication-visibility.md`.
4. Read `../qa-management-roles/references/presale-upsell-rules.md` when the project has any expansion/upsell signal to report (see Content Rules, Расширение / Upsell).
5. Identify project, audience, report type, and period:
   - regular report
   - on-demand report
   - requested project, or all projects if explicitly requested
   - absolute start/end dates for relative periods such as "last week"
6. If the project is not specified and cannot be inferred from context, ask for the project unless the user clearly wants a multi-project status.
7. Run `.agents\scripts\show_project_state.py --project <Project> --summary` (or a full dump if you need more) to see current People count — a project with more than one QA needs the per-person/per-stream breakdown (see Chat Text Shape); a single-QA project doesn't.
8. Review available evidence for the requested period first, then use older artifacts only for context.

## Source Order

1. Existing status reports for the same project.
2. Project development plans and plan-progress notes.
3. Project QA metrics and individual QA metrics that affect the project picture.
4. Project risk summaries.
5. Workbook status rows, strategy-chat notes, 1to1 analysis findings, transcripts, or source extracts.
6. Pending sources under `00_Inbox`, durable references under `90_Storage/Reference`, and extracted copies under `90_Storage/_System/extracts/source`.

For DOCX/XLSX sources, prefer existing extracted files under `G:\My Drive\QA_Management\90_Storage\_System\extracts\source\YYYY-MM-DD\<Project>\...`. If no suitable extract exists, use `.agents/scripts/qa_source_extract.py`.

## Workflow

1. Build a short evidence-backed status for the requested period.
2. Decide the shape: flat (single QA) or per-person/per-stream (more than
   one) — see Chat Text Shape. Don't force a breakdown that the evidence
   doesn't support (e.g. one QA doing two unrelated task types isn't two
   streams).
3. Focus on what changed, what matters now, and what happens next.
4. Include metrics or risk levels only when they add useful management signal.
5. Separate current facts from plans, risks, and missing evidence.
6. Keep the report concise enough to paste into a chat without editing.
7. Decide the destination (see Destination) and deliver there.

## Destination

Real weekly reports on these projects are posted directly into the
project's own strategy chat — that's the default for a regular report,
not a saved Doc. Ask if genuinely unclear, but default to:

- **Regular weekly/status update** → chat-ready text for the project's
  strategy chat (paste-ready, per Chat Text Shape). Only also save it as a
  Doc under `status_reports` if the user asks for a kept copy, or if the
  project has no active strategy-chat channel to post into.
- **On-demand / ad hoc status** ("what's the status right now") → returned
  in conversation, per the existing default. Save only if asked.
- **Explicitly requested as a saved/archival report** → Google Doc under
  `status_reports`, per `document-contract.md`'s naming/versioning rules.

## Chat Text Shape

Default structure (single QA / flat project):

```text
<Project> status, <period>

Done / changed:
- ...

Risks / blockers:
- ...

Next steps:
- ...
```

Per-person/per-stream structure (more than one QA on the project — see
`show_project_state.py --summary`'s People count): lead with a short
project-wide line if there's genuine cross-cutting news, then one block per
person/stream, then a shared closing section for anything that doesn't
belong to one person (contract, staffing, cross-project comms):

```text
<Project> status, <period>

<Person/stream 1>:
- done/changed, risks, next step - whatever's evidence-backed for them

<Person/stream 2>:
- ...

Прочее (contract/staffing/cross-cutting):
- ...
```

Optional sections when evidence supports them, in either shape:

- Metrics / quality
- Feedback / communication
- Help needed
- Расширение / Upsell — only when a real diagnostic signal or an actual
  conversation exists (see `presale-upsell-rules.md`); omit rather than
  padding with generic upsell language on a project with no such signal.

**Monthly narrative variant** — use instead of the bulleted shapes above
when the period is a full calendar month, or the user explicitly asks for
a monthly overview/narrative/paragraph form. Two short paragraphs, not a
bulleted digest:

```text
<Project>, обзор за <месяц год>

<Paragraph 1 — what happened: progress, delivered work, quality/metrics
signal, notable events during the month.>

<Paragraph 2 — forward-looking: plans, staffing questions, risks/
concerns, next steps.>
```

- Same evidence discipline as the bulleted shapes — no invented content,
  same "Data note" fallback for a weak period (see document-contract.md,
  Missing Evidence).
- Same M2 Focus content categories apply (staffing, risk/blocker
  movement, plan progress, client communication) — they just get woven
  into prose instead of separate bulleted sections.
- For a multi-person project, name the people/streams naturally within
  the prose rather than switching to per-person blocks — the paragraph
  form is what the user asked for; don't silently revert to the bulleted
  per-stream shape just because there's more than one person to cover.
- A third short paragraph is acceptable if the month genuinely has that
  much material (e.g. several people, a real staffing change, and a
  material risk shift all in the same month) — but that is the ceiling;
  don't let it grow into the long analytical report this skill explicitly
  avoids.

## Guardrails

- Do not invent progress, blockers, feedback, dates, metrics, or ownership.
- Do not write a long analytical report; this skill produces a short status update.
- Do not expose sensitive internal details unless needed for the management action.
- Do not duplicate full risk, metrics, or development-plan reports. Summarize only what is useful for status.
- If available evidence for the requested period is weak, say that directly and state which sources were missing.
- Do not default to a saved Doc for a regular report without checking whether the project has an active strategy chat to post into instead — that's the more common real destination.
- Do not include a Расширение / Upsell section built from generic service-menu language with no project-specific evidence — see `presale-upsell-rules.md`, Rule.
