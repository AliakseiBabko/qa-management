---
name: m2-status-meeting-intake
description: Process a multi-project M2/M3 status-review meeting transcript (a live sync call covering several projects in sequence, e.g. a "traffic light" walkthrough) - split findings per project and route through the normal m2_input/action_items/evidence_log chain. Use when a meeting transcript discusses more than one of M2's own projects, not one project's own strategy chat and not a single person's 1:1.
---

# M2 Status Meeting Intake

## What This Is, And Isn't

- Not `m2-strategy-chat-analysis`: that skill covers one project's own
  running chat export. This is a spoken meeting covering several projects
  in one sitting.
- Not `qa-1to1-analysis`: not person-scoped.
- Not `m2-admin-note-intake`: this is a full transcript, not a short
  pasted snippet.

## Required Start

1. Read `../qa-management-roles/references/aliases.md` before treating an
   unfamiliar project/person name from the transcript as new.
2. Read `../qa-management-roles/references/m2-role-rules.md`'s
   Project-Level Rollups and Cascading Updates sections - the routing
   rules below apply directly.

## Workflow

1. Read the transcript in full. Segment by project as the meeting itself
   usually does (one speaker/block per project).
2. For each of M2's own projects mentioned: extract dated facts, open
   risks, and concrete next steps.
3. Route each project's facts via `pipeline_common.add_questions()` into
   that project's `m2_input` (new round if the last one is answered,
   addendum if still pending) - never write straight to `project_risk`/
   `project_development_plan` from a meeting transcript; the same
   preliminary-analysis gate applies as for any other source.
4. Log concrete, datable next steps into that project's `action_items`;
   run `refresh_timeline_registry.py` after.
5. Log one `evidence_log` row per affected project, `source_type =
   meeting_transcript` (see `google-workspace-rules.md`'s canonical
   `source_type` list).
6. Skip projects mentioned that belong to a different M2 - name-recognition
   only, per `aliases.md`.

## Guardrails

- Do not synthesize a `project_risk`/`project_development_plan` rollup
  directly from the transcript - the `m2_input` gate applies the same as
  any other source.
- A reliability caveat about an information source (e.g. "X is not fully
  reliable right now") is itself a fact worth logging in the affected
  project's `m2_input`, not something to resolve or judge on the spot.
- Don't force every project discussed into the same depth of treatment -
  a project that only got a passing mention because the meeting ran out
  of time is itself worth one line in `m2_input` ("discussion didn't
  happen, needs a real independent check"), not a fabricated full update.
