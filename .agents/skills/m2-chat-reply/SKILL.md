---
name: m2-chat-reply
description: Draft a short chat-ready reply to a specific incoming question/message, using collected M2 project and person context (recent 1:1s, project_metrics, project_risk, m2_input, action_items, evidence_log). Use when the user says "help me answer this" / "help me reply to this" and pastes or describes a message someone sent them, as opposed to a periodic status update or 1:1 prep list.
---

# M2 Chat Reply

Use this skill for one output family only:

- a short, chat-ready reply to one specific incoming question or message,
  blending new information from M2's own project/person records with the
  user's own stated plan or judgment

This is different from `m2-project-status-report` (a periodic/on-demand
status update with no specific question to answer) and `m2-1to1-prep` (a
question list for a call that hasn't happened yet). This skill answers a
message that already exists — a question from a manager, a client-facing
colleague, a teammate — where the reply needs facts this workspace has
already collected, not a fresh 1:1.

## Required Start

1. Read the message/question being answered carefully. Identify exactly
   what is being asked, and — just as important — what that message
   already tells its own recipient (context it states, claims it makes,
   numbers it cites). That part is already known to whoever sent it; it
   never belongs in the reply.
2. Read `../qa-management-roles/references/chat-message-style-rules.md`.
3. Read `../qa-management-roles/references/m2-role-rules.md`.
4. Identify the project and/or person this question concerns. If it can't
   be inferred and genuinely isn't clear, ask once, briefly — don't guess
   a project/person scope silently.
5. Run `.agents\scripts\show_project_state.py --project <Project>`
   (add `--person <Person>` scoping or `--document <name>` for a narrower,
   cheaper pull once you know what you actually need) to gather current
   facts. `search_workspace.py search "<name/topic>"` fills gaps
   `show_project_state.py` doesn't cover (older evidence_log/action_items
   rows, m2_input history).

## Source Order

1. The most recent 1:1/meeting evidence for this person or project
   (`evidence_log`, `individual_development_plan`'s "Текущее состояние",
   the latest `individual_metrics` rows) — this is usually where the
   genuinely *new* information lives, the part worth actually saying.
2. `m2_input`'s latest round/addenda, if the question touches something
   already surfaced there.
3. `project_metrics` / `project_risk`, if the question is about
   project-level standing (profitability, risk, continuity).
4. `action_items` open items relevant to the question.
5. Whatever the user has already told you directly in this conversation as
   their own plan, decision, or reasoning — treat that as settled input,
   not something to re-derive from documents. Fold it in using their own
   framing, not a re-formalized paraphrase.

## Workflow

1. From Required Start step 1, list what the incoming message already
   establishes — mark it off-limits for the reply, even if it's also true
   and also documented in M2's own records.
2. Pull only what's relevant to the actual question from Source Order —
   not a full status dump of everything known about the project/person.
3. Separate what you found into two kinds of content: **new information**
   (dated, sourced — something learned since whatever the recipient
   already knows) and **the plan** (the user's own decision or judgment,
   in their words). Both are usually needed; neither replaces the other.
4. Draft a reply that blends the two in natural flow — the new information
   motivates or grounds the plan, not two stapled-together paragraphs
   where one reads like a document excerpt and the other like a separate
   verbal note. See Before/After below.
5. If part of the plan isn't settled yet (needs to re-confirm with someone,
   needs another data point), phrase it as an intention or next step, not
   a fact already true.
6. Do not add contingencies, alternative options, or hedges the user
   didn't actually describe — if they said no other option is being
   considered, don't soften that with an invented fallback.
7. Present as plain chat text in the reply's own language (Russian by
   default for this workspace's business communication, per AGENTS.md,
   unless the user asks for another language for this message). Never
   save as a Doc unless the user asks for a kept copy.

## Before/After (illustrative — placeholders, not a real project)

Incoming message (already known to its own recipient — do not repeat):

> Рентабельность выровняли повышением рейта, но проект всё ещё в жёлтой
> зоне. Нужно подумать план по <Person>.

A first-draft reply that just restates the incoming message's own content
back, then bolts on the plan as an unrelated second paragraph, is wrong:

```text
Рентабельность выровняли повышением рейта в июне, но всё равно в жёлтой
зоне...  <-- already known to the recipient, drop entirely

Текущий план - продолжаем проект как есть. ...  <-- fine, but stapled on
```

The blended version leads with what's actually new, and lets that new
fact motivate the plan in the same breath:

```text
По <Person>: из 1:1 всплыл новый момент - горизонт по контракту
подтверждён только до конца этого года, продление не подтверждено, и
клиент активно тестирует AI-агентов именно с целью закрывать больше
своими силами. Так что пока продолжаем проект как есть.

По второй ставке - раньше <Person> говорил(а), что отдельный проект не
нужен; похоже, это по-прежнему не вариант, но переспрошу ещё раз, чтобы
уточнить.
```

## Guardrails

- Never restate the substance of the message being answered, or anything
  already established in that same chat thread — the recipient wrote it
  or already knows it.
- Never invent a fact, date, decision, or number not grounded in an actual
  source document or the user's own explicit statement this session.
- Do not add a "let's discuss further" / open-ended closing unless the
  user's own dictated content included one — see
  `chat-message-style-rules.md`'s no-default-closing rule.
- Do not add contingency plans, alternative options, or extra hedges
  beyond what the user actually described as the plan.
- If the user's own dictated reasoning conflicts with what the collected
  evidence actually says, flag the discrepancy to the user directly before
  finalizing wording — never silently override the user's stated plan,
  and never silently paper over a contradiction either.
- Apply `chat-message-style-rules.md` in full (no em dashes, no
  unrequested clarifying questions, no meta-commentary explaining the
  message's own framing, no default format-choice closing).
- Do not produce a periodic status report or a 1:1 question list here —
  redirect to `m2-project-status-report` or `m2-1to1-prep` if that's what
  the user actually wants instead of a reply to a specific message.
