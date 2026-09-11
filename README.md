# qa-management

Repository for QA-management agent infrastructure.

This repo stores:

- shared skill definitions under `.agents/skills/`
- canonical CSV templates under `Templates/`
- shared 1to1 analysis rules under `.agents/skills/qa-1to1-analysis/references/`
- a machine-local adapter at `.agents/skills/qa-management-roles/`; the
  canonical role skill is in the private sibling
  `../ai-management/skills/qa-management-roles/`

Operational data and generated report files are managed in the QA Management Google Drive workspace:

`https://drive.google.com/drive/u/0/folders/1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`

Google Drive root folder ID:

`1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`

The desktop mirror / filesystem fallback is:

`G:\My Drive\QA_Management`

Current Drive layout:

- `00_Inbox/`: the single recursive intake folder. Drop transcripts,
  chats, emails, spreadsheets, or other source files here without manually
  classifying them. Empty means there is no unprocessed file intake.
  Everyday discovery scans this folder only.
- `05_People_Management/`: `_people_registry` — the single workspace-wide
  people Sheet, covering everyone (M1-managed, M2-staffed, client-side)
  regardless of which skill is looking at it. Deliberately not nested under
  `10_` or `20_` so a repo clone used for only M1 or only M2 work still
  finds it.
- `10_M1_People_Management/`: person-based (`<Person>/` subfolder per
  team member)
- `20_M2_Project_Management/`: project-based M2 project-management outputs,
  plus two cross-project rollups at the lane root: `_project_registry` (the
  generated executive war-room view) and `_metrics_collector_registry` (one
  row per (Person, Project) pair holding a key for the external git-metrics
  collector - hand-maintained, M2/M3 only, see `m2-git-metrics-onboarding`)
- `30_Project_Knowledge/`: project-based, learning/onboarding project
  understanding — distinct from M1/M2 management reporting above
- `40_PM_Case_Library/`: flat, cross-project, personal-reference
  management-pattern case library
- `50_QA_Department_Standards/`: flat, personal-reference department
  standards (current tools/process requirements/direction) plus a
  personal lessons-learned log
- `60_Assessments_And_Interviews/`: session-based — session *type* folder
  (`internal_assessments/`, `external_interviews/`, `other_interviews/`),
  then `<Person>/`, then one dated feedback document per session, plus a
  flat `_assessment_index` at the lane root. Append-only: a new session
  never rewrites an earlier one's document
- `55_AI_Adoption/`: cross-project AI-in-QA practice - a tiered knowledge
  base at the lane root (source notes, knowledge store, best-practices wiki,
  plus a Russian generic rules digest derived from the wiki) and one dated
  scored review per project per session under `reviews/`. Append-only for
  reviews: a re-review is a new document
- `80_Exports/` (optional): created only when an explicit immutable package
  or copy is prepared for external sharing; internal extracts do not belong here
- `90_Storage/`: the single non-actionable storage root:
  - `Reference/`: durable source and training/reference material
  - `Processed_Sources/`: originals already processed by the intake pipeline
  - `_System/`: generated extracts and review bundles
  - `Backups/`: private-mirror recovery bundle
  - `Retired/`: retired outputs and legacy folders
  This root is explicitly excluded from source discovery; moving a file
  here means it is no longer part of the active intake backlog.

Full per-lane folder shapes, document conventions, and sharing/visibility
rules for every folder above:
[docs/workspace-layout.md](docs/workspace-layout.md).

The role-skill adapter is a junction, not a second copy. Recreate it after a
fresh clone with:

```powershell
python .agents\scripts\link_management_adapters.py --project .
```

No raw video/multimedia is stored in Drive - only transcripts and
documents. Folder moves use the Drive API so file IDs, links, revisions,
and existing permissions are preserved. See
`.agents/skills/qa-management-roles/references/google-workspace/workspace-basics.md`
for the full folder-mapping notes, and
`.agents/skills/qa-management-roles/references/google-workspace/api-sharing-editing.md`
for Sharing Safety.

Final business outputs should prefer Google Sheets for tabular artifacts and Google Docs
for narrative/status artifacts when Google API access is available. Local CSV/Markdown
files remain valid as fallback, staging, source-extraction, and export artifacts.

## Documentation

This README is the entry point; detailed reference lives in `docs/`:

- [docs/workspace-layout.md](docs/workspace-layout.md) — the People
  Registry, M1 Person Layout, M2 Project Layout (visibility boundaries,
  update chain, process checklist, presale/upsell, Outstaff Delivery
  milestone reports), Project Knowledge Layout, PM Case Library Layout,
  QA Department Standards Layout, Assessments & Interviews Layout, and the
  Visual Evidence Drop folder.
- [docs/pipeline-scripts.md](docs/pipeline-scripts.md) — source
  extraction, the Google API smoke test, the legacy M2 batch-generation
  tool, and the full reference for every script under `.agents/scripts/`
  that actually runs day to day (`qa_manage.py`, `show_project_state.py`,
  `search_workspace.py`, telemetry closeout, mirror/rollback, and the
  rest).
- [docs/reporting-skills.md](docs/reporting-skills.md) — status reports,
  the department traffic light, timeline/action items, self-review, and
  monthly KPI reports.

Large implementation plans and cross-agent review notes are kept in the
private sibling repository [`ai-management`](../ai-management/management/),
shared across project repositories. This repository retains only the local
adapter and wrapper.

For a multi-model planning dialogue, use the
[`management-plan-dialogue`](.agents/skills/management-plan-dialogue/SKILL.md)
skill. It defines how models exchange canonical plans, attributable reviews,
responses, disagreements, and independently proposed improvements.
The adapter delegates to the canonical skill in `../ai-skills`.

Skill inventory and behavior live in each skill's own `.agents/skills/<name>/SKILL.md`,
not in this README or AGENTS.md — see `.agents/skills/`.
