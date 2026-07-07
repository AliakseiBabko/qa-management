# Document Contract

Primary final output is a Google Doc in
`20_M2_Project_Management\<Project>\people\<Person>`, with local Markdown
fallback. This is a narrative document: one living Doc per person, not a row
per focus area.

## Purpose

Use this reference for the individual development-plan document family.

## Expected Output

One individual development-plan Google Doc per person, inside their project
scope.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\people\<Person>`

Doc title (Drive file name): `individual_development_plan`

Local Markdown fallback naming pattern (only when Google API access is
unavailable): `план_развития_qa_<Project>_<Person>_YYYY-MM-DD.md`

## Versioning

- Update the living `individual_development_plan` Doc in place. Google Docs
  version history already preserves prior revisions, so do not create a new
  dated file for routine updates.
- Append source traceability to the project `evidence_log` Sheet.
- Create a separate dated snapshot only for a formal reporting event or when
  the user explicitly asks for one.

## Scope

- one QA engineer
- inside one project or project-set context

## Section Skeleton

Write the Doc as headed prose, in this order. Omit a section if there is no
evidence for it rather than inventing content, but keep the order when
sections are present.

1. **Title** — `<Person> — план развития (<Project>)`, followed by a short
   metadata line (Stream/role, Обновлено, Review cycle, Следующий review).
2. **Цель на период** — one paragraph: what the person should move toward
   over the review horizon and why it matters for the project.
3. **Фокус развития / Зоны роста** — the specific growth areas, each as its
   own bullet or short paragraph naming what is weak/missing today.
4. **План действий** — the actual plan, broken into review horizons (e.g. 2
   weeks / 1 month / 2 months / 3 months, or 30/60/90 days). Each action item
   is a bullet carrying its own success criterion inline, e.g.
   `Action. Критерий: Y.`
5. **Поддержка менеджера** — what M2 support/check cadence is committed, if
   any.
6. **Текущий прогресс** — current progress against the goal, if there is a
   prior plan to compare against.
7. **Источники / Evidence** — bullet list of source references (1:1s, chats,
   docs) the plan draws on.

## Source Priority

1. Existing individual development plan.
2. Project goals, business context, and what the project needs from the
   person.
3. Individual metrics file.
4. Person workbook rows and 1to1 analysis findings.
5. Project development plan only for context.

## Normalization

- State the goal/progress paragraph once; do not repeat it before every focus
  item the way a spreadsheet row would require.
- Tie each focus item to the project role the person needs to grow into:
  ownership, visibility, responsibility, authority, trust, client/team entry
  point, or process/module ownership.
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
  relevant paragraph (mirroring how the original homework was reviewed
  documents in Word), not as an extra column or appended text block.
- If the source document is genuinely sparse or empty, keep the Doc with a
  title and a short note naming what evidence is still missing, rather than
  omitting the file entirely.

## Rule

Keep the plan project-contextual and person-specific. If a focus item is
actually a project process initiative, move it to the project
development-plan skill.

Each focus item should state what it gives the project/client/business or how
it grows the person's project role.
