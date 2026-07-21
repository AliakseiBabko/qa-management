---
name: qa-1to1-analysis
description: Analyze 1to1 transcripts with QA engineers and extract reusable structured findings for both M1 people management and M2 project management. Use when classifying the dominant meeting topic, identifying concrete facts, separating people-side and project-side signals, calibrating risk signals, or preparing evidence for downstream 1to1 Google Sheet/CSV-fallback writer and risk-report skills.
---

# QA 1to1 Analysis

Use this skill for transcript analysis only. It does not own final report-file creation.

Default language:

- Use Russian for analysis findings and report-ready text unless the user explicitly requests another language.
- Preserve English terms, definitions, or transcript citations when they are part of the source or normal company vocabulary.
- Keep final wording suitable for Russian business documents.

Default transcript location:

- raw intake: `G:\My Drive\QA_Management\00_Inbox`

Once a transcript's facts are extracted, move it to
`90_Storage\Reference\Source_Documents\<Project>` (if still useful as durable
reference) or `90_Storage\Processed_Sources` — there is no separate "processed" holding
folder.

## Required Start

1. Read the raw transcript, transcript summary, or explicit user notes first.
2. Read `references/analysis-contract.md`.
3. Load only the needed references:
   - `references/topic-selection.md`
   - `references/risk-signals.md`
   - `references/writing-rules.md`
   - `references/runtime-notes.md` only for runtime-specific invocation differences

## Workflow

1. Determine who the conversation is about and when it happened.
2. Classify the dominant meeting topic.
3. Extract the strongest concrete facts from the transcript.
4. Separate signals into:
   - current-state facts
   - people-risk signals
   - project-risk signals
   - actions or follow-ups
5. State uncertainty explicitly when the source lacks evidence.

## Deliverable

Prepare structured findings that another skill can consume:

1. meeting date
2. dominant topic
3. concrete facts
4. people-management signals
5. project-management signals
6. possible action items

## Guardrails

- Do not generate a final role-specific report here.
- Do not write `Templates/1to1.csv` outputs here; use an M1 or M2 writer skill for that.
- Do not invent facts not supported by the transcript.
- Do not translate weak hints into strong conclusions without evidence.

## Maintenance

- Keep this file procedural.
- Put topic rules in `references/topic-selection.md`.
- Put risk-signal guidance in `references/risk-signals.md`.
- Put wording quality rules in `references/writing-rules.md`.
