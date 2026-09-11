---
name: ai-adoption-review
description: Run and write up an AI adoption review for one project - assess how well and how legitimately a project team implements AI tooling in its QA work (manual and automation), against the scored rubric in `Templates/ai_adoption_review.md`, and produce a per-project review Google Doc under `55_AI_Adoption\reviews\`. Also covers adding a processed session to the AI adoption knowledge base (source notes, knowledge store, best-practices wiki). Use when preparing for or writing up an "AI project support" session, when asked how a project's AI usage should be verified or scored, or when a new AI-related session needs folding into the cross-project best-practices synthesis. Not for assessing a named person's competence (that is M1's `individual_risk`) and not for department-wide tool requirements (that is `qa-department-standards-intake`).
---

# AI Adoption Review

Two related outputs, one lane (`55_AI_Adoption`):

- **`<Project>_ai_adoption_review_<YYYY-MM-DD>`** - a per-project, per-session
  scored review under `55_AI_Adoption\reviews\`. The primary output.
- **The knowledge base** - `ai_adoption_source_notes`,
  `ai_adoption_knowledge_store` and `ai_in_qa_best_practices`, the tiered
  cross-project synthesis the rubric is calibrated against.

`Templates/ai_adoption_review.md` owns the review document's format, its 0-4
scale, its question bank and its per-scenario expectations. This skill owns when
to run it, how to keep the knowledge base tiered, and the judgment calls the
template cannot make for itself.

## What This Is, And Isn't

- **A review of a project's AI practice**, never of a person. A single
  engineer's setup may be described in detail; the assessment is of the
  project. A verdict about a named engineer's competence or reliability belongs
  in M1's `individual_risk`, and this lane must not carry one.
- **Boundary vs `qa-department-standards-intake`:** a settled department-wide
  tool or process requirement surfaced during a review (e.g. "the company is
  standardising on X", "everyone with a git repo must install the push-count
  tool") goes to `qa_department_standards`. This lane holds how projects
  actually implement, not what the department requires.
- **Boundary vs `30_Project_Knowledge`:** PK is per-project technical and
  business understanding. A project's AI implementation detail lives here; if a
  session also taught something durable about the product or architecture, that
  part routes to PK.
- **Boundary vs `40_PM_Case_Library`:** a generalisable management-situation
  pattern surfaced during a review routes to `pm-case-knowledge-intake`. This
  lane is not a case library.
- **Boundary vs `qa-1to1-analysis` / `m2-1to1-apply`:** a 1:1 that happens to
  cover an AI implementation still routes its people and project signals
  through the normal 1:1 chain. Only the AI-implementation content comes here,
  and compensation, staffing and personal-plan content never does - see
  Guardrails.

## Required Start

1. Read `Templates/ai_adoption_review.md` end to end. It is the document
   contract; do not paraphrase its sections from memory.
2. Read `references/scoring-calibration.md` - what each score actually requires,
   and the recurring mis-scores.
3. Read `references/knowledge-base-contract.md` before touching any of the three
   knowledge base documents.
4. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`,
   `artifact-conventions.md` and `api-sharing-editing.md` in the same folder.
5. Read the current `ai_in_qa_best_practices` and `ai_adoption_knowledge_store`,
   plus any previous review document for this project. A review that repeats a
   finding already on record without noting it is a repeat is worth much less
   than one that shows a trajectory.

## Workflow - reviewing a project

1. **Pre-read.** The project's completed questionnaire, the client's AI policy
   or approval matrix if one exists, and the previous review. Fill template §A
   and as much of §B as the paperwork answers, before the session.
2. **Classify the ecosystem** (template §B) - open/client-endorsed, restricted/
   client-owned, closed, or negotiated autonomy. This decides which dimensions
   are even reachable, so it is done before scoring, not after.
