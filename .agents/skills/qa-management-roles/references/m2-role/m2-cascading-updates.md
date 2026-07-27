# M2 Cascading Updates

Scope: The per-person to per-project to workspace-wide update chain, and its relationship to document_graph.yaml.

## Cascading Updates

The chain is `individual_metrics`/`individual_development_plan` (per
person) → `project_metrics` (per project, M2's full-picture dashboard) →
`_project_registry` (across every project M2 owns, the "war room" view).
When a new source (a chat, a transcript, a document dropped in
`00_Inbox`, `90_Storage/Reference`, direct M2 input) changes something at the
person level, update the whole chain in the same pass — not just the
bottom layer:

1. Update the person's `individual_metrics` row(s) and
   `individual_development_plan` sections that the source actually
   supports.
2. Refresh the corresponding rows in that project's `project_metrics` —
   the `Вклад в проект: <Имя>` conclusion (and the aggregated team row, if
   the project has more than one person), and `Горизонт совместной
   работы` / `Бизнес-риск продукта клиента` / `Качество QA-процесса` if
   the source touched any of those. Every metric row in `project_metrics`
   is a **current-value dashboard row keyed on (project, metric name,
   person)** — update that one row in place (new date + new explanation),
   never append a second row for the same key. A real intake once appended
   a fresh dated `Вклад в проект: <Имя>` row instead of updating the
   existing one; `refresh_project_registry.py` doesn't dedupe by person,
   so the duplicate rendered as `<Имя>, <Имя>` live in `_project_registry`
   until caught by audit and repaired by hand. If the metric's evolution
   over time is itself worth keeping, log it in `evidence_log` (already
   append-only) or a dedicated history table — not as a second current row
   in this sheet.
3. Refresh that project's row in `_project_registry` to match.

Leaving `project_metrics` or `_project_registry` stale after an
`individual_metrics` update defeats the point of the dashboard — it's
supposed to be the one place to see the full picture, not one of several
places that might be out of date.

The same refresh discipline applies no matter which document the change
enters through. `_project_registry` is mechanically generated from
`project_metrics` only (`refresh_project_registry.py` never reads
`project_risk` directly), so a `project_risk` update refreshes the
registry only when it also changes one of the `project_metrics` rows the
registry mirrors (`Статус проекта`, `Горизонт совместной работы`,
`Бизнес-риск продукта клиента`, `Вклад в проект: <Имя>`,
`Качество QA-процесса`) — for example, a risk review that concludes a
project should move to `На паузе`, or that changes a person's `Вклад в
проект` conclusion. When a `project_risk` pass does touch one of those
`project_metrics` rows, update that row and rerun
`refresh_project_registry.py` in the same pass, same as any other
`project_metrics` change — do not treat `project_risk` as a dead end just
because the script doesn't read it directly.

This fan-out (and the M1 chain) is encoded as data in
`.agents/document_graph.yaml`; `.agents/scripts/check_cascade_closure.py`
expands it into a checklist and flags downstream documents not yet
accounted for. Run it at the end of any pass that touched these documents
instead of re-deriving the chain from this prose — and keep the graph file
in sync when a new document type or dependency is introduced (same commit
as the skill that adds it). The script only computes *which* documents to
visit; whether each one changes, and what to write, remains this file's
judgment rules.
