# M2 Metrics Attribution

Scope: Which cascade layer a metric fact belongs to (automation, production bug leakage), contribution-level calibration, registry data-gap semantics, and multi-person metric ownership.

## Automation Metric Layering

Automation coverage percentage, automation framework/code-quality
assessment, pass rate, flaky-test status, and CI/CD state are project/team
QA-process metrics, not individual performance metrics — even when only one
QA engineer currently owns or maintains the framework. They describe the
project/team QA-process asset, not a personal performance metric for
whoever happens to maintain it.

A source that reports these facts updates the chain in this order:
`qa_process_metrics` first, then `project_metrics`, then `_project_registry`
— the same cascading discipline as any other change (see Cascading Updates
above), applied specifically to automation facts. `individual_metrics`
reflects only the person's contribution, ownership, or behavior around that
automation — owns the automation framework, contributes tests, improves
visibility/reporting, needs support to present automation progress, lacks
autonomy maintaining the framework — never the coverage number, the
framework/code-quality verdict, pass rate, flaky status, or CI/CD state
itself, even when that person is the framework's sole owner.

## Production Bug Leakage Attribution

Production bug leakage — defects found after release, in production, or by
users/client/business/product owner, as distinct from the "known open
bugs" current-defect snapshot — is a project/team QA-process metric,
tracked in `qa_process_metrics` and rolling up through `project_metrics`
(`Качество QA-процесса`) to `_project_registry`, the same as any other
Core `qa_process_metrics` metric.

Leakage is a strong QA-process signal, but it is not automatically personal
underperformance. Classify each finding where possible: QA leakage (should
reasonably have been caught), requirement/product gap, environment/data/
config issue, known accepted risk, or unclear/needs triage — only the
first of these is actually about QA's own catch rate. When an exact count
is unknown, record a qualitative value backed by evidence rather than
guessing a number: no data, no confirmed leakage, confirmed cases exist
but count unknown, or N confirmed cases.

**RCA (root cause analysis) is required before attributing a leaked defect
to a person** — not just "a source mentioned a name." Classifying a finding
as QA leakage specifically, and naming who is responsible for it, both
depend on having actually traced the defect back to its cause; without
that, the finding stays at "unclear/needs triage" or one of the other
non-personal categories above, not a personal attribution. Do not add a
leakage finding as an `individual_metrics` row by default — being the only
QA on a project is not the same as RCA-backed attribution. It becomes an
`individual_metrics` row (see `Templates\метрики_qa_по_проекту.md`,
"Prod leakage attributable after RCA") only when an RCA has actually been
done and it directly attributes responsibility to a named person with
evidence (a traceable claim — e.g. a DC/QA Lead naming who owned the
affected area/task after tracing the cause — not an assumption or
"someone on QA"), and even then `qa_process_metrics`/`project_metrics`/
`_project_registry` are updated first, same as any other source that
touches this metric.

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
