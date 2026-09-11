# M2 Project Development Plan Schema

Scope: `project_development_plan` Doc purpose, audience and register, the inference requirement, template, expected output, versioning, and section skeleton.

Primary final output is a Google Doc in `20_M2_Project_Management\<Project>`,
with local Markdown fallback. This is a narrative document: one living Doc per
project, not a row per initiative.

## Purpose

Use this reference for the project-level development-plan document family.

## Audience And Register

**This is a finished document written for management above M2** — the head
of QA, the delivery director, whoever reviews the project at that level.
Write it so it stands on its own for a reader who has no access to the M2
workspace, has never seen a previous version, and will not go looking
anywhere else. Everything below follows from that one fact.

- **No pointers to other internal artifacts.** Never write `(см.
  action_items)`, `(см. evidence_log)`, `(см. m2_input, раунд ...)`, `(см.
  individual_metrics Арины)`, a `30_Project_Knowledge/...` path, a chat
  export filename, or a transcript date used as a citation. The reader
  cannot open any of those. If a fact from one of them matters, state the
  fact in the reader's own terms; if it does not matter enough to state,
  leave it out. Full traceability already lives in `evidence_log`, which
  exists precisely so this document does not have to carry it.
- **No `Источники` section.** Removed from the skeleton entirely (was an
  optional §12 until 2026-09-07). Even the sanctioned one-line form ("По
  итогам 1:1 с командой и обзора метрик") told an M3 reader nothing they
  could act on and invited the raw-path version to creep back.
- **No edit-history narration.** The document states the current
  understanding as of its `Обновлено` date, in the present tense. It never
  narrates its own revisions: no "исправлено по чату X", no "ранее ошибочно
  записано здесь", no "устаревшая характеристика заменена этим
  обновлением", no "пропущено в предыдущем проходе", no "нуждается в
  переподтверждении". That commentary is addressed to whoever maintains the
  document, not to whoever reads it. Docs version history holds the
  revisions; `evidence_log` holds the correction trail.
- **No appended dated update blocks.** Every update replaces the content of
  the section it affects. Bolting a new "Update YYYY-MM-DD" block onto the
  end leaves the reader with two contradicting accounts and no way to tell
  which one is current.
- **No evidence-status vocabulary in prose.** `observed` / `estimated` /
  `Data Confidence` are `project_metrics` column values. In a narrative
  document, express the same uncertainty in plain language.

## Silence Is Not An Empty Section

A section is **never** satisfied by "Открытый вопрос: в источниках нет
данных". The client on most projects is quiet, gives little direct
feedback, and never states a business objective outright — that is the
normal case, not a blocked one, and a plan that goes blank whenever the
client is silent is a plan that is blank most of the time. Every section
carries M2's best current read.

- **Infer from indirect signal.** What the client funds and staffs, who
  they hire and where, what they escalate versus quietly accept, which of
  their products get QA and which get none, the contract or tender horizon,
  the constraints they impose (location, security, vendor chain), what they
  ask us to prove, the shape of their own roadmap in the tickets, and the
  codebase itself are all evidence of what the client expects. Read them.
- **Mark an inference as one, once, in place**: append `(гипотеза M2)` to
  the claim — the same wording `_project_registry`'s client-goal column
  already uses — and follow it with the one thing that would confirm or
  refute it. Do not hedge every sentence; mark the judgment, then write
  plainly.
- **Name the signal in the same sentence.** An inference that does not say
  what it rests on is indistinguishable from an invention. "Клиент
  оптимизирует стоимость, а не скорость (гипотеза M2): ограничил поиск
  кандидатов Польшей и отклонил более дорогих" is a hypothesis; "клиент,
  вероятно, хочет качества" is not.
- **Do not overreach either.** Missing a hypothesis is a failure; a
  confident-sounding invented one is a worse failure, because it survives
  into decisions unchallenged. Confidence must match the signal.
- **What genuinely cannot be inferred** becomes one line in `Открытые
  вопросы` — a question addressed to a named person — not the body of a
  section.

## Synthesis, Not A Fact Inventory

This document sits at the end of the pipeline, not the start. The facts
have already been recorded upstream: in 1:1 records, meeting and strategy
transcripts, `evidence_log`, `project_metrics`. What this document adds is
the reading of them.

- **The test:** if a sentence could be moved into a 1:1 record or a
  transcript summary without losing anything, it belongs there, not here.
  A dated event with no consequence attached is such a sentence.
- Numbers appear in service of a judgment, not as an inventory — one or two
  per point, chosen because they carry the argument.
- Every `Текущее состояние` item ends in a consequence for the project, not
  in a state. "Единственный QA на проекте" is a fact; "единственный QA на
  проекте, поэтому любой её выход останавливает и ручное тестирование, и
  automation" is the plan's content.

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
evidence for it (see `m2-role/m2-metrics-calibration.md`, Template Consistency).
A section with no direct client statement behind it is still written: give
M2's inferred read of it, marked `(гипотеза M2)`, per "Silence Is Not An
Empty Section" above. Only what genuinely cannot be inferred at all becomes
a line in `Открытые вопросы` — never a section body reading "нет данных".

1. **Title** — `<Project> — план развития проекта`, followed by a short
   metadata line (Обновлено / Review cycle / Следующий review). Refresh both
   dates on every update, and check that `Следующий review` is later than
   `Обновлено` — a next-review date in the past is the first thing an M3
   reader notices, and it discredits everything under it.
2. **Бизнес-фокус и бизнес-флоу** — how the client's business actually makes
   money: who buys, why, what the revenue model is, current priorities. This
   is not a functional walkthrough or user-scenario description — that is the
   single most common mistake in the source homework, called out on nearly
   every submission.
3. **Ожидания клиента** — what the client wants for their own business on
   this project. A directly stated expectation is written as fact. Where the
   client has never stated one — the usual case — infer it from what they
   fund, staff, escalate, constrain, and ignore, mark it `(гипотеза M2)`, and
   say what would confirm it. "Клиент молчит" is not an acceptable body for
   this section, and neither is a generic assumption like "wants fast,
   quality releases."
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
   "we shipped a release." Where those criteria were never stated, judge
   against M2's inferred version of them and mark it `(гипотеза M2)` — the
   absence of a client scorecard does not excuse the section from reaching
   a verdict.
7. **Текущее состояние** — current state, broken out by stream/initiative/
   workstream when the project has more than one, each as its own short
   paragraph or bullet, not repeated verbatim across later sections. Each
   item ends in a consequence for the project, not in a state — see
   "Synthesis, Not A Fact Inventory" above.
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

There is no `Источники` section. It was §12 until 2026-09-07 and is now
prohibited outright — see "Audience And Register" above.

## Rule

Do not mix project-level and individual-level development plans in one
document unless the user explicitly asks for a combined document.
