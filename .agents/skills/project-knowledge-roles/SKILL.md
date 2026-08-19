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

## Project-Type Routing: Knowledge-Only vs M2-Owned

Before choosing the update scope, check whether the project is an M2-owned
project: it must be present in the M2 project registry and have a project
folder under `20_M2_Project_Management/<Project>/`. These projects have two
parallel lanes. Update the Project Knowledge documents for durable technical
and business understanding, and route project-management findings through
the M2 documents (for example `project_status`, `project_development_plan`,
`project_risk`, `project_metrics`, `m2_input`, `action_items`, and
`evidence_log`) according to the applicable M2 intake skill.

If the project is not in the M2 registry and has no M2 project folder, it is
a knowledge-only project (for example, a consultant or QA-engineer
assignment outside the user's project-owner responsibility). Update only
the Project Knowledge lane and genuinely relevant downstream QA knowledge
documents. Do not create M2 risk, status, plan, metrics, or action-tracking
artifacts merely because a transcript mentions delivery, staffing, or risk.
Record such facts as project knowledge when durable, and keep unresolved
details as non-blocking Open Questions. If a source contains a separate M2
management signal for another owner, flag it for that owner rather than
silently creating M2 records here.

This routing check is a scope decision, not a completeness gate: missing
details and unanswered questions never justify skipping the knowledge-base
update.

## Required Start

1. Identify the project's `30_Project_Knowledge/<Project>/` folder (create
   via `project_knowledge_workspace_layout.py` if it doesn't exist yet).
2. Read the project's current `pk_knowledge_base` (if any) before treating
   new source content as novel - a fact already captured shouldn't be
   re-added as if new, and a genuine correction should update the existing
   section rather than appending a contradicting one beside it.
3. When the task is about performance-testing scope, deployed services,
   JMeter/GitLab runs, environment reachability, or translating submodules
   into physical test targets, read
   `references/performance-environment-discovery.md` too.

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
- **Never create one of these three as a placeholder.** A first-time
  `pk_test_plan`/`pk_test_strategy`/`pk_performance_test_plan` gets created
  only when the user explicitly asks for it, or when the knowledge base
  already holds concrete, non-generic content to put in it (real
  workflows, real scope boundaries, real workload/latency numbers - not
  restated section headings). A generic test plan or strategy with no
  project-specific content is worse than no document at all - it looks
  authoritative while carrying zero information, and someone will act on
  it as if it were real. If the knowledge is too thin for a real first
  version, say so and leave the document uncreated rather than filling the
  gap with boilerplate.
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
- **Check the knowledge base before asserting a fact in any output, not
  just before adding one.** Drafting a message, summary, or recommendation
  that states a specific operational/technical fact from conversation
  memory alone risks restating a belief the knowledge base has already
  corrected. This showed up in practice as an outgoing question to a
  colleague that asserted an environment detail (a resource-contention
  claim) already corrected in the project's own knowledge base earlier in
  the same session - the fact was one lookup away and the lookup simply
  didn't happen before the message went out. Before a specific claim about
  the project leaves the conversation (a drafted message, a stated
  recommendation, an escalation), do the same quick knowledge-base check
  that would be done before writing the fact down for the first time.
- **Do a core-section extraction before writing "unknown".** Business
  Goals, System/Architecture, Core Workflows, Data/Integrations, and QA
  Scope are not optional skim targets. Before leaving one of these
  sections blank, vague, or "not described by sources", re-read the source
  and any linked sidecar evidence (screenshots, notes, tables) specifically
  for that section. If the source answers the section indirectly through
  product walkthroughs, screen flows, examples, or owner explanations,
  extract that answer instead of preserving a generic unknown placeholder.
  Keep "unknown" only when the re-read still finds no evidence, and make
  the resulting Open Question specific.

## Structural Format: Sub-Headings And Change Log Discipline

Found via an audit of one large project knowledge base (roughly 282K chars
under 14 flat H2 sections, no sub-structure at all): a knowledge base that only
ever gets bigger without ever getting more structured stops being
findable long before anyone notices, because every individual intake
pass still looks reasonable in isolation. Two concrete rules fix this:

- **Change Log entries are dated one-line pointers, never a content
  destination.** An entry says what changed and which section(s) it
  touched - it does not restate the fact itself. If you're tempted to
  write more than ~2 lines for one entry, that content belongs in the
  topical section, not here. This rule exists because of a real failure
  mode: past project-knowledge passes, trying to avoid the heading-inheritance bug
  below, appended entire new facts to Change Log as a workaround instead
  of inserting them into System/Architecture or Known Constraints where
  they belonged - by the time this was caught, 29 real facts (a project
  constraint, several open questions, a whole topic area) were sitting
  under "Change Log" and invisible to anyone searching the section they
  actually belonged to. Never use Change Log as a safe parking spot for
  content you're unsure how to insert - solve the insertion problem
  instead (see the next rule).
- **Once a topical section (Overview, System/Architecture, Core
  Workflows, etc.) grows past roughly 800 words or accumulates more than
  ~3 distinct sub-topics, split it with Heading 3 sub-headings** keyed to
  how the source material actually clusters (a module name, a workshop
  topic, a subsystem) - not a generic scaffold imposed up front. Adding
  the right sub-heading needs the whole section's content in view to
  choose a sensible split, so this is a periodic housekeeping pass (do it
  when a section visibly has become an undifferentiated block, or when
  `qa-retro` flags one), not a requirement on every single intake. A
  single intake pass appending 2-3 sentences to an already-organized
  section just appends under the right existing H3 - it does not need to
  re-derive the whole section's structure each time.
- **Insert new content at the end of the target section (or target H3
  sub-section), never at a heading's own start index.** This is the fix
  for the Docs API heading-inheritance bug documented in
  `../qa-management-roles/references/google-workspace/api-sharing-editing.md`
  ("Docs API Editing") - inserting text exactly at a heading paragraph's
  `startIndex` makes the new content silently inherit that heading's
  style. Appending at the end of the preceding section's content (right
  before the *next* heading) avoids the bug entirely and matches how a
  human would read the document (newest fact last within its topic, not
  first).

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
