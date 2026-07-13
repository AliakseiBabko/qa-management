---
name: m2-admin-note-intake
description: Process short, pasted-inline (not file-based) M2 conversation snippets about chat access/membership, project or chat naming ambiguity, and structured person-info cards. Use when M2 pastes a short DM/thread excerpt about who's in which strategy chat, who can grant access, whether two similarly-named chats are the same project, or a person's Job Title/M-level/Prof.Level/Mentor/DC card - not a full exported chat file and not a person-focused 1:1 transcript.
---

# M2 Admin Note Intake

Use this skill for two specific input shapes that don't fit the other
intake skills:

1. **Chat topology notes** — a short exchange (often undated, or dated only
   in relative terms like "51 min") about strategy-chat access/membership,
   or about whether two differently-named chats refer to the same project.
2. **Person cards** — a structured block of fields (Name, Email, Job Title,
   M-level, Prof.Level, Mentor, DC) handed over directly by M2 for one
   person.

## What This Is, And Isn't

- Not `m2-strategy-chat-analysis`: that skill expects a dated, multi-topic,
  exported chat file (`<Project>_strategy.txt`) covering weeks/months. This
  skill is for a short pasted excerpt of a live conversation, often just a
  few messages, with no filename convention at all.
- Not `qa-1to1-analysis`: that skill is about one person's performance
  discussion. This skill is about workspace *plumbing* — who has access to
  what, what a chat/project is actually called, who a person is.

## Required Start

1. Read `../qa-management-roles/references/google-workspace-rules.md`'s
   `_people_registry` section, including **Person Card Intake** — the field
   mapping for person cards lives there, not duplicated here.
2. Read `../qa-management-roles/references/m2-role-rules.md`'s Risk Rules
   (topology risk) and Communication and Visibility sections — a chat
   topology finding is often itself a risk signal, not just registry
   housekeeping.

## Workflow — Person Cards

1. Save the card to a file and run
   `.agents\scripts\apply_person_card.py --file <path>` first — it parses
   the fields, computes Role/Internal rank/Notes per the Person Card Intake
   mapping, and looks up any existing `_people_registry` row by email, so
   you're not re-deriving the mapping by hand each time. Pass `--file`, not
   stdin — a Windows bash heredoc was found to silently drop the Cyrillic
   half of the name.
2. It only auto-writes a genuinely **new** row (`--apply`); for an existing
   person it prints the existing row and the computed fields side by side
   but does not write — Name/Project(s) changes, and any contradiction
   against that person's `individual_metrics`/`individual_development_plan`
   (e.g. the AQA-vs-manual-track pattern in `m2-role-rules.md`'s Вклад в
   проект Calibration), still need your read before applying.
3. Log the addition/correction to whichever project's `evidence_log` is
   most contextually relevant (the project the card arrived alongside), with
   `source_type` = `m2_conversation`.

## Workflow — Chat Topology Notes

1. Extract the concrete fact(s): who's missing from which chat, who granted
   or couldn't grant access, and why (e.g. "never added myself"), or which
   raw chat names map to which single canonical project.
2. Cross-check against `_project_registry`/`_people_registry` — a topology
   note is exactly the kind of source that resolves (or reveals) exactly
   the kind of ambiguity flagged in `google-workspace-rules.md`'s registry
   rules (unclear role, unclear project mapping).
3. If the note reveals a real visibility/access gap (M2 or M3 missing from
   a project's own strategy chat, no M3 present at all, unclear who can
   grant access), treat it as a topology risk per `m2-role-rules.md` — add
   it to that project's `m2_input` with `pipeline_common.add_questions()`
   (it auto-routes to extending a pending round or opening a fresh one, so
   you don't need to check `get_last_round_status()` or pick between the
   lower-level `append_doc_round`/`append_to_pending_round` yourself).
   Frame it as a question for M2 to decide on escalation, not a foregone
   conclusion. If the note instead directly *answers* a question already
   sitting in a pending round, use `add_answer()` instead.
4. If the note simply resolves a naming/mapping ambiguity (e.g. confirming
   two chat names are the same project) with no risk implication, a plain
   `evidence_log` entry is enough — no `m2_input` round needed.
5. Log the conversation itself to `evidence_log` (`source_type` =
   `m2_conversation`), even though there's no source file — see
   `google-workspace-rules.md`'s note on logging conversational updates.

## Guardrails

- Dates in these snippets are often relative ("51 min", "4 min") or absent
  entirely — don't fabricate an absolute date; use today's date for the
  `evidence_log`/`m2_input` entry and state the ambiguity if the snippet's
  own timing matters to the fact (e.g. whether something happened before or
  after a recorded cutoff date elsewhere in the registry).
- Do not silently resolve a contradiction with an existing registry cutoff
  or role (e.g. a "was M2 until <date>" note vs. a message implying the
  role continued) — state both readings and pick the one the new evidence
  actually supports, explaining why, rather than picking silently.
- Do not add every person mentioned in passing to `_people_registry` — same
  scoping rule as `m2-strategy-chat-analysis`: only people whose role
  matters for QA-management topology.
- Use `pipeline_common.add_questions()`/`add_answer()` for all `m2_input`
  writes, never the lower-level `append_doc_round()`/
  `append_to_pending_round()` directly — picking between those two by hand
  produced a real bug once (see README.md's `pipeline_common.py` entry and
  the <Project> evidence_log, 2026-07-13).
