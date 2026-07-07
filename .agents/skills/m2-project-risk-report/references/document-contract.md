# Document Contract

Primary final output is a Google Sheet in `20_M2_Project_Management\<Project>`,
with local CSV fallback. Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the project-risk document family.

## Template

`<repo-root>\Templates\светофор_рисков_проекта.csv`

## Expected Output

One project-risk traffic-light document per reporting snapshot.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>`

Suggested naming pattern:

`светофор_рисков_проекта_YYYY-MM-DD.csv`

## Versioning

- Use the living project-local `project_risk` file for current state, and append
  source traceability to the project `evidence_log`.
- Do not overwrite an existing formal dated project-risk snapshot by default.
- If the target snapshot-date file already exists, create the next versioned file with a `_vN` suffix before `.csv`, for example `_v2` or `_v3`.
- Update an existing project-risk snapshot in place only when the user explicitly asks for revision.

## Schema

Use exactly the columns in `Templates\светофор_рисков_проекта.csv`:

1. `Проект`
2. `Период / snapshot date`
3. `Общий уровень риска`
4. `Риск delivery`
5. `Риск QA process`
6. `Риск staffing / continuity`
7. `Риск communication / client`
8. `Evidence / источники`
9. `Комментарии`
10. `План действий`
11. `Owner`
12. `Следующий review`

## Inputs

- QA 1to1 findings
- project transcripts
- delivery/process notes
- staffing or project context data
- extracted source corpus under `G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`

## Evidence Rules

- Prefer direct project evidence over general impressions.
- Keep people-performance concerns out of the project-risk file unless they create explicit project continuity, delivery, or client risk.
- Put source names or dated meetings in `Evidence / источники`.
- Name the feedback path when it affects confidence: direct client, intermediary, DC/QA Lead, team, or employee self-report.
- Treat hidden topology as evidence gap and risk signal for active projects: unknown streams, real team size, DC/PM ownership, vendor/intermediary chain, client path, tender/contract horizon, or security/location constraints.
- Use only `Низкий`, `Средний`, or `Высокий` in risk level fields and final documents. Do not use `Low`, `Medium`, `High`, `Critical`, or `Unknown` as final risk values.
- Risk-level dictionary:
  - `Низкий` = legacy `Low`: текущих проектных проблем не видно, и в ближайшей перспективе нет явных признаков ухудшения.
  - `Средний` = legacy `Medium`: текущего острого кризиса нет, но есть фоновые факторы, которые без управления могут привести к проблемам в delivery, QA/process, staffing, клиентской коммуникации, бизнес-ценности или роли нашей команды.
  - `Высокий` = legacy `High`: риск уже виден в фактах или устойчивых сигналах; нужны управленческие действия, mitigation, escalation или конкретный recovery plan.
- English aliases are for migration/interpretation only and must not appear as risk values in generated outputs.
- Treat missing visibility as a risk signal for active projects. If a project is not at the very beginning and the current level cannot be detected because metrics, delivery status, QA-process evidence, or client/team feedback are unavailable, set the affected level to at least `Средний` and explain the evidence gap in comments.
- For a genuinely new project with insufficient evidence, use `Средний` by default unless concrete facts support `Низкий` or `Высокий`.
- State why the risk matters and what future harm it can cause.
- Separate project/stake risk from individual performance risk. Do not lower or raise a project risk solely because one QA is strong or weak unless that fact affects delivery, continuity, client trust, or role value.
- Keep sensitive internal details out of final comments unless they are necessary for the management action. If location, security, vendor-chain, or client-path facts are needed, phrase them as concise risk context.

## Risk Interpretation Notes

- If a project-side stakeholder questions the need for QA or believes QA can be replaced without loss, treat this as an `our-role` / business-value risk and map it to communication/client or QA-process dimensions as appropriate.
- If the project is paused, contract end is near, tender horizon is known, or client dissatisfaction has already affected continuation, reflect that in the overall level and action plan.
- If a junior or newly onboarded QA is placed into a senior/project-critical expectation, classify the risk by project impact, not by personal criticism.

## Rule

Keep this skill scoped to one project-risk document format only.
