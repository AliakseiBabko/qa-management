---
name: m2-project-qa-metrics-report
description: Create or update a QA metrics report for M2 project management. Use when preparing a metrics document for one project or for the QA engineers working on that project set.
---

# M2 Project QA Metrics Report

Use this skill for one output family only:

- project-level QA metrics document

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/m2-role-rules.md`.
3. Identify the target project and reporting period.
4. Read project metrics first, then supporting development plans, risk summaries, business/project context, and workbook status rows.
5. If only individual metrics exist, aggregate cautiously and mark the data status as partial.

## Workflow

1. Produce one row per meaningful project QA metric.
2. Use a balanced metric set when evidence exists:
   - quality
   - project/product movement
   - business/client value
   - development/delivery
   - our QA work and role/value
3. Prefer the scorecard dimensions used in source files when available:
   - stability
   - scalability
   - delivery predictability
   - communication
   - documentation / onboarding
   - automation / regression visibility
   - data completeness
4. For each row, preserve score/status, trend, evidence, owner, and next action.
5. Keep metric names stable across projects when the same management dimension is being measured.

## Guardrails

- Do not mix metrics output with development-plan output.
- Do not mix metrics output with project-risk output.
- Do not invent quantitative metrics. If a score is qualitative or source-derived, label the evidence and data status clearly.
- Do not include metrics that are impossible to measure regularly unless the row explicitly states the data gap.
