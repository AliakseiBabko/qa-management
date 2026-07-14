---
name: m1-individual-development-plan
description: Create or update an individual OKR / development-plan Google Doc for one QA engineer, for M1 people management. Use when drafting or refreshing the OKR a person will operationalize in Jira after a Performance Review, based on `Templates/okr_m1.md` from this repository.
---

# M1 Individual Development Plan (OKR)

Use this skill for one output family only:

- individual OKR Google Doc for one person in `10_M1_People_Management`, with Markdown fallback

This mirrors the company's real OKR process: created at each Performance
Review for the period until the next one, minimum 3 objectives, each Key
Result carrying acceptance criteria, a result, and a deadline. The Doc
produced here is the staging copy the person pastes/operationalizes into
their Jira OKR card — it is not itself the Jira record.

Two other M1 skills read this Doc as a source, downstream of this skill:

- `m1-1to1-prep` treats an overdue Key Result as a direct follow-up
  question.
- `m1-monthly-report` uses OKR-cycle activity (drafted, closed, or
  status-updated within the reporting month) as evidence for the `Работа с
  ОКР` obligation row.

Neither of those skills writes back into the OKR Doc — status/result
updates land here only when the user is actually working on this skill's
output.

## Required Start

1. Read `references/document-contract.md`.
2. Read `references/okr-process-rules.md`.
3. Read `../qa-management-roles/references/google-workspace-rules.md`.
4. Read `../qa-management-roles/references/m1-role-rules.md`.
5. Identify the target person, their current project (or bench status), and the Performance Review date this OKR is for.
6. Read the person's existing OKR Doc if one exists, their `<Person> 1to1` Sheet, their people-risk report row, and — if they're on a project — that project's context (tech stack, tools, current focus).

## Workflow

1. Use `Templates/okr_m1.md` as the section skeleton. Keep it to 3-4 objectives, 2-3 Key Results each — do not pad an objective with restated context or generic filler KRs just to look complete.
2. Build each objective from real context, not a generic checklist:
   - **Техническое развитие** — if the person is on a project, pull the direction from that project's actual technologies, tools, and process gaps (project context, `individual_metrics`, recent 1:1 mentions) — it should be obvious the KR grows their project performance, not a random skill. If the person is on bench, pick a direction with broad market usefulness; if no market/skill direction has been stated by the user, ask rather than invent one.
   - **ИИ** — one modest, practical KR (course, assessment, or one applied use case). Do not inflate this into several KRs by default; check whether the person already has AI-tool usage on record (1:1 notes, project context) and build from that instead of starting blank.
   - **Soft skills / командная работа** — source only from the person's `1to1` Sheet, people-risk report, and any explicit manager notes. Do not invent a growth area with no evidence behind it. If there's no usable signal for the period, say so plainly and leave the KR open/general (e.g. "collect team feedback") instead of manufacturing an issue.
   - **Департамент** — an activity the person chooses for themselves (mentoring, meetup, internal course, process help). Frame it as their pick, not an assignment.
3. Every Key Result carries: the action, "Критерии для оценки" (acceptance criteria), "Результат" (what gets produced/shown), a deadline, and a status. This is a Confluence-mandated format — do not drop any of the four fields even to keep things short.
4. If the OKR is being drafted after a specific Performance Review date, name the Doc/title accordingly (`OKR к Perfomance review DD.MM.YY`) per `references/okr-process-rules.md`.
5. When closing out an existing OKR (new PR cycle), require a status and result on every KR from the prior cycle before starting the new one; unresolved KRs either get an explicit "не достигнуто" status or are carried into the new OKR — never silently dropped.

## Guardrails

- Do not produce project-level or team-level OKRs here — this skill is scoped to one person.
- Do not invent soft-skill growth areas, personal concerns, or motivation without 1:1/risk-report evidence — same rule as `m2-individual-development-plan`.
- Do not pad the document past 3-4 objectives; if the person genuinely needs a 5th objective, check with the user first rather than defaulting to it.
- Do not duplicate `individual_metrics`/project-metrics values here — reference them, don't restate.
- Do not create the OKR for unpaid interns — they follow a separate internship program, not this OKR process.
- Do not skip the "Критерии для оценки" / "Результат" / deadline / status fields on any KR, even for a short/placeholder objective.
