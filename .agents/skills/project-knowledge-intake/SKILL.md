---
name: project-knowledge-intake
description: Source-triggered intake skill for the Project Knowledge lane - processes a project_knowledge_transcript/document/chat/notes source into a summary (where appropriate), a pk_source_index row, and a pk_knowledge_base update. Use when a discovered source has been classified as one of these four source_types.
---

# Project Knowledge Intake

Processes one Project Knowledge source end to end. Load
`../project-knowledge-roles/SKILL.md` first - it holds the shared
judgment rules this skill applies (gradual accumulation, durable-vs-one-off
distinction, open questions, M1/M2 boundary, QA-docs-are-downstream rule).

## Required Start

1. Read `../project-knowledge-roles/SKILL.md` in full.
2. Confirm the project scope - never infer or guess a project name; if
   unclear, resolve it before proceeding (same discipline as every other
   intake skill).
3. Read the project's current `pk_knowledge_base` (if it exists) so new
   content can be judged against what's already captured.

## Workflow

1. **Summarize, if appropriate.** For `project_knowledge_transcript`/
   `project_knowledge_document`/`project_knowledge_chat`, write a
   `pk_summary` document (`Templates/pk_summary.md` shape) capturing what
   the source actually said - context, key topics, extracted facts,
   decisions/constraints, open questions. `project_knowledge_notes` is
   short enough that it usually skips this step and goes straight into the
   knowledge base - use judgment; a longer note set may still warrant its
   own summary.
2. **Append `pk_source_index`.** One row per processed source, every time
   - including when nothing durable came out of it (a `no_change`-shaped
   row is still a row, same discipline as `evidence_log`).
3. **Update `pk_knowledge_base`.** Fold durable facts into the relevant
   section(s) (Overview, Stakeholders/Roles, System/Architecture, Core
   Workflows, Data/Integrations, QA Scope, Performance-Critical Scenarios,
   Known Constraints, Glossary) and update Open Questions/Source Index/
   Change Log. Record `no_change` explicitly when the source adds nothing
   durable - do not force an update just because a source was processed.
4. **Run the closing quality gate (mandatory) before finishing.** With
   `pk_summary` written and `pk_knowledge_base` updated, do one more pass
   comparing them before moving on:
   - For every section of the `pk_summary` you just wrote, decide: has its
     durable content been promoted into `pk_knowledge_base`, or is it
     deliberately staying summary-only? If the latter, the reason should
     be evident (genuinely one-off, unconfirmed, or source-local detail) -
     not just an oversight.
   - Check specifically for concrete formulas, worked examples,
     configuration/string syntax, and thresholds - these are exactly the
     details a summary-only pass tends to drop. Promote them into the
     knowledge base (or the relevant QA doc) if they're durable, per
     `../project-knowledge-roles/SKILL.md`.
   - Check specifically for performance-test-relevant facts: workload
     formulas, data volumes, latency/timing targets, concurrency
     assumptions, async/batch boundaries, consistency windows,
     startup/restart behavior, scaling/failover assumptions, observability
     signals, and configurable limits. Any of these appearing or changing
     is the signal that decides step 5 below, not source_type alone.
   - **Cross-check new source content against the existing KB Open
     Questions section before closing (mandatory).** Read
     `pk_knowledge_base`'s current Open Questions list for this project and
     compare it against what this source actually said - not just the open
     questions that happen to come to mind while writing the summary. If
     the source resolves or supersedes an open question, that question
     must be corrected in place with the resolved fact, never left
     standing next to the new information as stale uncertainty. If the
     source adds a genuinely new uncertainty, add a specific and
     actionable open question for it - concrete enough to drive a
     follow-up question or a test-design decision, not a vague
     placeholder. Never duplicate a contradictory open question beside the
     one it should have replaced - merge or correct instead of appending a
     second, conflicting version.
5. **Update QA docs when the gate found a reason to.** Update
   `pk_performance_test_plan`, test scope (`pk_test_plan`), or overall test
   approach (`pk_test_strategy`) when step 4's performance-relevant check
   turned up something that actually changes scope/approach - these
   remain the exception, not the default; most passes leave all three
   untouched, but "most passes skip this" is not a reason to skip the
   check itself.
6. **Log `_skill_invocations`** via `pipeline_common.log_skill_invocation()`
   with `source_type` set to the source's actual type and `Documents
   touched` listing everything actually written this pass.

## Guardrails

- No presentations, no Google Slides - `pk_presentation_brief`-equivalent
  output does not exist in this skill; a later phase owns that.
- Do not route a management fact (people-risk, project-risk, staffing)
  found inside a Project Knowledge source into `pk_knowledge_base` -
  flag it and route separately through the normal M1/M2 chain instead.
- Do not skip logging `pk_source_index` for a source that turned out to
  add nothing new - a `no_change` outcome is still a recorded outcome.
