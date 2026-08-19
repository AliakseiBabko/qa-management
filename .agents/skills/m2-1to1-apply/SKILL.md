---
name: m2-1to1-apply
description: Apply a QA 1:1 transcript's people/project signals (already extracted via qa-1to1-analysis) through the M2 cascading-update chain - individual_metrics, individual_development_plan, project_risk/project_development_plan, m2_input, evidence_log. Use after analyzing an M2 1:1 transcript from 00_Inbox when the findings should actually update live project documents, not just produce a summary.
---

# M2 1to1 Apply

`qa-1to1-analysis` explicitly does not own writing to final documents ("does
not own final report-file creation... use an M1 or M2 writer skill for
that"). For M2, this is that skill — the routing step between "here's what
the transcript says" and "here's what changed in the project's canonical
documents." It mirrors `m2-strategy-chat-analysis`'s workflow, just for a
1:1 transcript instead of a strategy chat.

## Required Start

1. Run `qa-1to1-analysis` first — topic classification, strongest facts,
   people/project signal separation. Don't skip straight to routing.
2. Read `../qa-management-roles/references/m2-role/m2-cascading-updates.md`
   and `../qa-management-roles/references/m2-role/m2-project-rollups.md`.
3. Read `../qa-management-roles/references/google-workspace/m2-layout.md`
   (person/project document locations), `../qa-management-roles/references/google-workspace/operational-registries.md`
   (`evidence_log` discipline), and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`
   (this skill writes and shares Drive artifacts directly - see Workflow).
4. Run `.agents\scripts\show_project_state.py --project <Project>` to see
   current state before editing anything — a transcript often corroborates
   or resolves something already recorded, not just adds new content.

### Efficiency and reliability protocol

Before starting a live Drive pass:

- Resolve the project and person through the registry/queue identity first.
  Keep the canonical IDs and names in variables; do not repeatedly rediscover
  the same folder by display-name search or mix a registry name with an ad-hoc
  transliteration in later closure commands.
- Use the existing Drive source-reader and pipeline helpers. Do not begin
  with an experimental raw Drive API download when a supported reader already
  exists; this avoids duplicate OAuth/network round trips and inconsistent
  decoding.
- Prefer targeted state reads for the documents in this route. Use the full
  project-state view only when the judgment actually depends on unrelated
  project documents.
- Build the touched-document set once from the routing decision, then apply
  the direct updates and downstream rollups in dependency order. Do not run
  broad refresh/export commands between individual document writes.
- All subprocesses that receive or print business text must use UTF-8
  explicitly, especially on Windows. Before continuing after a write, reject
  replacement characters or `?`-filled names; a malformed identity or closure
  row is a failed write, not a cosmetic warning.
- Treat a snapshot as a finalization step. Prefer a valid scoped snapshot;
  if scope resolution fails, diagnose the identity/path problem before
  falling back to a workspace-wide export, because the latter is materially
  slower and can mask the original defect.
- Keep the required telemetry closeout as the final bounded step. For a
  queue-backed run use `closeout_telemetry.py`; do not create an additional
  current-session central row for the same pass.

## Workflow

1. Update the person's `individual_metrics`/`individual_development_plan`
   directly with whatever the transcript factually supports (Cascading
   Updates step 1) — no gate needed for direct, evidence-backed person-level
   facts.
2. If the transcript's content would change a `project_risk`/
   `project_development_plan` conclusion, route it through `m2_input` using
   `pipeline_common.add_questions()` — it auto-opens a new round or extends
   the current pending one, whichever the doc's state calls for. Don't edit
   `project_risk`/`project_development_plan`'s judgment conclusions directly
   from a single 1:1 the way you would a person's own metrics.
3. If the transcript resolves a question already sitting in a pending
   `m2_input` round (this happens — a 1:1 is a common way a previously-open
   question actually gets answered), write the resolution with
   `pipeline_common.add_answer()` rather than leaving the round stale. Only
   do this when the transcript genuinely settles the question, not when
   it's merely related.
4. If `qa-1to1-analysis` flagged a management-case candidate, route it to
   `pm-case-knowledge-intake` now (load `../pm-case-knowledge-roles/SKILL.md`
   first) - it confirms the case has real shape and writes
   `pm_case_library`/`pm_case_index` itself; this skill never edits those
   directly. Most passes have no candidate to route - that's normal.
5. Log `evidence_log`: `source_type` = `qa_1to1`, `routed_to`
   listing every document actually touched (person-level and project-level
   both, when both changed) - include `pm_case_library` if step 4 wrote one.
6. Close the cascade: run `.agents\scripts\check_cascade_closure.py
   --touched <routed_to list>`. Resolve every OPEN item it reports —
   update the document, run the named script, or state "no change needed"
   with a reason — before declaring the intake done.

7. Refresh only mechanical dependants required by the touched set (for
   example `refresh_project_registry.py` after `project_metrics` changes),
   then archive the source, take the final snapshot, complete the queue, and
   close telemetry. These finalization operations should not be interleaved
   with judgment edits.

- A single finding can legitimately belong in more than one place at once
  - don't under-scope it to just the first document that seems to fit. A
  story like "manager didn't hear my side of a conflict" can simultaneously
  be a people-risk signal (`individual_development_plan`), project-process
  evidence (`m2_input` - e.g. a single point of contact/failure), and a
  wider organizational-process finding (`m2-role-rules.md` or a similar
  shared reference - see its module index if it's not scoped to just this
  project). Route it to
  every document it actually supports, not just the most obvious one.

## Guardrails

- Apply the same registry-scoping and Person Card cross-reference
  guardrails as `m2-strategy-chat-analysis` (don't duplicate them here) —
  a 1:1 can just as easily surface a role/track/level mismatch (see
  `m2-role/m2-metrics-attribution.md`, Вклад в проект Calibration) as a strategy chat can.
- Don't fabricate an "M2 answer" in `m2_input` — only write into the answer
  section when the transcript's content actually resolves the round's
  questions, not to force a round closed.
- A 1:1 is evidence about the person and, incidentally, the project they're
  on — not project-wide evidence by default. Don't let one person's account
  of a project-wide event (e.g. "the client ignored us") stand in for
  independent confirmation if the same fact should really come from a
  strategy chat or a direct account-level source; note whose account it is
  when the confidence matters (see `m2-role/m2-risk-rules.md` — naming
  the feedback path).
