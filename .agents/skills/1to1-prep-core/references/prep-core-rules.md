# 1to1 Prep Core Rules

Scope: Common preparation workflow, question derivation, confidentiality hygiene, output structure, and non-mutation boundaries across all 1:1 question-prep skills.

## 1. Purpose & Boundary

Use this reference for common 1:1 question-list preparation rules.
- **M1 Role Adapter (`m1-1to1-prep`)**: owns people-management 1:1 preparation (see `../../qa-management-roles/references/m1-role-rules.md`).
- **M2 Role Adapter (`m2-1to1-prep`)**: owns project-management 1:1 preparation (see `../../qa-management-roles/references/m2-role/m2-metrics-attribution.md` and `../../qa-management-roles/references/m2-role/m2-project-rollups.md`).
- **Newcomer Checks**: see `../../qa-management-roles/references/newcomer-support-rules.md`.

Neither adapter substitutes for the other, but both follow the unified rules defined here.

## 2. Core Preparation Principles

### 2.1 Evidence-Grounded Derivation
- Every question must trace directly to a documented gap, unconfirmed status, overdue milestone, or specific risk signal.
- Never use generic small talk or ungrounded filler questions.
- If a person has calm or empty records with no open gaps, state that plainly and include a brief, light confirmation question rather than inventing artificial problems.

### 2.2 Freshness & Deduplication
- Pull candidate questions starting from the most authoritative current-state records.
- Drop any item that has already been resolved, closed, or answered by a fresher source.
- Do not re-ask about a metric that now has a recorded value, or an action item that has already been marked done.

### 2.3 Confidentiality & Neutral Questioning
- **Private Risk Records (`individual_risk`)**: Use private risk records solely to determine *what topic to probe*, never to decide *what phrasing to use*.
- Formulate questions neutrally and openly (e.g. "Walk me through how the last few release cycles went"). Never quote, summarize, or hint at the existence of private notes.
- **Gated Attention Flags (`People requiring attention` / `[Stale: review required]` in `_project_registry`)**: Use flags as exploratory signals to check for unexpressed friction or support needs; never assert unconfirmed project-level claims as established facts.

### 2.4 Sizing & Structure
- Normal sizing: **4–8 questions total**, grouped into 2–4 short topical sections.
- Keep questions open and conversational; leave room for the engineer to speak without scripting the entire meeting.
- Omit any section that has no real content.

## 3. Output Format Contract

### 3.1 Default Transient Output
Primary output is **chat-ready Markdown text**, ready to copy into meeting notes or chat:

```text
1to1 prep — <Person>, <date if given>

<Section 1 Heading>:
- <Question 1>
- <Question 2>

<Section 2 Heading>:
- <Question 3>
- <Question 4>
```

### 3.2 Optional Archival Saving
- Do not create or save a Google Doc/Sheet by default.
- If the user explicitly asks to save a copy:
  - Save as a Google Doc titled `1to1_prep_<YYYY-MM-DD>`.
  - Target folder for M1: `10_M1_People_Management/<Person>/`.
  - Target folder for M2: `20_M2_Project_Management/<Project>/people/<Person>/` (or `private/`).
  - Do not overwrite previous dated preps; use versioning if the same date exists.

## 4. Non-Mutation Guardrail

Preparation skills generate prospective questions for an upcoming meeting. They **must never mutate or update target records**:
- Do not write into or update `светофор_рисков.csv`, `1to1.csv`, `_m1_timeline`, `individual_metrics`, `project_risk`, `project_metrics`, `m2_input`, or OKR documents.
- All record updates, risk re-gradings, metric values, and timeline event closures must occur only after the actual 1:1 takes place, via the respective post-meeting skills (`qa-1to1-analysis`, `m1-people-risk-report`, `m1-people-1to1-file`, `m1-individual-development-plan`, `m2-1to1-apply`, `m2-individual-qa-metrics-report`).
