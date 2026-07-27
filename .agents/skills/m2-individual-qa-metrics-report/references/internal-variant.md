# M2 Individual Metrics Internal Variant

Scope: the private `individual_metrics_internal` Sheet — when and how to use it, separate from the shared `individual_metrics`. Load only when actually writing or updating this Sheet.

`individual_metrics_internal` is a second, separate Sheet per person —
`private\people\<Person>\individual_metrics_internal`, separated from the
employee-facing `individual_metrics` but never shared with that employee
(see `google-workspace/api-sharing-editing.md`, Sharing Safety). It exists because M2
sometimes has a real, evidence-based read that isn't ready — or isn't
appropriate — to put in front of the employee: a subjective doubt about
whether an improvement is durable, a concern surfaced by someone else (a
1:1, a client aside) that hasn't been confirmed enough to act on, a
perspective that conflicts with what's already recorded in the shared
table. This is not a place to invent concerns — every row still needs real
evidence, same as the shared table; the difference is readiness/
appropriateness to share, not evidence quality.

Schema: same 8 columns as `individual_metrics`, plus one —
`Сторона` inserted after `Дата`: who this read belongs to (`M2`, `M1`,
`клиент`, `команда`, `QA-инженер` for self-report) — because this table
exists specifically to hold multiple, sometimes-disagreeing perspectives
side by side rather than collapsing them into one voice the way the shared
table does.

Same current-state/dedup mechanics as `individual_metrics` — one row per
(`Проект`, `Сотрудник`, `Метрика`, `Сторона`); new evidence for the same
side updates that row in place. `Сторона` is part of the key (not `Дата`)
because the same metric can carry different reads from different sides at
once — that's the coexistence this table exists for. It is not a place to
stack the same side's opinion over time; if a side's read on a metric
changes, update their row, and keep the evolution in `evidence_log` if
it's worth keeping.

Do not feed this table into the automated `project_metrics` rollup script —
it only reads the shared `individual_metrics` Core set. Anything from here
that should influence `project_risk` or `project_development_plan` goes
through the normal `m2_input` two-phase gate (see `m2-role/m2-project-rollups.md`
Project-Level Rollups): raise it as a preliminary-analysis question, wait
for M2's answer, then apply it — the same discipline as any other
project-level rollup input, not a shortcut around it.

When something recorded here becomes solid enough to share, promote a
sanitized version of it into `individual_metrics` or
`individual_development_plan`'s `Фокус развития` — do not just widen access
to this Sheet.
