---
name: repo-maintenance
description: Consistency checklist for any structural change to this repository - adding or editing a skill, script, template, document type, or dependency. Use whenever a change touches .agents/skills, .agents/scripts, Templates, document_graph.yaml, AGENTS.md, or README.md, so every companion file that mirrors the change gets updated in the same commit.
---

# Repo Maintenance

Several files in this repo mirror each other by convention, not by
tooling: README's script section mirrors `.agents/scripts/`,
`document_graph.yaml` mirrors the cascade prose in the skills, and
`SKILL_INVOCATION_SOURCE_TYPES` mirrors
`qa-management-roles/references/google-workspace/operational-registries.md`'s
canonical `source_type` list. A
change that updates one side and not the other creates exactly the
silent drift the graph/closure work exists to prevent. This skill is the
checklist that keeps the mirrors in sync - run through it for **every**
structural change, in the same commit as the change itself.

**AGENTS.md is intentionally a thin startup router**, not an inventory.
It carries no per-skill table - the canonical skill inventory is
`.agents/skills/` itself plus each `SKILL.md`'s own frontmatter, validated
structurally by `validate_repo.py`. A new or renamed skill therefore never
needs an AGENTS.md edit; only add AGENTS.md content when a change touches
one of the compact policy rules AGENTS.md itself states (the public-repo
boundary, the `.local/` exception, startup routing, the canonical data
boundary, core judgment rules) - see AGENTS.md's own opening note before
adding anything to it.

## Checklist By Change Type

**New or renamed skill**
- `.agents/skills/<name>/SKILL.md` with frontmatter `name` +
  `description` that says both what it produces and when to use it (the
  description is the router - agents pick skills from it, and
  `validate_repo.py` requires it to be present and non-empty).
- If it writes a new document type or adds a dependency between
  documents: update `document_graph.yaml` (node, edges, aliases) - see
  below.
- If it processes a new source shape: see "New source shape" below.
- If README genuinely documents the user-facing structure or behavior
  the skill produces (a new folder, a new document family, a new
  pipeline script) - update the relevant README section in the same
  commit. Not every skill needs a README change; a routing/prep skill
  with no new output document usually doesn't.
- If it is an M1/M2 report-writing skill matching a bundle declared in
  `.agents/reference_bundles.yaml` (`m2-report-writer`/`m1-report-writer`):
  copy that bundle's module list verbatim into Required Start and add the
  skill to the bundle's `used_by` in the same commit -
  `validate_repo.py`'s `check_reference_bundles()` fails otherwise.

**New or changed document type / dependency between documents**
- `document_graph.yaml`: add the node with its `downstream` edges
  (kind: `direct` / `gated` / `judgment` / `script`), and an `aliases`
  entry for every spelling that will appear in `routed_to` /
  `Documents touched`. Periodic (calendar-cadence) documents go in
  `periodic`, not `documents`.
- Sanity-check with
  `check_cascade_closure.py --touched <new_doc>` - the printed chain
  should match the prose in the owning skill and `m2-role/m2-cascading-updates.md`.
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
  `pipeline_common.py` **and** to
  `qa-management-roles/references/google-workspace/operational-registries.md`'s
  canonical list - both together, never one side.
- Add it under `sources:` in `document_graph.yaml` with its entry
  documents.

**Template / schema change**
- Update the file in `Templates/` and every skill that names it.
- Existing generated documents keep their old schema unless the user
  asks for migration - note the coexistence in the skill if relevant.

**Splitting a monolithic shared reference into a thin index + modules**
- Only split when there's a real payoff: either several skills each need
  a different subset (a thin `<name>-rules.md` index plus scoped modules
  under `<name>/`, the pattern used for Google Workspace rules, M2 role
  rules, and the M2 QA-metrics/project-report contracts), or one file has
  a genuinely situational chunk worth gating separately (an "Extended
  Catalog"/"Internal Variant"-style section not needed on every
  invocation). Splitting a single-consumer file that has no situational
  content doesn't reduce anything - it just adds header overhead. Don't
  do it without one of these two payoffs.
- Preserve every substantive line verbatim; only reword a cross-reference
  when the moved content's new filename requires it. Verify with an
  automated line-diff before finalizing, not by eyeballing.
- Size targets: thin index <=4 KiB; each module <=12 KiB where practical,
  <=16 KiB hard cap; combined index+modules within 95-110% of the
  original file's size (some growth from repeated H1/Scope headers per
  module is normal and expected).
- Retarget every consumer's Required Start to the smallest module set it
  actually needs - never make a skill read every module "just in case."
  Retarget prose cross-references (other skills, Templates, README) to
  the owning module too, except a genuinely generic "see also" pointer,
  which may keep citing the parent file/index.
