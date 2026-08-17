# M2 Project Risk Schema

Scope: `project_risk` Sheet purpose, template, expected output, versioning, and row schema.

Primary final output is a Google Sheet in `20_M2_Project_Management\<Project>`,
with local CSV fallback. Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the project-risk document family.

## Templates

`project_risk` is a 2-tab living Google Sheet with local CSV fallbacks:

- `<repo-root>\Templates\светофор_рисков_проекта.csv` — `Summary` worksheet column schema (1 row per project executive summary).
- `<repo-root>\Templates\project_risk_items.csv` — `Risk Items` worksheet column schema (itemized risk register with full lifecycle).

## Expected Output

One living 2-tab project-risk Sheet per project in `20_M2_Project_Management\<Project>\private`.
- `Summary` tab: exactly one row per project, updated in place.
- `Risk Items` tab: itemized risk register tracking each risk from earliest signal to closure.

Target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>\private`

## Versioning

- Both worksheets are living tables, updated in place. Do not create dated snapshot files for routine updates.
- One row per project, always, on the Summary worksheet.
- `Summary` tab updates `Дата обновления` when any cell changes.
- `Risk Items` tab updates `Дата последнего изменения (Last Changed)` and `Дата последнего review (Last Reviewed)` on edit/review.
- Append source traceability to the project `evidence_log`.

## Schema — `Summary` Worksheet

Columns in `Templates\светофор_рисков_проекта.csv`:

1. `Проект` — project name.
2. `Дата обновления` — date the summary row was last modified.
3. `Общий уровень риска` — `Низкий`, `Средний`, `Высокий`.
4. `ID ключевого риска` — reference to the primary active risk item in the `Risk Items` tab (e.g. `RSK-01`).
5. `Ключевой ранний сигнал` — concise statement of earliest observable signal.
6. `Статус прогнозирования` — prediction status of key risk (`Detected Early`, `Detected Late`, `Not Detectable`, `Not Reviewed`).
7. `Риск delivery` — `Низкий`, `Средний`, `Высокий`.
8. `Риск QA process` — `Низкий`, `Средний`, `Высокий`.
9. `Риск staffing / continuity` — `Низкий`, `Средний`, `Высокий`.
10. `Риск communication / client` — `Низкий`, `Средний`, `Высокий`.
11. `План действий M2` — synthesized action plan.
12. `Уверенность в данных` — `Высокая`, `Средняя`, `Низкая`.
13. `Owner` — accountable owner.
14. `Следующий review` — next review date (`YYYY-MM-DD`).

## Schema — `Risk Items` Worksheet

Columns in `Templates\project_risk_items.csv`:

1. `Risk ID` — unique item identifier per project (e.g. `RSK-01`, `RSK-02`).
2. `Проект` — project name.
3. `Формулировка риска` — specific threat/risk statement.
4. `Категория` — `delivery`, `QA process`, `staffing / continuity`, `communication / client`, `role / value`.
5. `Уровень риска (Severity)` — `Низкий`, `Средний`, `Высокий`.
6. `Дата первого сигнала` — earliest observable signal timestamp (`YYYY-MM-DD`).
7. `Дата фиксации риска` — date the risk was logged in the register (`YYYY-MM-DD`).
8. `Ожидаемая дата наступления (Expected Impact)` — forecast impact date (`YYYY-MM-DD`).
9. `Дата материализации` — date risk materialized (`YYYY-MM-DD`, required when status is `Materialized`).
10. `Дата закрытия (Closed Date)` — date risk was closed (`YYYY-MM-DD`, required when status is `Closed`).
11. `Дата последнего review (Last Reviewed)` — date risk was last reviewed.
12. `Дата последнего изменения (Last Changed)` — timestamp of last substantive edit.
13. `Статус прогнозирования` (Prediction Status):
    - `Detected Early` — observable signal logged before expected impact with actionable lead time.
    - `Detected Late` — first logged after impact, missed milestone, or escalation.
    - `Not Detectable` — evidence demonstrates the signal was genuinely unavailable beforehand.
    - `Not Reviewed` — evidence was available in sources but unreviewed in time.
    *(Legacy rows have empty Prediction Status).*
14. `Обоснование статуса` — concrete evidence explaining the prediction status.
15. `Migration State`:
    - `Normal` — active or migrated item with complete prediction status.
    - `Legacy — detection status unavailable` — legacy imported item (excluded from prediction stats and top-risk selection).
16. `Уверенность в доказательствах (Evidence Confidence)` — `Высокая`, `Средняя`, `Низкая`.
17. `Ссылка на evidence_log` — pointer to source entry (e.g. `evidence_log: row 42`).
18. `Митигация` — concrete mitigation action.
19. `Owner` — accountable mitigation owner.
20. `Текущий статус` (Current Status) — `Open`, `Mitigating`, `Materialized`, `Accepted`, `Closed`.

### Conditional Date Consistency Rules:

- **Unmaterialized forecast risk**: $\text{First Signal} \le \text{Risk Logged} \le \text{Expected Impact}$.
- **Materialized or late-detected risk**: $\text{Expected Impact} \le \text{Materialization Date}$ when both dates known.

### Candidate PM Case Review Trigger:

Risks marked `Detected Late` or `Materialized` create a review candidate for `40_PM_Case_Library`. The review may resolve as `logged` or `no_case_logged`.
