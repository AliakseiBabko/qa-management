# M2 Role Rules

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

## Metric Rules

Use a small balanced metric set. Cover different perspectives:

- quality metrics: defects, escaped defects, severity, regression, automation stability
- project/product metrics: releases, delivered features, missed scope, blocker age, documentation/readiness, project goal progress
- business metrics: revenue, paid users, conversion, retention, market/region coverage, cost reduction, support cost, client satisfaction, expansion opportunities (see `presale-upsell-rules.md` for what a real expansion opportunity looks like — an evidenced diagnostic signal, not a generic aspiration)
- development metrics: throughput, cycle time, feature quality, rework, story points when available
- our-work metrics: QA performance, visibility, accepted suggestions, project role growth, client/team trust

Every metric must be:

- measurable on a recurring basis
- linked to a question it answers
- useful for decision-making
- tied to evidence or explicitly marked as missing

Avoid abstract goals as metrics. Convert goals into observable indicators.

Connect project metrics with individual QA metrics when individual signals materially affect the project picture: capacity, coverage, QA cycle time, defect quality, escaped defects, automation contribution, stakeholder visibility, accepted improvements, blockers, overload, or continuity risk. Keep the boundary clear: individual QA metrics explain contribution and constraints; project metrics aggregate what those signals mean for project quality, speed, predictability, client/team trust, and business value.

Do not mechanically compare people unless their context is comparable. Different streams, seniority, scope, access, deadlines, project process maturity, and role expectations can make raw person-to-person metrics misleading. Separate personal performance from project/system constraints.

Validate metric fit before using standard delivery metrics. Closed tasks, moved tasks, story points, or sprint throughput are weak primary metrics when scope changes constantly, task size is not comparable, estimates are abstract, or there is no stable release cadence. In that case, choose metrics that explain the real management question: QA value, risk reduction, client trust, blocker discovery, escaped defects, process maturity, automation usefulness, or project visibility.

## Template Consistency

`individual_metrics`, `individual_development_plan`, `project_metrics`,
`qa_process_metrics`, `project_development_plan`, `project_risk`, and every
other document with a defined section/row skeleton use the **same
structure every time**, regardless of how much data exists for a given
person or project. This is what makes people and projects comparable and
what makes a blank field mean something (a real, checkable gap) instead of
looking like an oversight.

Concretely:

- Never omit a Core metric row, a template section, or a schema column by
  judgment because "there's no data for it" or "it doesn't look
  collectible on this project." Include it. Leave the value cell blank and
  say why in the row's own explanation field (`Пояснение` for
  `individual_metrics`/`qa_process_metrics`, the section's own text for a
  Doc). "Нет данных — <short reason, and what would close the gap>" is a
  complete, correct entry. An empty explanation next to a blank value is
  not — the reason is what makes the blank legible instead of looking like
  a bug.
- This applies exactly the same whether a person has rich source material
  or almost none. A person with an empty predecessor document still gets
  every section of `individual_development_plan` and every Core metric row
  of `individual_metrics` — each one blank, each one with its own reason
  stated, not a single placeholder line replacing the whole document.
- The one exception is metrics the catalog explicitly excludes as
  unmeasurable (see `m2-individual-qa-metrics-report`/
  `m2-project-qa-metrics-report` document-contracts) — those never become
  rows at all, missing data or not. That's a different rule (the metric
  itself is invalid) from a Core metric that's simply not collected yet on
  this project or for this person.
- If revisiting a document and a metric/section was left out entirely
  rather than included-blank-with-reason, that's a defect to fix the next
  time the document is touched, not a valid alternate style.
- A document-contract's Section Skeleton is the source of truth, not
  whatever an existing Doc/Sheet already contains — contracts get written
  or tightened after documents already exist, and a document predating a
  contract update is not evidence the contract doesn't apply to it. Before
  editing any `individual_metrics`/`individual_development_plan`/
  `project_metrics`/`qa_process_metrics`/`project_development_plan`/
  `project_risk` instance, check it against the current skeleton in its
  document-contract rather than assuming its existing structure is already
  correct just because nothing flagged it yet.
- When a document for one project/person is found to violate its
  template, check every other project's or person's instance of that same
  document type before considering the fix done. A structural defect this
  systemic (wrong section shape, wrong metric set, mechanically-extracted
  content) almost never affects only the one instance that happened to get
  reviewed — it traces back to how the whole set was first generated, so
  the other instances are likely broken the same way even though nobody
  has looked at them yet.

If metrics cannot be collected during active risk mitigation, overload, onboarding, or project instability, document why, set a review date, and treat prolonged absence of metrics as an M2 management risk.

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

## Project-Level Rollups

