---
name: external-interview-feedback
description: Produce an external client-interview debrief document (Google Doc, Markdown fallback) for one named engineer from the CV the client received plus the interview transcript - the client's real questions, how the candidate landed, where the CV and the answers diverged, what to fix before the next interview, and reusable signals about that client's bar. Use after a client-side interview has been recorded and needs writing up; not for internal grade assessments (use internal-assessment-feedback) and not for 1:1s (use qa-1to1-analysis).
---

# External Interview Feedback

One client interview in, one dated debrief document out, plus an
`_assessment_index` row. Load `../interview-assessment-roles/SKILL.md`
first - it holds the lane boundary, the evidence discipline, the storage
and indexing rules, and the privacy rules. The output form is
`Templates/external_interview_feedback.md`.

The question here is not "does this engineer hold a grade" - it is "did
this engineer win this seat, and what would make the next one land". The
bar is the client's, it is partly unstated, and it is not necessarily
fair. Assess against what the client actually asked, plus the CV they
received; never against our internal grade matrix.

## Inputs

1. **The interview transcript** - speaker-labeled. From a recording,
   `video-trim-and-audio-extract` produces one first.
2. **The CV the client received** - the exact version, since the
   candidate is accountable for what that document claims. If only a
   different version is available, say so; a CV-vs-answers finding
   against the wrong version is worse than none.
3. **The seat's requirements**, if we hold them - the client brief, the
   role description, the rate band, the stack.

Optional: our standard preparation material for this client, and the
candidate's earlier rounds in this lane (via `find_index`), so a repeat
failure is visible as a repeat rather than a fresh finding.

## Workflow

1. **Reconstruct what the client was testing for** from where they spent
   their time, not from the job description. If the transcript does not
   support an inference, record that it does not.
2. **Extract the session by theme.** Use `meeting-transcript-extract` in
   caller-defined-taxonomy mode with the themes the client actually
   raised as buckets - technical depth, domain/business framing,
   self-presentation and legend coherence, AI usage, English, reaction to
   pressure, and whether the candidate asked anything back. Derive the
   buckets from this transcript; do not impose a fixed list.
3. **Diff the CV against the answers.** For each claim the client
   probed, decide whether it held, needs rehearsal, or was overstated.
   Say "overstated" plainly when it is - softening it here is what causes
   the same failure at the next interview. Claims the client never
   touched are not findings; list them as what to expect next time.
4. **Locate the turn**, if the interview turned - the specific question
   where the room was lost or won. One concrete moment is worth more to
   the candidate than a page of general advice.
5. **For each theme, state what a winning answer needed** at this seat's
   level. A theme without this line is a transcript summary, not a
   debrief.
6. **Give the read**, with its basis and your confidence - or the actual
   result if it is already known, in which case skip the prediction.
   Where the seat was simply above the candidate's current level, say so
   as the headline rather than distributing it across small fixes.
7. **Write the gaps as owned actions**, each labeled by kind (knowledge,
   rehearsal, CV wording, delivery) since the remedies differ, with an
   owner: the candidate, their M-manager, or whoever prepares candidates
   for this client.
8. **Write the Markdown** per `Templates/external_interview_feedback.md`,
   quoting the client's questions in the language they were asked.
9. **Publish** with `publish_markdown_doc.py --folder-path
   "60_Assessments_And_Interviews/external_interviews/<Person>"` and the
   name from `assessment_workspace_layout.session_document_name(
   "interview_feedback", <date>, <Person>)`, creating the type/person
   folders via the layout module's `ensure_*` helpers only now.
10. **Log the `_assessment_index` row**, then `_skill_invocations` with
    `source_type: external_interview_transcript`, then the pass's closing
    telemetry via `record_agent_session.py`.

## Cross-Checks

Offer, never perform silently:

- A recurring client-side pattern (what this client always asks, how they
  probe, what they let slide) -> `pm-case-knowledge-intake`.
- A department-wide preparation requirement this exposes - a missing
  standard answer, an unprepared topic that keeps recurring across
  candidates -> `qa-department-standards-intake`.
- A CV that needs rewording, or preparation the person's manager owns ->
  the relevant M1/M2 development-plan skill. This skill never edits a CV
  or a development plan itself.
- Genuine people-risk signals (the candidate is demoralized after a
  failed round) -> M1's chain; flag rather than score.

## Guardrails

- Never assess against our internal grade matrix - wrong bar, wrong
  audience, and it will read as a competency verdict the client never
  made.
- Never record a judgment about the client-side interviewers' own
  competence, however weak their questions were. They are context.
- Never state an outcome as fact when it is an inference, and never
  present an inference with no transcript basis at all.
- Never turn the debrief into a staffing or rate recommendation.
- Never rewrite an earlier round's document - each round gets its own
  dated document, so a repeat pattern stays visible across them.
- Never quietly assess against a CV version the client did not receive.
