# M2 Role Basics

Scope: M2 purpose, responsibility boundary, minimum artifacts, business-value framing, project onboarding, the M2/DC development path, and common anti-patterns.

## Role Boundary

M2 owns project management. Typical scope is 3-5 projects and 5-10 people.

## Main Goal

Increase value, predictability, staffing quality, and business impact of QA work on client projects. M2 must understand what the client business needs, how the project succeeds, how QA contributes, and how the role of our people can grow on the project.

M2 also owns growing the company's footprint on each project: identifying
where additional QA/AQA services would genuinely help (more manual QA,
test automation, specialized testing) and advocating for them with the
client/project side. See
`qa-management-roles/references/presale-upsell-rules.md` for diagnostic
markers, automation-readiness criteria, the upsell problem/benefit
framework, and the productized service menu this draws from. This is not
a side activity — it is reported as its own section in
`m2-project-status-report` and `m2-project-development-plan`.

## Minimum Project Artifacts

For each active project, maintain or work toward:

- project development plan
- individual development plan for each QA in that project context
- project metrics
- individual QA metrics
- project risk view
- outsource process-maturity checklist (see `m2-project-process-checklist`)
- onboarding / project-entry plan for new people
- status and sync path in the project strategy chat or equivalent channel
- `m2_input` — M2's own context and judgment, collected before each
  project-level rollup (see Project-Level Rollups below)

## Business Focus

Start from business/project context before QA actions:

- how the product/project earns money or creates internal business value
- who buys or funds it
- why users/clients need it
- competitive advantages and market/region/customer priorities
- project success criteria, not only release completion
- what the client expects from the product, development team, QA, and our company
- how our QA work affects cost, speed, quality, revenue, retention, trust, expansion, or risk
- full project topology: streams, real team size, DC/PM ownership, vendor/intermediary chain, client path, security/location constraints, and known tender/contract horizon

Do not confuse:

- use case with business flow
- development/QA task list with project development plan
- quality metric with business/project metric
- completed work report with success criteria

## Project Entry and Onboarding

At project start or staffing:

- understand the request, domain, project processes, communication paths, teams, responsibilities, tools, and constraints
- define the project candidate/person portrait: domain interest, relevant experience, soft skills, commitment, fit for project specifics
- prepare the person before interview/start; use several candidates when possible
- coordinate with bench leads, preparation leads, M1, previous M2, M3, sales, project coordinator, DC/DM when relevant
- prepare and approve an onboarding plan with the project side
- define entry criteria: access, equipment, software, VPN/MDM/security, visa/travel if relevant
- write strategy-chat statuses about preparation, start, blockers, plans, and results
- sync more frequently during the first 1-2 weeks
- use real project tasks, boards, Jira, comments, bugs, and meetings to build context
- before treating a newly-assigned person as a blank slate, check whether
  they have a `10_M1_People_Management/<Person>` folder - anyone M2
  previously managed as M1 (or inherited from a different M1) already has
  real 1:1 history there. Use it to seed `individual_metrics`/
  `individual_development_plan`, clearly marked as self-reported/pre-M2
  where relevant, not as an already-confirmed project-level fact until
  independently reconfirmed on the M2 side.
- establish access to meeting recordings (dailies, other project syncs)
  early, as a standing practice, not a one-off ask - manual note-taking
  doesn't scale against real project data volume. See
  `m2-1to1-prep`'s obligatory first-contact topic for how to raise this
  with a person directly.

**Open process question (not yet resolved - flag, don't silently assume an
answer):** a real case traced a serious early-tenure conflict back to a
support gap created by the M1/M2 role split itself -
before the split, M1 owned a new hire's early support end-to-end; after
the split, that ownership can fall between M1 and M2, with neither
treating early hands-on support as clearly theirs. The person affected
named this gap herself, unprompted. Worth deciding explicitly: who owns
close support in the first 1-2 weeks after M1/M2 now that the roles are
split - M1 by default, M2 by default, or an explicit handoff point neither
role currently owns? Until that's decided, don't assume the other role has
it covered just because the onboarding checklist above lists both.

## M2 Development Path

For movement toward M2/DC:

- use defined M2/DC responsibilities as target responsibilities
- confirm the person's motivation and commitment
- develop on a real project, not only abstract training
- pass through DC training/assessment where required
- grow the project, show concrete actions that created expansion/value, and grow a replacement DC under control of the current DC/M2

## Common Anti-Patterns

- Overusing AI-generated abstract wording without concrete steps, owners, dates, acceptance criteria, or people.
- Listing QA responsibilities instead of unique project value.
- Writing only automation metrics when the project needs project/person/business metrics too.
- Treating “client wants quality” as business focus.
- Ignoring M2/M3/strategy-chat synchronization.
- Ignoring onboarding and project-start preparation.
- Ignoring the employee's own plan, motivation, and commitment.
- Reciting the presale-upsell service menu or generic industry benefit
  numbers as filler in a status/plan without a real diagnostic signal or
  conversation behind it (see `presale-upsell-rules.md`, Rule).
