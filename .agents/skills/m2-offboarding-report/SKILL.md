---
name: m2-offboarding-report
description: Create the offboarding retrospective report for a QA/AQA leaving a project's rate, per the department's Outstaff Delivery process standard - the reason for the stop, what was tried (was Risk Management run, did it work), the staffing portrait for the next hire on this rate, and whether the client is open to continuing. Use when a specialist's last working day on a project has happened or is imminent and the stop's cause and lessons need to be captured.
---

# M2 Offboarding Report

Use this skill for one output family only:

- the offboarding retrospective, posted to the project's strategy chat
  once the specialist's exit is confirmed (per the department's Outstaff
  Delivery process standard — see `qa_department_standards`, Process
  Requirements, for the current source reference)

This is a retrospective on *why the rate stopped*, not a farewell
message or an exit-logistics checklist — those are one-off chat actions
(final-day goodbye, tech/license return, anonymous feedback form) that
this skill doesn't template; the retrospective is the one artifact with a
fixed shape.

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-role-basics.md`, `../qa-management-roles/references/m2-role/m2-communication-visibility.md`, and `../qa-management-roles/references/m2-role/m2-risk-rules.md`.
4. Identify the project and the departing specialist. Confirm the stop
   is real/confirmed (a date has been communicated), not still a Risk
   Management situation still trying to save the rate — see
   `m2-project-risk-report`'s Outstaff Delivery Escalation Action-Plan
   Format section for that earlier stage.

## Source Order

1. Whether `Replacement` was already launched, and its outcome
   (see `m2-replacement-report` output/status for this rate, if run).
2. Whether Risk Management/an escalation action plan ran for this person
   before the stop (see `m2-project-risk-report`'s action-plan history) —
   what was tried and whether it worked.
3. Client/lead feedback on the reason for the stop (direct, via Sales, or
   via the team).
4. The person's own account, if available (offboarding 1:1).
5. `individual_risk`/`project_risk` history for this person/project.

## Workflow

1. Determine the real cause of the stop — do not default to a vague
   "fit issue" when a more specific cause (skill-level mismatch,
   communication discipline, client budget/scope change, contract end,
   personal circumstances) is actually in evidence.
2. State plainly whether Risk Management/an escalation plan was run: if
   yes, what the plan was and why it didn't hold the rate; if no, say so
   and note whether that was a judgment call worth reconsidering next
   time (per the source instruction's own worked example — a
   disciplinary-looking issue that, in hindsight, should have triggered
   Risk Management earlier).
3. Write a concrete staffing portrait for whoever replaces this person on
   this rate: level, stack-specific checks, communication style, whatever
   this client specifically needs — not a generic "strong Mid+"
   restatement of the original request.
4. State the client's openness to continuing (yes/no/unknown) as reported,
   not inferred from silence.
5. This retrospective is real evidence about the person and the project —
   after posting it, check whether it changes this person's
   `individual_risk`/`individual_metrics` closing note or this project's
   `project_risk`/`evidence_log`; those stay owned by their own skills
   (`m1-people-risk-report`/`m2-project-risk-report`/evidence-log intake),
   this skill only flags that the update is due, it doesn't perform it.
6. Deliver per Destination.

## Report Format

```text
Ретроспектива | [Имя] | [Проект]

Причина стопа: [описание]
Что предпринимали: [был ли запущен Risk Management, что делали, почему не сработало]
Портрет под проект: [что учитывать при следующем подборе: уровень, коммуникационный стиль, специфика клиента]
Клиент готов к продолжению: да / нет / неизвестно
```

## Destination

Posted directly into the project's own strategy chat by default, same
convention as `m2-project-status-report`. Save a copy under
`20_M2_Project_Management\<Project>\private\status_reports` only if the
user asks for a kept copy (see `references/document-contract.md`).

## Guardrails

- Do not write a generic/vague stop reason when a specific one is in
  evidence — "не сложилось" is not an acceptable substitute for the real
  cause.
- Do not invent whether Risk Management ran or what it consisted of.
- Do not write a staffing portrait that just repeats the original hiring
  request — it must reflect what was actually learned from this stop.
- Do not mark "клиент готов к продолжению" as yes/no without an actual
  signal; use "неизвестно" and say what's missing.
- Do not perform the `individual_risk`/`project_risk`/`evidence_log`
  updates this retrospective may trigger — flag them, let the owning
  skill do the write.
