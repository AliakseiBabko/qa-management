# Document Contract

Primary final output is a Google Doc in
`20_M2_Project_Management\<Project>\people\<Person>\shared`, with local Markdown
fallback. This is a narrative document: one living Doc per person, not a row
per focus area.

This Doc and `individual_metrics` are two halves of one whole: the Sheet
holds only values and a short explanation of each; this Doc carries
everything else — why a metric matters, what's missing from it, what's
actually going on, and what to do about it. Never duplicate metric values
here — link to the Sheet instead.

## Purpose

Use this reference for the individual development-plan document family.

## Template

`<repo-root>\Templates\план_развития_qa_по_проекту.md`

Use this as the section skeleton for every individual development plan. It
was derived from the real M2 homework corpus in
`30_Reference\Source_Documents\M2_personal_development_plan` and the head of QA's recurring
review comments on that homework.

## Expected Output

One individual development-plan Google Doc per person, inside their project
scope.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\people\<Person>\shared`

Doc title (Drive file name): `individual_development_plan`

Local Markdown fallback naming pattern (only when Google API access is
unavailable): `план_развития_qa_<Project>_<Person>_YYYY-MM-DD.md`

## Versioning

- Update the living `individual_development_plan` Doc in place. Google Docs
  version history already preserves prior revisions, so do not create a new
  dated file for routine updates. "In place" means the same file/URL, not
  preserving whatever section structure the Doc currently happens to have.
- "In place" means **merge new findings into the existing content**, never
  wholesale-regenerate the Doc from only the newest source. A real case:
  rewriting a Doc from a single new 1:1 transcript silently dropped
  still-valid facts from an earlier cycle (specific sprint metrics, a
  named process gap) that the new transcript simply didn't happen to
  repeat. Before writing, read the current Doc in full and carry forward
  every fact that's still true, updating or removing only what the new
  source actually supersedes.
- Append source traceability to the project `evidence_log` Sheet.
- Create a separate dated snapshot only for a formal reporting event or when
  the user explicitly asks for one.
- If an existing Doc predates this template — most commonly because it was
  carried over near-verbatim from the person's own source docx during first
  intake, using that document's own headers (e.g. "Цель на ближайшие 90
  дней" / "Источники" / "Поддержка от менеджера" as separate top-level
  sections) instead of the Section Skeleton below — migrate it to the
  current structure the next time it's substantively touched. Don't just
  append new facts under the old headers.

## Scope

- one QA engineer
- inside one project or project-set context

## Section Skeleton

Write the Doc as headed prose, in this order (full skeleton in the template
file above). Every section is always present, for every person, regardless
of how much source material exists — never omit a section because there's
no evidence for it (see `m2-role-rules.md`, Template Consistency). If a
section has nothing to say yet, write that plainly ("Неизвестно — <what's
missing and what would close the gap>") instead of inventing content or
dropping the section.

1. **Title** — `<Person> — план развития (<Project>)`, followed by a short
   metadata line (Stream/role, Обновлено, Review cycle, Следующий review).
2. **Роль на проекте** — who this person is, what they actually do, and what
   is expected of them. This is the role description and the expectations
   combined — not a skills résumé and not a separate "context" section.
3. **Метрики** — a hyperlink to the person's `individual_metrics` Sheet, plus
   prose covering what the Sheet itself cannot: which core metrics are
   missing and why, how the ones that exist get collected, and why a metric
   was substituted or adjusted for this project if it was. Never restate the
   Sheet's actual values here.
4. **Текущее состояние** — a short narrative of how things actually stand
   right now, informed by the metrics but not a row-by-row recap of them.
5. **Фокус развития** — the specific growth areas. Each item must
   answer **how it grows the role**: influence, responsibility, trust,
   visibility to the client/team, the project's dependency on this person.
   Do not state a focus item as a bare task list — that is the single most
   common gap across the source homework, called out on almost every
   submission ("as всё это развивает роль?").
6. **План действий** — split into two groups instead of fixed calendar
   horizons (2 weeks / 1 month / 30/60/90 days), which create a false sense of
   long-range forecast under Agile:
   - **Ближайшие шаги** — tied to a specific date/sprint. Each item: action +
     date or "by end of sprint" + success criterion.
   - **Направления развития** — a goal we're moving toward with no date
     commitment, plus how we'll know it's done.
`Источники` is deliberately not a section here. A bare list of 1:1 dates
tells the reader nothing; that traceability belongs in `evidence_log`, not
in a document meant to be read.

`Поддержка менеджера` / `Красные флаги / эскалация` are deliberately not
per-person sections. How M2 supports and escalates for key engineers is a
project-wide policy, not something that varies document to document — do
not reintroduce it here even if it seems relevant for a specific person.

`Вклад в проект` is deliberately **not** a section here — this document is
visible to the employee it's about, and that conclusion is M2's own
private judgment, not something meant to be shown to the person directly.
It lives as a per-person row (`Вклад в проект: <Имя>`) in `project_metrics`
(see
`Templates\метрики_проекта_qa.md` §2.3) — same three statuses (Позитивный/
Смешанный/Негативный), same reuse into `project_development_plan`/
`project_risk` rollups, just not visible to the person it describes. Do
not reintroduce this section here even if it seems convenient — write the
plan's other sections (`Фокус развития`, `План действий`) so they're
useful on their own without it.

## Source Priority

1. Existing individual development plan.
2. Individual metrics Sheet — what it has, and what it's missing.
3. Project goals, business context, and what the project needs from the
   person.
4. Person workbook rows and 1to1 analysis findings.
5. Project development plan only for context.

## Normalization

- Do not duplicate metric values from `individual_metrics` in this document.
  Link to the Sheet; explain what the Sheet can't explain about itself.
- Tie each focus item to the project role the person needs to grow into:
  ownership, visibility, responsibility, authority, trust, client/team entry
  point, or process/module ownership. A focus item that only restates a task
  ("collect X metric") without saying what it changes about the person's
  standing on the project is incomplete.
- If project expectations exceed the person's current level, state the
  project need and manager support explicitly instead of framing the gap only
  as personal underperformance.
- If the person's value must be demonstrated to defend QA stake, include
  concrete evidence-producing actions: useful metrics, accepted process
  proposals, visible risk prevention, automation/reporting usefulness, or
  client/team feedback.
- If project context blocks progress, such as vague requirements, weak
  documentation, access/security limits, unstable deadlines, or unclear
  ownership, put the manager support/escalation in the plan.
- Reviewer feedback belongs in native Google Docs comments tied to the
  relevant paragraph (mirroring how the original homework documents were
  reviewed in Word), not as an extra column or appended text block.
- If the source document is genuinely sparse or empty, keep the Doc with a
  title and a short note naming what evidence is still missing, rather than
  omitting the file entirely.
- Do not force every action item into a fixed calendar bucket (2 weeks / 30
  days / etc.). Split into date-bound near-term commitments and undated
  directional goals instead — matches how Agile teams actually plan.

## Rule

Keep the plan project-contextual and person-specific. If a focus item is
actually a project process initiative, move it to the project
development-plan skill.

Each focus item should state what it gives the project/client/business or how
it grows the person's project role.
