# M2 Project Development Plan Schema

Scope: `project_development_plan` Doc purpose, template, expected output, versioning, and section skeleton.

Primary final output is a Google Doc in `20_M2_Project_Management\<Project>`,
with local Markdown fallback. This is a narrative document: one living Doc per
project, not a row per initiative.

## Purpose

Use this reference for the project-level development-plan document family.

## Template

`<repo-root>\Templates\план_развития_проекта.md`

Use this as the section skeleton for every project development plan. It was
derived from the real M2 homework corpus in `90_Storage\Reference\Source_Documents\M2_project_development_plan`
and the head of QA's recurring review comments on that homework (see
`plan-sources-normalization.md` for what those comments actually said).

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
  dated file for routine updates. "In place" means the same file/URL, not
  preserving whatever section structure the Doc currently happens to have —
  see the parallel note in `m2-individual-development-plan`'s
  document-contract for why this matters.
- Append source traceability to the project `evidence_log` Sheet.
- Create a separate dated snapshot only for a formal reporting event (e.g. a
  monthly business review) or when the user explicitly asks for one.
- `generate_m2_outputs.py` (see README, "legacy first-pass tools") produces
  this Doc's first-pass content via generic markdown extraction from the
  source docx, not this template — it has, in practice, come out readable
  because Docs preserve source prose better than the Sheet extraction path
  does, but verify a given project's Doc actually matches the Section
  Skeleton below before assuming it's compliant just because it looks like
  prose.

## Section Skeleton

Write the Doc as headed prose, in this order (full skeleton in the template
file above). Every section is always present, regardless of how much source
material exists for this project — never omit a section because there's no
evidence for it (see `m2-role/m2-metrics-calibration.md`, Template Consistency). If a
section has nothing to say yet, write that plainly as an open question
instead of inventing content or dropping the section.

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
5. **Возможности расширения (Upsell)** — a real expansion opportunity
   (more QA/AQA headcount, additional automation, specialized testing),
   built from an actual diagnostic signal or conversation, per
   `qa-management-roles/references/presale-upsell-rules.md` (situational —
   read only when filling/changing this section, see `SKILL.md`). If no signal
   exists this period, say so plainly ("Нет сигналов к расширению в этот
   период — <what would change that>") rather than omitting the section
   or padding it with generic service-menu language (see
   `plan-sources-normalization.md` and `presale-upsell-rules.md`'s own Rule).
6. **Успешность проекта за отчётный период** — judged against the client's
   business criteria (goals, revenue, retention, deadlines met), not against
   "we shipped a release."
7. **Текущее состояние** — current state, broken out by stream/initiative/
   workstream when the project has more than one, each as its own short
   paragraph or bullet, not repeated verbatim across later sections.
8. **План** — split into two groups instead of fixed 30/60/90-day horizons,
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
9. **Метрики** — one heading, not four. Split into categories as bold-labelled
   sub-bullets within this single section (`**Метрики бизнеса:** ...`), not as
   separate headings per category — a heading per category is visual noise
   when the whole section is really one list of 4-8 items. Categories:
   business metrics (revenue, retention, contract/tender value),
   product/project metrics (progress toward goals, release predictability),
   development metrics (when relevant), and quality metrics (defect leakage,
   escape rate, stability). This four-way split is the head of QA's own
   framework, spelled out explicitly in review comments on the homework.
10. **Риски проекта** — same rule: one heading, categories as bold-labelled
    sub-bullets, not separate headings. Split by perspective, not just "QA
    risk": business risk, project/product risk, development risk, QA/process
    risk (matches `../qa-management-roles/references/m2-role/m2-risk-rules.md` Risk
    Rules).
11. **Открытые вопросы** — missing information and questions that need a
    stakeholder's answer, if any. Name it for what it actually is (things we
    don't know or can't confirm yet), not "decisions."
12. **Источники** — optional. Do not list raw evidence paths (`raw/...`,
    `wiki/...`) — they are unreadable and add nothing for someone reading the
    plan; full traceability already lives in `evidence_log`. If a source
    pointer is worth including, write one short human-readable sentence (e.g.
    "Based on May 2026 1:1s and the metrics review"), or omit the section.

## Rule

Do not mix project-level and individual-level development plans in one
document unless the user explicitly asks for a combined document.
