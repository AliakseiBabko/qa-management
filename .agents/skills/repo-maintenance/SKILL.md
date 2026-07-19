---
name: repo-maintenance
description: Consistency checklist for any structural change to this repository - adding or editing a skill, script, template, document type, or dependency. Use whenever a change touches .agents/skills, .agents/scripts, Templates, document_graph.yaml, AGENTS.md, or README.md, so every companion file that mirrors the change gets updated in the same commit.
---

# Repo Maintenance

Several files in this repo mirror each other by convention, not by
tooling: the AGENTS.md skill table mirrors `.agents/skills/`, README's
script section mirrors `.agents/scripts/`, `document_graph.yaml` mirrors
the cascade prose in the skills, and `SKILL_INVOCATION_SOURCE_TYPES`
mirrors `google-workspace-rules.md`. A change that updates one side and
not the other creates exactly the silent drift the graph/closure work
exists to prevent. This skill is the checklist that keeps the mirrors in
sync - run through it for **every** structural change, in the same
commit as the change itself.

## Checklist By Change Type

**New or renamed skill**
- `.agents/skills/<name>/SKILL.md` with frontmatter `name` +
  `description` that says both what it produces and when to use it
  (the description is the router - agents pick skills from it).
- Add/update the skill's row in AGENTS.md's skill table.
- If it writes a new document type or adds a dependency between
  documents: update `document_graph.yaml` (node, edges, aliases) - see
  below.
- If it processes a new source shape: see "New source shape" below.

**New or changed document type / dependency between documents**
- `document_graph.yaml`: add the node with its `downstream` edges
  (kind: `direct` / `gated` / `judgment` / `script`), and an `aliases`
  entry for every spelling that will appear in `routed_to` /
  `Documents touched`. Periodic (calendar-cadence) documents go in
  `periodic`, not `documents`.
- Sanity-check with
  `check_cascade_closure.py --touched <new_doc>` - the printed chain
  should match the prose in the owning skill and `m2-role-rules.md`.
- If the cascade prose in a skill/reference describes the same edge,
  keep both in the same commit; the graph is canonical, prose explains
  the judgment side.

**New or changed script**
- Reuse `pipeline_common` (`get_services()`, `reformat_sheet()` after
  Sheet writes, `log_skill_invocation()`, `add_questions()`/
  `add_answer()` for m2_input) instead of re-inlining boilerplate.
- Add/update the script's entry in README's "Current pipeline scripts"
  section - what it does, its dry-run/apply convention, and any known
  gap.
- Windows console prints Cyrillic: reconfigure stdout to UTF-8 like the
  existing scripts do.

**New source shape (a kind of input no skill processes yet)**
- Add the `source_type` value to `SKILL_INVOCATION_SOURCE_TYPES` in
  `pipeline_common.py` **and** to `google-workspace-rules.md`'s canonical
  list - both together, never one side.
- Add it under `sources:` in `document_graph.yaml` with its entry
  documents.

**Template / schema change**
- Update the file in `Templates/` and every skill that names it.
- Existing generated documents keep their old schema unless the user
  asks for migration - note the coexistence in the skill if relevant.

## Every Commit, Regardless Of Change Type

- Run `.agents\scripts\validate_repo.py` - it is this checklist's
  mechanical half automated (table/README/graph/source-type/template
  sync) and must exit 0 before the commit. The judgment half (does the
  description actually describe the skill, is the graph edge's kind
  right) stays here.
- If the change touched closure/graph/queue logic, run the unit tests:
  `python -m unittest discover -s .agents/tests` - they encode the
  known false-closure paths (diamond traversal, scope isolation,
  duplicate precedence, stale kinds) found in real review.
- Public-repo check: no real person/company/project name, contact
  detail, or verbatim first-party content - in files **or** the commit
  message. Run `.agents\scripts\check_sensitive_data.py` when the change
  involved anything derived from real sources.
- Commit message explains *why* (the failure pattern or need, stated
  abstractly), not just what changed - future agents read git history as
  context.
- If the change came out of a retro proposal (`qa-retro`), the retro's
  `_skill_invocations` row lists the edited files in
  `Documents touched`.

## Guardrails

- Don't defer the mirror updates to "a later cleanup pass" - same
  commit, or the drift window opens.
- Don't grow this checklist speculatively; it earns a new line the same
  way skills earn rules - a repeated, observed miss (route candidates
  through `qa-retro`).
