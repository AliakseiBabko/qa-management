# M2 Metrics Calibration

Scope: How to read metrics as signals rather than verdicts, and template/schema consistency across every metric-shaped document.

## Metrics Are Signals, Not Verdicts

Metrics — Core or optional, project-level or individual — are diagnostic
signals for M2 review, 1:1s, retrospectives, and project-risk decisions.
They are inputs to a judgment M2 makes, not automatic performance
verdicts that read themselves. A number moving the wrong way is a prompt
to investigate (talk to the person, check project/system constraints,
look for a data-quality problem) before it becomes a conclusion about
anyone's performance or a project's health.

Do not add an optional metric to every project by default. Add one only
when the project already has a recurring data source for it and there is
a concrete management question it answers — never as a placeholder "in
case a tool gets set up later" (see Template Consistency below for how
this differs from a Core metric's blank-with-reason row, which always
exists regardless of data).

If data is missing, record the gap explicitly (what's missing and why)
instead of fabricating a value or estimating one without saying so. A
stated gap is a legible, useful fact; a guessed number is not.

See `references/qa-metrics-catalog.md` for the full tiered catalog (Core
project QA-process metrics, optional project/release quality metrics,
optional individual contribution metrics) built on this principle, and
`Templates\метрики_проекта_qa.md` / `Templates\метрики_qa_по_проекту.md`
for the schema-owning definitions each catalog tier links back to.

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
