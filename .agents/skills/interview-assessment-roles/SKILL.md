---
name: interview-assessment-roles
description: Shared rules for the Assessments & Interviews lane (60_Assessments_And_Interviews) - per-session competency assessment and interview debrief documents about one named person, produced from a recorded session plus the person's own submitted material. Distinct from M1 people management (longitudinal current-state per person), M2 project management (per-project), Project Knowledge (per-project understanding), and the PM Case Library. Use when deciding whether a session belongs in this lane, what its output document must not claim, or how to store and index it.
---

# Interview & Assessment Roles

Shared context for `internal-assessment-feedback` and
`external-interview-feedback`. This skill owns the lane boundary, the
evidence discipline, storage/indexing, and the privacy rules. It does not
own either output format - the two skills and their templates
(`Templates/internal_assessment_feedback.md`,
`Templates/external_interview_feedback.md`) own that.

## What This Lane Is, And Isn't

One session, one dated document about one named person. Per-session and
append-only: a new session never rewrites an earlier session's document,
because the earlier document is the record of what was true at that
meeting. This is the opposite convention from M1/M2 current-state
documents, which are updated in place.

Two scored session types, plus a catch-all:

- **`internal_assessment`** - our own competency assessment against our
  own grade matrix. The question is *does this engineer hold this grade*.
  Inputs: the person's self-assessment matrix and the session transcript.
- **`external_interview`** - a client-side interview for a seat. The
  question is *did this engineer win this seat, and what would make the
  next one land*. Inputs: the CV the client received and the session
  transcript.
- **`other_interview`** - a genuinely different session (mock interview,
  internal role interview, screening) with no owning skill yet. Store it
  here rather than forcing it into one of the two scored forms; do not
  invent a scored verdict for it.

Boundaries with the neighbouring lanes:

- **vs M1 people management (`10_M1_People_Management`)** - M1 owns the
  durable per-person record: the longitudinal 1:1 file, risk status, the
  development plan, PR timing. This lane owns one meeting's assessment.
  A gap found here becomes a development-plan item **in M1's documents**,
  through M1's own skills - this lane never edits them, and never
  restates a person's overall risk status.
- **vs `qa-1to1-analysis` and the 1:1 skills** - a 1:1 is a management
  conversation with someone on your team, processed for people/project
  signals. An assessment or interview is an evaluation event with a
  verdict, a defined scope, and an external reader. Same input shape
  (a transcript), different question and different output; never route an
  assessment through the 1:1 chain, and never produce a grade verdict
  from a 1:1.
- **vs M2 project management (`20_M2_Project_Management`)** - M2 is
  per-project current state. A candidate's project is context in this
  lane, not a subject; project facts learned from an assessment
  transcript stay context unless they are genuinely project-level
  signals, which route to M2's own intake skills instead.
- **vs Project Knowledge (`30_Project_Knowledge`)** - a candidate
  explaining their project's architecture is evidence about the
  candidate, not our knowledge base about that project. Do not fold it
  into a `pk_knowledge_base`: it is uncorroborated, second-hand, and
  collected for a different purpose.
- **vs PM Case Library / QA Department Standards** - a recurring
  client-side interview pattern, or a department-wide preparation
  requirement this session surfaces, belongs in those lanes as a
  secondary output (`pm-case-knowledge-intake`,
  `qa-department-standards-intake`), not buried in one person's debrief.

## Required Start

1. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`,
   `../qa-management-roles/references/google-workspace/artifact-conventions.md`,
   and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`
   before creating or editing anything on Drive.
2. Read `../qa-management-roles/references/transcript-signal-triage.md` -
   the same extraction-worthiness discipline applies here: a familiar
   topic name in a transcript is an attention cue, not evidence.
3. Resolve the lane via `assessment_workspace_layout.py`
   (`find_root`/`find_type_folder`/`find_person_folder`/
   `find_session_document`/`find_index`). Never create the lane root, a
   type folder, or a person folder speculatively - a real session being
   processed is what creates them.
