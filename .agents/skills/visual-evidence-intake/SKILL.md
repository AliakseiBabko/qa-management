---
name: visual-evidence-intake
description: Organize and interpret raw screenshots dumped into 00_Inbox/_Visual_Drop with arbitrary filenames - inspect each image, rename/group them into a bundle with a preserved mapping, and recommend whether the bundle should later feed Project Knowledge or M2 supporting context. Use when the user says they've dropped screenshots/images somewhere and wants them sorted or explained, not when a transcript, chat export, or other text source already covers the same content.
---

# Visual Evidence Intake

Screenshots are a low-friction way for the user to hand over evidence the
agent can't get any other way (a UI state, an error dialog, a rough
folder/tooling layout). This skill turns a loose dump of screenshots into
an organized, mapped bundle. It does **not** decide what those screenshots
mean for a project/person document - that's the job of whichever skill
processes the bundle next (`project-knowledge-intake`, an M2 skill, or a
plain `evidence_log` entry), using the organized bundle as its source.

## Drop Folder Convention

Raw screenshots land in:

```text
00_Inbox/_Visual_Drop/
```

Filenames are arbitrary (`Screenshot 2026-07-24 143022.png`,
`image (3).png`, etc.) - do not assume filename encodes meaning. Image
extensions are not in `qa_manage.py`'s `SCAN_EXTS`, so files here are
never auto-picked-up by `scan`/`dashboard` as intake sources; this folder
is inert until an agent (this skill) organizes it.

## Optional Context File

`00_Inbox/_Visual_Drop/visual_context.md` may exist alongside the images
with rough, informally-written notes: which project the screenshots
relate to, a related meeting/source, a person, how the screenshots group
together, and what the user actually wants extracted. Treat it as a hint,
not a spec - it can be partial, outdated, or absent. If it's absent, rely
on whatever the user said in chat plus what's visible in the images.

## Workflow

1. **List** every file in `00_Inbox/_Visual_Drop/` (images plus
   `visual_context.md` if present).
2. **Inspect** each image directly. Do not guess from a filename, a
   thumbnail, or a partial/cropped/low-resolution view - if content is
   unclear, record it as unclear rather than inferring a likely meaning.
3. **Group** related images (same flow, same error, same meeting) using
   whatever the images and `visual_context.md`/chat context actually
   support - don't force a grouping the evidence doesn't show.
4. **Rename and move** into an organized bundle:

   ```text
   00_Inbox/<Project>/visual-bundle-<topic>/
     visual_context.md
     screenshots/
       <new-filename-1>.png
       <new-filename-2>.png
       ...
   ```

   Use `<Project>` from `_project_registry`/context when known; if the
   project is genuinely unclear, keep the bundle under
   `00_Inbox/_Visual_Drop/visual-bundle-<topic>/` instead of guessing a
   project folder, and say so.
5. **Preserve the mapping** as a table (in the bundle's own
   `visual_context.md`, or restated in chat) with one row per screenshot:

   | original filename | new filename | short description | confidence |
   |---|---|---|---|

   `confidence` is a plain read of how legible/certain the description is
   (e.g. clear / partial / unclear) - not a numeric score.
6. **Extract durable visual facts only when visible enough** - a fact goes
   in the mapping's description (or a short "facts" note) only if it's
   actually legible in the image, not inferred from what the UI probably
   does.
7. **Recommend a downstream path** for the bundle: does it look like
   supporting evidence for `project_knowledge_notes`/`document` (Project
   Knowledge lane), M2 supporting context (evidence_log/status), or
   neither yet (needs more context from the user first). This is a
   recommendation only - see Guardrails.

## Reading Different Screenshot Kinds

- **UI screenshots** can reveal menus, modules, and flows - describe what
  is visibly present, not what the feature probably does beyond the
  visible screen.
- **VS Code / editor screenshots** can reveal a rough folder/file/tooling
  structure (visible tree, open tabs, visible status bar) - this is not
  enough for real code analysis or a correctness judgment; say so rather
  than extrapolating into how the code behaves.
- **Screenshots of AI answers/tables/chat output** can be OCR'd/read for
  text, but if the user can paste the actual text instead, prefer that -
  a screenshot is a fallback for text, not the preferred source when text
  is available.

## Guardrails

- Screenshots are supporting evidence, not a substitute for source
  text/logs/repo files when those are already available - if a transcript,
  chat export, or document already covers the same content, prefer it and
  treat the screenshot as corroboration at most.
- Do not update M1/M2/Project Knowledge documents automatically during
  this organization step. Organizing the bundle and recommending a
  downstream path is the whole job here; actually writing into
  `evidence_log`/`pk_knowledge_base`/etc. is a separate, explicit pass
  using the relevant skill once the user confirms the bundle's meaning.
- Do not delete the original screenshots unless the user explicitly asks -
  move/rename into the bundle, don't discard.
- Do not commit real screenshot filenames or content to this (public)
  repository - this skill file only describes the pattern in the
  abstract; the bundles themselves live in the Drive workspace
  (`G:\My Drive\QA_Management\00_Inbox\...`), never in this repo.
- Don't guess from unclear or cropped content - an unreadable screenshot
  gets `confidence: unclear` and no fabricated description.
