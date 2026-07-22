---
name: project-knowledge-roles
description: Shared rules for the Project Knowledge lane (30_Project_Knowledge) - building project understanding gradually from whatever sources actually exist (transcripts, documents, chats, owner notes), distinct from M1/M2 management reporting. Use when processing a project_knowledge_transcript/document/chat/notes source, or updating a project's knowledge_base/performance_test_plan/test_plan/test_strategy.
---

# Project Knowledge Roles

Use this skill as shared context for the Project Knowledge lane. It does
not own a final document format - `project-knowledge-intake` and the
templates (`Templates/pk_knowledge_base.md`, `Templates/pk_summary.md`,
`Templates/pk_source_index.csv`, `Templates/performance_test_plan.md`,
`Templates/test_plan.md`, `Templates/test_strategy.md`) own that.

## What This Lane Is, And Isn't

This lane is for **learning/onboarding and project understanding**, not
M1 people-management or M2 project-management reporting. A project can
enter this lane with no formal knowledge-transfer process at all -
understanding gets built piece by piece from 1:1s, meetings, chats,
presentations, documents, and the owner's own notes. A formal KT session
(`project_knowledge_transcript`) is one possible input, never a
prerequisite - do not wait for one before starting a knowledge base, and
do not treat a project as "not ready" for this lane just because no KT
happened yet.

## Required Start

1. Identify the project's `30_Project_Knowledge/<Project>/` folder (create
   via `project_knowledge_workspace_layout.py` if it doesn't exist yet).
2. Read the project's current `pk_knowledge_base` (if any) before treating
   new source content as novel - a fact already captured shouldn't be
   re-added as if new, and a genuine correction should update the existing
   section rather than appending a contradicting one beside it.

## Core Rules

- **Knowledge accumulates gradually from fragments.** A single source
  rarely gives the full picture. Treat each source as a partial,
  incremental contribution - explicitly note what's still unknown (the
  knowledge base's Open Questions section) rather than presenting a
  fragment as a complete picture.
- **Distinguish durable project knowledge from one-off meeting remarks.**
  "The auth service uses OAuth2" is durable; "we're a bit behind this
  sprint" is a one-off status remark, not knowledge-base material. When in
  doubt, prefer the summary document over the knowledge base - a summary
  can hold context that isn't yet confirmed as durable.
- **Maintain open questions explicitly.** An unresolved gap or
  contradiction between sources belongs in the knowledge base's Open
  Questions section, not silently dropped or silently resolved by guessing.
- **Use Google Docs structure where practical.** Headings, a table of
  contents, and links back to the relevant `pk_summary` document make the
  knowledge base navigable as it grows - don't let it become one long
  undifferentiated wall of text.
- **Relationship to M1/M2 lanes: do not update management docs silently.**
  If a Project Knowledge source happens to contain a people-management or
  project-risk fact (e.g. a KT transcript that also mentions a staffing
  change), do not fold that into `pk_knowledge_base` and call it done -
  flag it and route it separately through the normal M1/M2 intake chain
  (a different source_type/pass, not this one silently reaching into
  another lane's documents).
- **Relationship to QA docs: they are downstream knowledge products, not
  automatic outputs.** `pk_performance_test_plan`/`pk_test_plan`/
  `pk_test_strategy` update only when a source's knowledge actually
  changes testing scope/approach - most sources touch only the knowledge
  base and leave these three untouched (a valid `no_change` outcome, not a
  gap).
- **No presentations, no Slides.** This lane does not produce
  presentation decks. A later phase may read a reviewed brief and generate
  one; nothing in this lane does that today.
- **Promote concrete, test-useful detail into the durable record.** A
  formula, worked example, configuration/string syntax, threshold, or
  calculation rule is exactly the kind of detail a summary-only pass tends
  to drop - if it's durable (true beyond this one source/moment), fold it
  into `pk_knowledge_base` or the relevant QA doc, not just the source's
  `pk_summary`. A vague paraphrase of a concrete rule is a regression, not
  a simplification.
- **Correct resolved uncertainty in place.** When a later source resolves
  an existing "unclear"/"unconfirmed"/"TBD" statement, update that
  statement directly with the resolved fact - do not leave the stale
  uncertain wording standing next to the correction. The knowledge base
  should read as the current understanding, not as a changelog of every
  belief ever held.
- **Keep the knowledge base keyed by topic, not append-only.** When new
  source content addresses a topic the knowledge base already covers,
  update that topic's existing statement in place (upsert) rather than
  appending a second, possibly competing statement beside it. Two
  differently-worded statements about the same fact is a sign one of them
  needs to be corrected or merged, not coexistence.
- **Open questions must be specific and actionable.** A question worth
  keeping open should be concrete enough to drive a follow-up question to
  a real person, or a concrete test-design decision - not a vague "needs
  more detail" placeholder. If a question can't be phrased that
  concretely, it usually means the underlying fact isn't durable enough to
  track yet, or has already been answered elsewhere in the source.
- **`pk_summary` is source-local; `pk_knowledge_base` is durable and
  consolidated.** `pk_summary` captures what one specific source said, in
  that source's own framing - useful for provenance and context even after
  its facts are folded elsewhere. `pk_knowledge_base` captures the
  project's current, cross-source understanding of a topic. The same fact
  can appear in both, but the summary should never be the only place a
  durable fact lives.

## Guardrails

- Do not infer or guess a project name from a source's content - if the
  scope isn't already clear from where the source was dropped or from
  explicit context, leave it for the agent processing the source to
  confirm before `start`.
- Do not treat incomplete/fragmentary sources as a reason to skip
  processing - a partial contribution logged with clear open questions is
  more useful than waiting for a complete picture that may never arrive.
- Do not silently expand this lane's scope into people-management or
  project-risk conclusions - see the M1/M2 relationship rule above.
