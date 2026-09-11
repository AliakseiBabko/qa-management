---
name: m2-individual-qa-metrics-report
description: Create or update an individual QA metrics report as a Google Sheet, with CSV fallback, for M2 project management. Use when preparing a metrics document for one QA engineer within a project or project-set context.
---

# M2 Individual QA Metrics Report

Use this skill for one output family only:

- individual QA metrics Google Sheet inside a project scope, with CSV fallback

This is currently a placeholder skill boundary. Use it when the outcome must be an individual-level metrics artifact rather than a project-level metrics file.

## Required Start

1. Read `references/individual-metrics-schema.md` (it owns the rule that
   `Перформанс` and `Git-активность за спринт (AQA)` are trend metrics
   scoped to one person's own history, never cross-person or
   cross-project comparisons). Read
   `references/internal-variant.md` too if also writing or updating the
   private `individual_risk` Sheet.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-metrics-calibration.md`
   and `../qa-management-roles/references/m2-role/m2-metrics-attribution.md`
   (which cascade layer an automation or leakage fact belongs to).
4. Identify the target person and project scope.
5. Read individual metrics first, then source workbook rows, project context, and transcript-derived findings.

## Workflow

1. Produce one row per meaningful individual metric. The 5 Core rows
   from `Templates\метрики_qa_по_проекту.md` always exist, including the
   per-sprint baseline pair (`Перформанс`, `Git-активность за спринт
   (AQA)`) — blank with a reason, or `Не применимо (manual QA stream)`
   for git on a manual stream.
2. Include metrics that show the person's project value, role growth, visibility, trust, delivery impact, and quality impact when evidence exists.
3. Prefer source scorecard dimensions when available:
   - delivery ownership
   - role effectiveness
   - quality / defects
   - automation
   - communication
   - documentation / reporting
   - growth focus
   - data completeness
4. Preserve score/status, trend, evidence, and next action.
5. Mark whether evidence is direct, partial, or absent.

## Guardrails

- Do not output project-level aggregate metrics here.
- Do not mix metrics with development-plan content.
- Keep this skill scoped to one expected document format.
- Do not convert manager opinions into numeric scores unless the source already provides a score or clear scale.
- Do not use abstract goals as metrics. Convert them into observable indicators or leave the data gap explicit.
- External git-metrics collector figures are not an input here by
  default. They enter only when `_metrics_collector_registry` marks that
  person's `Metrics validity` as `Reliable` (the collector grades against
  whatever branch is checked out when it finds no `main`/`master` trunk,
  and its direct-to-main anomaly misfires on squash-merge repos) - see
  `m2-git-metrics-onboarding`, which owns that tool and its registry, not
  this skill.
