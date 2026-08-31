---
name: internal-assessment-feedback
description: Produce an internal competency-assessment feedback document (Google Doc, Markdown fallback) for one named engineer from their submitted self-assessment matrix plus the session transcript, assessed against the department's own grade matrix and the governing assessment process pages. Covers full grade assessments and partial/single-block sessions. Use after an internal assessment or pre-assessment has been recorded and its result needs writing up as publishable feedback, per-topic matrix ratings, and shared-evaluation-table ratings; not for client-facing interviews (use external-interview-feedback) and not for 1:1s (use qa-1to1-analysis).
---

# Internal Assessment Feedback

One session in, one dated feedback document out, plus an
`_assessment_index` row. Load `../interview-assessment-roles/SKILL.md`
first - it holds the lane boundary, the evidence discipline, the storage
and indexing rules, and the privacy rules. The output form is
`Templates/internal_assessment_feedback.md`.

## Inputs

Three, and the pass is weaker for every one that is missing - say which
were unavailable rather than proceeding silently:

1. **The session transcript** - speaker-labeled. If the user has a
   recording but no transcript, `video-trim-and-audio-extract` produces
   one; do not attempt to assess from a recording directly.
2. **The candidate's self-assessment matrix** - the spreadsheet the
   candidate filled in before the session. Read it through the Sheets
   API. It supplies four things nothing else does: the target grade, the
   expected level per topic, the candidate's own per-topic self-rating,
   and their written self-description per topic.
3. **The governing process documentation** - the assessment format's own
   pages (scope, duration, assessor roles, feedback structure,
   calibration rules) plus the topic question banks and any cheat sheet
   the department publishes. Fetch them; do not assess from memory.

Optional but useful: the candidate's earlier sessions in this lane (via
`find_index`), so a previously-noted gap or an untested block gets
priority attention this time.

## Workflow

1. **Establish the bar before reading the transcript.** From the matrix:
   target grade, blocks in scope, expected level per topic. From the
   process pages: which format this session was, its agreed duration and
   assessor count, the required feedback structure, the rating
   vocabulary. Note the candidate's profile (manual QA, AQA) - it
   calibrates how much depth each block is expected to carry.
2. **Extract the session against the matrix's own topics.** Use
   `meeting-transcript-extract` in caller-defined-taxonomy mode, with the
   in-scope matrix topics as the buckets. Do not use the default meeting
   schema: facts/decisions/action items is the wrong shape for an
   evaluation, and it will quietly drop the thing that matters most -
   whether an answer was unaided.
3. **Tag every extracted answer** as unaided, partially led, led, or not
   covered, and for a led answer record who supplied the frame. This
   distinction drives the whole document; recover it now while the
   transcript is in front of you, not at write-up time.
4. **Rate each in-scope topic** against the expected level for the target
   grade, and against the candidate's own self-rating. Where they differ,
   in either direction, that is a finding.
5. **Decide the verdict** for each block in scope: does it clear the
   target grade's bar. Keep it free of conditions. If the session did not
   cover enough to decide a block, say that instead of guessing.
6. **Classify each gap** as a development-plan item or a re-sit
   condition, explicitly. Conflating them is the most consequential error
   this document can make - one goes to the candidate's manager, the
   other blocks a grade.
7. **Check the process shape** before writing anything in the process
   notes: confirm which lighter-than-maximal aspects were the agreed
   design for this format and this candidate profile, and separate those
   from real observations worth acting on. See the roles skill's rule.
8. **Write the Markdown** per `Templates/internal_assessment_feedback.md`,
   in the language the session was conducted in, keeping grade labels and
   rating vocabulary in their original form.
9. **Publish** with `publish_markdown_doc.py --folder-path
   "60_Assessments_And_Interviews/internal_assessments/<Person>"` and the
   name from `assessment_workspace_layout.session_document_name(
   "assessment_feedback", <date>, <Person>)`. Create the type/person
   folders via the layout module's `ensure_*` helpers only now, when a
   real session needs them.
10. **Log the `_assessment_index` row**, then `_skill_invocations` with
    `source_type: assessment_transcript`, then the pass's closing
    telemetry via `record_agent_session.py`.

## Cross-Checks

Offer these, do not perform them silently - each is a separate skill's
lane:

- A gap that should become a development-plan item -> M1's
  `m1-individual-development-plan` (or M2's, if the person is
  project-staffed rather than M1-managed). This skill never edits those
  documents.
- A department-wide requirement or a contradiction in the governing
  process pages -> `qa-department-standards-intake`.
- A management pattern worth generalizing -> `pm-case-knowledge-intake`.
- A people-risk signal (the person is stressed, considering leaving,
  overloaded) -> M1's own chain via `qa-1to1-analysis`; an assessment
  transcript is a poor evidence base for it, so flag it rather than
  scoring it.

## Guardrails

- Never assess a topic the matrix did not put in scope for this session,
  and never let an out-of-scope block appear as a gap.
- Never present a led answer as demonstrated competency, and never let
  an interviewer's own monologue become evidence about the candidate.
- Never soften a real gap into a compliment, and never characterize the
  person rather than their answers.
- Never write a verdict the transcript cannot support, and never leave
  the verdict ambiguous by attaching a condition to it.
- Never rewrite a previous session's document - a new session gets a new
  dated document; only a re-publish of *this* session's own document
  replaces a body.
- Never fold the candidate's project explanations into a Project
  Knowledge document (roles skill, boundary rules).
