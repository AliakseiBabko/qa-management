---
name: qa-department-standards-intake
description: Cross-check-triggered and direct-entry intake for QA Department Standards (50_QA_Department_Standards) - logs a real department-level QA tool/process/direction requirement to qa_department_standards, or a personal management lesson to m2_lessons_learned. Use when a source already being processed by m2-status-meeting-intake or m2-strategy-chat-analysis surfaces a genuine department-wide standards change, when M2 directly states a department requirement/tool decision (e.g. from an M3/department-head communication), or when the user wants to log a lesson learned about their own management activity.
---

# QA Department Standards Intake

Processes one of two things end to end - a department standards update,
or a personal lessons-learned entry. Either as a secondary output of
another skill's own pass, or a standalone pass when the user directly
states a requirement or a lesson to log. Load
`../qa-department-standards-roles/SKILL.md` first - it holds the shared
judgment (what counts as a real entry, the boundary vs Project
Knowledge/PM Case Library/M1/M2, structural format).

## When This Fires

Two distinct triggers, writing to two different documents:

**`qa_department_standards`** (department requirement/tool/direction):
- Direct M3/department-head communication relayed to M2 (a chat message,
  a meeting note stating "we now require X" or "the department is
  standardizing on Y tool").
- `m2-status-meeting-intake` (multi-project status/traffic-light
  meetings) - a department-wide expectation mentioned alongside
  individual project status.
- `m2-strategy-chat-analysis` (project strategy chats) - a department
  requirement surfacing in a project-specific conversation.
- Direct manual statement - the user just tells Claude the current
  requirement/tool/direction (including a short pasted chat/note snippet
  that isn't project-topology or person-card content, so out of scope for
  `m2-admin-note-intake`), no upstream transcript required.

**`m2_lessons_learned`** (personal retrospective):
- The user directly asks to log a lesson about their own management
  activity - no source-classification trigger; this is always a direct,
  on-request pass.
- Occasionally surfaces while processing a 1:1/status meeting/strategy
  chat for its own real purpose, the same secondary-output pattern as
  `pm-case-knowledge-intake`, when the situation is specifically about
  what the user (M2) would do differently.

A single source can produce zero, one, or (rarely) both outputs - most
sources produce zero; do not force it.

## Workflow

1. **Confirm it's real.** For a standards entry: a settled requirement or
   decision, not a proposal still under discussion (if it's still open,
   say so explicitly rather than logging it as current). For a
   lessons-learned entry: a concrete takeaway per
   `qa-department-standards-roles/SKILL.md`'s core rule, not a vague
   complaint, and not really a judgment about another named person.
2. **Resolve the documents.** `qa_dept_standards_workspace_layout.find_root`/
   `find_document` for `qa_department_standards`/`m2_lessons_learned`. If
   neither exists yet, this is the first real entry ever logged - create
   the `50_QA_Department_Standards` root folder and whichever document(s)
   are needed now (Doc structure from `Templates/qa_department_standards.md`
   or `Templates/m2_lessons_learned.md`), never before a real entry exists
   to justify it.
3. **For `qa_department_standards`:** check the current document first -
   if this updates an existing tool/requirement, rewrite that entry in
   place rather than adding a competing one; add a Change Log one-liner
   either way. If it's genuinely new, add it at the end of the matching
   topic section (Tools / Process Requirements / Current Department
   Direction).
4. **For `m2_lessons_learned`:** append the new entry at the end,
   chronological, never rewriting an earlier entry - if it supersedes an
   earlier lesson, say so in the new entry's text instead.
5. **Log `_skill_invocations`** in the same pass as the originating
   skill's own logging when this fired as a secondary output (`skills`
   lists both the originating skill(s) and
   `qa-department-standards-intake`; `source_type` stays whatever the
   real source's type was). For a standalone direct-entry pass, log it on
   its own with `source_type: m2_conversation`. `Documents touched` adds
   `qa_department_standards` and/or `m2_lessons_learned`, whichever was
   actually written.

## Guardrails

- Never create the root folder or either document speculatively - only
  when a real entry is being logged for the first time.
- Never treat "this source mentions a tool or a process" as automatically
  standards-worthy - apply the real-requirement test in step 1 every
  time; a proposal or one manager's personal preference is not yet a
  department standard.
- Never let a `qa_department_standards` entry apply only to one project -
  redirect that to the project's own Project Knowledge lane instead (see
  `qa-department-standards-roles/SKILL.md`'s boundary rules).
- Never let this skill edit `project_risk`/`m2_input`/`evidence_log`/
  `individual_risk`/`pm_case_library` - those stay owned by their real
  intake skills; this one only ever writes `qa_department_standards`/
  `m2_lessons_learned`.
