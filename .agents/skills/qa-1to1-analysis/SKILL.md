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
2. Read `references/analysis-contract.md` and
   `../qa-management-roles/references/transcript-signal-triage.md` (the
   name-recognition-is-not-sufficient / situation-with-structure filter
   this skill's own signal separation in step 4 below applies).
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
   - management-case candidates - a concrete client/stakeholder/team
     situation with a real approach-and-outcome shape, generalizable
     beyond this one project or person (not the same as a risk signal,
     which is about this project/person's current state) - see
     `pm-case-knowledge-roles/SKILL.md` for what counts. Most 1:1s
     produce none; don't force it.
5. State uncertainty explicitly when the source lacks evidence.

### Runtime and identity guardrails

- Use the repository's supported source-reader/pipeline path for Drive-backed
  transcripts. Do not probe the Google API ad hoc before checking the local
  reader and its documented authentication path.
- Resolve the person and project once against the canonical registries. Email,
  display name, transliteration, and queue scope are aliases, not independent
  identities; carry the resolved identity forward to every writer and closure
  check.
- Preserve source encoding end to end. On Windows, configure UTF-8 for both
  subprocess input and output before passing Russian text to a script. If a
  returned identity contains replacement characters or question marks, stop
  and correct the encoding before any append or overwrite.
- Treat approximate coverage percentages, AI-generated estimates, and similar
  measurements as directional evidence unless the denominator, collection
  method, and verification status are explicit. Record the estimate with its
  caveat and route the missing methodology as an open question when it could
  affect project judgment.

## Deliverable

Prepare structured findings that another skill can consume:

1. meeting date
2. dominant topic
3. concrete facts
4. people-management signals
5. project-management signals
6. possible action items
7. management-case candidates, if any (routed onward by the M1/M2 apply
   skill to `pm-case-knowledge-intake`, not written here)

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
