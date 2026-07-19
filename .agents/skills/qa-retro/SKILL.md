---
name: qa-retro
description: Improvement-loop retro pass - read everything since the last retro (_skill_invocations rows, feedback notes, cascade-closure misses, repo commits) and turn repeated friction into proposed edits to skills/references/document_graph.yaml, presented as diffs for the user's review. Use when the user asks for a retro, or after a significant intake batch; cheap enough to run daily or per-injection.
---

# QA Retro (Improvement Loop)

The skills under `.agents/skills/` are the distilled experience this
workspace exists to accumulate. This skill closes the loop from lived
passes back into those skills: without it, a rule only improves when the
user happens to notice a pattern themselves. With it, every pass leaves a
trace and repeated friction becomes a proposed rule change.

Capture is cheap and happens every pass; **rule changes are rationed** -
one correction is an anecdote, a repeat is a pattern. Running the retro
often is fine precisely because most runs should conclude "nothing
repeated yet, nothing to change."

## Required Start

1. Run `.agents\scripts\prepare_retro.py`. It finds the last `retro` row
   in `_skill_invocations`, prints every row since it (flagging
   `feedback:` notes), and lists repo commits over the same window. No
   rows since last retro and no feedback = say so and stop; don't
   manufacture findings.
2. Read `../qa-management-roles/references/google-workspace-rules.md`'s
   `_skill_invocations` section for the `feedback:` note convention this
   pass consumes.

## Workflow

1. Group the window's material by target - which skill, reference,
   script, or `document_graph.yaml` node each item is about:
   - `feedback:` notes in `_skill_invocations` (user corrections/overrides
     captured during intake passes)
   - feedback the user gave directly in the current conversation
   - cascade-closure misses (an OPEN item that turned out to be a real
     omission, not a "no change needed")
   - friction the agent itself hit (a rule that was ambiguous, a routing
     decision that took judgment the skill should have carried)
2. Apply the threshold per group:
   - **Seen once**: keep as a trace only - make sure it's captured as a
     `feedback:` note (add one now if it only exists in conversation).
     No skill edit.
   - **Seen twice or more** (same shape, not necessarily same words):
     draft a concrete edit - to the owning SKILL.md, a shared reference,
     `document_graph.yaml` (new edge/node/alias), or a script. The edit
     states the rule *and* the why, following the existing house style
     (rules cite the failure pattern abstractly, e.g. "this has already
     happened once on a real item").
   - **Contradicts an existing rule**: never silently rewrite - present
     both the current rule and the observed exceptions and let the user
     decide.
3. Present all drafted edits as diffs in one batch for the user's review.
   Apply and commit only what the user approves; follow the
   `repo-maintenance` skill's checklist for every applied edit (AGENTS.md
   table, README, graph sync, sensitive-data check).
4. Log the retro itself: `pipeline_common.log_skill_invocation()` with
   `source_type="retro"`, `skills="qa-retro"`, `Documents touched` =
   repo files actually edited (or blank), `Notes` = patterns found,
   proposals accepted/declined, and singles left as traces. This row is
   the marker the next `prepare_retro.py` run slices from - write it even
   when nothing changed.

## Guardrails

- This repo is public: proposed edits describe patterns abstractly -
  never a real name, project, or verbatim transcript/chat content, even
  when the pattern came from a specific person's case.
- Don't oscillate: a rule added by a previous retro isn't removed just
  because the window since then had no confirming case - removal needs
  positive evidence the rule misfires, and the user's approval.
- Don't inflate the window: if the same underlying event produced three
  notes, that's one occurrence, not three.
- Skill edits land as git commits the user has reviewed - never
  auto-apply a judgment-rule change and mention it afterwards.
- Business-data documents (Sheets/Docs on Drive) are out of scope here;
  this skill edits the repo's rules, not the workspace's data. A data
  problem found during retro routes through the normal intake chain.
