---
name: visual-evidence-context
description: Workspace-local facts for visual-evidence-organize (drop-folder path, project/identity resolution, permitted downstream destinations, cascade boundary) - read by that skill via a fixed path, never invoked as a standalone skill. Use only indirectly, when visual-evidence-organize is running inside this repo.
---

# Visual Evidence Context - qa-management

This is a passive context file, not a workflow - `visual-evidence-organize`
(in the separate `ai-skills` repo) reads this by its fixed path
(`.agents/skills/visual-evidence-context/SKILL.md`) before organizing a
screenshot drop in this workspace. All triage/inspection/grouping/mode
logic lives in that generic skill; this file supplies only what's specific
to this workspace.

## Drop-Folder Path

```text
00_Inbox/_Visual_Drop/
```

Filenames are arbitrary (`Screenshot 2026-07-24 143022.png`,
`image (3).png`, etc.) - do not assume filename encodes meaning. Image
extensions are not in `qa_manage.py`'s `SCAN_EXTS`, so files here are never
auto-picked-up by `scan`/`dashboard`; this folder is inert until organized.

An optional context-notes file may sit alongside the images (e.g.
`visual_context.md` or any clearly-named `visual_context_notes.txt`) - see
`visual-evidence-organize`'s own `triage-workflow.md` for how notes are
read and treated as authoritative triage instructions.

## Project/Identity Resolution

Use `<Project>` from `_project_registry`/chat context when known, to place
the organized bundle at:

```text
00_Inbox/<Project>/visual-bundle-<topic>/
```

If the project is genuinely unclear, keep the bundle under
`00_Inbox/_Visual_Drop/visual-bundle-<topic>/` instead of guessing a
project folder, and say so explicitly.

## Permitted Downstream Destinations

Recommend one of exactly these two, or "unclear, ask the user" - never a
name outside this list:

- **Project Knowledge lane** - `project_knowledge_notes`/`document`
  (`30_Project_Knowledge/<Project>`), when the bundle looks like durable
  project/technical evidence. If the natural home looks like a person's
  `individual_development_plan` but the content is really project-level
  (framework/architecture/tooling that would outlive that person's tenure
  on the project), recommend a `30_Project_Knowledge/<Project>` folder
  instead/in addition - a person's plan becoming the general collection
  point for project-level technical knowledge is itself a signal the
  project needs its own knowledge base.
- **M2 supporting context** - `evidence_log`/`status`, when the bundle
  looks like project-management-relevant supporting evidence rather than
  durable technical knowledge.

## Cascade Boundary

Do not update M1/M2/Project Knowledge documents automatically during
organization. Organizing the bundle and recommending a downstream path is
the whole job; actually writing into `evidence_log`/`pk_knowledge_base`/etc.
is a separate, explicit pass using the relevant skill once the user
confirms the bundle's meaning.

## Also See

- Screenshots are supporting evidence, not a substitute for source
  text/logs/documents already available - if a transcript/chat/document
  already covers the meeting, treat screenshots as sidecar evidence, not a
  reason to reprocess the same meeting blindly.
- This repo is public - never commit real screenshot filenames or content
  here; bundles live only in the Drive workspace
  (`G:\My Drive\QA_Management\00_Inbox\...`).
