---
name: salary-review-prep
description: Help a person (a QA team member, or M1/M2 themselves) assemble their self-feedback document for a salary review, tracked inside a Performance Review — evidence-backed value growth, AI-competency assessment status, and a blocker pre-check. Use when preparing for a salary/grade review, checking whether someone (including yourself) is likely eligible, or drafting the self-feedback doc a person presents to their M/RM.
---

# Salary Review Prep

Use this skill for one output family only:

- `salary_review_self_feedback` Google Doc draft, per PR cycle

This is a shared skill, not M1- or M2-exclusive: the self-feedback document
is always **drafted by the employee, with manager support** (same pattern
as OKR drafting), so it applies both when M1 is helping a QA team member
prepare theirs, and when M1/M2 is preparing their own (alongside
`m-self-review`'s Критерии оценки команды for the M-level case).

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/salary-review-rules.md`.
3. Read `../qa-management-roles/references/performance-review-rules.md` for PR cadence context.
4. Identify the person and whether this is a team-member case (M1/M2 supporting a QA engineer) or a self case (M1/M2 preparing their own).
5. Read the person's OKR Doc (`m1-individual-development-plan` / `m2-individual-development-plan` / `m-self-review`), their `_m2_people_registry` row (grade, hire date), their `1to1` Sheet, and — if on a project — `project_metrics`'s `Вклад в проект` row.

## Workflow

1. Check eligibility first (`salary-review-rules.md`, Cadence and
   Eligibility): 6 months since the last salary review, probation closed;
   or, for an Intern→Junior conversion, ≥0.5 FTE on a commercial project
   for >3 months with ≥1 month of positive feedback. If eligibility is
   unclear, say so and ask rather than assuming this review is happening.
2. Use `Templates/salary_review_self_feedback.md` as the skeleton.
3. Assemble "Рост ценности" from real evidence, split into project /
   outside-project / team / department — pull from completed OKR Key
   Results, `project_metrics`, 1to1 notes, and department-facing OKR items.
   **Exclude routine on-level work** — only what the person did beyond
   their normal duties counts (`salary-review-rules.md`, "Рутина не в
   счет"). Do not pad this section with restated job description.
4. For "Коммерческая выработка" (billable hours), ask — this repository
   does not track commercial hours anywhere.
5. For "AI-компетенции," check whether an AI assessment for the current
   grade is on record. If unknown, ask. Never certify AI competency
   yourself — that's the current AI lead's call (QA or AQA track — look
   up who currently holds `AI Lead (QA)`/`AI Lead (AQA)` in
   `_m2_people_registry` rather than assuming a name), per
   `salary-review-rules.md`.
6. Run the blocker pre-check (dynamics, AI competency, bench status,
   feedback, department engagement) honestly against real evidence — the
   point is to surface a real blocker before the PR, not to produce a
   clean checklist. An unchecked item is a topic to raise, not something
   to hide or soften.
7. For a Senior already at their market fork ceiling, optionally note
   relevant growth levers from `salary-review-rules.md`'s Salary Forks
   section — only ones the person has actually mentioned or is already
   doing; frame the rest as discussion prompts, not facts.
8. Present the draft clearly as a draft the employee reviews/finalizes
   themselves before presenting it to M/RM — this skill assembles evidence,
   it does not write the final word-for-word self-feedback on the
   person's behalf as if it were their own voice.

## Guardrails

- Do not decide grade progression or approve a raise — RM decides, after
  the PR, per `salary-review-rules.md`'s Flow. This skill only assembles
  evidence and flags blockers.
- Do not certify AI competency — only the named AI leads can.
- Do not count routine, on-level tasks as achievements.
- Do not invent commercial billable-hours numbers — ask.
- Do not invent a salary-fork growth lever the person hasn't actually
  pursued or mentioned — offer it as a conversation topic, not a claimed
  achievement.
- Keep this skill scoped to self-feedback assembly for salary review. Do
  not use it to draft OKR (`m1-individual-development-plan`), the
  Критерии оценки команды artifact (`m-self-review`), or general PR
  self-assessment beyond the salary-review scope described here.