3. **Run the session.** 45-60 minutes, screen share if data sensitivity allows.
   Use the §N question bank. Two rules that produce most of the value: ask for
   the artifact rather than the intention ("show me the skill", not "do you use
   skills"), and ask what got worse, which is never volunteered.
4. **Score §C-§K** immediately after, while the demonstration is fresh. Score
   what was demonstrated, not what was described as planned; a planned item
   scores at its current state and goes into §L.
5. **Record findings separately** (§B and §M). Access-legitimacy problems are
   findings with an owner and an escalation path, never scores - see Guardrails.
6. **Fill §L with a real baseline.** A named metric, a baseline captured at this
   review, a collection method, an owner and a return date. If nothing was
   agreed, write that down and why, rather than leaving the section empty.
7. **Publish** the review Doc to `55_AI_Adoption\reviews\` via
   `publish_markdown_doc.py --folder-path`.
8. **Fold the session into the knowledge base** per
   `references/knowledge-base-contract.md`: a source extraction note always; a
   knowledge store upsert where it changes or corroborates an entry; a
   best-practices wiki update only where it changes the synthesised
   understanding. If the wiki changed, regenerate the Russian derived edition in
   the same pass or state in the handoff that it is now behind - see the
   contract's "Derived language editions" section, and note that the edition is
   a generic rules digest rather than a translation.
9. **Cross-check the other lanes.** Department requirement ->
   `qa-department-standards-intake`. Generalisable management pattern ->
   `pm-case-knowledge-intake`. Project or product understanding ->
   `project-knowledge-intake`. Person-level people signal -> the M1 chain. Most
   sessions produce zero or one of these; do not force it.
10. **Log `_skill_invocations`, then run `record_agent_session.py`.** The
    telemetry closeout is part of the pass, not an optional last step.

## Workflow - adding a session to the knowledge base only

For a session that is not a project review - an expert consultation, a
department session, a 1:1 whose AI content is worth keeping - skip steps 1-7
and run steps 8-10. The source note is still written in full; only the scored
review document is skipped.

## Judgment Calls

**Scoring against the ecosystem, not against an ideal.** A restricted project
where requirements are exported by hand is not failing at context grounding; it
is at its permitted ceiling. Record the constraint and score against what §B
permits. Equally, do not inflate a score because the constraint is real - a
project at its ceiling is at its ceiling, and the review says so.

**Governance is a gate.** A project cannot be rated above *Individual practice*
while §B carries an open finding, whatever its dimension scores. Strong tooling
does not offset unapproved access.

**Test case generation is assessed, not recommended by default.** Where
implementation details are unknowable until the feature exists and per-case cost
is low, mass generation is real relief even at a high discard rate. Where
business logic is complex and documentation thin, it fails regardless of the
prompt. The discriminator is what a wrong case costs. Do not hand a generic
generation skill to a project of the second kind - the knowledge base records
both outcomes and why they differ.

**A rejected automation target may be a correct decision.** Release reporting,
bug filing and uniform data generation are commonly faster by hand. Log analysis
commonly has no stable repeating shape. Record these as assessed-and-declined,
not as gaps. Only "not considered" is a gap.

**"What got worse" outranks everything else in the session.** The highest-value
findings come from upstream AI output landing on QA as extra load - generated
testing notes, documentation or autotests whose quality dropped - and from
ownership evaporating on AI-generated tests. Neither is fixable inside QA;
record, name the owner, escalate.

**Ask what it consumes, every time - in tokens, not in a price per test.** None
of the reviews on record asked anything about consumption, so the department has
no picture of it while one project reports a $500/month per-person seat running
out early. On a fixed subscription an engineer meets a limit, not a per-request
charge, so a dollars-per-test figure is derived from assumptions about allowance
size rather than measured; ask which tier, who pays, whether the allowance runs
out, and what burns it. Money is the right unit for seats, allowances and
metered API billing only. The knowledge base holds measured token reference
figures to calibrate against - use them rather than accepting "it's fine", and
note that roughly 57% of the reference totals are cache reads, which allowances
weight far below fresh input tokens.

**Do not promise a metric that does not exist.** The department's current
measures are activity measures. State which of activity or productivity the
review is measuring, and do not commit to a target that assumes a step change
in QA capacity - `ai_in_qa_best_practices` §5 holds the reasoning and the
honest ceiling.

## Guardrails

- Never score an access-legitimacy problem. It is a finding in §B/§M with an
  owner and an escalation path.
- Never answer "how do we leave no trace" operationally, and never record such
  an answer in this lane. If a project cannot legitimately integrate, that is
  the finding and the ceiling to design against. The alternatives to offer are
  the client's own tooling, a declared and approved subscription, or a local
  store the agent works against without touching client resources.
- Never let a review document carry a judgment about a named person's
  competence, reliability, compensation or future on the project. Where a
  source session contains that material (a 1:1 commonly does), it is excluded
  from this lane entirely and routed to the M1/M2 chain - the source note says
  that it was excluded and why, never what it said.
- Never create the `55_AI_Adoption` root, `reviews` subfolder, or any of the
  three knowledge base documents speculatively - only when a real review or a
  real processed source justifies it.
- Never rewrite an earlier review document. A re-review is a new dated document
  citing the previous one.
- Never let this skill edit `project_risk`, `m2_input`, `individual_risk`,
  `qa_department_standards`, `pm_case_library` or any Project Knowledge
  document. Those stay owned by their real intake skills; this one writes only
  the review documents and the three knowledge base documents.
- Never present a single project's practice as a department standard. A pattern
  needs corroboration across projects before it reaches the wiki as a
  recommendation, and the wiki says when a practice rests on one person's
  experience.
