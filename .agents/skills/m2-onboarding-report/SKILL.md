---
name: m2-onboarding-report
description: Create the milestone reports for a new employee's onboarding on a project following the department's Outstaff Delivery process standard - a Day-1 start report, and a final onboarding report (technical description, client expectations) once the checklist closes. Use when a new hire's first day happens, or when onboarding closes (checklist 100%, >= 2 tasks accepted by client Acceptance Criteria, all planned meetings attended). For the recurring weekly onboarding-block update, see m2-project-status-report instead - this skill owns the two milestone reports, not the weekly cadence.
---

# M2 Onboarding Report

Use this skill for two milestone artifacts only, both tied to a specific
project's Outstaff Delivery onboarding process (see
`qa_department_standards`, Process Requirements, for the current source
reference):

- **Start report** — sent end of Day 1
- **Final onboarding report** — sent once every completion criterion is
  met (checklist closed 100%, >= 2 profile tasks accepted per client
  Acceptance Criteria, all planned meetings attended)

The recurring **weekly onboarding-block** that runs during the period
between these two milestones is owned by `m2-project-status-report`
(Chat Text Shape) — it gets embedded into that project's regular weekly
status, not produced here.

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-role-basics.md` and `../qa-management-roles/references/m2-role/m2-communication-visibility.md`.
4. Identify the project, the new hire, and which of the two reports is
   being requested (or infer from context: a request right after a
   start date is the start report; a request naming closed checklist/
   accepted tasks/finished onboarding is the final report).
5. If genuinely unclear which report is wanted, ask rather than guessing.

## Source Order

1. The onboarding checklist for this person/project (see
   `qa_department_standards` for the checklist template reference) —
   completion state, dates, notes.
2. Prior weekly onboarding-block updates already posted for this person
   (from `m2-project-status-report` history) — progress trail.
3. 1:1 notes with the person during onboarding.
4. Project topology/business context already captured for this project
   (`pk_knowledge_base` if one exists) — for the final report's technical
   description.
5. Kickoff notes, Sales handoff info, interview notes for the start
   report's legend/contract/overlap facts.

## Workflow

### Start Report

1. Confirm the facts that must be present: project, contract type
   (T&M/Fixed price, term), legend (direct / through an intermediary,
   what the client sees vs the real location), security setup (office/
   remote, router, dedicated laptop), overlap hours, and what happened
   at kickoff (if it already ran) or when it's scheduled.
2. Do not invent any of these — if a fact isn't in evidence, say so
   explicitly in that field rather than guessing plausible values.
3. Deliver per Destination.

### Final Report

1. Verify completion criteria are actually met before drafting: checklist
   closed 100%, tasks accepted, meetings attended. If any criterion is
   still open, say so rather than writing the report as if onboarding
   were complete — this report certifies the transition to standard
   coordination.
2. Build the technical description from real evidence (stack,
   architecture, CI/CD/infra, AI usage, domain) — this becomes part of
   this project's durable technical picture; check the project's
   `pk_knowledge_base` and fold in genuinely new architecture/workflow
   facts there too (see `../qa-management-roles/references/m2-role/m2-cascading-updates.md`,
   Cross-Lane Step: Project Knowledge), not just the report text.
3. Capture client expectations for the role (what "strong" looks like
   beyond closing tickets on time — proactivity, communication style,
   response speed, etc.) from lead feedback, not assumed.
4. Deliver per Destination.

## Report Formats

### Start Report (chat-ready, sent end of Day 1)

```text
Стартовый отчёт | [Имя сотрудника]
Проект: [Название проекта]
Контракт: [T&M / Fixed price]. [Срочный до ДД.ММ.ГГГГ / Бессрочный].
Легенда: [Напрямую / через посредника Название]. Для клиента – [ссылка на CV], локация – [страна]. Реальная локация – [страна].
Безопасность: [Офис / удалённо]. Роутер – [есть / нет]. Отдельный ноутбук – [выделен / нет].
Оверлап: [ЧЧ:ММ–ЧЧ:ММ по timezone]. Если явно не оговорён – указываем рабочие часы команды клиента.
Чек-лист онбординга: [ссылка]
Кик-офф: [свободный текст – что обсудили, что зафиксировали, консерны]
```

If kickoff hasn't happened yet: replace the Кик-офф line with
`Запланирован на [дату]. Фоллоу-ап – отдельным сообщением после мита.`

### Final Onboarding Report (chat-ready, sent on completion)

```text
Финал онбординга | [Имя сотрудника]
Дней на онбординге: [X]
Чеклист: [ссылка] – закрыт на 100%
Закрытые задачи: [список/названия]
Миты: все плановые посещены за период онбординга
Техническое описание проекта:
• Стек: [технологии]
• Архитектура: [монолит / микросервисы / особенности]
• Инфраструктура/CI/CD: [как разворачивается, деплой]
• AI: [использование AI-инструментов на проекте, если применимо]
• Домен: [сфера/бизнес клиента]
Ожидания клиента: [что для лида является признаком сильного специалиста помимо своевременного закрытия задач – проактивность, вовлечённость в коммуникацию, готовность оспаривать решения с аргументами, автономность, скорость реакции и т.д.]
Команда: Лид – [Имя, Роль] | Состав: [X человек, роли]
```

## Destination

Both reports are posted directly into the project's own strategy chat by
default, same as `m2-project-status-report`'s regular reports — not a
saved Doc. Save a copy under
`20_M2_Project_Management\<Project>\private\status_reports` only if the
user asks for a kept copy (see `references/document-contract.md`).

## Guardrails

- Do not invent contract terms, legend details, security setup, or
  technical-description facts. State the gap instead.
- Do not send the final report before every completion criterion is
  actually met — flag what's still open instead.
- Do not duplicate the weekly onboarding-block shape here; that stays in
  `m2-project-status-report`.
- Do not skip the Project Knowledge cross-lane check on the final
  report's technical description — durable architecture/workflow facts
  belong in `pk_knowledge_base` too, not only in this one-time report.
