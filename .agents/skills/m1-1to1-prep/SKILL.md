---
name: m1-1to1-prep
description: Prepare a scoped question list for an upcoming M1 1to1 with a specific QA engineer, driven by that person's current people-risk signals. Use when the user asks what to ask/cover in their next people-management 1to1 with a named person.
---

# M1 1to1 Prep

Use this skill for one output family only:

- a short, chat-ready list of questions for M1's next 1to1 with one named person

This is the opposite direction from `qa-1to1-analysis` (which processes a
1to1 that already happened). This skill prepares for one that hasn't
happened yet.

## Required Start

1. Identify the person.
2. Read `references/document-contract.md`.
3. Read `../qa-management-roles/references/m1-role-rules.md`.
4. Read the person's current-cycle OKR Doc if one exists (see
   `m1-individual-development-plan`).
5. Check `_m1_timeline` (see `m1-timeline`) for any other open item logged
   against this person.

## Scope

Questions here are about **this person's people-side situation** —
motivation, loyalty, growth, workload sustainability, career readiness,
open risk signals from our side or theirs. Not project delivery details,
client expectations, or project metrics — those are M2's 1to1 (see
`m2-1to1-prep`). If a people-risk signal happens to be project-caused (e.g.
overload from a specific project), still frame the question around the
person's experience of it, not the project's fix.

## Source Order

1. This person's row in the M1 people-risk traffic-light Sheet
   (`10_M1_People_Management`, see `m1-people-risk-report`) — `Риск с нашей
   стороны (мы недовольны)` and `Риск со стороны сотрудника (он недоволен)`
   are the primary driver of this prep. Every open risk item becomes a
   question that either checks whether it's still true or moves it toward
   resolution. An empty or all-green risk row is itself worth a light
   confirming question, not silence.
2. This person's `План действий` from the same risk row — anything not yet
   done is a direct, concrete follow-up.
3. This person's 1to1 Sheet (`m1-people-1to1-file`) — the most recent row's
   `Assign`/`Action plan`. Check whether it was closed; if not, that is a
   follow-up question, not a fresh topic.
4. This person's current-cycle OKR Doc (`m1-individual-development-plan`) —
   any Key Result whose deadline has passed with no recorded status/result
   is a direct follow-up question. Keep it people-scoped: ask about
   progress/blockers on the OKR overall, and dig into the Soft skills and
   Департамент objectives specifically since those are M1's own territory;
   for a project-tied Техническое развитие KR, a light "on track / blocked"
   check is enough — a deep technical review belongs to the person and, if
   project-caused, to `m2-1to1-prep`, not here.
5. This person's open rows in `_m1_timeline` (`m1-timeline`) — any event
   not covered by sources 1-4 (e.g. a logged reminder unrelated to risk or
   OKR) becomes a direct follow-up question.
6. Any `qa-1to1-analysis` findings from a transcript newer than the last
   risk-sheet update, if one exists and hasn't been folded in yet.

## Workflow

1. Pull candidate questions from each source above, in order.
2. Drop anything already resolved by a more recent source.
3. Group into short sections (suggested: Открытые риски, Открытые OKR,
   Последующие шаги — only include a section with real content).
4. Cap at what actually fits in a 1to1 — 4-6 questions is normal for a
   people-focused conversation; leave room for the person to talk, don't
   script the whole meeting.
5. Present as plain chat text. Do not create a Google Doc/Sheet by default;
   only save it if the user explicitly asks (see Versioning in the
   document-contract).

## Guardrails

- Do not include project delivery, client, or project-metrics questions —
  redirect those to `m2-1to1-prep`.
- Do not soften or omit an open "Риск с нашей стороны" item just because
  it's an uncomfortable topic — state it as a question to actually raise,
  not skip.
- If the person has no risk-sheet row yet, say so plainly rather than
  inventing generic onboarding questions not grounded in their actual
  history.
- Do not write into the OKR Doc or `_m1_timeline` from this skill —
  status/result updates and event-closure that come out of the actual
  1to1 get applied via `m1-individual-development-plan`/`m1-timeline`, not
  from what was planned to be asked.
- If the person has no current-cycle OKR Doc, say so plainly rather than
  treating it as nothing to ask about — a missing OKR past its due date is
  itself worth a question.
