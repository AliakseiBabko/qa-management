# M2 Project-Level Rollups

Scope: The 3-layer information architecture, two-phase project-level rollup process, m2_input preliminary-analysis gate, deterministic risk and confidence selection, outcome proxies synthesis, and gated cross-lane candidate contracts.

## Project-Level Rollups

### 1. The 3-Layer Information Architecture

M2 maintains project state across three distinct layers:
1. **Layer 1: Evidence & Measurements**: Raw measurements and per-person telemetry (`qa_process_metrics`, `individual_metrics`, `process_checklist`, M2 1:1 records, `evidence_log`). Never roll up directly to executive views without passing through Layer 2.
2. **Layer 2: Curated Project State & M2 Decisions**: Current-state records representing manager decisions: `project_metrics` (12-column composite identity `(Project, Metric Key, Role / Stream)` with 4-tier row taxonomy), `project_risk` (living 2-tab workbook: `Summary` + `Risk Items`), `individual_risk` (private), `m2_input` (decision gate), and `action_items`.
3. **Layer 3: Executive Rollup & Operational Registries**: Compact cross-project views mechanically derived from Layer 2: `_project_registry` (13-column executive sheet, 1,680 px width budget) and executive status reports.

### 2. The `m2_input` Preliminary-Analysis Decision Gate

`project_development_plan` and `project_risk` get updated by rolling up individual plans/metrics and `Вклад в проект: <Имя>` from `project_metrics` — but that rollup never runs purely mechanically. `m2_input` (see `Templates/m2_input.md`) is the explicit place for manager judgment, structured as a two-phase process:

1. **Preliminary analysis round.** Before combining anything, review individual plans and metrics, and write down specific, answerable questions (gaps, contradictions, unassigned risks). Append a new dated round to the project's `m2_input` Doc with these questions; leave "Ответ и общие соображения M2" empty.
2. **Wait for M2's answer.** Do not proceed to the rollup until the latest round's answer section is filled in. An empty answer section is a stop condition.
3. **Rollup round.** Once answered, combine individual plans/metrics with that round's answers as an explicit input into the updated `project_development_plan` and `project_risk`.

`m2_input` is one living Doc per project. Do not delete prior rounds. Track pending round age and addenda via `qa_manage.py gates`.

### 3. Deterministic Top-Risk Selection Algorithm

To eliminate subjectivity when updating `project_risk` Summary and `_project_registry` (Column 3: `Общий уровень риска`, Column 8: `Ранний сигнал / Прогноз`), the primary active risk is selected deterministically from the `Risk Items` tab:
1. **Filter Active**: Exclude `Closed` risks and `Migration State = Legacy`.
2. **Cascading Tie-Breaker**:
   - **Severity**: `Высокий` > `Средний` > `Низкий`.
   - **Expected Impact Date**: Earliest date first. Missing/empty dates are treated as `9999-99-99` (lowest impact-urgency) with a warning.
   - **Detection Timeliness**: `Detected Late` > `Detected Early` (late detections require executive visibility).
   - **Last Changed**: Most recent update timestamp.
3. **Default**: When no active risks exist, emit `Нет открытых рисков` with `Низкий` severity and `Качественный контроль в норме`.

### 4. Outcome Proxies & Composite Outcome Rollup

`_project_registry` Column 4 (`Текущее состояние QA / результат`) is one analytical statement combining process evidence, delivery facts, and evidence gaps. It must not be a link/date dump or a repeated status label. Use `Смешанный` when positive facts coexist with material validation gaps; use `Неизвестно` when evidence is insufficient. Do not treat a QA engineer's unvalidated opinion as `Позитивный`.

`_project_registry` Column 7 (`Цель клиента / Ценность QA (гипотеза M2)`) is a higher-level M2 inference about the client's product/business objective and the role or value of our QA team in achieving it. Do not fill this column with regression, coverage, leakage, or other operating metrics; those belong in process quality/current result. Label the view as an M2 hypothesis in the header, not repetitively in every cell.
1. **Standard Catalog (Formulas 1–6)**: Regression turnaround ($\le X$h), Production bug leakage ($\le Y\%$), Late-stage critical defects ($\le Z\%$), Blocker discovery ($\ge W\%$), Onboarding speed ($\le N$ days), Rework hours avoided ($\ge M$h).
2. **Zero-Denominator Semantics**: When no releases occurred in the period, record `No releases in period`.
3. **Composite Format**: `Baseline [<val>] → Показатель [<val>] → Target [<val>]` (e.g. `Leakage: Base 8% -> Curr 2% (Tgt <=3%) | Reg: Base 48h -> Curr 12h (Tgt <=8h)`).

### 5. Deterministic Confidence Synthesis

`_project_registry` Column 11 (`Уверенность в данных`) is synthesized deterministically (the registry intentionally has no redundant Owner column):
- $\text{Confidence} = \min(\text{outcome\_confidence}, \text{risk\_confidence})$
- When components diverge, display the breakdown (e.g. `Средняя (Out: Высокая, Risk: Средняя)`).

### 6. Gated Cross-Lane Candidate Contracts

1. **`People requiring attention` (`_project_registry` Column 9)**: Surfaces candidate flags from unlinked high private `individual_risk` or active onboarding milestones. If an underlying private risk is unreviewed for $>30\text{d}$, append `[Stale: review required]`. Consumed by `m1-1to1-prep` without mutating M1 records.
2. **PM Case Library Trigger**: Project risks marked `Detected Late` or `Materialized` generate a gated candidate for `40_PM_Case_Library` (resolved via `pm-case-knowledge-intake`).

### 7. Inactive Project Gate

Projects with `Статус проекта = 'Не активен'` are excluded from active registry rollups and briefings.
