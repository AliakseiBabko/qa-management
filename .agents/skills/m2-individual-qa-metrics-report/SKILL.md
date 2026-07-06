---
name: m2-individual-qa-metrics-report
description: Create or update an individual QA metrics report for M2 project management. Use when preparing a metrics document for one QA engineer within a project or project-set context.
---

# M2 Individual QA Metrics Report

Use this skill for one output family only:

- individual QA metrics document inside a project scope

This is currently a placeholder skill boundary. Use it when the outcome must be an individual-level metrics artifact rather than a project-level metrics file.

## Required Start

1. Read `references/document-contract.md`.
2. Identify the target person and project scope.
3. Read individual metrics first, then source workbook rows, project context, and transcript-derived findings.

## Workflow

1. Produce one row per meaningful individual metric.
2. Prefer source scorecard dimensions when available:
   - delivery ownership
   - role effectiveness
   - quality / defects
   - automation
   - communication
   - documentation / reporting
   - growth focus
   - data completeness
3. Preserve score/status, trend, evidence, and next action.
4. Mark whether evidence is direct, partial, or absent.

## Guardrails

- Do not output project-level aggregate metrics here.
- Do not mix metrics with development-plan content.
- Keep this skill scoped to one expected document format.
- Do not convert manager opinions into numeric scores unless the source already provides a score or clear scale.