- Audit and retarget any existing test that hardcodes the old monolith's
  path before finalizing - splitting a file silently breaks a test that
  reads it directly and asserts specific section text. When a moved
  section is asserted by a test class that also asserts content from a
  section that ends up in a *different* new module, split that test class
  too so each one reads only its own module.
- A genuinely duplicated rule (the same fact restated in two files, each
  citing the other as if it were a separate authority) should be
  consolidated into whichever file already owns it canonically, with the
  other file trimmed to a short pointer plus only its own distinct,
  non-duplicate framing - not left duplicated "for convenience." Don't
  invent a new shared directory for this if an existing canonical module
  already covers the concept; point there instead.
- If a read should only happen for a specific section/scenario (not every
  invocation), mark it conditional in Required Start prose using explicit
  `when`/`if` language ("too when filling the Upsell section", "too if
  also writing the internal variant") - this is what the continuation-
  line-aware conditional detector in the loading-contract tests and
  `validate_repo.py`'s bundle check actually look for. A conditional read
  must never be phrased so it reads as unconditional (e.g. don't just
  drop the file into a same-line list with the mandatory ones).

**Repeated Required Start module bundle (3+ skills reading the identical
module set)**
- Declare it in `.agents/reference_bundles.yaml` with its `modules` list
  and `used_by`; `validate_repo.py`'s `check_reference_bundles()` then
  fails if any listed skill's Required Start stops matching. Don't declare
  a bundle for fewer than 3 consumers - the naming overhead isn't worth it
  yet.
- A bundle is a drift-prevention registry only, never a mechanism a skill
  reads instead of the real paths. Required Start must keep spelling out
  every module path explicitly (never `- see the m2-report-writer bundle`
  in place of the actual paths) - an agent must always see which layout
  module (M1 vs M2) and which safety file it is reading, and this repo
  has no runtime engine to expand an alias for it anyway.
- Every bundle must include `api-sharing-editing.md` unconditionally -
  never make it optional, situational, or omit it to shrink a bundle.
- Only put a module in a bundle if literally every one of that bundle's
  consumers needs it unconditionally. A module some but not all consumers
  need (e.g. `people-registry.md` for 3 of 5 M1 report-writers,
  `search-source-extraction.md` for 2 of 9 M2 report-writers) stays a
  per-skill addition outside the bundle, not bundle content.
- Never merge the M1 and M2 layout modules into one generic bundle name -
  each bundle stays role-specific so the agent's Required Start always
  names the correct, explicit layout file.

## Every Commit, Regardless Of Change Type

- Run `.agents\scripts\validate_repo.py` - it is this checklist's
  mechanical half automated (skill frontmatter/README/graph/source-type/
  template sync) and must exit 0 before the commit. The judgment half
  (does the description actually describe the skill, is the graph edge's
  kind right, does README need updating for this specific skill) stays
  here.
- If the change touched closure/graph/queue logic, run the unit tests:
  `python -m unittest discover -s .agents/tests` - they encode the
  known false-closure paths (diamond traversal, scope isolation,
  duplicate precedence, stale kinds) found in real review.
- Public-repo check: no real person/company/project name, contact
  detail, or verbatim first-party content - in files **or** the commit
  message. Run `.agents\scripts\check_sensitive_data.py` - it scans the
  whole commit candidate (index, working tree, untracked, file contents
  *and* paths, repo-wide), not just this change, so it is worth running
  even when the edit itself touched nothing real. It reports path/line
  only - never the matched value, and never the path itself for a
  filename hit - and it fails closed (exit 2) rather than reporting a
  clean tree it could not fully read. It cannot catch company names,
  contacts, unregistered identifiers, or paraphrased content - those
  still need your own read.
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
- Don't split a shared reference further just because it's large. A
  single-topic reference with multiple consumers and no situational
  subset (e.g. `people-registry.md`, `performance-review-rules.md`,
  `newcomer-support-rules.md`) is already minimally scoped - fragmenting
  a cohesive topic doesn't remove duplication, it only adds files. Split
  again only when a new situational subset or a new genuinely duplicated
  rule actually appears, not speculatively.
- A skill sitting over any given size threshold is not by itself a reason
  to split anything - check first whether the load is a repeated,
  reducible bundle (declare/extend a `reference_bundles.yaml` entry) or a
  genuinely necessary stack for that skill's own safety/role/schema
  context (nothing to do). Don't chase a lower byte number for its own
  sake once every reference a skill reads is already minimally scoped and
  either mandatory-every-time or correctly gated conditional.
