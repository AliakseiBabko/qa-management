---
name: 1to1-prep-core
description: Shared preparation and output rules for QA 1:1 question lists (M1 people management and M2 project management). Defines common question derivation, sizing, privacy/neutrality, output formatting, and non-mutation guardrails for role-specific adapters like m1-1to1-prep and m2-1to1-prep.
---

# 1to1 Prep Core

Shared core framework for preparing upcoming QA 1:1 question lists. This is
the opposite direction from `qa-1to1-analysis` (which processes a 1:1 that
already happened): this skill family prepares for a 1:1 that hasn't happened yet.

Role-specific adapters inherit from this core:
- **`m1-1to1-prep`**: M1 people-management focus (motivation, loyalty, workload sustainability, career readiness, soft skills, people-risk signals, OKR progress, gated `People requiring attention` candidate flags).
- **`m2-1to1-prep`**: M2 project-management focus (performance calibration, metric gaps, technical development, project blockers, contribution caveats, preliminary-analysis questions from `m2_input`).

## Required Start

1. Read `references/prep-core-rules.md`.
2. Identify the target person and the management scope (M1 people vs. M2 project).
3. Read the relevant role-specific guidance (`../qa-management-roles/references/m1-role-rules.md` or `../qa-management-roles/references/m2-role/m2-metrics-attribution.md` / `../qa-management-roles/references/m2-role/m2-project-rollups.md`).
4. Read `../qa-management-roles/references/newcomer-support-rules.md` for newcomer/probation checks.

## Common Preparation Principles

1. **Evidence-Grounded Extraction**:
   Every question must trace to a concrete open gap, missing metric, unconfirmed caveat, overdue item, or risk signal. Do not pad prep with generic "how are things going" filler.

2. **Deduplication & Freshness**:
   Drop any question that has already been resolved or superseded by a more recent source.

3. **Proactive Newcomer Exploration**:
   If `Первый коммерческий проект` is unconfirmed or confirmed `Да` within the first month, proactively include specific questions on environment, process, and buddy/mentor effectiveness.

4. **Neutral Confidentiality Hygiene**:
   Private risk notes (`individual_risk`) or gated candidate flags (`People requiring attention` / `[Stale: review required]`) inform *what to explore neutrally*, NEVER *what to quote directly*. Frame inquiries as open, neutral exploration; never reveal the existence of private risk records or unconfirmed claims.

5. **Meeting Sizing & Dialogue Room**:
   Keep total question count focused (typically 4–8 questions across 2–4 clean sections). Leave ample room for the engineer to speak; do not over-script the entire conversation.

## Output Format Contract

Primary output is **transient, plain chat text (Markdown)**, formatted for direct use in the meeting:

```text
1to1 prep — <Person>, <date if given>

<Section 1>:
- ...

<Section 2>:
- ...
```

- Omit any section that has no real content.
- Do not create a Google Doc or Sheet by default.
- If the user explicitly asks to save a copy, save as a Google Doc named `1to1_prep_<YYYY-MM-DD>` in the appropriate folder (`10_M1_People_Management/<Person>/` for M1; `20_M2_Project_Management/<Project>/people/<Person>/` or `private/` for M2).

## Non-Mutation Guardrail

Preparation skills **never mutate or update target records** (`светофор_рисков.csv`, `1to1.csv`, `_m1_timeline`, `individual_metrics`, `project_risk`, `project_metrics`, `m2_input`). Preparation produces candidate questions; actual record updates occur only through post-1to1 analysis and documentation skills after the conversation takes place.