`project_development_plan` and `project_risk` get updated by rolling up
every person's individual plan, individual metrics, and their `Вклад в
проект: <Имя>` conclusion from `project_metrics` — but that rollup
should never run purely mechanically. Metrics and per-person plans don't
carry the manager's own judgment (why a risk matters more or less than the
numbers suggest, context that isn't in any metric, how to weigh one
person's read of the project against another's). `m2_input` (see
Templates\m2_input.md) is the explicit place for that judgment, and the
rollup is a two-phase process built around it:

1. **Preliminary analysis round.** Before combining anything, review every
   person's individual plan and metrics on the project, and write down
   specific, answerable questions — gaps in data, contradictions between
   people's signals, risks visible in the metrics but with no clear owner,
   what to do about someone whose Core metrics aren't collectible yet.
   Append a new dated round to the project's `m2_input` Doc with these
   questions; leave "Ответ и общие соображения M2" empty.
2. **Wait for M2's answer.** Do not proceed to the rollup until the latest
   round's answer section is filled in. An empty answer section means the
   rollup for that round cannot happen yet — that's a stop condition, not
   something to route around by falling back to metrics alone.
3. **Rollup round.** Once answered, combine individual plans/metrics with
   that round's answers as an explicit input — on par with the metrics
   themselves, not a tie-breaker used only when metrics disagree — into the
   updated `project_development_plan` and `project_risk`.

`m2_input` is one living Doc per project, not a new file per cycle. Each
round is a new dated section appended to the same Doc; do not delete or
archive prior rounds — the visible history of questions and answers across
cycles is itself useful context for the next round, and Google Docs version
history is a backstop, not a substitute for keeping rounds visible in the
document.

A round left unanswered while new addenda keep stacking on top of it is
itself a signal, not just a growing backlog — `project_risk`/
`project_development_plan` stay frozen behind the gate the whole time,
even as real new evidence piles up unrolled-up. When appending an addendum
to an already-pending round, check how old the round is and how many
addenda it already has; if it's been open for multiple weeks or has
several addenda, say so explicitly to the user when you finish (e.g. "this
round has been open since <date> with N addenda — the rollup has been
frozen that whole time") rather than silently adding addendum N+1 as if
nothing's unusual. This doesn't mean answering it on the user's behalf —
it means surfacing the staleness so the user can decide to actually close
it out.

## Cascading Updates

The chain is `individual_metrics`/`individual_development_plan` (per
person) → `project_metrics` (per project, M2's full-picture dashboard) →
`_project_registry` (across every project M2 owns, the "war room" view).
When a new source (a chat, a transcript, a document dropped in
`00_Source_Docs`, direct M2 input) changes something at the
person level, update the whole chain in the same pass — not just the
bottom layer:

1. Update the person's `individual_metrics` row(s) and
   `individual_development_plan` sections that the source actually
   supports.
2. Refresh the corresponding rows in that project's `project_metrics` —
   the `Вклад в проект: <Имя>` conclusion (and the aggregated team row, if
   the project has more than one person), and `Горизонт совместной
   работы` / `Бизнес-риск продукта клиента` / `Качество QA-процесса` if
   the source touched any of those.
3. Refresh that project's row in `_project_registry` to match.

Leaving `project_metrics` or `_project_registry` stale after an
`individual_metrics` update defeats the point of the dashboard — it's
supposed to be the one place to see the full picture, not one of several
places that might be out of date.

This fan-out (and the M1 chain) is encoded as data in
`.agents/document_graph.yaml`; `.agents/scripts/check_cascade_closure.py`
expands it into a checklist and flags downstream documents not yet
accounted for. Run it at the end of any pass that touched these documents
instead of re-deriving the chain from this prose — and keep the graph file
in sync when a new document type or dependency is introduced (same commit
as the skill that adds it). The script only computes *which* documents to
visit; whether each one changes, and what to write, remains this file's
judgment rules.

## Вклад в проект Calibration

Don't default to Смешанный as a safe middle answer when the evidence is
actually clear. Four things commonly get mistaken for mixed personal
contribution and should not pull the status down on their own:

- **A data-completeness gap** — reporting/export not wired up yet (metrics
  not pulled from Allure/CI/Jira, no per-tenant split, etc.). This is
  missing evidence, not negative evidence. If the evidence that does exist
  is positive, the status is Позитивный with the gap noted as a follow-up
  action, not Смешанный.
- **A staffing/capacity risk** — overload, competing priorities, a
  sustainability concern. This belongs in `project_risk` or as a flagged
  risk item, not folded into the contribution judgment; someone can be a
  strong contributor and still be at risk of burnout.
- **A project/process-maturity gap** — no formal DoR/DoD, no TMS decision,
  no CI pipeline. These are usually project/PM-level decisions, not one
  person's shortfall (see Risk Rules above on separating individual
  performance risk from project/stake risk).
- **A client-driven scope-vs-track mismatch** — someone staffed for an
  anticipated scope (most commonly: an AQA engineer staffed expecting an
  automation scope from the client) who ends up executing a different
  scope by necessity because that scope never materialized. Clients often
  promise automation work that depends on their own timeline/priorities;
  staffing an AQA against that expectation is a calculated bet, and if it
  doesn't pay off, the person's actual on-project work (frequently manual)
  is not a personal shortfall, a track misassignment, or evidence they're
  underperforming against their real role. This belongs in `project_risk`
  as a staffing risk (with a periodic review point for whether the scope
  still might materialize), not folded into their contribution judgment —
  grade-fit should be assessed against the scope they're actually assigned,
  not the scope that was hoped for. Real example pattern seen on this
  team: someone staffed as AQA Engineer (confirmed via HRM) ends up
  executing fully manual/negative-testing scope because the client's
  promised automation scope hasn't materialized.
- **An assessed-level-vs-confirmed-level mismatch** — a sibling of the above,
  but about seniority rather than track: `individual_metrics`/
  `individual_development_plan` prose assessing someone against a Middle or
  Senior bar (autonomy, ownership of process decisions, leading without
  supervision) when their actual confirmed `Prof.Level` (via HRM/person
  card) is lower. This produces the same failure shape as the track
  mismatch — a "gap" that's really the project expecting more seniority
  than was ever staffed, not the person falling short of their own real
  level. When a person card reveals this, don't silently lower the bar
  yourself — flag it as a question (does the project genuinely need that
  level of ownership from this seat, and if so is that a staffing gap to
  fix, not a performance gap to coach) rather than assuming either side is
  right. Real example pattern seen on this team: someone assessed against
  a Middle bar with a confirmed Prof.Level of Junior, or assessed against
  Senior-level QA Lead autonomy with a confirmed Prof.Level of Middle.

Only mark Смешанный or Негативный when the negative signal is actually
about that person specifically — inconsistent delivery, disengagement,
declining trend, feedback problems tied to their own work. When in doubt,
write out the positive evidence and the caveat separately in `Пояснение`
and let the reader see both, rather than compressing them into a single
hedged label.

## Registry Data-Gap Semantics

`Наименьший вклад в проект` in `_project_registry` can hold two different
kinds of signal, and they must not be written as if they were the same
thing:

- an actual worst-known judgment (Негативный/Смешанный/Позитивный) — a
  real read of that person's contribution, backed by curated
  `individual_metrics`.
- `Неизвестно` — no judgment exists yet because the underlying
  `individual_metrics` for that person is missing or uncurated. This is a
  data gap, not a performance signal, and must never be treated as
  equivalent to a Негативный finding.

When a project has both — some people with a real judgment and others with
no data — report the worst *known* judgment plus its name(s), and name the
people with no data separately in the same cell rather than folding them
into the worst-case label (for example: `Смешанный (Имя А) — данных нет по
Имени Б и Имени В`). A row that is `Неизвестно` for every person on the
project is itself worth surfacing as a staffing-data risk, not left to
read as "nothing to report."

## Owner Selection for Multi-Person qa_process_metrics

`qa_process_metrics` needs one named `Owner` per row, not a generic QA
team label (see `Templates/метрики_проекта_qa.md` §2). On a single-person
project the owner is that person. On a multi-person project, pick whoever
has the clearest ownership signal for QA-process facts specifically —
release/automation/pipeline ownership evidence in their `individual_metrics`
or mentions in `project_risk`, not seniority or tenure alone. If no one
person has that kind of evidence, say so explicitly and name the metric
as needing an owner to be assigned, rather than guessing or defaulting to
whoever is listed first.

## Development Plans

Project plans must answer:

- what the project is trying to achieve
- why this matters to the client business
- what problems or risks block the outcome
- what we will do
- who owns it
- how success will be measured
- how and where progress will be communicated

Individual project-context plans must answer:

- what the project needs from this person
- what role/value this person should grow into on the project
- what authority, responsibility, client/team visibility, or trust should increase
- what concrete actions will create that role growth
- how progress will be measured
- how M2 will support, check, and escalate

Role growth is not just “do tasks better.” Role growth means increased value, authority, responsibility, visibility, dependency, or trust on the project, such as lead/DC movement, client entry point, ownership of module/process, accepted process proposals, or expansion-driving work.

## Risk Rules

Classify risks by perspective:

- business risks
- project/product risks
- development risks
- QA/process risks
- staffing/continuity risks
- our-role risks

For each risk, state:

- what can happen
- why it matters
- impact on business/project/role
- early signals
- mitigation/action
- owner

Do not list current problems as risks without stating what future harm they can cause.

Do not conflate "at least one named risk is serious" with "the project's
overall risk level is high." Individual risks can and should be classified
by severity on their own (see `m2-project-risk-report` document-contract for
the full definition) — but the project-wide level is a separate, stricter
judgment about whether something concretely threatens the engagement's
continuation or trust right now, not a maximum over the individual items.
Nearly every active project has at least one serious individual risk;
treating that as sufficient for a high overall level makes most projects
read as high-risk and defeats the point of having the field.

Assess evidence strength for feedback and risk signals. Mark whether feedback is direct client feedback, intermediary feedback, DC/QA Lead feedback, team feedback, or employee self-report. Multi-hop or indirect feedback can still be useful, but it lowers confidence and should be named in the evidence.

A source's category (DC/QA Lead, self-report, etc.) sets a baseline
confidence, but it is not the whole picture — weigh it further by the
source's position/seniority/domain expertise relative to the *specific
claim*, and by whether their incentives align with an accurate answer or
push them toward a distorted one. A senior DC/QA Lead's concrete, checkable
technical assessment (e.g. a specific code-quality or comprehension gap)
carries real weight, particularly when they have no incentive to make the
project look worse than it is. A newcomer's self-report on their own
performance — especially on their first commercial project — should be
read through the onboarding-fragility lens (`newcomer-support-rules.md`),
not treated as an equally authoritative counter-claim just because it
disagrees with someone more senior.

Do not let a reliability concern on one axis discount a source's claims on
an unrelated axis. Whether someone is honest/consistent in what they tell
a person directly versus what they say about that person to a third party
(a communication/diplomacy axis) is a different question from whether
their technical assessment of that person's work is accurate (a
judgment/expertise axis). A source shown to be inconsistent on the first
does not become unreliable on the second — name which axis is actually in
question rather than applying a blanket "this source is unreliable" label
to everything they say. Independent verification (code review, direct
metrics) is still the right closing step for any single-source claim
regardless of how credible the source already is — not because the source
is under suspicion, but because that is the standard bar before this
document treats a conclusion as settled.

The premise "a source shown to be inconsistent" needs the same evidence bar
as any other claim before it gets asserted — do not skip that step just
because the claim is *about* reliability rather than about a technical
fact. A report that "X said one thing to me and something different to
someone else" is very often just one party's own interpretation of an
ambiguous exchange — different phrasing of the question, timing, tone, or
a simple account relayed secondhand through a third party — not a
transcript-confirmed contradiction. Without the actual transcript or
direct corroboration from both sides, do not write it up as an
established fact about that person's reliability, and do not let it anchor
an ongoing characterization in later documents ("already showed himself
unreliable"). Two people holding conflicting impressions of the same
interaction is the normal case, not evidence one of them is lying — record
it, if at all, as an unverified single-party account, not a settled
judgment about the source.

Treat hidden or unclear project topology as a risk signal: unknown streams, unknown DC/PM ownership, unclear vendor chain, missing client path, or incomplete staffing visibility can cause wrong escalations, duplicated communication, missed stakeholders, or loss of project scope.

Separate individual performance risk from project/stake risk. A person may perform well while the project is still high risk because of vendor-chain issues, client dissatisfaction, role value doubts, weak processes, or contract horizon.

The reverse also happens: sometimes an individual's own performance/position genuinely is the primary driver of a project risk (e.g. a client explicitly requests a more experienced replacement, reinforced by real performance history). When that's the case, say so directly and put it first in the risk narrative — do not default to splitting it into parallel, co-equal sub-risks (like "continuity risk" vs. "process maturity risk") just to keep individual and project risk visually separate. Secondary/background factors (process immaturity, documentation gaps) still belong in the writeup, but as subordinate to the actual primary cause, not sitting next to it as an alternative explanation.

## Communication and Visibility

M2 must make project work visible:

- strategy-chat status updates
- explicit escalation process and red buttons
- project/team sync cadence
- 1to1 project syncs where the employee opens the project, boards, tasks, bugs, comments, and reports
- periodic presentation of metrics, risks, plans, and accepted improvements

If a plan does not say how it will be synchronized and demonstrated, it is incomplete.

Before sending risk, metrics, or status artifacts to a project-side audience, make the M2 role explicit: support project visibility, value growth, staffing quality, and risk prevention. Avoid creating the impression that M2 is auditing the DC/PM or trying to replace project ownership.

On outsource projects specifically, QA should escalate to M2 when: a blocker can't be resolved inside the team, requirements/process are unclear, a timeline/quality risk is emerging, a conflict needs resolving, or a deviation from the standard process checklist needs sign-off (see `m2-project-process-checklist`'s `references/outsource-operating-principles.md` for the full list and the "M2 is support, not an auditor" framing this reinforces).

Coordinate status routing with DC/PM. If DC already owns strategy status, align wording and route through DC when appropriate; if DC does not provide visibility, M2 may post directly with clear ownership and next actions.

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
