---
name: m1-individual-development-plan
description: Create or update an individual OKR / development-plan Google Doc for one QA engineer, for M1 people management. Use when drafting or refreshing the OKR a person will operationalize in Jira after a Performance Review, based on `Templates/okr_m1.md` from this repository.
---

# M1 Individual Development Plan (OKR)

Use this skill for one output family only:

- individual OKR Google Doc for one person in `10_M1_People_Management`, with Markdown fallback

This mirrors the company's real OKR process: created at each Performance
Review for the period until the next one, minimum 3 objectives, each Key
Result a single concrete-action line (no separate acceptance-criteria/
result/deadline fields - see `references/okr-process-rules.md`). The Doc
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

`m1-timeline`'s `scan_m1_events.py` reads this Doc's title (`OKR к
Perfomance review DD.MM.YY`) to surface upcoming/overdue Performance
Review dates and people missing a current OKR entirely — another
read-only downstream consumer, same as the two above.

## Required Start

1. Read `references/document-contract.md`.
2. Read `references/okr-process-rules.md`.
3. Read `../qa-management-roles/references/performance-review-rules.md` for the real PR cadence (used to compute the Doc title date, see Workflow step 4).
4. Read `../qa-management-roles/references/google-workspace-rules.md`.
5. Read `../qa-management-roles/references/m1-role-rules.md`.
6. Read `../qa-management-roles/references/newcomer-support-rules.md`.
7. Identify the target person, their current project (or bench status), and the Performance Review date this OKR is for.
8. Read the person's existing OKR Doc if one exists, their `<Person> 1to1` Sheet, their people-risk report row, their `_m1_people_registry` row (`Дата трудоустройства`/`Дата последнего PR`/`M1`/`Первый коммерческий проект`), and — if they're on a project — that project's context (tech stack, tools, current focus). If the person is also M2-staffed, `_m2_people_registry` points back at `_m1_people_registry` for these facts rather than duplicating them - read there, not both.

## Workflow

1. Use `Templates/okr_m1.md` as the section skeleton. Keep it to 3-4 objectives, 2-3 Key Results each — do not pad an objective with restated context or generic filler KRs just to look complete.
2. Build each objective from real context, not a generic checklist:
   - **Техническое развитие** — if the person is on a project, pull the direction from that project's actual technologies, tools, and process gaps (project context, `individual_metrics`, recent 1:1 mentions) — it should be obvious the KR grows their project performance, not a random skill. If the person is on bench, pick a direction with broad market usefulness; if no market/skill direction has been stated by the user, ask rather than invent one.
   - **ИИ** — one modest, practical KR (course, assessment, or one applied use case). Do not inflate this into several KRs by default; check whether the person already has AI-tool usage on record (1:1 notes, project context) and build from that instead of starting blank.
   - **Soft skills / командная работа** — source only from the person's `1to1` Sheet, people-risk report, and any explicit manager notes. Do not invent a growth area with no evidence behind it. If there's no usable signal for the period, say so plainly and leave the KR open/general (e.g. "collect team feedback") instead of manufacturing an issue.
   - **Департамент** — an activity the person chooses for themselves (mentoring, meetup, internal course, process help). Frame it as their pick, not an assignment.
   - If `Первый коммерческий проект` = `Да` and the person is within their
     first month on the project, add one KR under **Техническое развитие**
     (not Департамент — this isn't their own pick) naming their assigned
     buddy/mentor and the support cadence, per `newcomer-support-rules.md`.
     This is in addition to the normal 2-5 KR count for that objective, not
     a replacement for the project-technology KR.
3. Every Key Result is one line: the concrete action, with a real deadline folded into the same line only when one is actually known. Do not break a KR into separate "Критерии для оценки"/"Результат"/deadline/status fields, and do not add a metadata line (role/level/project/period/Jira epic) under the title — real OKRs at this company are terser than that; see `references/okr-process-rules.md`.
4. Name the Doc title's date using the real cadence, not an arbitrary guess: `Дата последнего PR + 6 months` if set, else `Дата трудоустройства + 3 months` for a first/probation-closing OKR (see `performance-review-rules.md`, "Deriving Expected Next PR Date"). If neither is known in `_m1_people_registry`, use the `(дата уточняется)` placeholder title rather than inventing a date - and don't add an inline note explaining the date is missing inside the document itself; that's tracked separately via `scan_m1_events.py`'s `undated_draft` candidate (see `m1-timeline`).
5. When closing out an existing OKR (new PR cycle), require a short one-line result on every KR from the prior cycle before starting the new one; unresolved KRs either get an explicit short "не достигнуто" comment or are carried into the new OKR — never silently dropped.
6. After the PR that closes this cycle actually happens, update that person's `Дата последнего PR` in `_m2_people_registry` to the real PR date — this is what keeps `m1-timeline`'s cadence tracking accurate; a new OKR Doc alone doesn't update it.

## Guardrails

- Do not produce project-level or team-level OKRs here — this skill is scoped to one person.
- Do not invent soft-skill growth areas, personal concerns, or motivation without 1:1/risk-report evidence — same rule as `m2-individual-development-plan`.
- Do not pad the document past 3-4 objectives; if the person genuinely needs a 5th objective, check with the user first rather than defaulting to it.
- Do not duplicate `individual_metrics`/project-metrics values here — reference them, don't restate.
- Do not create the OKR for unpaid interns — they follow a separate internship program, not this OKR process.
- Do not reintroduce the "Критерии для оценки" / "Результат" / deadline / status field breakdown per KR, or a metadata line under the title — both were tried and explicitly rejected in favor of the terser format real OKRs at this company actually use.
- This skill drafts OKR content for **any one person**, including an M1's or M2's own OKR when they're preparing for their own Performance Review (see `m-self-review`) — the Doc mechanics (skeleton, single-line KRs, cadence-based title date) are identical either way. The only thing that changes is where the Doc lives: a team member's own `10_M1_People_Management\<Person>\` (or project) folder vs. `_self_review\<Person>\` for an M-manager's own OKR — see `m-self-review`'s document-contract.md. Confirm which case applies rather than assuming from context.
