---
name: m2-project-risk-report
description: Create or update a project risk traffic-light Google Sheet (living 2-tab workbook with Summary and Risk Items), with CSV fallback, for M2 project management. Use when producing a project-focused risk report from QA 1to1 findings, project transcripts, delivery signals, or other project data sources.
---

# M2 Project Risk Report

Use this skill for one output family only:

- project risk traffic-light Google Sheet (living 2-tab workbook with `Summary` and `Risk Items` tabs), with CSV fallback (`Templates/светофор_рисков_проекта.csv` and `Templates/project_risk_items.csv`).

## Required Start

1. Read `references/risk-schema.md` and `references/risk-evidence-rules.md`.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-risk-rules.md` and
   `../qa-management-roles/references/m2-role/m2-project-rollups.md`
   (the `m2_input` gate this report's conclusions roll up through).
4. Identify the target project. This is a living 2-tab Sheet, not a dated
   snapshot series (see `references/risk-schema.md`, Expected Output) —
   read the project's existing workbook first, if any, located in
   `20_M2_Project_Management/<Project>/private/`.
5. Read the smallest relevant evidence set:
   - extracted project risk/summary documents
   - project development plans
   - project metrics
   - business/project context and client expectations
   - workbook 1to1/status rows
   - `qa-1to1-analysis` findings when transcripts are one of the inputs
6. State source gaps before filling the template.

## Workflow

1. **Maintain Living 2-Tab Structure**:
   - `Summary` tab: exactly one row per project, updated in place. Update `Дата обновления` whenever any cell changes.
   - `Risk Items` tab: itemized risk register tracking each threat (`RSK-01`, `RSK-02`, etc.) with full lifecycle fields from earliest signal to closure.
2. **Itemize Threat Signals in `Risk Items`**:
   - Assign unique `Risk ID` (`RSK-01`, `RSK-02`, etc.).
   - Classify `Категория` (`delivery`, `QA process`, `staffing / continuity`, `communication / client`, `role / value`).
   - Set item-level `Уровень риска (Severity)` (`Низкий`, `Средний`, `Высокий`).
   - Record lifecycle dates: `Дата первого сигнала`, `Дата фиксации риска`, `Ожидаемая дата наступления (Expected Impact)`, `Дата последнего review (Last Reviewed)`, `Дата последнего изменения (Last Changed)`.
   - Record `Дата материализации` (when status is `Materialized`) or `Дата закрытия (Closed Date)` (when status is `Closed`).
   - Assign objective `Статус прогнозирования` (Prediction Status):
     - `Detected Early`: signal logged before expected impact with actionable lead time.
     - `Detected Late`: first logged after impact, missed milestone, or escalation.
     - `Not Detectable`: signal was genuinely unavailable in prior sources.
     - `Not Reviewed`: signal existed in sources but was unreviewed in time.
   - Set `Migration State` (`Normal` for active/curated items, `Legacy — detection status unavailable` for legacy unreviewed rows).
   - Set `Текущий статус` (`Open`, `Mitigating`, `Materialized`, `Accepted`, `Closed`).
   - Link concrete source evidence in `Ссылка на evidence_log`.
3. **Roll Up Primary Risk to `Summary` Tab**:
   - Select top active risk using deterministic tie-breaking:
     1. Highest item `Severity` (`Высокий` > `Средний` > `Низкий`);
     2. Earliest `Expected Impact Date` (missing dates deprioritized);
     3. `Detected Late` prioritized over `Detected Early`;
     4. Latest `Last Changed` timestamp.
   - Populate `ID ключевого риска`, `Ключевой ранний сигнал`, `Статус прогнозирования`, and `План действий M2` from the top active risk item.
   - Rate `Общий уровень риска` (`Низкий`, `Средний`, `Высокий`) and 4 dimension levels (`Риск delivery`, `Риск QA process`, `Риск staffing / continuity`, `Риск communication / client`).
   - Set `Уверенность в данных` (`Высокая`, `Средняя`, `Низкая`), `Owner` (`M2`), and `Следующий review` (`YYYY-MM-DD`).
4. **Trigger PM Case Review on Late/Materialized Risks**:
   - Any risk marked `Detected Late` or `Materialized` creates a candidate review trigger for `40_PM_Case_Library`.
5. **Sanitize Sensitive Context**:
   - Store in `20_M2_Project_Management/<Project>/private/`.
   - Never leak individual people-risk narratives or unshared HR details into project risk summaries.

## Risk Level Rules

Use the same three-level model as `qa-1to1-analysis`, expressed in Russian for all final project-risk documents.

Dictionary:

| Final CSV value | Legacy English alias | Definition |
| --- | --- | --- |
| `Низкий` | `Low` | Текущих проектных проблем не видно, и в ближайшей перспективе нет явных признаков ухудшения. |
| `Средний` | `Medium` | Текущего острого кризиса нет, но есть фоновые факторы, которые без управления могут привести к проблемам в delivery, QA/process, staffing, клиентской коммуникации, бизнес-ценности или роли нашей команды. |
| `Высокий` | `High` | Риск уже виден в фактах или устойчивых сигналах; нужны управленческие действия, mitigation, escalation или конкретный recovery plan. |

Use only the Russian `Final CSV value` terms in project-risk level fields and final documents. English aliases are for migration/interpretation only and must not appear as risk values in generated outputs.

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

## Outstaff Delivery Escalation Action-Plan Format

For a project following the department's Outstaff Delivery process standard (see `qa_department_standards`, Process Requirements, for the current rollout deadline and source reference), an internal risk (stop risk noticed before the client escalates) or a client escalation (negative feedback / official stop notice) requires a **second artifact** alongside this Sheet row, not a replacement for it: a numbered action plan posted to the project's strategy chat. This skill still owns the Sheet's risk-level record (Низкий/Средний/Высокий); drafting the action-plan text is in scope too when the user asks for it for one of these situations.

Each numbered item:

```text
Экшен-план | <Имя сотрудника> | <Project>

<Проблема, которую исправляет>
Что делаем: <конкретное действие>
Дедлайн: <ДД.ММ.ГГГГ>
Ответственный: <M2 / M1 / другой>
```

- Internal risk: tag Sales + PC + the employee's Head/RM in the strategy chat when the plan is posted; check in at least 2×/week until every item is done; escalate to `Replacement` if the plan stalls repeatedly.
- Client escalation: same plan shape, but relayed to the client through Sales (or the employee to their lead); request an interim and then a final client read on whether they see improvement; an official stop notice means running `Replacement` proactively in parallel, not waiting for the plan's outcome.
- Do not conflate this plan with the Sheet's `Комментарий`/action-plan cell content — the chat post is the real-time working artifact; the Sheet stays the current-state summary.

## Guardrails

- Do not output people risk traffic lights here.
- Do not output metrics or development plans here.
- Do not infer client dissatisfaction, staffing risk, or delivery risk from weak hints. When evidence is missing, mark the level according to the uncertainty rules and state exactly which evidence is missing.
- Do not list a current problem as a risk without explaining future impact on business/project/role.
- `project_risk` is unshared (M2/M3 only) and lives in `20_M2_Project_Management/<Project>/private/`.
