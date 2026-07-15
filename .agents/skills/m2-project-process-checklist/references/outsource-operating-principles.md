# Outsource Operating Principles

Source: internal corporate Confluence articles "Роль М2 на аутсорс
проекте" and "Особенности работы на аутсорс проектах". Both are
needed to interpret a checklist gap correctly: a missing item is not
automatically a defect on an outsource project — the operating context
(fixed timelines, fixed scope, fast onboarding, pragmatic delivery focus)
is what decides whether it's an acceptable trade-off or a real risk.

## Why Outsource Is Different

Outsource work happens under fixed constraints (timeline, budget, scope)
where the real goal is quality delivery, not a textbook-perfect process.
Five operating conditions shape almost every judgment call:

1. **Сжатые сроки (fixed deadlines).** Contract-fixed timelines with
   little or no slack mean prioritization beats full coverage. Example
   pattern: 3 days to release with unstable functionality → QA picks the
   critical user flow, negotiates a reduced test scope with the team, and
   documents the risk in uncovered areas explicitly, rather than either
   attempting a full regression or silently skipping coverage.
2. **Фиксированный scope.** Any scope change needs re-agreement. QA's job
   is to notice scope creep ("this is part of the current task" additions
   mid-sprint) and check it against what was actually agreed, escalating
   through M2 when needed — not silently absorbing it.
3. **Быстрое погружение (fast onboarding).** No time for a long onboarding
   and documentation may not exist. QA is expected to build a working
   understanding fast: explore the product like a user, ask the developer/
   BA directly, and build a minimal checklist rather than waiting for full
   documentation before starting to test.
4. **Фокус на результате.** Delivery matters more than a "perfect"
   process. A medium-severity bug that would blow the deadline to fix
   might reasonably ship as a documented known issue after discussion with
   the team and M2 — a pragmatic call, not corner-cutting, as long as it's
   made explicitly and the risk is visible.
5. **Гибкость процессов + Неопределённость.** Processes won't always match
   the textbook, and requirements can be incomplete or shifting. The
   response is to think rather than mechanically apply a template — e.g.
   build a checklist only for the critical scenarios instead of trying to
   fully document a project that only has verbal agreements — and to
   proactively reduce ambiguity (clarify expected behavior, propose
   acceptance criteria, record what was agreed) rather than waiting for
   someone else to resolve it.

**Communication is the one place outsource conditions never justify
silence.** QA (and M2) should surface a risk of missed coverage, scope
creep, or a slipping deadline as soon as it's visible, with options, not
at the last moment.

## Applying This to the Process Checklist

- A checklist item marked `Не применимо` or a `Нет`/`Частично` status is
  not automatically a project-risk finding — read it against the five
  conditions above first. A missing formal test-management tool on a
  3-month fixed-scope engagement may be a reasonable trade-off; a missing
  bug-closure criteria on a 2-year strategic account is a real gap.
- Every `Нет`/`Не применимо` still needs a stated reason in `Обоснование`
  (see `document-contract.md`, Schema) — "acceptable given fixed 3-month
  scope, revisit if extended" is a complete, valid reason. A blank
  `Обоснование` next to a gap is incomplete, matching the same discipline
  used for blank metric cells elsewhere in this repository (see
  `m2-role-rules.md`, Template Consistency).
- A process-maturity gap is usually a project/PM-level condition, not a
  personal QA shortfall — this checklist reinforces the same rule already
  in `m2-role-rules.md`'s Вклад в проект Calibration (no formal DoR/DoD,
  no TMS decision, no CI pipeline are examples given there). Do not let a
  checklist gap pull an individual's contribution judgment down on its
  own.

## M2's Role and When QA Should Escalate

M2 is the key support and quality-control point on every outsource
project — not just a manager, but the resource for hard questions,
escalations, and client-side agreement.

### M2's Responsibilities

- **Process/quality control** — checks QA-process adherence, helps set up
  workflow/environments/documentation standards, confirms chosen QA
  approaches are agreed with the team/PM/DM/client, and tracks that
  agreements are actually kept.
- **Team support** — helps unblock hard/blocking tasks, advises on
  testing/process/tooling questions, helps prioritize under time pressure.
- **Communication and escalation** — the link between the team and the
  client; escalates timeline/quality/resource risk to the client or
  internal leadership; makes the call on disputed in-project situations.
- **Knowledge management** — mentors new team members, organizes domain/
  process knowledge transfer, helps QA ramp up on project specifics
  quickly.
- **Release acceptance** — approves release readiness from a QA
  standpoint, confirms Definition of Done criteria are met, participates
  in regression/release planning.

### When QA Should Go To M2

- a blocker that can't be resolved inside the team
- unclear requirements or process
- an emerging timeline or quality risk
- a conflict that needs resolving
- confirming a deviation from the standard checklist/process (see above —
  every exception needs sign-off, not just a personal judgment call)

### Practical Reminders

- Escalate early — don't wait for a problem to become critical.
- Log agreements reached through M2 (in the checklist's `Комментарии`,
  `project_risk`, or `evidence_log` as appropriate) so they don't get
  relitigated later from memory.
- Use M2 as the fast-onboarding resource, not just an escalation contact.
- When priorities/ownership are unclear, confirm through M2 rather than
  guessing.

M2 is support and quality control, not an auditor of DC/PM — the same
framing already stated in `m2-role-rules.md`'s Communication and
Visibility section; this checklist and the escalation list above are
tools for that support role, not a compliance audit to hold over the
project team.
