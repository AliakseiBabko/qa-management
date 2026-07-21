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
4. **Optionally update QA docs.** Only when the source's knowledge clearly
   affects performance-test scope/approach (`pk_performance_test_plan`),
   test scope (`pk_test_plan`), or overall test approach
   (`pk_test_strategy`) - these are the exception, not the default; most
   passes leave all three untouched.
5. **Log `_skill_invocations`** via `pipeline_common.log_skill_invocation()`
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