4. Read the governing process documentation for this session type before
   assessing anything, and cite it in the output. It is external
   (department wiki, client brief), it changes, and it is the only source
   of the actual bar - do not assess against remembered criteria. Use
   `../qa-management-roles/references/live-source-access-rules.md` for
   how to reach it (a wiki page goes through `confluence_client.py`, not
   a browser session).

## Core Rules

- **Assess against the stated bar for the stated target, nothing else.**
  An answer that would be thin for a senior can be comfortably above the
  bar for a junior. Every judgment names the target it is measured
  against, or it is not a judgment.
- **Every strength and every gap cites what the person actually said.**
  No impressions, no "seemed confident overall". If you cannot point at
  the answer, it does not go in the document.
- **Separate "did not know" from "was led there".** An answer the
  interviewer supplied before the candidate exhausted their own is not a
  demonstrated competency, and it is also not the same failure as not
  knowing. Record which happened, and who supplied the frame. This is the
  single most common way an assessment document overstates *and*
  understates the same person at once.
- **An unprobed topic is not a gap.** Mark it unprobed with the reason
  (out of scope, no time, expected light for this profile). A blank and a
  deliberate skip mean opposite things to the next assessor.
- **Check the process shape before calling anything a deviation.** A
  lighter format - fewer interviewers, shorter session, uneven weight
  between blocks - is frequently the agreed design for that session type,
  or a deliberate calibration to the person's profile (a manual QA is not
  expected to carry an automation-infrastructure block at the same
  depth). Confirm which it is; do not report a designed choice as a
  procedural failure. See `feedback_status_labels_vs_evidence` and
  `project_business_focus_assessment_format` in user memory.
- **Self-assessment is a claim, not a finding.** Where the session
  contradicts the person's own rating in either direction, that
  difference is itself a finding - state it rather than smoothing it.
- **Never invent a verdict to complete the form.** If the session did not
  cover enough to decide, say what is undecided and what would settle it.
- **Keep the verdict clean of conditions.** A verdict with a second
  condition smuggled into the sentence is unusable by whoever publishes
  it. Development-plan items and re-sit conditions are different things
  and go in different sections.

## Storage And Indexing

- Documents live at
  `60_Assessments_And_Interviews/<type folder>/<Person>/<YYYY-MM-DD>_<role> - <Person>`
  via `assessment_workspace_layout.session_document_name` - never
  hand-build the name.
- Author the report as local Markdown first, then publish with
  `publish_markdown_doc.py` (`--folder-path`/`--folder-id`). Republishing
  the same session's document replaces its body via `--doc-id`; it never
  appends a second copy, and never creates a second document for the same
  session.
- A transcript kept alongside the output goes in the same person folder
  under the `session_transcript` role. Raw video/audio never goes to
  Drive (README, "No raw video/multimedia").
- Log one `_assessment_index` row per processed session (schema:
  `Templates/assessment_index.csv`, columns in
  `assessment_workspace_layout.INDEX_COLUMNS`). This is the lane's ground
  truth for what was run and how it ended, the role `pk_source_index` and
  `pm_case_index` play in their lanes. One row per session, appended -
  a re-run of the same session updates that row rather than adding a
  second one.
- Log `_skill_invocations` with `source_type: assessment_transcript` or
  `external_interview_transcript`, and record the closing telemetry for
  the pass (`record_agent_session.py`) - required, not optional; see
  `feedback_telemetry_closeout_habit` in user memory.

## Privacy And Tone

- Internal-only. Real names, real verdicts, and named process criticism
  belong here; the repository copy of every template and skill stays
  abstract (AGENTS.md, "No Sensitive Data In This Repository").
- The person will plausibly read this, or a text derived from it. Write
  the gaps so they are actionable rather than softened - but never
  characterize the person, only their answers at this session.
- Third parties named in a transcript (a client-side interviewer, a
  colleague, a vendor) are context. Do not record a judgment about their
  competence; nobody assessed them.
- Never let this lane's document become a compensation or headcount
  recommendation. It reports competency evidence; staffing and pay
  decisions are made elsewhere with more inputs.
