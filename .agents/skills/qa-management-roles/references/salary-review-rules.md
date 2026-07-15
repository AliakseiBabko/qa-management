# Salary Review Rules

Source: internal Confluence articles "Пересмотр зарплаты (Salary Revision)"
and "Вилки пересмотров зарплат" (<Name>). Salary review happens
*inside* a Performance Review (see
`performance-review-rules.md`) but has its own eligibility gates and a
distinct self-feedback flow — kept as a separate reference rather than
folded into `performance-review-rules.md`.

## Cadence and Eligibility

- Every 6 months for staff employees Junior and above, once probation is
  closed (3 months from hire) — same cadence as the regular post-probation
  PR (see `performance-review-rules.md`).
- Intern → Junior conversion: the salary review (and full conversion) can
  happen once the employee has held their own commercial project at ≥0.5
  FTE for more than 3 months AND has worked on it for at least 1 month
  with positive feedback. This is on individual timing, not the standard
  6-month formula (matches the Intern→Junior PR exception in
  `performance-review-rules.md`).

## What Decides a Revision

A revision is a holistic read of:

1. **Growth in value** — on the project, outside the project, for the
   team, and for the department. Only counts what the person did *beyond*
   their normal level's duties — routine on-level tasks are not grounds
   for a raise ("Рутина не в счет").
2. **Commercial output** — billable hours on projects over the previous
   period.
3. **AI competency** — verified level of AI-tool skill, matched to grade.

### AI Competency Verification

- Verification is done by the named AI leads: **<Name>** (QA
  track) and **<Name>** (AQA track) — not self-certified, not
  inferred from OKR "ИИ" objectives alone.
- The AI assessment is taken once per grade, usually alongside (or shortly
  after) the main technical assessment for that grade.
- **Case 1 — sitting a grade assessment (e.g. going for Middle):** AI-team
  representatives join the assessment and evaluate AI competency
  alongside the technical evaluators. Both approvals are required for the
  grade. Once passed, no re-assessment is needed for subsequent PRs at
  that grade.
- **Case 2 — no AI assessment on record:** a separate AI-only assessment
  must be taken before the next PR to confirm grade-appropriate AI
  competency, with results shown at that PR/review.

### Achievement Matrix

Manual QA and AQA each have their own competency-matrix template (referenced
in the source article but not attached to this repository — locate/ask for
the actual matrix document rather than inventing one) that ties concrete
achievements to next-level criteria, to keep the assessment structured and
less subjective.

## Flow (within the PR)

1. Employee prepares a self-feedback document and presents it to RM and
   their M: what improved, with evidence, matched to the categories above,
   plus their own feedback on working with the company.
2. M and RM validate each point during this presentation, asking for more
   evidence where needed.
3. Within the main PR: 360 feedback, project feedback, manager feedback,
   RM feedback are all discussed.
4. Future plans are discussed.
5. After the PR, RM stays with the employee to clarify expectations.
6. RM analyzes all feedback + progress and comes back with a decision.
7. Confirmed improvements get logged in HRM (опыт-навыки).

## Why a Revision Might Not Happen

- **No developmental dynamics** — tasks at the same complexity as last
  period; no hard-skill progress or expanded responsibility.
- **Insufficient AI competency** — no attempt to adopt AI tools into daily
  work; no measurable quality/speed improvement from them; no AI
  assessment confirming the person's current grade level (get this from
  the AI leads named above).
- **On bench at review time** — blocking. A revision can only happen after
  the person is back on a project; the new rate starts from the month they
  actually start on it, not from the PR date.
- **Unsatisfactory feedback** (360 / manager / RM) — critical remarks,
  soft-skill/communication/process/values issues.
- **Negative project feedback.**
- **Low department engagement** — skipping main department chats, team
  syncs, 1:1s; being effectively disconnected from the team.

## Salary Forks (Вилки)

Client budgets cap what they'll pay per grade — pay can't rise
indefinitely without the person's professional level rising with it.

- **Junior/Middle:** to keep growing pay, the person needs to level up
  (pass the grade assessment) once they hit the top of their current
  fork *and* have enough commercial experience — RM tells them when
  they've hit the ceiling at a review.
- **Senior:** typically hits the market ceiling for base rate. Growth from
  there comes from taking on more value-generating activity, not from a
  base-rate assessment:
  - **Regular project rate increases** — a Senior who's been stable on one
    project for 1+ year with strong performance can push for repeated rate
    increases; the company pays an ongoing bonus (growing with each rate
    increase) for the life of the project. Requires initiative — showing
    project value, pinging RM/Head/Sales, not waiting to be offered it.
  - **Project expansion / becoming a lead** — a bonus per added FTE; a
    lead role opening new seats earns an ongoing lead bonus.
  - **Internal M-management** — becoming an M-manager, taking on
    leadership, training, and staffing duties earns a leadership bonus.
  - **Multi-project management** — a bonus for successfully running 2-3
    projects at once; if that's not sustainable solo, taking on a
    shadow/trainee/intern to offload load is the alternative path.
  - **Trainee mentorship** — sustained, quality mentoring.
  - **Other department/company help** — presales participation, test-task
    support, crisis/escalation support, helping Sales sell QA (trainings,
    joining client calls as an expert), project support, community
    building, mock interviews and hiring interviews, meetups, request/
    interview prep, tool/domain/process consulting.
  - If someone wants to help beyond their project but isn't sure how, the
    source article's own advice is to talk to Head/RM/their lead directly
    — this repository does not decide that for them.

## What `salary-review-prep` Does and Doesn't Cover

`salary-review-prep` helps assemble evidence for the self-feedback
document and runs the blocker pre-check above — it does not decide grade
progression or approve a raise (RM decides, after the PR), and it does not
certify AI competency (the named AI leads decide that). Commercial billable
hours are not tracked anywhere in this repository — always ask for that
number rather than estimating it.
