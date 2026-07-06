---
name: m2-project-qa-metrics-report
description: Create or update a QA metrics report for M2 project management. Use when preparing a metrics document for one project or for the QA engineers working on that project set.
---

# M2 Project QA Metrics Report

Use this skill for one output family only:

- project-level QA metrics document

## Required Start

1. Read `references/document-contract.md`.
2. Identify the target project and reporting period.
3. Read project metrics first, then supporting development plans, risk summaries, and workbook status rows.
4. If only individual metrics exist, aggregate cautiously and mark the data status as partial.

## Workflow

1. Produce one row per meaningful project QA metric.
2. Prefer the scorecard dimensions used in source files when available:
   - stability
   - scalability
   - delivery predictability
   - communication
   - documentation / onboarding
   - automation / regression visibility
   - data completeness
3. For each row, preserve score/status, trend, evidence, owner, and next action.
4. Keep metric names stable across projects when the same management dimension is being measured.

## Guardrails

- Do not mix metrics output with development-plan output.
- Do not mix metrics output with project-risk output.
- Do not invent quantitative metrics. If a score is qualitative or source-derived, label the evidence and data status clearly.
