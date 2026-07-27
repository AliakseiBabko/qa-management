# Operational Registries

Scope: the workspace-wide operational logs that track *how* sources get
processed — `evidence_log` traceability discipline, the canonical
`source_type` list, `_skill_invocations`, `_closure_outcomes`, and
`_intake_queue`. Load this module for any intake, retro, or repo-maintenance
skill that reads or writes one of these logs, or that needs the canonical
`source_type` spelling for a new source shape. This is the canonical owner
of the `source_type` list — `pipeline_common.SKILL_INVOCATION_SOURCE_TYPES`
and `validate_repo.py` both check against it directly.

## Evidence Log Traceability

`evidence_log` traceability is not just for automated sync-script runs.
Any update made conversationally — processing a transcript/chat dropped in
`00_Inbox`, applying M2's own answers from an `m2_input` round,
analyzing a source file on request (e.g. a grade/assessment matrix) — must
also get an `evidence_log` row, with the same columns as an automated sync:
`date, source, source_type, project, routed_to, notes`. When the source is
the conversation itself rather than a file (e.g. M2's answers in a
preliminary-analysis round), use a descriptive `source` value (e.g. "M2
conversation 2026-07-08 — risk level & rollup answers") and a `source_type`
like `m2_conversation`. List every document actually touched in
`routed_to`, comma-separated, not just the first one. The point is that
`evidence_log` should answer "which live documents changed because of this
source" for every source, automated or conversational — a log that only
covers automated syncs is misleading about what actually changed.

## Canonical `source_type` List

`source_type` canonical values (do not invent a new spelling of an
existing concept — check this list first): `strategy_chat`,
`meeting_transcript`, `m1_history`, `m2_conversation`, `qa_1to1`,
`admin_note`, `people_case_chat` (a person-specific incident chat under
`02_Chats_and_Emails`, e.g. a leaving-case thread — distinct from a
project-wide `strategy_chat`), `retro` (a `qa-retro` improvement-loop
pass over the log itself — its row is also the marker
`prepare_retro.py` slices the next window from). Three pre-classification
values — `raw_transcript`, `raw_chat`, `source_document` — are written
only by `prepare_intake_review.py` on newly-discovered files ("pending M2
review"); once a source is actually processed, its rows use one of the
real types above, never the raw label. If a genuinely new source shape
appears, add it here rather than picking an ad hoc value silently at the
point of use.

Four more values belong to the Project Knowledge lane (`30_Project_Knowledge`,
see `document_graph.yaml`'s `lanes:` mapping — a separate lane from M1/M2
management reporting, for building project understanding from whatever
sources actually exist): `project_knowledge_transcript` (a recorded/
transcribed conversation), `project_knowledge_document` (a written
artifact — design doc, presentation export, spec), `project_knowledge_chat`
(a chat/message-thread export), `project_knowledge_notes` (the owner's own
short notes, too brief to warrant a separate summary document). None of
these four route to any M1/M2 document — see `project-knowledge-roles`.

## `_skill_invocations`

Separate from `evidence_log` (which is per-project and answers "which live
documents changed because of this source"), `_skill_invocations` is a
single workspace-wide living Sheet at the Drive root (not nested under
`10_`/`20_`, same clone-independence reasoning as `_people_registry`) that
answers "what skill(s) actually got applied to this source" — across both
M1 and M2, so those patterns can be analyzed later (e.g. "which document
shapes reliably trigger which skill combo") instead of only living in
conversation history. Log a row every time a source document or
conversational request gets processed through one or more skills —
whether or not it ends up changing a canonical document (a first-contact
1to1-invite draft that produces no lasting document is still worth
logging, since the point is skill-trigger patterns, not just outcomes).

Use `pipeline_common.log_skill_invocation()` rather than hand-rolling the
Sheets write — it validates `source_type` against the same canonical list
above and reformats the Sheet after writing. Columns: `Date`, `Source`,
`Source type`, `Project` (blank if not project-scoped), `Person` (blank if
not about one person), `Skills applied` (comma-separated skill folder
names, e.g. `qa-1to1-analysis, m2-1to1-apply` — list every skill actually
applied, not just the first one that seems to fit, same discipline as
`evidence_log`'s `routed_to`), `Documents touched` (blank if none),
`Notes`.

When the processing pass belongs to an intake-queue run (`qa_manage.py`),
`Notes` must also carry the exact run token `run:<run-id>` — `complete`
verifies the token's presence, and substring/source-path matching is
deliberately not accepted (an old invocation row for the same source must
not satisfy a new run).

`Notes` additionally carries the improvement loop's raw material: when
the user corrects or overrides something during a pass (wording, routing,
a judgment call), capture it in that pass's row as a note prefixed
`feedback:` naming the target, e.g. `feedback: m2-1to1-apply — routed X
only to individual_metrics, user also wanted m2_input`. Keep it abstract
enough for pattern-matching (the skill/rule and the shape of the miss),
one `feedback:` note per distinct correction. `qa-retro` groups these
notes across passes and proposes a rule change once the same shape
repeats — a correction that only lives in conversation history is
invisible to that loop.

## `_closure_outcomes`

Workspace-wide append-only Sheet at the Drive root: one row per resolved
cascade edge per intake run — `Run ID`, `Timestamp`, `Project`, `Person`,
`Route variant`, `Source node`, `Target node`, `Edge kind`, `Outcome`,
`Reason`, `Actor`. Written via `closure_outcomes.py record` (never a raw
Sheets write — it validates the outcome against the edge's kind in
`document_graph.yaml`: `direct`→`updated`; `judgment`→`updated`/`no_change`
(+reason); `gated`→`gated` (+reason)/`updated`; `script`→`regenerated`).
The same edge may resolve differently for two projects/people in one run —
that's what the scope columns are for. `check_cascade_closure.py --run-id`
reads these rows, so "no change needed" becomes a recorded, checkable fact
instead of a sentence in a chat reply. Until the intake queue mints
canonical run ids, use `<date>-<source-slug>`.

## `_intake_queue`

Workspace-wide Sheet at the Drive root: one row per intake run, managed
only through `qa_manage.py` (scan/next/start/record-analysis/resolve-edge/
record-apply/resolve-edge/block/resume/complete/fail/historical) — never
edited by hand, and unlike the append-only logs its rows are updated in
place as a run moves through `discovered → needs_scope/ready → processing
(analysis→apply→closure) → finalizing → completed/failed/historical/
ignored`, with `blocked` as a parking state and `finalizing` as the
retryable verification-passed-but-bookkeeping-pending step. `historical`
asserts the source WAS processed pre-queue (evidence required); `ignored`
(categorized: course material / reference material / duplicate artifact)
asserts it is not intake at all and is reachable only from
pre-processing states — never conflate the two. `historical` is the terminal state for sources processed
before the queue existed (evidence required — pre-queue history is not a
failure); `failed` may be corrected to `historical` when migration
evidence turns up. Source identity is (path, content hash): changed
content at a known path is rediscovered as a superseding run, identical
content at a new path is recorded as a duplicate. `start` records the
agent's classification with explicit (project, person) scope tuples —
never a Cartesian product, never a silent default (`needs_scope` instead).
`record-apply` records a per-scope outcome for every route entry document
(`updated` / `no_change`+reason / `not_applicable`+reason); only updated
entries seed the cascade. `complete` is a verification gate: entry
outcomes valid per scope, strict closure per scope, the exact
`run:<run-id>` token in `_skill_invocations`, and a clean mirror snapshot
not older than the run's last mutation. Its exact SHA is persisted on the row,
and `complete` validates that this specific business snapshot SHA contains the
exported text blob for any `Source text version 1` run. The terminal queue state
itself is exported to the mirror as a follow-up commit. The `review <run-id>` command provides a read-only evaluation of
a run's completion readiness (missing invocation evidence, snapshot problems,
unresolved edges) without mutating the queue. All `qa_manage.py` commands support
a strict `--json` contract (suppressing normal stdout and emitting exactly one
JSON envelope at the end) for programmatic agent integration. Rows hold operational
metadata and short summaries only — never transcript content or analysis bodies.
The queue's `Run ID` is the canonical run id used in `_closure_outcomes`,
`_skill_invocations` notes, and mirror commit messages.
