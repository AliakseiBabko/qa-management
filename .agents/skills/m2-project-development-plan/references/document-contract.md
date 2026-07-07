# Document Contract

Primary final output is a Google Doc in `20_M2_Project_Management\<Project>`,
with local Markdown fallback. This is a narrative document: one living Doc per
project, not a row per initiative.

## Purpose

Use this reference for the project-level development-plan document family.

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

Write the Doc as headed prose, in this order. Omit a section if there is no
evidence for it rather than inventing content, but keep the order when
sections are present.

1. **Title** — `<Project> — план развития проекта`, followed by a short
   metadata line (Обновлено / Review cycle / Следующий review).
2. **Краткое резюме** — one paragraph: what kind of account/project this is,
   the main tension or opportunity, and the headline focus for the period.
3. **Business focus and value** — how the project creates business value, what
   the client wants, and the end value QA/the team brings (map to the
   homework skeleton the head of QA set: business focus and flow, client
   expectations, value delivered, success over the last period).
4. **Текущее состояние** — current state, broken out by stream/initiative/
   workstream when the project has more than one, each as its own short
   paragraph or bullet, not repeated verbatim across later sections.
5. **План** — the actual plan, broken into review horizons (30/60/90 days, or
   phased months for a longer-horizon plan). Each action item is a bullet
   carrying its own owner and success criterion inline, e.g.
   `Action. Owner: X. Критерий: Y.`
6. **Нужные решения** — open questions/decisions blocking progress, if any.
7. **Риски проекта** — risks as short reasoned paragraphs (what the risk is,
   why it is real, what reduces it), not a single-line traffic-light row.
8. **Источники / Evidence** — bullet list of source references (1:1s, chats,
   docs) the plan draws on.

## Source Priority

1. Existing project development plan.
2. Business/project context, client expectations, strategy-chat statuses, and
   project goals.
3. Project risk summary.
4. Project metrics.
5. Workbook status/context rows.
6. Individual plans only when they reveal a project-level capability or
   continuity gap.

## Normalization

- State the executive summary and current-state context once; do not repeat
  it before every action item the way a spreadsheet row would require.
- Use exact review dates when provided by the source.
- Each initiative should answer: what project/business problem it solves,
  what value it brings, how success is measured, and where progress will be
  synchronized.
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
