---
name: m2-1to1-apply
description: Apply a QA 1:1 transcript's people/project signals (already extracted via qa-1to1-analysis) through the M2 cascading-update chain - individual_metrics, individual_development_plan, project_risk/project_development_plan, m2_input, evidence_log. Use after analyzing an M2 1:1 transcript (00_Source_Docs\01_Meeting_Transcripts) when the findings should actually update live project documents, not just produce a summary.
---

# M2 1to1 Apply

`qa-1to1-analysis` explicitly does not own writing to final documents ("does
not own final report-file creation... use an M1 or M2 writer skill for
that"). For M2, this is that skill — the routing step between "here's what
the transcript says" and "here's what changed in the project's canonical
documents." It mirrors `m2-strategy-chat-analysis`'s workflow, just for a
1:1 transcript instead of a strategy chat.

## Required Start

1. Run `qa-1to1-analysis` first — topic classification, strongest facts,
   people/project signal separation. Don't skip straight to routing.
2. Read `../qa-management-roles/references/m2-role-rules.md`'s Cascading
   Updates and Project-Level Rollups sections.
3. Run `.agents\scripts\show_project_state.py --project <Project>` to see
   current state before editing anything — a transcript often corroborates
   or resolves something already recorded, not just adds new content.

## Workflow

1. Update the person's `individual_metrics`/`individual_development_plan`
   directly with whatever the transcript factually supports (Cascading
   Updates step 1) — no gate needed for direct, evidence-backed person-level
   facts.
2. If the transcript's content would change a `project_risk`/
   `project_development_plan` conclusion, route it through `m2_input` using
   `pipeline_common.add_questions()` — it auto-opens a new round or extends
   the current pending one, whichever the doc's state calls for. Don't edit
   `project_risk`/`project_development_plan`'s judgment conclusions directly
   from a single 1:1 the way you would a person's own metrics.
3. If the transcript resolves a question already sitting in a pending
   `m2_input` round (this happens — a 1:1 is a common way a previously-open
   question actually gets answered), write the resolution with
   `pipeline_common.add_answer()` rather than leaving the round stale. Only
   do this when the transcript genuinely settles the question, not when
   it's merely related.
4. Log `evidence_log`: `source_type` = `1to1_transcript`, `routed_to`
   listing every document actually touched (person-level and project-level
   both, when both changed).

## Guardrails

- Apply the same registry-scoping and Person Card cross-reference
  guardrails as `m2-strategy-chat-analysis` (don't duplicate them here) —
  a 1:1 can just as easily surface a role/track/level mismatch (see
  `m2-role-rules.md`, Вклад в проект Calibration) as a strategy chat can.
- Don't fabricate an "M2 answer" in `m2_input` — only write into the answer
  section when the transcript's content actually resolves the round's
  questions, not to force a round closed.
- A 1:1 is evidence about the person and, incidentally, the project they're
  on — not project-wide evidence by default. Don't let one person's account
  of a project-wide event (e.g. "the client ignored us") stand in for
  independent confirmation if the same fact should really come from a
  strategy chat or a direct account-level source; note whose account it is
  when the confidence matters (see `m2-role-rules.md`, Risk Rules — naming
  the feedback path).
