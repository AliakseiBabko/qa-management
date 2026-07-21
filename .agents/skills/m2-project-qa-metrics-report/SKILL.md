---
name: m2-project-qa-metrics-report
description: Create or update a QA metrics report as a Google Sheet, with CSV fallback, for M2 project management. Use when preparing a metrics document for one project or for the QA engineers working on that project set.
---

# M2 Project QA Metrics Report

Use this skill for one output family only:

- project-level QA metrics Google Sheet, with CSV fallback

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Read `../qa-management-roles/references/m2-role-rules.md`.
4. Identify the target project and reporting period.
5. For DOCX/XLSX sources, first check whether an extracted copy already exists under `G:\My Drive\QA_Management\90_Storage\_System\extracts\source\YYYY-MM-DD\<Project>\...`.
6. If no suitable extract exists, use `.agents/scripts/qa_source_extract.py` to extract source documents into text-friendly Markdown, CSV, JSON, and manifest files before analysis.
7. Read project metrics first, then supporting development plans, risk summaries, business/project context, and workbook status rows.
8. Read individual QA metrics when they exist and use them as inputs to the project picture where they affect capacity, coverage, quality, visibility, delivery predictability, or risk.
9. If only individual metrics exist, aggregate cautiously and mark the data status as partial.

## Workflow

1. Produce one row per meaningful project QA metric.
2. Select a small project-specific set, usually 3-5 metrics, that can satisfy both client/project visibility and our M2 management needs without duplicating existing reporting streams.
3. If a project development plan is the main management artifact, include plan progress as a first-class metric: whether planned improvements are moving, blocked, accepted, or delivering visible value.
4. Use a balanced metric set when evidence exists:
   - quality
   - project/product movement
   - business/client value
   - development/delivery
   - our QA work and role/value
5. Prefer the scorecard dimensions used in source files when available:
   - stability
   - scalability
   - delivery predictability
   - communication
   - documentation / onboarding
   - automation / regression visibility
   - data completeness
6. For each row, preserve score/status, trend, evidence, owner, and next action.
7. Keep metric names stable across projects when the same management dimension is being measured.
8. When a project metric is built from individual QA metrics, explain the aggregation logic and separate personal contribution from project/system constraints.

## Guardrails

- Do not mix metrics output with development-plan output.
- Do not mix metrics output with project-risk output.
- Do not invent quantitative metrics. If a score is qualitative or source-derived, label the evidence and data status clearly.
- Do not include metrics that are impossible to measure regularly unless the row explicitly states the data gap.
- Do not read large extracted documents end to end by default. Start from manifest/JSON metadata and preview rows, then search or sample only the sheets/sections needed for the target metric question.
