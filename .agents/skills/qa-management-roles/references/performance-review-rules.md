# Performance Review Rules

Source: internal corporate Confluence article "Performance Review (New)".
Kept here as the shared cadence/process reference — OKR
cadence (`m1-individual-development-plan`'s `okr-process-rules.md`) and
`m1-timeline`'s PR-date tracking both depend on the cadence rules here, so
this lives in `qa-management-roles` rather than being duplicated per skill.

## Purpose of PR

A regular process to evaluate an employee's results, surface potential,
and set goals for the next period: sync on shared goals, identify
strengths/growth areas, and set professional-development opportunities.

## Cadence Table

| Category | Frequency | Tied to salary review | OKR | Duration | Who runs it |
|---|---|---|---|---|---|
| Trainee QA (unemployed) | 1.5mo interim + 3mo wrap-up | No — tied to hiring into staff | Free-form single plan for the whole internship | 30 min | Mentor |
| Any grade on probation (intern/junior/middle/senior, employed) | Once, 3 months after hire | No (unless offer states otherwise) | One OKR for the whole probation period (editable) | 30 min | M1 |
| Intern who newly qualifies for Junior | Individual timing — as soon as formal Junior criteria are met (independent project work + passed Junior assessment) | Yes | OKR set for the next 6 months to the next PR | 1 hour | Employee self-initiates with M1 + RM; M1 schedules/runs |
| Any grade post-probation (junior — except this first one, middle, senior) | Every 6 months | Yes | OKR set for the next 6 months | 1 hour | M1 |
| M1 / M2 / M3 (as the employee being reviewed) | Every 6 months | Yes | OKR set for the next 6 months | 1.5 hours | M1/M2 reviewed by M3; M3 reviewed by M4 |

Key rule for computing the next date: **after probation closes, the next
PR is exactly 6 months from the date of the PR that closed probation** —
and every PR after that is 6 months from the previous one. The 3-month
probation interval is a one-time anchor from hire date, used only for the
very first PR.

Exception: the Intern→Junior transition PR happens on individual timing
(whenever formal criteria are met), not on the standard 3-month/6-month
formula — do not auto-compute this one; ask/confirm instead.

## Deriving the Expected Next PR Window (for `m1-timeline`, `_m1_pr_calendar`)

The next PR is not a single predicted date — it's a **window**: opens no
earlier than 6 months after the last PR, and shouldn't slip past 7 months
without a stated reason. Given `Дата трудоустройства` and `Дата последнего
PR` from `_m2_people_registry`:

1. If `Дата последнего PR` is set: window opens at that date + 6 months.
2. Else if `Дата трудоустройства` is set: window opens at hire date + 3
   months (the probation-closing PR hasn't happened yet).
3. Else: cannot compute — surface as a data gap (ask for hire date) rather
   than guessing or silently omitting the person from tracking.
4. The window **closes** exactly 1 month after it opens (6mo → 7mo from
   the anchor date). Before the window opens: not due yet. Inside the
   window: due. Past the window close: overdue, absent a stated exception
   (an explicit reason logged for the specific person, not a silent
   slip — see `_m1_pr_calendar`'s `Комментарий` column).

Cross-check the computed window against the person's current OKR Doc title
(`OKR к Perfomance review DD.MM.YY`, see `m1-individual-development-plan`)
when one exists — the Doc's date should fall inside the computed window,
since the OKR period is defined to end at the next PR. A Doc date outside
the window means one of the two sources is stale and needs reconciling,
not that one is automatically right.

`refresh_m1_pr_calendar.py` generates a dedicated `_m1_pr_calendar` Sheet
(see `m1-timeline`'s document-contract) from this same `_m2_people_registry`
data — a PR-only view, mechanically regenerated, never hand-edited, so it
never becomes a second source of truth for `Дата последнего PR`.

## Mandatory Participants

- Trainee: mandatory — trainee, mentor, internship lead; optional — M1, HR.
- Probation-close: mandatory — employee, M1, M2 (if on a project), mentor +
  lead of the internship program (for former interns); optional — M3, RM,
  Head, strategic HR.
- Intern→Junior transition: mandatory — employee, M1, RM, M2 (if on a
  project); optional — M3, Head, strategic HR, Head of Bench (if on bench,
  at M1's discretion).
- Post-probation regular PR: mandatory — employee, M1, RM, M2 (if on a
  project); optional — M3, Head, strategic HR, Head of Bench (if on bench).
- M1/M2/M3 self-review: mandatory — the employee being reviewed (M1 or
  M2), M3, RM (for M1/M2 reviews); for M3's own review — M3, Head, RM,
  strategic HR; optional — Head, strategic HR (for M1/M2 reviews).
- A meeting can start once mandatory participants have joined — don't wait
  on optional ones.

## Meeting Structure (fixed agenda)

1. Small talk / employee's impressions of the past period (5-10 min).
2. Employee's self-presentation: achievements and growth areas, tied
   explicitly to value delivered to the team (25-30 min; longer for M-level
   reviews, which also cover team results — hence the 1.5h M-level slot).
3. Manager's feedback: own view + project feedback + 360 feedback (10 min).
4. OKR discussion: recap the just-finished OKR, then set direction for the
   next one — the manager asks the employee what they want the next OKR to
   be, rather than dictating it (10 min).
5. RM's closing feedback and meeting wrap-up (5 min).

## Required Jira Tasks (PGROWTH epic, per employee category)

- **Probation employees** (4 tasks): Фидбек от проекта, Фидбек 360, Фидбек
  М-руководителя (includes OKR feedback), Саммари по результатам PR.
- **Post-probation Intern/Junior/Middle/Senior** (5 tasks): adds Оценка
  результатов сотрудником (filled by the employee before the meeting) to
  the above four.
- **M1/M2/M3** (7 tasks): Оценка результатов сотрудником, Фидбек от
  проекта, Фидбек 360 (collected by HR, not the manager), Фидбек
  М-руководителя (+ OKR feedback), Фидбек RM, Критерии оценки команды
  (filled by the employee — their team's aggregate metrics, discussed in a
  separate pre-PR sync with the M-grade above + M3 of the direction +
  Head, 3-4 days before the PR; only the summary comes to the main PR),
  Саммари по результатам PR.

## Timing Before the PR

- ~1 month before: automatic email notifications to the employee, their
  M-manager, strategic HR, and RM.
- The employee's M-manager creates the calendar meeting with agenda and a
  room.
- ~4 weeks before: feedback collection starts; the employee fills "Оценка
  результатов сотрудником" (skipped for probation-close PRs, which aren't
  tied to salary review).
- The M-manager collects project feedback (from M2) or bench feedback
  (from Head of Bench), 360 feedback, and forms their own view from OKR
  results + all collected feedback.
- For M1/M2/M3 PRs: the employee-being-reviewed gathers their team's
  evaluation criteria and holds a pre-PR sync 3-4 days before with the
  M-grade above, M3 of the direction, and M4 — only the summary of that
  sync is discussed at the main PR.
- After the PR, the employee writes the summary, drops it in the meeting
  chat for approval (M-manager approves first), then the summary gets
  added to the "Саммари по результатам PR" Jira task.

## What This Skill Set Does and Doesn't Cover

This repository's M1 skills (`m1-individual-development-plan`,
`m1-monthly-report`, `m1-1to1-prep`, `m1-timeline`, `m1-people-risk-report`,
`m1-people-1to1-file`) are scoped to **M1 running these processes for their
own QA team** — drafting/tracking team members' OKR, prepping team 1to1s,
tracking team PR dates, filing M1's own monthly KPI report about that work.

**M1's (or M2's) own Performance Review as the employee being reviewed** —
the "М1/М2/М3 self-review" row above — is covered separately by
`m-self-review`: the Критерии оценки команды scoring artifact and a
self-review prep summary. An M-manager's own OKR reuses
`m1-individual-development-plan`/`m2-individual-development-plan`'s Doc
mechanics directly (same template, same required KR fields), just stored
under `_self_review\<Person>\` instead of a team member's own folder — see
`m-self-review`'s document-contract.md.

`m-self-review` does not cover RM feedback or HR-collected 360 content
themselves (those are filled by RM/HR, not by M1/M2, per the "Required
Jira Tasks" table above) — it covers what the person being reviewed
prepares themselves: their own OKR recap and the team-scoring artifact.
Do not silently fold self-review content into the team-facing skills
above, or vice versa — they're about different subjects (the manager
themselves vs. their team) even when the underlying data overlaps.

**Salary review** (see `salary-review-rules.md`), which happens inside a
PR for eligible employees, is covered by `salary-review-prep` — a shared
skill usable both for a QA team member (M1 supporting them, same
"drafted by the employee, with manager support" pattern as OKR) and for
M1/M2 preparing their own.
