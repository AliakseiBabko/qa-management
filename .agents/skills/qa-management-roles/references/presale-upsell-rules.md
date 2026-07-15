# Presale / Upsell Rules

Source: internal corporate Confluence articles on QA presale and account
expansion — "Продающий скрипт для AQA (AQA Sailing script)", "Шаблон
(план) пресейла для QA", "Upsale (допродажа) на текущих проектах —
Автоматизация", "Upsale (допродажа) на текущих проектах — Ручное
тестирование", "Стратегия расширения проектов через РС", "QA Services for
Upsales", "Универсальный промт для QA эстимаций с помощью ИИ".

M2's mandate is not only to protect and report on QA quality — it also
includes actively growing the company's footprint on each project by
identifying where additional QA/AQA services would help, and advocating
for them. This reference is what `m2-project-status-report` and
`m2-project-development-plan` draw on for their "Возможности расширения
(Upsell)" section, and what informs the "expansion opportunities" business
metric in `m2-role-rules.md`.

## Diagnostic Markers (Is There an Expansion Opportunity?)

Ask/observe these on every active project — any one of them is a signal
worth surfacing, not proof by itself:

- Do releases slip? Late-discovered defects and expensive late fixes are
  a common root cause.
- Are there defects in production? Direct signal of testing gaps.
- Does the team consistently finish the planned iteration scope, or not?
- Is there real regression testing coverage on the project at all?
- Is there a high volume of regression bugs (the "pesticide effect" —
  the same old tests miss new regressions as the codebase grows)?
- Is there any test automation on the project at all, and if so, does it
  cover more than a thin smoke layer?

Also worth asking the PM/team directly: Is there a QA on the project?
Is QA headcount sufficient? Is the project actively hiring QA? Are the
people on it contractors or internal staff? Is there any automation?

## Automation Readiness (When to Pitch AQA Specifically)

Automation is not always the right pitch — judge readiness against these
factors before proposing it (from the "AQA Sailing script"):

- **Project stage.** Not at project start (functionality too unstable,
  frequent rewrites, automation destabilizes release timelines) and not
  at a project's final/wind-down stage (manual regression is cheaper at
  that point). The right window is **active development**, once a piece
  of functionality has stabilized — bring automation engineers in 1-2
  weeks ahead of when they'd start writing tests, so they have time to
  set up framework/CI-CD infrastructure first.
- **Project duration.** Short projects rarely justify automation's setup
  cost — manual testing is usually more cost-effective there. Long-running
  projects benefit the most (regression surface and cross-module
  dependencies only grow over time). A short project **with a committed
  support phase afterward** is also a good case — automated coverage pays
  off directly for sustaining that support work.
- **Team size.** Small teams (1-2 teams of 8-10) rarely need automation
  unless the project is long-running — less new functionality means a
  smaller regression scope. Larger multi-team setups benefit more:
  automation removes cross-team end-to-end verification burden and
  supports cross-team QA process.
- **Regression volume.** The larger the regression suite, the stronger
  the case — manual regression cost scales with suite size; automation is
  what keeps that cost from growing unbounded.

## Upsell Problem/Benefit Framework

Use this to build a concrete, business-language pitch rather than a
generic "we should add QA/automation" statement. Two situations, each with
its own problem → consequence → benefit chain — pick the ones that
actually match observed evidence on the project, don't recite the whole
list:

### No/thin automation on the project
Common problems worth naming when observed: testing takes too long each
release; defects are found late and cost more to fix by then; regression
gaps let bugs slip into production; testing doesn't scale with project
growth (cross-browser/mobile coverage); manual-only testing costs more in
labor and team fatigue; no CI/CD integration means slow developer
feedback; backend/API logic goes untested if testing is UI-only. Each
maps to a concrete automation benefit (faster regression, earlier defect
detection, scalable parallel coverage, CI/CD feedback loop, API-level
coverage) — state the specific one that applies, with a rough impact
figure only when it's a genuinely defensible estimate, not a generic
industry number pasted in unchanged.

### Existing automation is limited
Problems worth naming: coverage doesn't reach new features/edge cases;
scripts aren't maintained and break on changes; tests run sequentially
with no parallelization; automation expertise is concentrated in 1-2
people with no backup; there's no test analytics/reporting; the test
pyramid is UI-heavy instead of pushing coverage down to unit/API level.

### No/thin manual QA on the project
Problems worth naming: negative/destructive/security/e2e scenarios go
uncovered; no regression testing at all; release cycles stretch out from
late-discovered issues; developers aren't thinking through edge cases
without QA input during analysis; no shift-left (requirements aren't
reviewed before development starts); developers get pulled off coding to
test their own work; planning becomes unreliable because of frequent
urgent fixes; no test documentation exists, which hurts onboarding; only
the dev environment gets tested. With a QA already on the project but
short-staffed: pesticide effect (same tests, no new scenarios), thin
documentation, no time to properly prepare test data/environments,
single-point-of-failure risk (no coverage during time off), no second set
of eyes on test plans/checklists.

