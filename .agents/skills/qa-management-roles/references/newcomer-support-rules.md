# Newcomer / First Commercial Project Support Rules

Cross-cutting rule for both M1 and M2 skill families — referenced from
people-risk, OKR/development-plan, and 1to1-prep skills on both sides,
rather than duplicated in each.

## What This Tracks

Whether this is the person's **first commercial project** — their first
time carrying real work on a real client-facing/production project, with
real stakes, real people, and real process, as opposed to internship
projects, training/sandbox work, or purely internal tooling.

This is a distinct fact from:

- **Recent hire** — an internal transfer or rehire can be a brand-new hire
  by date and still not be on their first commercial project.
- **Internal rank (Junior)** — a Junior with a year of real project
  experience elsewhere is not this case; a Middle/Senior moved into their
  first-ever client-facing role technically could be, though this is rare
  in practice — don't assume rank alone settles it either way.

Do not infer this from `Дата трудоустройства`, internal rank, or tenure.
Ask directly.

## Detection

- Ask the engineer themselves, their M1, or the project's DC/QA lead —
  whichever is available first. Do not guess or leave it unrecorded.
- Record the answer in `_people_registry`'s
  `Первый коммерческий проект` column (`Да` / `Нет`) — see
  `google-workspace-rules.md`. Leave blank only while genuinely unconfirmed,
  and treat an unconfirmed value on someone newly staffed to a project as
  something to actively resolve, not a permanent gap.
- A Person Card Intake (see `google-workspace-rules.md`, Person Card
  Intake) that states this fact maps directly into the same column; if it
  doesn't, ask rather than leaving the column blank once the person is
  actually staffed on a project.

## Elevated-Attention Window

The first **one month** of actual work on the project (from the person's
real project start date, not their hire date) — the fragile onboarding
period this rule exists to protect. A person who cleared this window
without incident does not need it re-applied on a later project move
unless that move is itself their first commercial project (e.g. someone
who was bench-only or internship-only until now).

## Required Response When `Первый коммерческий проект` = Да, Within The Window

- **Assign a named buddy or mentor** — an experienced teammate, the
  project's DC/QA lead, or M1 themselves — for at least the first month.
  "The team will support them" is not an assignment; it needs one
  accountable name.
- **Elevate `Риск с нашей стороны` to at least `Средний`** in the people-risk
  traffic-light (`m1-people-risk-report`) purely on onboarding fragility,
  even with no negative incident yet — this is a leading indicator the rule
  exists to surface early, not a lagging one that waits for a real problem
  to already show up.
- **Note it explicitly in the OKR / individual development plan**
  (`m1-individual-development-plan`, `m2-individual-development-plan`) for
  the cycle that covers this window — a short, real KR or note about buddy
  support and integration, not folded silently into a generic technical KR.
- **Ask about it proactively in 1to1 prep** (`m1-1to1-prep`, `m2-1to1-prep`)
  during this window — environment, process, team fit, whether the
  buddy/mentor relationship is actually working — rather than waiting for
  the person to raise a problem on their own once it's already serious.

## Ownership

Matches the existing M1/M2 boundary (`m1-role-rules.md`): the buddy/mentor
assignment and the person-level risk elevation are M1's to track and act
on. M2/DC surfaces the same fragility in `project_risk`
(`m2-project-risk-report`) only if it could concretely affect delivery —
same "project impact, not personal criticism" framing that document
contract already uses for a junior placed into a senior-level expectation.

## Rationale

Added 2026-07 after a real case where a newcomer's difficulties on their
first commercial project went unaddressed early on, and several of the
resulting problems were avoidable had "first commercial project" been
asked about and flagged from week one, with a named buddy assigned
immediately. This rule exists specifically because that fact was not being
asked or recorded anywhere before this.
