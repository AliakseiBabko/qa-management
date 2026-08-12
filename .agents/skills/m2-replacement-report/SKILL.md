---
name: m2-replacement-report
description: Draft the staged chat posts that carry a Replacement (staffing to save an at-risk or already-stopped rate) through its stages, per the department's Outstaff Delivery process standard - the candidate profile request, screening-results summary, CV-review approval note, post-interview internal feedback, and the Won/Lost close-out. Use when a rate needs a replacement candidate (proactively during Risk Management, or after a confirmed stop) and M2 needs the chat text for the current stage of that staffing process.
---

# M2 Replacement Report

Use this skill for the chat-post artifacts that carry a `Replacement`
through its stages (see `qa_department_standards`, Process Requirements,
for the department's Outstaff Delivery source reference). Unlike
Onboarding/Offboarding/Shadow Onboarding, this process has no single
fixed report template — each stage below produces a short, distinct
post. Identify which stage is being requested before drafting; don't
default to the first one.

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-role-basics.md` and `../qa-management-roles/references/m2-role/m2-communication-visibility.md`.
4. Identify the project, the rate being replaced, and why Replacement was
   triggered (proactive, mid Risk Management; or reactive, after a
   confirmed stop/lost escalation) — this context belongs in the
   Stage 1 profile post.
5. Identify which stage's artifact is actually being requested.

## Stages And Formats

### Stage 1 — Launch (candidate profile request)

Posted to the strategy chat, tagging the Head and RM of the relevant
department, as soon as the need for a replacement is confirmed.

```text
Замена | [Проект] | Ставка: [роль/грейд]

Причина замены: [risk stop / confirmed stop / lost escalation]
Стек: [технологии]
Грейд: [Junior/Mid/Senior + уточнения]
Важно для клиента: [коммуникационный стиль, специфика, что учли из ретроспективы/риска]
```

### Stage 2 — Screening results

Posted after candidate screenings, tagging HoB, Head/RM, and Sales.

```text
Скрининг кандидатов | [Проект] | Ставка: [роль]

Одобрено M2/DC:
- [Кандидат 1] — [короткое обоснование фита]
- [Кандидат 2] — ...

Отклонено:
- [Кандидат] — [причина: таймзона / стиль общения / грейд не подходит / другое]
```

### Stage 3 — CV review approval

Posted once CVs are reviewed against the position portrait, tagging
Sales for client submission.

```text
CV Review | [Проект] | Ставка: [роль]

Аппрув на отправку клиенту: [Кандидат(ы)]
Комментарий: [соответствие портрету, что подчеркнуть клиенту]
```

### Stage 4 — Post-interview internal feedback

Posted after each client interview, tagging Sales (and HoB/Head-RM if the
outcome looks like a likely rejection).

```text
Фидбек после интервью | [Кандидат] | [Проект]

Плюсы: [...]
Минусы: [...]
Оценка шансов: [высокая / средняя / низкая]
```

### Stage 5 — Close-out (Won / Lost)

Posted once the client's final decision is known.

```text
Замена закрыта | [Проект] | Ставка: [роль]
Результат: Won / Lost

[Won] Новый старт: [Имя], дата старта [ДД.ММ.ГГГГ]. Артефакты для онбординга подготовлены (CV, описание позиции). Переходим в Onboarding.

[Lost] Причина отказа: [описание]. План на следующие потенциальные замены: [короткий план]
```

## Workflow

1. Confirm which stage is being requested; do not silently skip earlier
   stages' facts if they're needed for context (e.g. Stage 5 needs Stage
   1's original reason for replacement to close the loop).
2. Never approve/present a candidate the evidence doesn't actually
   support — this skill drafts M2's own judgment calls (screening
   approval, CV review), it doesn't rubber-stamp a raw candidate list.
3. All communication to the client about a candidate goes only through
   Sales — never draft text that implies direct client contact about a
   candidate outside that channel.
4. On a Won close-out, note explicitly that `Onboarding` starts next (see
   `../m2-onboarding-report/SKILL.md`) — this skill doesn't draft the
   start report itself, that's the next process.
5. Deliver per Destination.

## Destination

Each stage is posted directly into the project's own strategy chat by
default. Save a copy under
`20_M2_Project_Management\<Project>\private\status_reports` only if the
user asks for a kept copy (see `references/document-contract.md`).

## Guardrails

- Do not invent screening outcomes, CV-review judgments, interview
  feedback, or the client's final decision.
- Do not draft language that implies M2/DC or the candidate communicating
  directly with the client outside the Sales channel.
- Do not conflate this with the offboarding retrospective — Replacement
  covers finding the next person; `m2-offboarding-report` covers the
  outgoing person's stop analysis. Both can run in parallel for the same
  rate.
- Do not skip stating the original reason for the replacement (risk stop
  vs. confirmed stop vs. lost escalation) — it belongs in the Stage 1
  post and should carry through to the close-out.
