---
name: m2-1to1-prep
description: Prepare a scoped question list for an upcoming M2 1to1 with a specific QA engineer. Use when the user asks what to ask/cover in their next 1to1 with a named person, or wants prep questions before a sync with someone on their project.
---

# M2 1to1 Prep

Use this skill for one output family only:

- a short, chat-ready list of questions for M2's next 1to1 with one named person

This is the opposite direction from `qa-1to1-analysis` (which processes a
1to1 that already happened). This skill prepares for one that hasn't
happened yet.

## Required Start

1. Identify the person and confirm which project(s) their 1to1 prep should
   draw from (a person can be on more than one project).
2. Read `references/document-contract.md`.
3. Read `../qa-management-roles/references/m2-role-rules.md`.

## Scope

Questions here are about **this person specifically** — their performance,
their read of the project, filling gaps in their own metrics, what they
need from M2. Not project-wide staffing strategy, hiring, timelines, or
client-relationship questions; those belong in the project's own
development-plan conversation, not a person's 1to1. If the person's project
has open project-level questions that only they can answer (e.g. they're
the only one with visibility into a specific blocker), include those, but
frame them as "what do you know about X," not "what should we do about the
project."

## Source Order

1. That person's `individual_metrics` — every row with a blank `Показатель`
   is a candidate question; use its `Пояснение` to phrase what's actually
   missing (e.g. a blank Нагрузка row whose Пояснение says "субъективная
   нагрузка не обсуждалась" becomes "how does your workload actually feel
   right now — sustainable, or are you stretched?").
2. That person's `individual_development_plan` — open items in `Ближайшие
   шаги`/`Направления развития` that are due, close to due, or owned by
   them; anything a section marked "Неизвестно" is waiting on from them.
3. That project's `project_metrics` — this person's `Вклад в проект: <Имя>`
   row. If its `Пояснение` states a caveat or something not yet confirmed
   ("нужно ещё 1-2 цикла подтверждения," "провизорный статус," feedback not
   yet collected), turn the caveat into a question that would resolve it.
4. That project's `m2_input` — the latest round's still-unanswered
   preliminary-analysis questions, filtered to ones this person can
   actually answer (skip questions aimed at other stakeholders, PM/client
   coordination, or M2's own judgment calls).
5. That person's `individual_metrics_internal`, if it exists — use it to
   decide *what to probe*, never to decide *what to say*. A private doubt
   ("improvement might be situational, not durable") becomes a neutral,
   open question ("walk me through how the last few weeks have gone") —
   never a question that references or implies the private note exists.
   This file is M2-only; nothing that would reveal its existence or content
   belongs in a question asked directly to the person.
6. That project's `qa_process_metrics` — rows where this person is Owner
   and `Показатель` is still blank.

## Workflow

1. Pull candidate questions from each source above, in order.
2. Drop anything already answered by a more recent source (don't ask about
   a metric row that already has a value, even if an older plan item
   implied it was still open).
3. Group into 2-4 short sections (suggested: Метрики/факты, Развитие,
   Проект — only include a section if it has real content).
4. Cap at what actually fits in a 1to1 — 5-8 questions total is normal; do
   not pad with restated small talk to hit a target count.
5. Present as plain chat text, ready to bring into the meeting. Do not
   create a Google Doc/Sheet by default — this is a working list for one
   conversation, not a tracked artifact. Only save it if the user explicitly
   asks to keep a copy (see Versioning in the document-contract for where).

## Guardrails

- Never phrase a question so it reveals `individual_metrics_internal`
  content, or that such a note exists.
- Do not include project-level strategy/staffing/client questions unless
  this person is genuinely the only source for that specific fact.
- Do not invent a question about a metric that already has real data —
  check for the latest value first.
- If a person has almost no data anywhere (a near-empty `individual_metrics`
  and dev plan), say so plainly and lead the question list with the basics
  needed to close that gap, rather than padding with generic questions.
