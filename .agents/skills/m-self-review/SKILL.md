---
name: m-self-review
description: Help an M1 or M2 prepare their OWN Performance Review materials — the "Критерии оценки команды" team-scoring artifact and a self-review prep summary (own OKR recap, team score, required PGROWTH tasks) — as the employee being reviewed by the grade above (M3), not as the manager running PR for their team. Use when M1/M2 is preparing for their own PR, computing their team's effectiveness score, or asking what they still owe before their own review.
---

# M-Self-Review

Use this skill for two output families:

- `критерии_оценки_команды` Google Sheet (dated per PR cycle), with CSV fallback
- a chat-ready self-review prep summary (own OKR recap, team score, outstanding PGROWTH tasks)

This is the counterpart to `m1-individual-development-plan` /
`m1-monthly-report` / `m1-timeline`, which are about **M1 running these
processes for their own QA team**. This skill is about **M1 (or M2)
preparing their own PR as the person being reviewed**, per
`../qa-management-roles/references/performance-review-rules.md`'s "М1/М2/М3
self-review" row — a different document, about a different subject, even
though some of the same underlying data feeds both.

## Required Start

1. Read `references/document-contract.md`.
2. Read `references/team-criteria-rules.md`.
3. Read `../qa-management-roles/references/performance-review-rules.md`.
4. Identify whether the person is M1 or M2 (this decides the target root
   folder — see document-contract.md) and their team.
5. Read their existing OKR Doc (`m1-individual-development-plan` /
   `m2-individual-development-plan` — same Doc mechanics apply to an
   M-manager's own OKR, just stored under `_self_review`, see
   document-contract.md), their most recent `критерии_оценки_команды`
   snapshot if one exists, `_m2_people_registry`, and — for metric 4 — each
   team member's `project_metrics` `Вклад в проект` rows.

## Workflow

### Критерии оценки команды

1. Use `Templates/критерии_оценки_команды.csv` as the schema. Score all 17
   metrics per `references/team-criteria-rules.md` — do not renumber,
   merge, or drop a metric even if it seems redundant for a small team.
2. Metric 1 (team feedback) is collected by the grade above (M+1), not the
   person being reviewed — if the user is filling this in themselves, flag
   that this one specifically needs to come from their own manager, don't
   let them self-report it.
3. For metric 4, pull what `project_metrics` already has for each team
   member before asking the user for projects this repo doesn't track.
   For metrics 6 and 12, pull what `_m2_people_registry` already has
   (`Role`, `Internal rank`) before asking for the rest.
4. Every other metric needs a real number from the user (utilization tool,
   HRM, mock-interview tool, interview-report chat, offboarding records,
   photo report) — ask, do not estimate or default to a middle score.
5. Leave a metric's `Балл` blank (not `0`) when genuinely unknown — `0` is
   a real negative score.
6. Compute the total once every knowable metric is scored:
   `сумма баллов / 34 * 100`. State whether it clears the 70% effectiveness
   threshold. If any metric is still blank, say the total is partial and
   name what's missing rather than presenting an incomplete score as final.
7. Save as a new dated Sheet per PR cycle (see Versioning) — this is a
   point-in-time PR artifact, not a living document like `_m1_timeline`.

### Self-review prep summary

1. Pull: the outgoing OKR's KR statuses/results (see
   `m1-individual-development-plan`), the current `критерии_оценки_команды`
   total (if scored), and which PGROWTH tasks are still outstanding for
   this person's employee category (`performance-review-rules.md`,
   "Required Jira Tasks" — М1/М2/М3 row: 7 tasks).
2. Present as plain chat text — this is prep, not a final artifact; only
   save it as a Doc if the user explicitly asks (mirrors `m1-1to1-prep`).
3. Remind the user of the pre-PR sync requirement: results must be
   discussed with M+1 and M+2 before the main PR (an M1 invites their own
   M2 and M3; only the summary of that discussion goes to the main PR).

Salary-review self-feedback (own or a team member's) is a separate skill,
`salary-review-prep` — not covered here. Critical criteria overlap (project
value, team value) but the artifact, template, and eligibility gating are
different; don't fold one into the other.

## Guardrails

- Do not conflate this with `m1-individual-development-plan` /
  `m1-monthly-report` / `m1-timeline` — those are M1 managing their team;
  this is M1 being managed. If the user's request is actually about their
  team (drafting a QA engineer's OKR, tracking team PR dates), redirect to
  those skills instead.
- Do not self-score metric 1 — it belongs to the grade above.
- Do not invent numbers for externally-sourced metrics (utilization, HRM,
  mock-interview pass rates, etc.) — ask, and leave blank if unavailable.
- Do not present a partial score (some metrics blank) as the final
  effectiveness percentage without saying it's partial.
- Do not reinterpret a scoring band's wording to fit an edge case — quote
  the band back to the user and ask which one applies.
