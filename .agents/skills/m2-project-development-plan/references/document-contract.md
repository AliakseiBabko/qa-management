# Document Contract

Primary final output is a Google Doc in `20_M2_Project_Management\<Project>`,
with local Markdown fallback. This is a narrative document: one living Doc per
project, not a row per initiative.

## Purpose

Use this reference for the project-level development-plan document family.

## Template

`<repo-root>\Templates\план_развития_проекта.md`

Use this as the section skeleton for every project development plan. It was
derived from the real M2 homework corpus in `00_Source_Docs\M2_project_development_plan`
and the head of QA's recurring review comments on that homework (see Normalization
below for what those comments actually said).

## Expected Output

One project-level development-plan Google Doc per project.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>`

Doc title (Drive file name): `project_development_plan`

Local Markdown fallback naming pattern (only when Google API access is
unavailable): `план_развития_проекта_<Project>_YYYY-MM-DD.md`

## Versioning

- Update the living `project_development_plan` Doc in place. Google Docs
  version history already preserves prior revisions, so do not create a new
  dated file for routine updates.
- Append source traceability to the project `evidence_log` Sheet.
- Create a separate dated snapshot only for a formal reporting event (e.g. a
  monthly business review) or when the user explicitly asks for one.

## Section Skeleton

Write the Doc as headed prose, in this order (full skeleton in the template
file above). Omit a section if there is no evidence for it rather than
inventing content, but say so as an open question instead of silently
dropping it.

1. **Title** — `<Project> — план развития проекта`, followed by a short
   metadata line (Обновлено / Review cycle / Следующий review).
2. **Бизнес-фокус и бизнес-флоу** — how the client's business actually makes
   money: who buys, why, what the revenue model is, current priorities. This
   is not a functional walkthrough or user-scenario description — that is the
   single most common mistake in the source homework, called out on nearly
   every submission.
3. **Ожидания клиента** — what the client wants for their own business on this
   project, tied to a real signal (a meeting, a sync, feedback), not a
   generic assumption like "wants fast, quality releases."
4. **Ценность нашей работы для бизнеса** — the value specifically attributable
   to QA/our team, not to the working product as a whole. Each point should
   answer: what would be worse without this work?
5. **Успешность проекта за отчётный период** — judged against the client's
   business criteria (goals, revenue, retention, deadlines met), not against
   "we shipped a release."
6. **Текущее состояние** — current state, broken out by stream/initiative/
   workstream when the project has more than one, each as its own short
   paragraph or bullet, not repeated verbatim across later sections.
7. **План** — split into two groups instead of fixed 30/60/90-day horizons,
   which create a false sense of long-range forecast under Agile, where
   sprints reshuffle priorities every 1-2 weeks:
   - **Ближайшие шаги** — tied to a specific date/sprint. Each item: action +
     Owner + date or "by end of sprint N" + success criterion, e.g. "Migrate
     10 test cases from Puppeteer to Playwright by end of sprint. Owner: X.
     Критерий: 10 cases pass on Playwright."
   - **Направления развития** — a goal we're moving toward with no date
     commitment. Each item: direction + Owner (if any) + how we'll know it's
     done, e.g. "Complete the Puppeteer-to-Playwright migration. Owner: X.
     Критерий: Puppeteer no longer used in the project."
8. **Метрики** — one heading, not four. Split into categories as bold-labelled
   sub-bullets within this single section (`**Метрики бизнеса:** ...`), not as
   separate headings per category — a heading per category is visual noise
   when the whole section is really one list of 4-8 items. Categories:
   business metrics (revenue, retention, contract/tender value),
   product/project metrics (progress toward goals, release predictability),
   development metrics (when relevant), and quality metrics (defect leakage,
   escape rate, stability). This four-way split is the head of QA's own
   framework, spelled out explicitly in review comments on the homework.
9. **Риски проекта** — same rule: one heading, categories as bold-labelled
   sub-bullets, not separate headings. Split by perspective, not just "QA
   risk": business risk, project/product risk, development risk, QA/process
   risk (matches `../qa-management-roles/references/m2-role-rules.md` Risk
   Rules).
10. **Открытые вопросы** — missing information and questions that need a
    stakeholder's answer, if any. Name it for what it actually is (things we
    don't know or can't confirm yet), not "decisions."
11. **Источники** — optional. Do not list raw evidence paths (`raw/...`,
    `wiki/...`) — they are unreadable and add nothing for someone reading the
    plan; full traceability already lives in `evidence_log`. If a source
    pointer is worth including, write one short human-readable sentence (e.g.
    "Based on May 2026 1:1s and the metrics review"), or omit the section.

## Source Priority

1. Existing project development plan.
2. `m2_input` — the latest round's answers. If the latest round's answer
   section is empty, this is a rollup and you must stop and run the
   preliminary-analysis round first (see `m2-role-rules.md`
   Project-Level Rollups) rather than proceeding on metrics alone.
3. Business/project context, client expectations, strategy-chat statuses, and
   project goals.
4. Project risk summary.
5. Project metrics, including the `Команда: ...` rollup rows and each
   person's `Вклад в проект`.
6. Workbook status/context rows.
7. Individual plans only when they reveal a project-level capability or
   continuity gap.

## Normalization

- State the executive summary and current-state context once; do not repeat
  it before every action item the way a spreadsheet row would require.
- Use exact review dates when provided by the source.
- Every initiative should answer: what project/business problem it solves,
  what value it brings, how success is measured, and where progress will be
  synchronized.
- Do not describe the project's business flow as a functional use-case
  ("user does X, then Y"). Business flow is how the product earns money: who
  buys, why, through what channel, what drives revenue.
- Do not attribute the whole product's value to QA. State the value that
  would specifically be missing without QA's work.
- Do not call the project "successful" because work shipped. State the
  business criteria the client cares about and whether they were met.
- Do not force every plan item into a fixed 30/60/90-day bucket. Split into
  date-bound near-term commitments and undated directional goals instead —
  matches how Agile teams actually plan.
- Include topology/context initiatives when needed for project control:
  clarify streams, real team size, DC/PM ownership, vendor/intermediary
  chain, client path, tender/contract horizon, security/location
  constraints, or feedback route.
- If the project needs better visibility before detailed improvement work is
  possible, write a visibility initiative with an owner, date, and expected
  artifact instead of inventing downstream actions.
- If QA value or project-side trust is under question, include an initiative
  that proves QA business value through metrics, accepted improvements,
  defect/risk prevention, or client/team feedback.
- Reviewer feedback belongs in native Google Docs comments tied to the
  relevant paragraph (mirroring how the original homework was reviewed
  documents in Word), not as an extra column or appended text block.

## Rule

Do not mix project-level and individual-level development plans in one
document unless the user explicitly asks for a combined document.
