---
name: visual-evidence-intake
description: Organize and interpret raw screenshots dumped into 00_Inbox/_Visual_Drop with arbitrary filenames - inspect each image, read any rough context notes, rename/group them into a bundle with a preserved mapping, and recommend whether the bundle should later feed Project Knowledge or M2 supporting context. Use when the user says they've dropped screenshots/images somewhere and wants them sorted or explained, including when the screenshots are sidecar visual evidence for a transcript, chat export, or other text source.
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

## Optional Context Notes

`00_Inbox/_Visual_Drop/visual_context.md` may exist alongside the images,
but the user can also provide any clearly named free-form `.txt`/`.md`
notes file in the same folder (for example `visual_context_notes.txt`).
The notes do not need a formal structure: they can be a rough dictated
commentary that mentions original screenshot filenames, a related
meeting/source, a project, a person, how the screenshots group together,
and what the user actually wants extracted. Treat these notes as the
identity/context source of truth when they name the project/person/source;
the screenshots are the visual evidence. If several note files conflict,
ask which one is authoritative before moving or writing anything. If no
notes exist, rely on whatever the user said in chat plus what is visible
in the images.

## Workflow

Read the user's notes before opening a single image. Notes come first,
inspection second - not the other way round. The point is to spend
inspection effort only on screenshots that need it.

1. **List** every file in `00_Inbox/_Visual_Drop/` (images plus any
   context notes such as `visual_context.md` or `visual_context_notes.txt`
   if present).
2. **Read the context notes first**, before opening any image. The user's
   own dictated/written comments are the first source of triage
   information, not just identity context.
3. **Build a per-screenshot processing plan** from the notes before doing
   any inspection: for each file, decide `process` or `skip`, with a
   reason. Treat the user's own comments as authoritative skip
   instructions, not merely hints to weigh - if a note says a screenshot
   is a duplicate, low quality, blurry, from a bad export, or "not
   important", mark it `skip` with that reason and do not fully inspect
   it. This is specifically to cut manual work on a large drop (e.g.
   screenshots extracted from a recorded video review, where duplicates
   and bad frames are routine) - don't re-decide a skip the user already
   made. If the notes are silent on a file, default to `process`. Share
   or at least state this plan before acting on it, so an obviously wrong
   skip/process call can be caught before time is spent either way.
4. **Inspect** each `process`-marked image directly. Do not guess from a
   filename, a thumbnail, or a partial/cropped/low-resolution view - if
   content is unclear, record it as unclear rather than inferring a
   likely meaning. For `skip`-marked images, do not open/describe them -
   record the mapping row with the skip reason instead (see step 6).
5. **Group** related processed images (same flow, same error, same
   meeting) using whatever the images and context notes/chat context
   actually support - don't force a grouping the evidence doesn't show.
6. **Rename and move** into an organized bundle:

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
   project folder, and say so. Topic-prefix choice (`ui-`, `automation-`,
   `roadmap-`, or whatever fits the actual content) is free-form - any
   scheme is fine - but it must be written down: state the prefixes used
   and what each means at the top of the bundle's own `visual_context.md`,
   not left implicit in the filenames alone. Skipped files stay out of
   `screenshots/` - leave them in `00_Inbox/_Visual_Drop/` (or move to a
   `screenshots/skipped/` subfolder if the user prefers them relocated
   too) so the processed bundle only contains what was actually inspected.
7. **Preserve the mapping** as a table (in the bundle's own
   `visual_context.md`, or restated in chat) with one row per screenshot,
   including skipped ones:

   | original filename | new filename | short description | confidence |
   |---|---|---|---|

   `confidence` is a plain read of how legible/certain the description is
   (e.g. clear / partial / unclear) - not a numeric score. For a
   `skip`-marked file, `new filename` is blank/unchanged, `short
   description` is the skip reason from step 3 (e.g. "skipped - user
   noted duplicate of <other file>"), and `confidence` is `n/a (not
   inspected)` - never fabricate a description for a file that was never
   opened.
8. **Extract durable visual facts only when visible enough** - a fact goes
   in the mapping's description (or a short "facts" note) only if it's
   actually legible in the image, not inferred from what the UI probably
   does. If a screenshot's content is itself an AI-generated
   estimate/analysis (an AI assistant's own read of code coverage,
   quality, or effort), label it in the extracted fact as self-reported/
   AI-estimated with unclear methodology, not as a verified measurement -
   the screenshot proves the estimate was produced and what it said, not
   that the estimate is accurate.
9. **Recommend a downstream path** for the bundle: does it look like
   supporting evidence for `project_knowledge_notes`/`document` (Project
   Knowledge lane), M2 supporting context (evidence_log/status), or
   neither yet (needs more context from the user first). This is a
   recommendation only - see Guardrails. If the natural home for the
   extracted content is a person's `individual_development_plan` but the
   content is really about the project (framework/architecture/tooling
   that would outlive that person's tenure on the project), say so
   explicitly and recommend a `30_Project_Knowledge/<Project>` folder
   instead/in addition - a person's plan becoming the general collection
   point for project-level technical knowledge is itself a signal that
   the project needs its own knowledge base, not a reason to keep
   appending there.

## Reading Different Screenshot Kinds

- **UI screenshots** can reveal menus, modules, and flows - describe what
  is visibly present, not what the feature probably does beyond the
  visible screen.
- **VS Code / editor screenshots** can reveal a rough folder/file/tooling
  structure (visible tree, open tabs, visible status bar) - this is not
  enough for real code analysis or a correctness judgment; say so rather
  than extrapolating into how the code behaves.
- **QA automation screenshots** can support a descriptive automation
  implementation overview: framework/tooling, visible folder structure,
  page-object or helper patterns, fixtures/auth setup, visible test files,
  and coverage gaps named by the screenshot or notes. Do not turn this
  into a numeric quality score unless the source itself provides measured
  numbers.
- **Screenshots of AI answers/tables/chat output** can be OCR'd/read for
  text, but if the user can paste the actual text instead, prefer that -
  a screenshot is a fallback for text, not the preferred source when text
  is available.

## Guardrails

- Screenshots are supporting evidence, not a substitute for source
  text/logs/repo files when those are already available. If a transcript,
  chat export, or document already covers the meeting, treat screenshots
  as sidecar evidence that can enrich UI/tooling details, clarify what was
  visible on screen, or corroborate the text source - not as a reason to
  reprocess the same meeting blindly.
- Do not infer project/person/meeting identity from a screenshot filename,
  URL, browser title, repo name, or cropped UI label alone. Identity must
  come from the user's notes/chat, an explicit linked source, or a
  registry-backed lookup. If identity is missing or conflicting, ask
  before moving or routing the bundle.
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
- The user's own notes are an authoritative instruction for triage
  (skip/reject a specific screenshot as a duplicate, bad quality, or not
  important), not just descriptive context to weigh against your own
  read - honor a stated skip without re-opening/re-judging that file.
  The goal is less manual work per pass, not more independent judgment
  calls on files the user already disposed of.
- Do not treat an AI-generated estimate visible in a screenshot (a
  coverage %, a quality score, an effort guess produced by some other AI
  assistant reading code) as a verified metric once it lands in a durable
  document - label it as self-reported/AI-estimated with unclear
  methodology. Do not build automated verification of such a number
  without the user first defining a concrete methodology - guessing at
  one is worse than leaving the caveat in place.
