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

1. Apply the Person Card Intake field mapping from `google-workspace-rules.md`
   exactly — don't re-derive it per card.
2. Check `_people_registry` for an existing row for this person first. If
   found and a field conflicts, treat the card as the stronger source (see
   that section) and fix every document that repeated the old fact.
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
   it as an addendum to that project's **pending** `m2_input` round via
   `pipeline_common.append_to_pending_round()` (check
   `get_last_round_status()` first; if the round is already answered, open
   a new one with `append_doc_round()` instead). Frame it as a question for
   M2 to decide on escalation, not a foregone conclusion.
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
- Never use `pipeline_common.append_doc_round()` to add to an
  already-pending round — it appends at the Doc's end, which lands after
  the empty answer heading and breaks `get_last_round_status()`'s pending
  detection. Use `append_to_pending_round()` for that case.
