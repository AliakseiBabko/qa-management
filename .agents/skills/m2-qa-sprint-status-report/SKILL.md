---
name: m2-qa-sprint-status-report
description: Write the per-sprint QA sub-team status report in the corporate Project Coordination format - a traffic light plus three sections (processes and quality, risks, upsells), adapted from a whole-team standard to the QA stream M2 actually owns - one report per project per closed sprint, posted to the project's strategy chat and appended to that month's accumulating status document. Use when a sprint closes, when asked for the sprint QA status of a project, or when the department asks for the traffic-light status of QA. Not for the free-form status report answering an arbitrary period or ad hoc question (that is m2-project-status-report), and not for the monthly KPI workbook (m2-monthly-report).
---

# M2 QA Sprint Status Report

The corporate standard (GDO Outstaff Delivery → Project Coordination) is
written for a delivery team as a whole, and it is normally the DC or the
delivery-side M2 who fills it in. QA appears there as one clause seen from
the outside — "QA returned the task with comments" — because that report's
author owns the whole team and reports QA in passing.

This skill produces the missing half: the same traffic light and the same
brevity, narrowed to the three things QA-side M2 can actually speak to —
процессы и качество, риски, апсейлы. Delivery status is deliberately not
among them: that is the DC's to report, and duplicating it from our side
adds nothing. The project may hold one QA engineer or several; either way it
is one report per project per sprint.

The two reports coexist deliberately. The DC's covers the team; this one
goes deeper on QA. A project can be 🟢 for the DC and 🟡 for QA — that
divergence is the reason this exists, not a contradiction to reconcile.

## Required Start

1. Read `Templates\qa_sprint_status_report.md` — the canonical format,
   traffic-light definitions, filling rules and worked examples.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`,
   `../qa-management-roles/references/google-workspace/m2-layout.md`,
   `../qa-management-roles/references/google-workspace/artifact-conventions.md`,
   and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../m2-project-qa-metrics-report/references/qa-process-metrics-schema.md`
   too if the deferred `Метрики за спринт` line is being re-enabled — it
   holds the sprint-column layout and the trend rule that line depends on.
   Not needed for the standard three-section report.
4. Read `../qa-management-roles/references/m2-role/m2-communication-visibility.md`.
5. Run `.agents\scripts\show_project_state.py --project <Project>` for the
   project's current records, and confirm the sprint id and dates from the
   `Ритм спринтов` row in `project_metrics`. A project with no sprints
   (`Нет спринтов (Kanban)`) reports per calendar month instead, keeping
   everything else identical.

## Source Order

The report is assembled, not composed from memory. Three sections means
three questions, and the sources answer them directly:

**Процессы и качество** — how testing is set up on this project and what
moved:

1. **`evidence_log` for the sprint window** — what was processed, which 1:1s
   happened, what they surfaced.
2. **`project_metrics`'s `Качество QA-процесса`** row and the engineers'
   `individual_metrics` / `individual_development_plan` — the current
   process verdict and what each person actually worked on.
3. **`pk_knowledge_base`** for the project's standing QA constraints, when
   the sprint changed one of them.

**Риски**:

4. **`project_risk`** active items, and **`m2_input`** — a round still
   pending is itself worth a sentence when it blocks a decision.
5. **`action_items`** due or closed in the window, for the "what we're doing
   about it" half of a risk line.

**Апсейлы**:

6. Expansion signals in QA scope from the same 1:1 and strategy-chat
   evidence — growing manual volume, an automation request, a new product to
   test, a testing direction nobody owns.

**Continuity**: the previous sprint's report, always. This is what makes
"без изменений, продолжаем начатое" honest rather than lazy.

## Workflow

1. Determine the closing sprint's id and date range.
2. Gather the sources above for that window only. Older material is context,
   not content.
3. Set the traffic light **on the QA stream**, using the definitions in the
   template. The colour follows the Риски section and nothing else: an empty
   Риски is 🟢. An open process gap does not make a project yellow — see the
   risk definition in Content Rules.
4. Fill the three sections to one to three sentences each. A section with
   nothing in it gets `—`. If nothing moved, Процессы и качество says so
   plainly and names the work being continued.
5. Deliver to both destinations (below).
6. Log to `evidence_log` with `routed_to: qa_sprint_status_report` and the
   sprint id, so the next report can find its predecessor.

