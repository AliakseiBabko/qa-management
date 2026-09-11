---
name: m2-project-development-plan
description: Create or update a project development-plan report as a Google Doc, with Markdown fallback, for M2 project management. Use when preparing a development-plan document for one project or for the QA engineers working on that project set.
---

# M2 Project Development Plan

Use this skill for one output family only:

- project-level development-plan Google Doc, with Markdown fallback

This is a narrative document, not a tabular record: it reads as an essay with
headed sections, not one row per initiative. Do not flatten it into a Sheet.

It is also the **end of the pipeline, not a working file**. It is written to
be read by management above M2, by someone with no access to this workspace
and no memory of a previous version. Facts belong upstream — in 1:1 records,
meeting and strategy transcripts, `evidence_log`, `project_metrics`; what
belongs here is the reading of them. See `references/plan-schema.md`,
"Audience And Register" and "Synthesis, Not A Fact Inventory", before
writing a line.

## Required Start

1. Read `references/plan-schema.md` and
   `references/plan-sources-normalization.md`.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-role-basics.md`
   (business-value framing) and
   `../qa-management-roles/references/m2-role/m2-development-plans.md`
   (what a project development plan must answer).
4. Read `../qa-management-roles/references/presale-upsell-rules.md` too
   when filling or changing the Возможности расширения (Upsell) section —
   not needed for the rest of the plan.
5. Identify the target project, period, review cycle, and next review date if present.
6. Read the existing project development plan first, then project metrics, risk summaries, and workbook status rows.

## Workflow

1. Start from business/project context: how the project creates value, what the client/business needs, and what success means.
2. Write the plan as prose organized under headings (see `references/plan-schema.md` for the section skeleton), not as rows in a table.
3. Cover, in order: business focus, client expectations, the value QA brings, expansion/upsell opportunities (see `presale-upsell-rules.md`), success against the client's own criteria, current state (by stream/initiative where relevant), the plan split into date-bound near-term steps and undated directions, metrics, risks, and open questions. There is no sources section.
4. Each plan item should carry its owner and success criterion inline in the sentence or bullet, not as separate table columns.
5. Cover project movement, business/client value, QA/process value, staffing/continuity, communication, and role/value growth where evidence supports it.
6. Use evidence from the source corpus; keep uncertainty explicit — but a
   quiet client is not missing evidence. Where nothing was stated directly,
   infer the read from what the client funds, staffs, escalates, constrains,
   and ignores, mark it `(гипотеза M2)`, and name the signal it rests on.
   Never leave a section reading "нет данных".
7. Update the living Doc in place — replace the content of each section it affects, rather than appending a new dated copy or a trailing "Update YYYY-MM-DD" block. Google Docs version history already preserves prior revisions, so the document itself never narrates its own edits.

## Guardrails

- Do not mix this output with metrics output.
- Do not mix this output with project-risk output.
- Do not turn an individual employee development issue into a project initiative unless it materially affects project delivery or QA process.
- Do not treat a QA task list, automation plan, or completed-work report as a project development plan unless it is mapped to project/business goals and success criteria.
- Do not restate the same summary/context paragraph once per initiative; state it once, then let initiatives reference it.
- Do not point the reader at another internal artifact. No `(см.
  action_items)`, `(см. evidence_log)`, `(см. m2_input)`, `(см.
  individual_metrics ...)`, no `30_Project_Knowledge/...` path, no chat or
  transcript filename, no 1:1 date used as a citation — the reader cannot
  open any of them. State the fact, or leave it out.
- Do not narrate the document's own revision history in its body
  ("исправлено по чату X", "ранее ошибочно записано", "нуждается в
  переподтверждении"). That is maintainer commentary in a document written
  for someone else.
- Do not write a `Источники` section. It is prohibited, not optional.
- Do not leave a section reading "нет данных" because the client never said
  anything. Infer, mark `(гипотеза M2)`, name the signal.
- Do not list facts a reader could have got from a transcript. If a sentence
  would survive being moved into a 1:1 record unchanged, it belongs there.
- Do not fill the Возможности расширения (Upsell) section with generic service-menu language — every item must trace to a real diagnostic signal or conversation (see `presale-upsell-rules.md`, Rule). State "no expansion signal this period" when that's the honest read, rather than omitting the section or padding it.
