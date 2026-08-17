---
name: m2-project-qa-metrics-report
description: Create or update a QA metrics report as a Google Sheet (12-column composite identity model), with CSV fallback, for M2 project management. Use when preparing a metrics document for one project or for the QA engineers working on that project set.
---

# M2 Project QA Metrics Report

Use this skill for one output family only:

- project-level QA metrics Google Sheet (`project_metrics`), with CSV fallback (`Templates/метрики_проекта_qa.csv`).

## Required Start

1. Read `references/project-metrics-schema.md` and
   `references/qa-process-metrics-schema.md`. Read
   `references/extended-metrics-catalog.md` too when adding an
   Extended-tier `qa_process_metrics` row or extracting a raw DOCX/XLSX
   source (steps 5-6 below).
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, `../qa-management-roles/references/google-workspace/search-source-extraction.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-metrics-calibration.md`
   and `../qa-management-roles/references/m2-role/m2-metrics-attribution.md`
   (which cascade layer an automation or leakage fact belongs to).
4. Identify the target project and reporting period.
5. For DOCX/XLSX sources, first check whether an extracted copy already exists under `G:\My Drive\QA_Management\90_Storage\_System\extracts\source\YYYY-MM-DD\<Project>\...`.
6. If no suitable extract exists, use `.agents/scripts/qa_source_extract.py` to extract source documents into text-friendly Markdown, CSV, JSON, and manifest files before analysis.
7. Read project metrics first, then supporting development plans, risk summaries, business/project context, and workbook status rows.
8. Read individual QA metrics when they exist and use them as inputs to the project picture where they affect capacity, coverage, quality, visibility, delivery predictability, or risk.
9. If only individual metrics exist, aggregate cautiously and mark the data status as partial.

## Workflow

1. **Composite Row Identity & Structure**:
   Maintain `project_metrics` using the 12-column composite identity:
   `(Project, Metric Key, Role / Stream)`
   where project-wide rows use `Role / Stream = Project-wide`.

2. **Maintain 4-Tier Row Taxonomy**:
   - **Canonical Context Rows**:
     - `Статус проекта` — `Активен` or `Не активен`.
     - `Engagement outlook` — `YYYY-MM-DD [Contractual] — <Continuation Outlook> (<Confidence>)`.
     - `Цель клиента / Ценность QA` — stated client objective with alignment flag.
     - `Фокус M2` — technical/delivery management focus.
     - `Статус согласования (Alignment)` — `Согласовано`, `В процессе калибровки`, or `Расхождение ожиданий`.
     - `Сигнал capacity` — delivery/staffing capacity alert.
   - **Outcome Proxy Rows** (`Outcome proxy: <Name>`):
     Select 1 to 3 operational business outcome proxies connecting QA activities to client business value (e.g. `Regression turnaround duration`, `Production bug leakage`, `Blocker discovery lead time`, `Onboarding speed`).
     Maintain `Baseline`, `Показатель` (Current Value), `Target`, `Evidence Status`, `Data Confidence`, `Пояснение`, `Owner`, `Тренд`.
   - **QA Process Quality Overview**:
     Summary overview of QA execution quality.
   - **Person Contribution Attribution Rows**:
     `Вклад в проект: <Person>` with explicit `Role / Stream` (e.g. `AQA`, `Manual QA`) and status `Позитивный`, `Смешанный`, `Негативный`.

3. **Apply Outcome Proxies Playbook**:
   - *Formula 1 (Regression Duration)*: $(\text{Baseline} - \text{Current})$ turnaround duration in days/hours per cycle $\rightarrow$ Delivery Speed / Lead Time.
   - *Formula 2 (Production Leakage)*: Escaped P0/Critical defects per release $\rightarrow$ Release Stability.
   - *Formula 3 (Late-Stage Critical Defects)*: Critical defects caught on Staging/RC + Production per release.
   - *Formula 4 (Blocker Discovery Ratio)*: Ratio of critical defects found in Dev/Sprint pre-test vs. all stages $\rightarrow$ Decision Predictability (Shift-Left).
   - *Formula 5 (Onboarding / Ramp-up Speed)*: Working days from start to first accepted test suite/commit $\rightarrow$ Continuity Efficiency.
   - *Formula 6 (Estimated Rework Hours Avoided)*: $(\text{Critical bugs caught pre-prod}) \times (\text{Prod fix hours} - \text{Pre-prod fix hours})$ (requires project-specific estimates and `estimated` / `assumption-based` status).

4. **Enforce Epistemic & Zero-Denominator Rules**:
   - **Evidence Status**: Set explicitly to `observed`, `estimated`, `projected`, or `assumption-based`.
   - **Data Confidence**: Set explicitly to `Высокая`, `Средняя`, or `Низкая`.
   - **Zero-Denominator Events**: For periods with zero releases or zero incidents, record the factual text `No releases in period` or `Not applicable (no incidents)` with `Evidence Status = observed`. Do NOT report numeric zero, 0%, or 100% false certainties.
   - **Not Applicable vs. No Data Yet**:
     - `Not applicable`: metric does not apply to this project's phase or stream.
     - `No data yet`: metric applies, but data collection has not begun.

5. **Expectation Gap Rule**:
   - When `Статус согласования (Alignment) = Расхождение ожиданий`, open an `m2_input` question or an action item.
   - An active project risk item is created only when credible impact exists on delivery, client trust, staffing, or contract continuation.

## Guardrails

- Do not mix metrics output with development-plan narrative.
- Do not mix metrics output with project-risk item registers.
- Do not invent quantitative metrics. If a score is qualitative or estimated, label `Evidence Status` and `Data Confidence` clearly.
- `project_metrics` is unshared (M2/M3 only) and lives in `20_M2_Project_Management/<Project>/private/`.
