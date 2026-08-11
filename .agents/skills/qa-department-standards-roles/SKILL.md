---
name: qa-department-standards-roles
description: Shared rules for QA Department Standards (50_QA_Department_Standards) - a personal reference of current department-wide QA tools, process requirements, and direction, plus a separate personal log of M2's own management lessons learned. Distinct from Project Knowledge (per-project technical/business understanding), the PM Case Library (cross-project management situation patterns), and M1/M2 current-state tracking (per-person/per-project). Use when deciding whether a fact belongs here, or updating qa_department_standards/m2_lessons_learned.
---

# QA Department Standards Roles

Use this skill as shared context before touching either document in
`50_QA_Department_Standards`. It does not own a final document format -
`qa-department-standards-intake` and the templates
(`Templates/qa_department_standards.md`, `Templates/m2_lessons_learned.md`)
own that.

## What This Is, And Isn't

Two separate documents, one lane:

- **`qa_department_standards`** - a current-state, topic-organized
  reference of what the department expects *right now*: required tools,
  process requirements, standing priorities/direction. This is what you
  check your own projects' alignment against. It answers "what should be
  done" at the department level, not "how did this one project do it."
- **`m2_lessons_learned`** - a personal, append-only, retrospective log
  of your own management-activity lessons: what you'd do differently,
  what worked and is worth repeating. About your own practice, not a
  record of department policy.

Neither is a duplicate of an existing lane:

- **Boundary vs Project Knowledge (`30_Project_Knowledge`):** PK is
  per-project technical/business understanding (architecture, workflows,
  one project's own QA scope). `qa_department_standards` is department-wide
  and project-agnostic - a requirement or tool that applies to one project
  only belongs in that project's `pk_test_strategy`/process checklist
  instead, not here.
- **Boundary vs PM Case Library (`40_PM_Case_Library`):** PM cases are
  situation patterns (what happened, what was tried, the outcome) -
  reusable regardless of who was managing. `qa_department_standards` is
  standards/requirements, not situations; `m2_lessons_learned` is
  situations but specifically about *your own* decisions, not a
  generalizable cross-project pattern. A source can legitimately produce
  a PM case and a lessons-learned entry from the same event if both
  angles are genuinely present - they answer different questions.
- **Boundary vs M1/M2 current-state (`individual_risk`/`project_risk`/
  `m2_input`/etc.):** those remain the authoritative current-state record
  for a specific person or project. This lane never substitutes for them
  and never records a verdict about a named person's competence or
  reliability - that stays M1's lane. `m2_lessons_learned` is about your
  own actions, never a judgment of someone else's.
- **Boundary vs `qa-management-roles`:** that skill holds durable role
  definitions (what M1/M2 responsibilities are, in general). This lane
  holds concrete, current, changeable department requirements - the kind
  of fact that gets superseded when department direction shifts, not a
  stable role definition.

## Required Start

1. Resolve the root folder and both documents via
   `qa_dept_standards_workspace_layout.py` (`find_root`/`find_document`) -
   never create the folder or either document speculatively; the first
   real entry being logged is what creates them.
2. Read the current target document before adding to it -
   `qa_department_standards` in particular should never accumulate a
   second, competing entry for the same tool/requirement; update the
   existing entry in place instead (see Structural Format).

## Core Rules

- **A standards entry needs to be a real, current requirement or
  decision** - not a wishlist item, not something only proposed. If it's
  still under discussion, say so explicitly in the entry rather than
  presenting it as settled.
- **A lessons-learned entry needs a real takeaway**, not just a vague
  complaint - what you'd concretely do differently, or what specifically
  worked and why it's worth repeating. Same narrative-shape test as
  `../pm-case-knowledge-roles/SKILL.md`'s core rule, applied to your own
  practice instead of a management situation.
- **Never log a lessons-learned entry that is really a judgment about
  another named person** - if the substance is about someone else's
  competence or reliability, it belongs in M1's `individual_risk`, not
  here. A lesson can *involve* other people acting in a situation, but
  the reusable content is what you would do differently, not a verdict on
  them.
- **`qa_department_standards` entries are optional, occasional output**
  from the sources listed in `qa-department-standards-intake` - most
  sources processed for their real purpose will not surface a genuine
  standards change; do not manufacture one to have something to write.
- **Never invent a requirement or a lesson** - if a signal is ambiguous
  about whether it's an actual department requirement versus one
  manager's personal preference, or whether a situation has actually
  produced a real takeaway yet, say so and skip rather than guessing.

## Structural Format

- `qa_department_standards` is organized by the three topic sections the
  template defines (Tools, Process Requirements, Current Department
  Direction) - current-state, one entry per requirement/tool, updated in
  place when it changes (rewrite the entry), never append-only. This is
  the opposite convention from the PM Case Library and Project
  Knowledge's knowledge bases, which are append/accumulate - see
  `feedback_current_state_table_shape` in user memory for why a
  current-requirement document should read as one clean picture, not a
  log.
- `m2_lessons_learned` is append-only, chronological, newest entry added
  at the end - never rewritten in place. If a later entry supersedes an
  earlier lesson, say so in the new entry.
- Insert a new `qa_department_standards` entry at the **end** of its
  target topic section (or replace an existing entry's text in place),
  never at a heading's own start index - avoids the Docs API
  heading-inheritance bug (`api-sharing-editing.md`, "Docs API Editing").
- Change Log entries (on `qa_department_standards` only) are dated
  one-liners - what changed and in which topic section, never the full
  entry content itself.

## Guardrails

- Do not create the `50_QA_Department_Standards` root folder or either
  document as a placeholder "in case something comes up later" - only on
  the first real entry actually being logged.
- Do not let `qa_department_standards` drift into a per-project
  document - a requirement that only applies to one project belongs in
  that project's own Project Knowledge lane instead.
- Do not let `m2_lessons_learned` become a judgment archive about other
  people - see the M1 boundary rule above.
- Do not let this become a duplicate of `evidence_log`/`m2_input` for an
  actively-managed project - those stay the ground truth for current
  project state; this lane is department-wide standards and personal
  retrospective only.
