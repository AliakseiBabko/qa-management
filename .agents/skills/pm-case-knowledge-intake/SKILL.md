---
name: pm-case-knowledge-intake
description: Cross-check-triggered intake for the PM Case Library (40_PM_Case_Library) - logs a real management-pattern case (client/team/stakeholder situation, what was tried, what happened, the takeaway) surfaced while processing a 1:1, project/status meeting, or Project Knowledge source for its own real purpose. Use when a source already being processed by qa-1to1-analysis, m2-strategy-chat-analysis, m2-status-meeting-intake, or project-knowledge-intake contains a genuine, generalizable case that doesn't belong in that document's own scope, or when the user directly asks to log a case.
---

# PM Case Library Intake

Processes one management case end to end - either as a secondary output
of another skill's own pass (the common case) or a standalone pass when
the user directly describes a case to log. Load
`../pm-case-knowledge-roles/SKILL.md` first - it holds the shared
judgment (what counts as a case, the M1/M2/PK boundary, structural
format).

## When This Fires

This is not a source-classification-triggered intake like
`project-knowledge-intake` - it has no `source_type` of its own. Instead,
another skill's own pass surfaces a candidate case while doing its real
job, and hands off here as a secondary step:

- `qa-1to1-analysis` (1:1 transcripts) - a situation with a client,
  stakeholder, or team-management pattern that doesn't fit the 1:1's own
  M1/M2 output.
- `m2-strategy-chat-analysis` (project strategy chats) - a resolved or
  ongoing situation worth generalizing beyond this one project.
- `m2-status-meeting-intake` (multi-project status meetings) - a pattern
  from a project the user doesn't even manage, surfaced in passing.
- `project-knowledge-intake` (PK sources) - a management/behavior fact
  that PK's own guardrail already says doesn't belong in
  `pk_knowledge_base` (that guardrail says "flag and route through the
  normal M1/M2 chain" - a generalizable case routes here instead, when it
  isn't really an M1/M2 current-state fact either).

A single source can produce zero, one, or (rarely) more than one case -
most sources produce zero; do not force it.

## Workflow

1. **Confirm it's a real case.** Situation, approach, outcome (or
   explicitly ongoing/unresolved), and a takeaway - per
   `pm-case-knowledge-roles/SKILL.md`'s core rule. If the candidate is too
   vague or is really a judgment about one named person's competence, do
   not log it here - say so and skip (or flag it toward the M1 lane if
   that's genuinely where it belongs).
2. **Resolve the library.** `pm_case_workspace_layout.find_root`/
   `find_document` for `pm_case_index`/`pm_case_library`. If neither
   exists yet, this is the first real case ever logged - create the
   `40_PM_Case_Library` root folder and both documents now (Sheet header
   from `Templates/pm_case_index.csv`, Doc structure from
   `Templates/pm_case_library.md`), never before a real case exists to
   justify it.
3. **Check for a near-duplicate first.** Read the current
   `pm_case_library`; if this is genuinely a follow-up or second data
   point on an already-logged case, extend that entry in place rather
   than creating a second one for the same underlying situation.
4. **Pick a theme.** Use an existing H3 theme if the case fits it.
   Otherwise file it under "Recent / Unsorted Cases" - unless this would
   be the 3rd case clustering around the same not-yet-named pattern, in
   which case create the new theme now and move all matching cases (the
   existing ones plus this new one) into it together.
5. **Insert the case** as one paragraph at the end of the target section,
   in the shape the template documents (`[Project, Date]` tag, then
   Situation / Approach / Outcome / Takeaway prose) - never at a heading's
   own start index (see `pm-case-knowledge-roles/SKILL.md`, "Structural
   Format").
6. **Append one `pm_case_index` row.**
7. **Add one Change Log one-liner** - what was added, which theme, not
   the case content itself.
8. **Log `_skill_invocations`** in the same pass as the originating
   skill's own logging - `skills` lists both the originating skill(s) and
   `pm-case-knowledge-intake`; `source_type` stays whatever the real
   source's type was (`qa_1to1`, `strategy_chat`, `m2_conversation`,
   `project_knowledge_*`); `Documents touched` adds `pm_case_library` and
   (if a row was appended) `pm_case_index`. Do not create a separate
   invocation row just for the case - it is one pass, logged once.

## Guardrails

- Never create the root folder or either document speculatively - only
  when a real case is being logged for the first time.
- Never treat "this source mentions a client or a difficult situation" as
  automatically case-worthy - apply the real-shape test in step 1 every
  time.
- Never let this skill edit `project_risk`/`m2_input`/`evidence_log`/
  `individual_risk` - those stay owned by their real intake skills; this
  one only ever writes `pm_case_library`/`pm_case_index`.
