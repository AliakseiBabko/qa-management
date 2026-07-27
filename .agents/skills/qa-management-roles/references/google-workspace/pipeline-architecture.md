# Pipeline Architecture

Scope: what runs mechanically versus what stays a conversational judgment
step. Load this module for repo-maintenance-style work or any skill
reasoning about which part of the sync pipeline is safe to automate.

There is no automated observer/dispatcher watching inbox folders. Every sync
this repo does — extraction (`qa_source_extract.py`), intake review
(`prepare_intake_review.py`), Sheet/Doc sync
(`sync_m2_source_docs_to_sheets.py`, `sync_m2_plans_to_docs.py`), formatting
(`format_all_sheets.py`), and the registry refresh
(`refresh_project_registry.py`) — runs because M2 asked for it in
conversation, not because a file landed in an inbox folder. Treat "drop a
chat/email in an inbox folder and it gets processed" as the intent behind
this pipeline, not as something already wired up.

`prepare_intake_review.py` is the mechanical front half of that intent —
classify what's new and log it — but it stops at exactly the same judgment
boundary as everything else here: it does not decide what a new file means
for a project, only that the file exists and (when classifiable) which
project it probably belongs to. Reading the flagged files and deciding
whether they change the picture enough to warrant an `m2_input` round is
still a conversational step.

The one piece that is safe to run mechanically without a human judgment step
is `refresh_project_registry.py` — it copies each project's already-curated
`project_metrics` dashboard rows (Горизонт/Бизнес-риск/Вклад в
проект/Качество QA-процесса) into `_project_registry`, worst-case not
averaged, with no interpretation of its own. `rollup_individual_metrics_to_project.py`
is deprecated (see README, "Current pipeline scripts") — it computed a
statistical `Команда: ...` distribution row that `project_metrics` no
longer has any place for; `refresh_project_registry.py` is its replacement
as "the mechanical step," not a rollup of `individual_metrics` at all.
Everything upstream of `project_metrics` itself — deciding what's shareable
vs. `m2_input`-only, drafting plan/risk language, weighing one person's read
of a project against another's, and writing `project_metrics` in the first
place — is a judgment step, and should stay conversational until there's a
long track record showing those judgment calls are stable and repeatable
enough to encode.
