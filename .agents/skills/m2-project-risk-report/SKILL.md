---
name: m2-project-risk-report
description: Create or update a project risk traffic-light document for M2 project management. Use when producing a project-focused risk report from QA 1to1 findings, project transcripts, delivery signals, or other project data sources.
---

# M2 Project Risk Report

Use this skill for one output family only:

- project risk traffic-light file

## Required Start

1. Read `references/document-contract.md`.
2. Identify the target project and reporting snapshot date.
3. Read the smallest relevant evidence set:
   - extracted project risk/summary documents
   - project development plans
   - project metrics
   - workbook 1to1/status rows
   - `qa-1to1-analysis` findings when transcripts are one of the inputs
4. State source gaps before filling the template.

## Workflow

1. Build one project-level row per project/snapshot.
2. Rate the overall project risk as one of: `Low`, `Medium`, `High`, `Critical`, or `Unknown`.
3. Separate risk dimensions:
   - delivery
   - QA process
   - staffing / continuity
   - communication / client
4. Keep comments factual and evidence-linked.
5. Write the action plan as concrete next management steps with an owner and next review date.

## Guardrails

- Do not output people risk traffic lights here.
- Do not output metrics or development plans here.
- Do not infer client dissatisfaction, staffing risk, or delivery risk from weak hints. Use `Unknown` when evidence is missing.
