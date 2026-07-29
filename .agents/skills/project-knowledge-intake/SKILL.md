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
4. Read `../qa-management-roles/references/google-workspace/operational-registries.md`
   (the `_skill_invocations` conventions step 6 writes into) and
   `../qa-management-roles/references/google-workspace/api-sharing-editing.md`
   (this skill writes Docs/Sheets directly).

## Live/Interactive Investigation Sources

A Project Knowledge source does not have to be a file already dropped in
`00_Inbox`. A live admin console, repository browser, API call log,
notebook-style source collection, generated endpoint documentation, or
browser-opened document can all be valid sources. Classify by shape: a
live system/log/repo investigation is usually `project_knowledge_notes`;
a spec, PDF, exported doc, or written artifact reached through that
investigation is usually `project_knowledge_document`. Apply the same
full discipline either way: summary where appropriate, `pk_source_index`
row, `pk_knowledge_base` update or explicit `no_change`, Change Log, and
`_skill_invocations`.

Repeated live-investigation patterns:

- A live operational log beats a static doc for "what is actually used"
  questions. When a system exposes its own call/audit log, prioritize
  checking it before inferring from specs, generated docs, or source code.
- Notebook-style AI-curated source collections can duplicate material
  already reviewed elsewhere. Check their source list before treating the
  collection as new content, and prefer the collection's source summaries
  or guide panels when those are the fastest reliable path to the facts.
- A source dropped as a local path under the user's Google Drive mirror
  (`G:\My Drive\QA_Management\...`) ending in `.gdoc`/`.gsheet`/`.gslides`
  is **not** a real file - Drive for Desktop keeps no readable bytes for
  Google-native types locally, so `Read`/`cat`/`Get-Content` on it fails
  with an I/O error even though it looks like a normal small file. This is
  not a live/interactive-investigation source needing browser automation -
  resolve it straight to the real Drive file via
  `python resolve_drive_path.py "<local path>"` (see
  `../qa-management-roles/references/google-workspace/api-sharing-editing.md`,
  "Resolving A Local Drive-Mirror Path") and then read/export it through the
  Docs/Sheets API directly. Reach for a live browser only when the source
  genuinely has no corresponding local mirror path (a bare Drive URL the
  user pasted with nothing synced locally) or the API path itself fails.
- Browser-opened document editors can resist DOM scraping because content
  lazy-loads or renders per page. If automation is not quickly exposing
  the text, don't burn repeated tool calls fighting the renderer:
  - For an online spreadsheet, try driving the editor's own **File >
    Export > Download as** (CSV/TXT) yourself first, then inspect the
    downloaded file directly - this reliably beats scraping a
    virtualized/canvas-rendered grid, and needs no back-and-forth with
    the user.
  - For an online word processor (or anything the export route doesn't
    solve), ask the user to paste the raw text instead.

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
   - **Run a core-section extraction check before writing or keeping
     "unknown".** Re-read the source and any linked sidecar evidence
     section-by-section for Business Goals, System/Architecture, Core
     Workflows, Data/Integrations, and QA Scope. A product walkthrough,
     screen sequence, worked example, owner explanation, or automation
     screenshot can answer one of these sections even when the source never
     uses that section's exact heading. Do not leave "not described by
     sources" / "unknown" / vague filler in these sections until this
     targeted check has been done. If evidence is still absent, keep the
     gap as a specific Open Question rather than a broad placeholder.
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
   check itself. If one of these three doesn't exist yet for the project,
   creating it here is still subject to the same rule as any other
   creation of it (see `project-knowledge-roles/SKILL.md`, "Never create
   one of these three as a placeholder") - do not scaffold it with generic
   section headings just because this pass happened to touch the topic;
   only create it when there's real, project-specific content to write.
6. **Log `_skill_invocations`** via `pipeline_common.log_skill_invocation()`
   with `source_type` set to the source's actual type and `Documents
   touched` listing everything actually written this pass.
   Before moving to the next source, check whether the user corrected a
   routing, wording, or judgment call in this pass. If so, log a
   separate `feedback:`-prefixed row in the same pass, following
   `operational-registries.md`'s convention. Do not leave that correction
   only in conversation history or as a later mental note; `qa-retro`
   cannot see it unless it is logged.

## Guardrails

- No presentations, no Google Slides - `pk_presentation_brief`-equivalent
  output does not exist in this skill; a later phase owns that.
- Do not route a management fact (people-risk, project-risk, staffing)
  found inside a Project Knowledge source into `pk_knowledge_base` -
  flag it and route separately through the normal M1/M2 chain instead.
- Do not skip logging `pk_source_index` for a source that turned out to
  add nothing new - a `no_change` outcome is still a recorded outcome.
