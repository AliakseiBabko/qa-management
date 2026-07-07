---
name: m2-project-development-plan
description: Create or update a project development-plan report as a Google Doc, with Markdown fallback, for M2 project management. Use when preparing a development-plan document for one project or for the QA engineers working on that project set.
---

# M2 Project Development Plan

Use this skill for one output family only:

- project-level development-plan Google Doc, with Markdown fallback

This is a narrative document, not a tabular record: it reads as an essay with
headed sections, not one row per initiative. Do not flatten it into a Sheet.

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Read `../qa-management-roles/references/m2-role-rules.md`.
4. Identify the target project, period, review cycle, and next review date if present.
5. Read the existing project development plan first, then project metrics, risk summaries, and workbook status rows.

## Workflow

1. Start from business/project context: how the project creates value, what the client/business needs, and what success means.
2. Write the plan as prose organized under headings (see `references/document-contract.md` for the section skeleton), not as rows in a table.
3. Cover, in order: business focus and value the project/QA brings, current state (by stream/initiative where relevant), the plan itself broken into review horizons (e.g. 30/60/90 days, or phased months), open decisions, risks, and evidence/sources.
4. Each plan item should carry its owner and success criterion inline in the sentence or bullet, not as separate table columns.
5. Cover project movement, business/client value, QA/process value, staffing/continuity, communication, and role/value growth where evidence supports it.
6. Use evidence from the source corpus; keep uncertainty explicit.
7. Update the living Doc in place — replace section content rather than appending a new dated copy. Google Docs version history already preserves prior revisions.

## Guardrails

- Do not mix this output with metrics output.
- Do not mix this output with project-risk output.
- Do not turn an individual employee development issue into a project initiative unless it materially affects project delivery or QA process.
- Do not treat a QA task list, automation plan, or completed-work report as a project development plan unless it is mapped to project/business goals and success criteria.
- Do not restate the same summary/context paragraph once per initiative; state it once, then let initiatives reference it.
