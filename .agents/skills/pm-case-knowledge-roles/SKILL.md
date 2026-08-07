---
name: pm-case-knowledge-roles
description: Shared rules for the PM Case Library (40_PM_Case_Library) - a cross-project, personal-reference collection of real management situations (client/team/stakeholder behavior, what was tried, what happened, the takeaway), organized by pattern rather than by project. Distinct from Project Knowledge (per-project technical/business understanding) and from M1/M2 (current-state tracking for actively-managed people/projects). Use when deciding whether a fact belongs in the case library, or updating pm_case_library/pm_case_index.
---

# PM Case Library Roles

Use this skill as shared context before touching the PM Case Library. It
does not own a final document format - `pm-case-knowledge-intake` and the
templates (`Templates/pm_case_library.md`, `Templates/pm_case_index.csv`)
own that.

## What This Is, And Isn't

This is a **personal, cross-project reference of reusable management
patterns** - not a record of any single project's current state, and not
a judgment archive about any single person. A "case" is a concrete,
already-happened-enough-to-be-useful situation: what the situation was,
what was tried (by us or the client/stakeholder side), what resulted, and
the takeaway - phrased so it's useful to someone who wasn't there and
doesn't know the project. Cases can come from any project - the user's
own actively-managed ones, or another M2's project surfaced in a status
meeting or general conversation - as long as the pattern itself is real
and generalizable, not private judgment about one named colleague.

## Required Start

1. Resolve the root folder and both documents via
   `pm_case_workspace_layout.py` (`find_root`/`find_document`) - never
   create the folder or either document speculatively; the first real
   case being logged is what creates them.
2. Read the current `pm_case_library` (if it exists) before adding a new
   case - a near-duplicate of an already-logged situation should extend
   that entry (a follow-up outcome, a second data point) rather than
   creating a second, competing entry for the same underlying case.

## Core Rules

- **A case needs real shape: situation, approach, outcome, takeaway.** A
  vague remark ("client was difficult") isn't case-worthy on its own - it
  needs enough concrete detail that someone else could recognize a similar
  situation and use the takeaway. An outcome that's still unresolved is
  fine to log (mark it as ongoing/unresolved explicitly), but the
  situation and approach still need to be concrete.
- **Boundary vs M1 (people-management):** never log a case whose only real
  content is a judgment about one named person's competence, reliability,
  or performance - that belongs in `individual_risk`/`individual_metrics`,
  M1's own current-state record for that person. A case CAN involve named
  people acting in a situation, but the reusable content this library
  captures is the *situation pattern* (how a type of stakeholder/client
  behavior played out, what approach worked or didn't), not a verdict on
  any individual's ability.
- **Boundary vs M2 (project_risk/m2_input/evidence_log):** those remain
  the authoritative current-state record for one specific actively-managed
  project - logging a case here is never a substitute for maintaining
  them, and this skill never edits them. A case is a distilled,
  retrospective, reusable lesson pulled from the same source, filed
  separately once the situation has enough shape to be useful
  pattern-matching material later.
- **Boundary vs Project Knowledge (`30_Project_Knowledge`):** PK is
  per-project technical/business understanding (architecture, workflows,
  QA scope) - this is cross-project management/behavior pattern
  understanding. The same source (a meeting, a 1:1) can legitimately
  produce both a PK entry and a PM case; they answer different questions
  and neither substitutes for the other.
- **Cases are optional, occasional output - never forced.** Most sources
  processed for their real purpose (a 1:1, a status meeting, a PK source)
  will not contain a case worth logging. Do not manufacture one to have
  something to write; a pass that finds no case is a normal, silent
  outcome, not a gap.
- **Never invent an outcome or takeaway.** If the situation is real but
  still unfolding, log it as ongoing/unresolved rather than guessing how
  it ends or forcing a lesson that hasn't actually been learned yet.

## Structural Format

Same underlying rules as the Project Knowledge lane's knowledge bases
(`project-knowledge-roles/SKILL.md`, "Structural Format") - see there for
the full incident/rationale; the short version applies here too:

- Organize `pm_case_library` by **theme/pattern**, not by project - a
  reader should find "cases like this one" without knowing which project
  it came from. New cases land under "Recent / Unsorted Cases" until 3+
  similar ones would cluster into a real theme.
- Insert a new case at the **end** of its target section (theme, or
  Unsorted), never at a heading's own start index - avoids the Docs API
  heading-inheritance bug (`api-sharing-editing.md`, "Docs API Editing").
- Change Log entries are dated one-liners only - what was added and to
  which theme, never the case content itself.

## Guardrails

- Do not create the `40_PM_Case_Library` root folder or either document
  as a placeholder "in case something comes up later" - only on the first
  real case actually being logged.
- Do not silently expand this lane's scope into a people-management
  judgment archive - see the M1 boundary rule above.
- Do not let this become a duplicate of `evidence_log`/`m2_input` for an
  actively-managed project - those stay the ground truth for current
  state; this captures the retrospective, reusable pattern only.