### Specialized automation (beyond functional UI/API)
Load testing (JMeter/Gatling/k6) prevents crashes under peak traffic.
Performance testing (response time, memory, CPU) prevents slow-UX churn.
Security automation (OWASP ZAP, SonarQube-style static analysis) catches
vulnerabilities proactively. Mobile automation (Appium) covers
cross-device/OS compatibility that manual-only testing on 1-2 devices
misses.

## How to Promote (Internal Motion)

- Promote from **inside** the project, grounded in real pain the team is
  already feeling — not a cold pitch.
- Raise the problem and a proposed solution at daily/retro/grooming, with
  all real stakeholders present (dev, PM, client) when possible.
- Once there's genuine interest, propose a concrete next step. Example
  framing that's worked before: "I have hands-on experience setting up
  CI/CD automation on a similar project — I can build a quick POC and
  show the team how it would work here," or, for headcount: "I know a QA
  engineer I've worked with before who's available right now and could
  strengthen this team."
- A pilot/trial period is a strong additional lever: propose ~1 month of
  trial work (free or low-cost) arranged through Sales — this is exactly
  the shape of the "Демо версия процессов QA и архитектуры автоматизации"
  package below.
- Escalate to **Head of QA** or the current presale-team lead for support
  building the actual expansion strategy/pitch — this repository does not
  replace that conversation, it prepares the evidence for it. Look up who
  currently holds the presale-lead role in `_people_registry` (`Role` =
  `Presale Lead`) rather than naming a specific person here — this
  repository holds skill logic and templates only; who's who is company
  data that lives in `_people_registry` on the corporate Google Drive,
  not in this public repo, and role holders change over time regardless.

## Business-Language Arguments

Frame the pitch in terms the client's business cares about, not QA
process purity:

- The cost of a defect found late grows multiplicatively — each
  subsequent development phase adds changes on top, making root-cause
  analysis and the eventual fix progressively more expensive.
- Poor quality slows and inflates the cost of development itself: bug
  backlogs force constant context-switching, and change-impact analysis
  gets harder as defects accumulate.
- A low-quality product is worth measurably less to the end user than one
  where core tasks work smoothly and predictably.
- Testing work happens regardless of whether a dedicated QA does it —
  when it's absorbed by developers, PMs, or BAs instead, it's done by
  more expensive, less specialized resources than a QA would be.

## Productized Upsell Services (Menu)

From "QA Services for Upsales" — a concrete service catalog to draw
specific pitches from, each with an approximate timeline and client
value. Use these as the specific ask when a diagnostic marker/problem
above has been confirmed on a real project — don't propose the whole menu
at once.

1. **Test-case writing** (smoke + critical path) — 3-7 days depending on
   product size. Value: reusable test documentation, fewer early-stage
   bugs, foundation for later automation.
2. **Smoke / critical-path test execution** — 2-5 days per cycle. Value:
   fast release validation, surfaces automation candidates.
3. **UI test automation** (Cypress/Playwright for web, Appium for
   mobile) — up to 2 weeks for ~100 tests baseline coverage. Value:
   automatic regression, time savings on repeat testing.
4. **API test automation** (from Swagger/OpenAPI/Postman, up to ~50
   endpoints) — 1-2 weeks. Value: backend stability, faster integration
   error detection, CI/CD-ready reporting.
5. **CI/CD integration of automated tests** — 1-2 days on top of existing
   automation. Value: continuous testing, faster releases, less manual
   effort.

Optional add-ons on request: accessibility testing (WCAG, Axe/WAVE scans
+ manual smoke, 3-7 days) and basic security testing (OWASP Top 10, ZAP/
Burp scans + manual critical-path checks, 5-10 days).

**Demo package** ("Демо версия процессов QA и архитектуры
автоматизации"): 2-3 weeks of a QA engineer free of charge, covering
smoke/critical-path test cases and execution, automation framework/CI-CD
setup, and smoke/critical-path automated coverage, ending in a team demo.
The client then decides whether to continue (QA moves to paid) or not
(QA rolls off, all work product stays with the project either way). This
is the concrete version of the "pilot period" lever above — use it as the
default low-friction ask when a client is receptive but not yet ready to
commit budget.

## Estimation Support

For sizing a concrete upsell proposal's effort (a WBS-based QA-hours
estimate), there is a standing AI prompt ("QA Master-Prompt") maintained
internally for this — it walks through strategy
selection (Lean/Standard/Complex), applies fixed constants (Standard QA
~30% of dev hours, Security ~120h full OWASP WSTG cycle, Performance
56-320h by project size, localization +15-20% per language, etc.), and
outputs a fully itemized WBS with assumptions/risks. Locate the current
prompt version in Confluence rather than treating this summary as the
prompt itself — the actual tool is iterated on independently of this
repository. **Before using it, anonymize any client documents fed into
it** — strip proper names and identifying details first; this is the
same evidence-handling discipline this repository already applies
elsewhere (do not paste sensitive client/personal data into an external
AI tool unscrubbed).

## Rule

Section content built from this reference is a genuine opportunity
assessment, not a sales-speak filler paragraph. Every upsell mention in a
status report or development plan must trace to an actual diagnostic
signal or a real conversation already had — do not manufacture an
expansion narrative on a project with no supporting evidence, and say so
plainly ("no expansion signal observed this period") when that's the
honest read.
