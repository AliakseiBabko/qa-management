---
name: m2-shadow-onboarding-report
description: Create the weekly Shadow Onboarding status block for a project's strategy chat while a shadow is being onboarded behind a client-facing specialist (facade scheme), per the department's Outstaff Delivery process standard - progress on the task in hand, blockers, how the face-shadow handoff of context is going, and any legend/security incidents. Use during the shadow's onboarding period (up to 6 weeks) for the weekly update, or when the shadow starts/completes independent work for the milestone notification text.
---

# M2 Shadow Onboarding Report

Use this skill for the Shadow Onboarding artifacts (see
`qa_department_standards`, Process Requirements, for the department's
Outstaff Delivery source reference) — a facade scheme where a "shadow"
is onboarded behind a client-facing "face" specialist, invisible to the
client. Two outputs:

- **Weekly status block**, embedded in the project's regular weekly
  status while the shadow is onboarding (up to ~6 weeks)
- **Milestone notifications** — short one-line posts at kickoff-approval
  and at independent-work approval, not a template, just confirmation
  text

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-role-basics.md` and `../qa-management-roles/references/m2-role/m2-communication-visibility.md`.
4. Identify the project, the face specialist, the shadow, and the
   current week number of the shadow's onboarding.

## Source Order

1. Prior weekly Shadow Onboarding blocks for this face-shadow pair.
2. 1:1/sync notes between M2/DC and the face-shadow pair (at least
   weekly per the source process).
3. Task-tracker evidence for the task currently in the shadow's hands.
4. Any legend/security incident notes (device/VPN/access mismatches).

## Workflow

1. Confirm the facade scheme is understood and accepted by both face and
   shadow before drafting anything (this is a Step-0/Step-2 precondition
   in the source process, not something this skill re-verifies itself —
   assume it's already in place unless told otherwise).
2. Weekly block: report on the task currently in progress, not a general
   summary of the whole week — same discipline as
   `m2-project-status-report`'s Onboarding block.
3. Describe the face-shadow handoff quality concretely (is context
   transfer happening daily, are there gaps) — this is the signal that
   actually determines readiness for independent work, more than task
   count.
4. Legend field: default to "Нет инцидентов" only when there's genuine
   evidence nothing happened — don't default to it just because nothing
   was mentioned; say "не проверялось" if genuinely unknown.
5. Milestone notifications are short and factual — do not pad them into
   a full report.
6. Deliver per Destination.

## Report Formats

### Weekly Status Block

```text
Shadow Onboarding | [Имя шедоу] → [Имя лица] | Неделя [X]
Задача в работе: [ID – Название]
• Прогресс: [Идёт по плану / Риск сдвига – описать]
• Блокеры: [Нет / Описать + действия M2/DC]
Связка лицо–шедоу: [Как идёт передача контекста, есть ли сложности]
Легенда: [Нет инцидентов / Описать если были]
```

### Milestone Notifications (one-liners, not templated further)

- Kickoff approval, posted to strategy + project chat: `Для [имя лица]
  заводим шедоу, стартует [дд.мм].`
- Independent-work approval, posted to strategy chat: `Шедоу [имя]
  заонборжен на проекте [название].`

## Destination

Weekly blocks are embedded in the project's regular weekly status
(strategy chat), same as `m2-project-status-report`'s Onboarding block.
Milestone one-liners post directly to chat. Save a copy under
`20_M2_Project_Management\<Project>\private\status_reports` only if the
user asks for a kept copy (see `references/document-contract.md`).

## Guardrails

- Do not invent task progress, blockers, or handoff quality.
- Do not default "Легенда" to "Нет инцидентов" without a real basis for
  it.
- Do not draft the independent-work approval notification before
  confirming the shadow is actually closing tasks without the face's
  involvement — that's the real completion criterion, not elapsed time.
- Do not treat this as a general onboarding report — the shadow is
  invisible to the client by design; nothing drafted here should read as
  if the shadow were the client-facing specialist.
