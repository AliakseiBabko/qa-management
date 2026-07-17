---
name: m2-strategy-chat-analysis
description: Analyze a project-level M2 strategy chat export (filename ending "_strategy", e.g. `<Project>_strategy.txt` under `00_Source_Docs\02_Chats_and_Emails`) — a running, multi-month, multi-stakeholder chat used for planning and solving common problems on one project — and extract structured project-management facts for routing into that project's own artifacts. Use when a new "_strategy" chat file needs processing, or when asked what changed for a project based on its strategy chat.
---

# M2 Strategy Chat Analysis

Use this skill for analysis only. It does not own final report-file creation — see
`qa-management-roles/references/m2-role-rules.md` and `google-workspace-rules.md`
for who updates what.

## What This Is, And Isn't

A "_strategy" chat is a **project-scoped**, **multi-topic**, **chronological**
chat log — the ongoing sync/status channel for one project, covering staffing
decisions, DC/PM ownership, client communication, visas/logistics, hiring,
and weekly status, spanning weeks or months and multiple stakeholders (DC,
PM/intermediary, client, M2/M3).

This is not `qa-1to1-analysis` (a single person's 1:1, people+project signals
mixed but scoped to that person) and not a meeting transcript. Don't force a
strategy chat through the 1to1 skill — there is no single "who this is about."

## New-File Convention

Never add new messages to an existing `_strategy` file in place. Each new
batch of chat content is a **new file** — e.g.
`<Project>_strategy_2026-07-20.txt` — dropped into
`00_Source_Docs\02_Chats_and_Emails`. This matters mechanically, not just
stylistically: detection below dedups by filename, not content hash, so
editing an already-logged file in place makes new content invisible to it.

## Required Start

1. Check `../qa-management-roles/references/aliases.md` before treating an
   unfamiliar project/person name from the chat as new.
2. Run `.agents\scripts\detect_strategy_chats.py` first. It finds
   `_strategy` files not yet in the project's `evidence_log`, classifies
   the project from the filename prefix, resolves the message date range
   (Google Chat headers carry no year and use relative weekday-only
   timestamps for recent messages — resolved against the file's mtime, a
   heuristic worth a sanity check if the range looks off), logs one
   `evidence_log` row per file, and writes a review bundle under
   `80_Exports\intake_review\strategy_chats_<date>.md`. It does not
   extract facts or touch any other document — see its own docstring.
3. Read the flagged file(s) from the bundle in full, chronologically —
   these chats mix languages and jump between topics message-to-message;
   don't sample. If a file came back `UNCLASSIFIED`, confirm the project
   with the user and rename the file (`<Project>_strategy...txt`) before
   continuing.
4. Read `../qa-management-roles/references/m2-role-rules.md` and
   `../qa-management-roles/references/google-workspace-rules.md` before
   writing anything — the routing/gating rules there (Cascading Updates,
   Project-Level Rollups, registry role-conflict handling) apply directly.

## Workflow

1. Walk the chat in date order and extract dated facts, tagging each with
   its topic:
   - staffing/team changes (joins, departures, replacements, mentors)
   - DC/PM/ownership facts (who holds DC/DC Lead/PM roles, and since when)
   - client relationship, visits, visas, logistics
   - risk signals, per person or per project
   - status-report snapshots (who's doing what, current focus)
2. Cross-check every named person against `_people_registry`. A strategy
   chat is exactly the kind of source likely to reveal a stale or wrong role
   (e.g. someone recorded as client-side who is actually an internal DC) —
   when the chat contradicts the registry, or the user directly supplies a
   person's real profile, treat it as a correction, note it explicitly, and
   fix every document that repeated the wrong fact (registry entry, and any
   project doc prose that named the person's affiliation/role) — see
   `m2-role-rules.md`'s Template Consistency note on fixing a defect
   everywhere it propagated, not just where it was first noticed.
3. Cross-check dated facts against the project's existing `m2_input`,
   `project_risk`, and `project_development_plan` for contradictions (a
   later chat message can supersede or reopen an earlier settled
   conclusion — e.g. "candidate found" vs. a later "still searching").
   Surface contradictions as open questions; do not silently pick one side.
4. Route extracted facts using the same chain as any other source
   (`m2-role-rules.md`, Cascading Updates):
   - direct, unambiguous corrections (a wrong name/role/affiliation) can be
     fixed directly in `_people_registry` and any doc that repeated them.
   - person-level facts that materially change a picture already in
     `individual_metrics`/`individual_development_plan` update those
     directly.
   - anything that would change `project_risk` or `project_development_plan`
     conclusions goes through an `m2_input` preliminary-analysis round
     first (new dated section, questions only, answer left blank) — a
     strategy chat is a source, not a substitute for M2's own judgment
     round. Use `pipeline_common.add_questions()` to add the question(s) —
     it auto-routes to opening a fresh round or extending the current
     pending one, whichever the doc's current state calls for; you don't
     need to check `get_last_round_status()` or choose between
     `append_doc_round`/`append_to_pending_round` yourself (an earlier,
     lower-level version of this API made that choice wrong once on a real
     project — `add_questions` exists specifically so that mistake isn't
     repeated). If M2 answers a
     round directly in conversation, write it with `add_answer()`, which
     requires a round to actually be pending.
5. Update the `evidence_log` row `detect_strategy_chats.py` already created
   for this file (same `date`/`source` — don't append a duplicate): replace
   `routed_to` ("pending M2 review") with every document actually touched,
   and extend `notes` to summarize what changed and what was left as an
   open question, on top of the date-range note the script wrote.

## Guardrails

- Do not treat every person mentioned in a strategy chat as registry-worthy.
  `_people_registry` is scoped to QA-management-relevant roles (M1/M2/M3/M4/
  HR/DC/QA/AQA/PM/client stakeholder/etc.) — a strategy chat for a
  DE-heavy project will name many developers who are simply not in scope;
  only add people whose role matters for QA-management topology (DC/PM
  ownership, QA staffing, client stakeholders relevant to QA value).
- Do not resolve a contradiction between chat messages (or between the chat
  and existing docs) by picking whichever reads more recent/authoritative on
  your own — surface it as a question in `m2_input` unless it's a plain
  factual correction (a name, a date, a role) rather than a judgment call.
- Do not invent a project's business context from a strategy chat that only
  discusses staffing/logistics — a chat full of visa and hiring detail is
  not evidence about how the client's product makes money.
- Preserve chronology when citing evidence — a chat spans months, and
  "current state" should reflect the latest dated entry, not an earlier one
  that happens to appear first when skimming.
- Do not conflate "this person acts as M1/M2/DC for someone on this project"
  with "this person is staffed on this project." A strategy chat is exactly
  where this shows up — e.g. an AQA staffed on `<Project A>` who also acts
  as M2 for a QA on `<Project B>` is not staffed on `<Project B>`.
  `_people_registry`'s
  `Project(s)` column is staffing only; a cross-project management duty goes
  in `Notes`, naming which project(s) it covers (see
  `google-workspace-rules.md`'s `Project(s)` definition). Someone can and
  often does wear more than one hat — capture each accurately, don't merge
  them into a single list that blurs which one is which.
