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

1. Read `../project-knowledge-roles/SKILL.md` in full, and
   `../qa-management-roles/references/transcript-signal-triage.md` before
   deciding what's worth extracting at all - a known project/person name
   is only the attention cue, not itself a reason to extract.
2. Confirm the project scope - never infer or guess a project name; if
   unclear, resolve it before proceeding (same discipline as every other
   intake skill).
3. Read the project's current `pk_knowledge_base` (if it exists) so new
   content can be judged against what's already captured. Before
   concluding a project has no knowledge base yet, check for a
   same-named doc anywhere under the project's own root folder, not just
   inside its `knowledge_base/` subfolder - this has already happened
   twice for real projects (a `knowledge_base` doc created in the
   project root instead of its subfolder), and a subfolder-scoped search
   alone looks identical to "never created" when the doc is simply
   misfiled. If found outside `knowledge_base/`, move it there rather
   than creating a second doc.
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
  Docs/Sheets API directly. Never fall back to a live browser for a source
  under this Drive mirror, even if `resolve_drive_path.py` or the follow-up
  API call hits a snag - debug that instead. A live browser is reserved for
  a genuinely different case: an external system outside this Drive account,
  gated behind its own separate login (e.g. `<Project>` documents behind
  their own credentials, unreachable by any Drive/Sheets/Docs API call this
  OAuth client has) - a narrow, deliberate exception, not a general fallback
  for local-mirror sources.
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
- Inside a genuinely external Drive location (the narrow browser-fallback
  case above), a **native** multi-tab Google Sheet exports reliably by
  navigating straight to
  `https://docs.google.com/spreadsheets/d/<id>/export?format=csv&gid=<gid>`
  for each tab - get each tab's `gid` by clicking it (see the frame-click
  gotcha below) and reading the resulting `#gid=...` from the page URL,
  then navigate to the export URL and read the downloaded file from the
  browser tool's own download directory (e.g. `.playwright-mcp/`).
- **Gotcha:** an **uploaded, non-native** file (`.xlsx`/`.csv` sitting in
  Drive, not a real Google Sheet) previewed via `/file/d/<id>/view` shows
  a Sheets-style grid, and its context menu offers "Open with Google
  Sheets" - but the resulting converted preview is not a real, exportable
  Sheet: navigating to its `/export?format=csv` (or even the plain
  `/edit`) URL reliably crashes the browser tool's connection entirely
  ("Connection closed"/`ERR_HTTP_RESPONSE_CODE_FAILURE"`), costing a full
  reconnect. For a small-to-medium uploaded file, skip export entirely -
  read the content directly from the preview iframe's rendered text
  (`document.body.innerText` on the frame whose URL contains
  `/preview/sheet`) instead. This is fast, needs no menu navigation, and
  never triggers the crash.
- **Gotcha:** clicking a Google Sheet's own tab bar, or its File > Download
  submenu, from a prior snapshot's element ref frequently fails to match
  ("does not match any elements") even though the element is visibly
  there - these controls live inside nested iframes the ref-based click
  tool doesn't reliably resolve across a snapshot/click round-trip.
  Iterate `page.frames()` and use `frame.getByRole('menuitem'|'button',
  { name, exact: true })` inside one script call instead (find the frame,
  then act, in the same call) - this succeeded consistently where
  ref-based clicks and even the same locator split across two separate
  tool calls did not (Google's custom menus close between calls with no
  continuous hover). For a tab bar specifically, the target tab's `gid`
  is recoverable from the page URL immediately after a successful click.

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
   Insert new content at the end of the target section (or its relevant
   H3 sub-heading if the section already has them) - never at a heading's
   own start index, and never into Change Log as a substitute for
   deciding where content belongs. See
   `../project-knowledge-roles/SKILL.md`, "Structural Format" for the
   Change Log one-liner rule and the sub-heading threshold.
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
   touched` listing everything actually written this pass. If the source
   was a real file under `00_Inbox` processed by hand (direct Docs/Sheets
   API calls, not the `qa_manage.py` queue/scan pipeline), archive it to
   `90_Storage/Processed_Sources/<year>/<month>/<run-id-style-slug>/`
   yourself before closing out the pass - a hand-run pass never touches
   `_intake_queue`, so `qa_manage.py`'s archive command has nothing to
   act on and the file silently sits in `00_Inbox` looking unprocessed.
   This has already happened for real sources.
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
  If the fact isn't really an M1/M2 current-state update either but is a
  concrete, generalizable management situation (client/stakeholder
  behavior, an approach that worked or didn't, a takeaway useful beyond
  this project) - route it to `pm-case-knowledge-intake` instead. See
  that skill and `pm-case-knowledge-roles/SKILL.md` for what counts as a
  real case; most sources produce none, don't force it.
- Do not skip logging `pk_source_index` for a source that turned out to
  add nothing new - a `no_change` outcome is still a recorded outcome.
