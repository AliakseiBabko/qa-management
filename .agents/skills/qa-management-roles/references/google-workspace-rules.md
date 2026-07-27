# Google Workspace Rules — Module Index

This file is a **routing index only** — it carries no normative rules of
its own. Load only the module(s) your skill actually needs from
`google-workspace/`, never this whole file plus every module.

| Module | Load it for |
|---|---|
| [workspace-basics.md](google-workspace/workspace-basics.md) | canonical Drive root, Sheets-vs-Docs choice, top-level folder map |
| [m1-layout.md](google-workspace/m1-layout.md) | any M1 people-management output (per-person folder, M1-root artifacts) |
| [m2-layout.md](google-workspace/m2-layout.md) | any M2 project-management output (private/shared folders, `_project_registry`) |
| [people-registry.md](google-workspace/people-registry.md) | reading/writing `_people_registry`, either person-card intake shape |
| [operational-registries.md](google-workspace/operational-registries.md) | `evidence_log`, `_skill_invocations`, `_closure_outcomes`, `_intake_queue`, or the canonical `source_type` list |
| [artifact-conventions.md](google-workspace/artifact-conventions.md) | naming/versioning, Sheet/Doc conventions, or writing final business-facing prose |
| [api-sharing-editing.md](google-workspace/api-sharing-editing.md) | actually calling the Drive/Sheets/Docs API, or sharing a folder |
| [search-source-extraction.md](google-workspace/search-source-extraction.md) | searching the workspace broadly, or analyzing a `.docx`/`.xlsx` source |
| [pipeline-architecture.md](google-workspace/pipeline-architecture.md) | judging what's safe to automate vs. what stays conversational |

Each module is self-contained; load the smallest set that covers your
skill's actual reads/writes, not every module "just in case."