## Destination

**The project's strategy chat** is the live destination — this is the report
the department expects there per sprint, stating explicitly whether risks
exist even when nothing else changed.

**The month's accumulating document**, `20_M2_Project_Management\M2\
monthly_status_reports\<YYYY-MM>.gdoc`, is where the same text is appended
so the month has a record. Append, never rewrite: each sprint's entry sits
under its project's heading in sprint order. A sprint belongs to the
calendar month its **end date** falls in (the same rule
`qa-process-metrics-schema.md` uses), so a month usually accumulates one to
three entries per project. Create that month's document from the previous
month's shape if it doesn't exist yet.

Use `.agents\scripts\docs_editing.py append-section` against the project's
heading rather than rewriting the document.

## Content Rules

- **Short is the contract, not a preference.** The whole report pastes into
  one chat message. If it needs scrolling, it has stopped being this report.
- **No findings dump.** Evidence, breakdowns and narrative belong in the
  documents that own them; this report cites the conclusion and moves on.
- **Three sections, and that's the report.** Delivery status is the DC's to
  report and is deliberately absent; project updates live in other
  documents; the metrics line is deferred until the sprint columns actually
  carry data. Don't reintroduce them because a sprint felt eventful — see
  the template's "Чего в отчёте нет и почему".
- **Процессы и качество is about the process, not the ticket list.**
  Coverage and its layers, CI/CD and quality gates, test-case management,
  defect prioritisation, requirements and AC quality, what reaches testing
  and what leaks to production. Not a recap of closed tickets.
- **Every number traceable** to a named source. No invented denominators, no
  coverage percentage without the estimate caveat the metrics schema
  requires.
- **A risk is a threat, not an unfinished improvement.** This is the rule
  that decides the colour, so it decides the report. Only three things
  qualify:
  - **Client-side signals** — intent to stop, reduce or replace the team,
    dissatisfaction with quality, an escalation.
  - **Capacity** — we are not covering what the client requires; the volume
    genuinely isn't being absorbed.
  - **Retention** — expectations the engineer stated in 1:1s keep going
    unmet, to the point they may leave the project or the company.

  Always paired with what is being done about it, and by when.

  These are **not** risks, and putting them there mis-colours the report:
  - process gaps and improvement opportunities (no CI/CD, no test-case
    management, backlog never groomed, developers setting defect priority) —
    they belong in Процессы и качество;
  - a scope agreement that never materialised, such as automation promised
    at staffing — that is an unused opportunity, so Апсейлы;
  - internal matters of responsibility and communication, such as a DC being
    absent or overloaded — our own kitchen, tracked in its own documents and
    absent from this report.

  One-line test: if it threatens neither QA's presence on the project nor
  keeping the engineer, it is not a risk and the section gets `—`.

  Most healthy sprints on a stable project are 🟢 with `Риски: —`, including
  sprints with real process work still outstanding. Do not reach for 🟡 to
  signal that improvements remain.
- **One person's account stays one person's account.** A claim from a single
  1:1 that would change a project-level conclusion is reported as their
  account, and the conclusion itself still routes through `m2_input`.
- **Russian, and written as Russian** — this goes to a chat colleagues read.

## Boundaries

- **vs `m2-project-status-report`**: that one answers an arbitrary period or
  an ad hoc question in a free shape. This one is the fixed corporate format
  on a sprint cadence. If the user asks "what's the status of X right now",
  that is the other skill.
- **vs `m2-monthly-report`**: that is the KPI/bonus workbook. This is a
  narrative status.
- **vs the department traffic-light table** (`m2-department-traffic-light`)
  and `_project_registry`: those are cross-project views with their own
  colour semantics. The colour here is scoped to one project's QA stream for
  one sprint and is not automatically the same value — do not copy one into
  the other.
- **vs `project_risk`**: this report *reads* risk, never sets it. A new
  risk conclusion goes through `m2_input` like any other.

## Guardrails

- Never pad a quiet sprint. A short report is the correct output for a quiet
  sprint.
- If `project_metrics`'s `Статус проекта` is `Не активен`, don't produce
  this report at all — the metrics sheet is frozen for the same reason.
- Don't restate the DC's whole-team report. If a fact isn't about QA, it
  belongs in Обновления only when it changes something for QA.
