---
name: m2-project-risk-report
description: Create or update a project risk traffic-light Google Sheet, with CSV fallback, for M2 project management. Use when producing a project-focused risk report from QA 1to1 findings, project transcripts, delivery signals, or other project data sources.
---

# M2 Project Risk Report

Use this skill for one output family only:

- project risk traffic-light Google Sheet, with CSV fallback

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Read `../qa-management-roles/references/m2-role-rules.md`.
4. Identify the target project and reporting snapshot date.
5. Read the smallest relevant evidence set:
   - extracted project risk/summary documents
   - project development plans
   - project metrics
   - business/project context and client expectations
   - workbook 1to1/status rows
   - `qa-1to1-analysis` findings when transcripts are one of the inputs
6. State source gaps before filling the template.

## Workflow

1. Build one project-level row per project/snapshot.
2. Rate the overall project risk as one of: `Низкий`, `Средний`, or `Высокий`.
3. Separate risk perspectives before mapping to template dimensions:
   - business
   - project/product
   - development
   - QA/process
   - staffing/continuity
   - our role/value
4. Separate template dimensions:
   - delivery
   - QA process
   - staffing / continuity
   - communication / client
5. Keep comments factual and evidence-linked.
6. Write the action plan as concrete next management steps with an owner and next review date.
7. State feedback confidence when feedback is part of the evidence: direct client, intermediary, DC/QA Lead, team, or employee self-report.
8. Sanitize sensitive context in final documents. Keep location/security/vendor-chain details only when they are needed to explain the risk or action.

## Risk Level Rules

Use the same three-level model as `qa-1to1-analysis`, expressed in Russian for all final project-risk documents.

Dictionary:

| Final CSV value | Legacy English alias | Definition |
| --- | --- | --- |
| `Низкий` | `Low` | Текущих проектных проблем не видно, и в ближайшей перспективе нет явных признаков ухудшения. |
| `Средний` | `Medium` | Текущего острого кризиса нет, но есть фоновые факторы, которые без управления могут привести к проблемам в delivery, QA/process, staffing, клиентской коммуникации, бизнес-ценности или роли нашей команды. |
| `Высокий` | `High` | Риск уже виден в фактах или устойчивых сигналах; нужны управленческие действия, mitigation, escalation или конкретный recovery plan. |

Use only the Russian `Final CSV value` terms in project-risk level fields and final documents. English aliases are for migration/interpretation only and must not appear as risk values in generated outputs.

- `Низкий`: текущих проектных проблем не видно, и в ближайшей перспективе нет явных признаков ухудшения.
- `Средний`: текущего острого кризиса нет, но есть фоновые факторы, которые без управления могут привести к проблемам в delivery, QA/process, staffing, клиентской коммуникации, бизнес-ценности или роли нашей команды.
- `Высокий`: риск уже виден в фактах или устойчивых сигналах; нужны управленческие действия, mitigation, escalation или конкретный recovery plan.

Do not use `Low`, `Medium`, `High`, `Critical`, or `Unknown` in final project-risk level fields.

Uncertainty is itself a risk signal for an active project. If the project is not at the very beginning and the evidence is too weak to estimate a level, use at least `Средний` and explain the evidence gap in comments. In particular, use at least `Средний` when we cannot detect the current risk level because we cannot collect project metrics, client/team feedback, delivery status, or QA-process evidence.

For a project that is genuinely at the start and has not yet produced enough delivery/process/client evidence, use `Средний` by default unless there are concrete facts supporting `Низкий` or `Высокий`.

## Additional Project Risk Signals

- Hidden or unclear project topology: unknown streams, team size, DC/PM ownership, vendor chain, client path, tender horizon, or security/location constraints.
- Indirect feedback chain: feedback comes through an intermediary, DC, QA Lead, or employee rather than directly from the client.
- Role-value risk: the client or project-side leadership questions whether QA is needed, whether QA can be replaced, or whether our team adds business value.
- Metrics visibility risk: standard metrics are unavailable, not trusted, or do not answer the project's real management question.
- Staffing/expectation mismatch: a junior or newly onboarded QA is expected to operate at a senior/project-critical level without enough process support.
- Process volatility: vague requirements, weak documentation, abrupt deadline changes, no stable release cadence, or undefined QA ownership.

## Guardrails

- Do not output people risk traffic lights here.
- Do not output metrics or development plans here.
- Do not infer client dissatisfaction, staffing risk, or delivery risk from weak hints. When evidence is missing, mark the level according to the uncertainty rules and state exactly which evidence is missing.
- Do not list a current problem as a risk without explaining future impact on business/project/role.
