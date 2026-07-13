# Document Contract

Primary final output is a Google Sheet in `20_M2_Project_Management\<Project>`,
with local CSV fallback. Preserve the CSV template columns as the Sheet schema.

## Purpose

Use this reference for the project-risk document family.

## Template

`<repo-root>\Templates\светофор_рисков_проекта.csv`

## Expected Output

One project-risk traffic-light document per reporting snapshot.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management\<Project>`

Suggested naming pattern:

`светофор_рисков_проекта_YYYY-MM-DD.csv`

## Versioning

- `generate_m2_outputs.py` (see README, "legacy first-pass tools") is not
  template-aware: it mechanically pulls `label: value` bullets out of each
  source document's own Scorecard section into whatever columns happen to
  line up, without synthesizing a single project-level voice per column —
  this is where rows like a `Риск staffing / continuity` cell literally
  reading `Owner: X. Owner: Y. Owner: Z.` come from. Its `project_risk`
  output is a raw source dump, not a compliant row — never treat it as
  already following this schema. When applying this schema to a project for
  the first time (or fixing a row that reads like disconnected fragments
  instead of one coherent risk assessment per column), back up the old row
  as `project_risk_predecessor_<date>` and write a real synthesized row from
  the evidence, the same way <Project>'s and <Project>'s were done.
  `sync_m2_source_docs_to_sheets.py` uses this same extraction path — it
  only creates `project_risk` when one doesn't exist yet (a rough
  bootstrap) and never overwrites an existing one, specifically so rerunning
  it can't silently replace a real synthesized row with fragments again.
- Use the living project-local `project_risk` file for current state, and append
  source traceability to the project `evidence_log`.
- Do not overwrite an existing formal dated project-risk snapshot by default.
- If the target snapshot-date file already exists, create the next versioned file with a `_vN` suffix before `.csv`, for example `_v2` or `_v3`.
- Update an existing project-risk snapshot in place only when the user explicitly asks for revision.

## Schema

Use exactly the columns in `Templates\светофор_рисков_проекта.csv`:

1. `Проект`
2. `Период / snapshot date`
3. `Общий уровень риска`
4. `Риск delivery`
5. `Риск QA process`
6. `Риск staffing / continuity`
7. `Риск communication / client`
8. `Комментарии`
9. `План действий`
10. `Owner` — an actual accountable owner (a person or M2 itself), not left
    blank. Every project's `Owner` cell was empty before 2026-07-08; treat a
    blank `Owner` as an incomplete row, not an acceptable default.
11. `Следующий review`

`Evidence / источники` was removed from this schema: it only ever held raw
source file paths, which is exactly the pattern already excluded from
`individual_development_plan` for the same reason — a bare list of paths
tells the reader nothing, and that traceability already lives in
`evidence_log`. Do not reintroduce a raw-path evidence column here.

## Inputs

- `m2_input` — the latest round's answers. If the latest round's answer
  section is empty, this is a rollup and you must stop and run the
  preliminary-analysis round first (see `m2-role-rules.md`
  Project-Level Rollups) rather than proceeding on metrics alone.
- Individual `Вклад в проект` conclusions and the `Команда: ...` rollup rows
  in `project_metrics` — a person flagged `Есть риск` is a candidate risk
  signal, but confirm via `m2_input` whether it's project-level or stays
  scoped to that person's own plan (see Risk Interpretation Notes).
- QA 1to1 findings
- project transcripts
- delivery/process notes
- staffing or project context data
- extracted source corpus under `G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`

## Evidence Rules

- Prefer direct project evidence over general impressions.
- Keep people-performance concerns out of the project-risk file unless they create explicit project continuity, delivery, or client risk.
- Put source names or dated meetings in `evidence_log`, not in this Sheet — `project_risk` has no evidence column (see Schema above).
- Name the feedback path when it affects confidence: direct client, intermediary, DC/QA Lead, team, or employee self-report.
- Treat hidden topology as evidence gap and risk signal for active projects: unknown streams, real team size, DC/PM ownership, vendor/intermediary chain, client path, tender/contract horizon, or security/location constraints.
- Use only `Низкий`, `Средний`, or `Высокий` in risk level fields and final documents. Do not use `Low`, `Medium`, `High`, `Critical`, or `Unknown` as final risk values.
- `Общий уровень риска` answers one specific question: does something concretely
  threaten this engagement's continuation, trust, or a near-term hard
  commitment *right now* — not "is there a serious problem somewhere in the
  project." Almost every active project has at least one individual risk
  item worth calling serious; if that alone were enough to set the overall
  level, every project would read `Высокий` and the field would stop being
  useful for telling projects apart. The homework corpus this contract is
  derived from (`00_Source_Docs\M2_project_development_plan`) never
  computes one project-wide score either — it lists named risks, each with
  its own severity, and never collapses them into a single verdict. Follow
  that same discipline: individual risk columns (`Риск delivery`, `Риск QA
  process`, etc.) can and should say a specific thing is serious in its own
  right; `Общий уровень риска` is a separate, stricter judgment about the
  engagement as a whole.
- Risk-level dictionary:
  - `Низкий`: no open item threatens continuation, trust, or a near-term
    commitment. Remaining gaps are business-as-usual execution/improvement
    items with clear ownership.
  - `Средний`: real, unresolved risk factors exist (process/coverage/staffing
    gaps, delivery pressure, an individual item rated seriously on its own)
    that could escalate without continued management attention — but
    nothing right now threatens the engagement itself, and there is no
    explicit client dissatisfaction or contract/staffing crisis in motion.
    This is the expected default for an actively-managed project with real
    gaps and no acute crisis — most projects, most of the time, belong here.
  - `Высокий`: something concretely and already threatens the engagement's
    continuation, trust, or a near-term hard commitment — explicit client
    dissatisfaction already voiced, a contract/renewal/tender decision
    genuinely in question, an active client-driven replacement/staffing
    crisis, or an equivalent already-materialized threat. Reserve this;
    do not set it just because one dimension or one named risk is severe.
- If `project_metrics`'s `Статус проекта` is `На паузе` (client-driven pause,
  not an official stop/cancellation — see `Templates\метрики_проекта_qa.md`
  §1.0), `Общий уровень риска` stays frozen at its last real value rather
  than being remapped onto the pause. A pause is not a point on the
  Низкий/Средний/Высокий scale (it answers a different question — "is work
  progressing," not "does something threaten the engagement") — don't force
  it into `Высокий` just because delivery has stopped, and don't lower it to
  `Низкий` just because the immediate MVP-instability risk that produced the
  current value is no longer the active concern. `Следующий review` gets no
  fixed date while paused — reactivation is a manual M2 decision (see §1.0),
  not a calendar event, so leave it stated as "no cadence, awaiting manual
  reactivation" rather than a stale or invented date.
- English aliases are for migration/interpretation only and must not appear as risk values in generated outputs.
- Treat missing visibility as a risk signal for active projects. If a project is not at the very beginning and the current level cannot be detected because metrics, delivery status, QA-process evidence, or client/team feedback are unavailable, set the affected level to at least `Средний` and explain the evidence gap in comments.
- For a genuinely new project with insufficient evidence, use `Средний` by default unless concrete facts support `Низкий` or `Высокий`.
- State why the risk matters and what future harm it can cause.
- Separate project/stake risk from individual performance risk. Do not lower or raise a project risk solely because one QA is strong or weak unless that fact affects delivery, continuity, client trust, or role value.
- Keep sensitive internal details out of final comments unless they are necessary for the management action. If location, security, vendor-chain, or client-path facts are needed, phrase them as concise risk context.

## Risk Interpretation Notes

- If a project-side stakeholder questions the need for QA or believes QA can be replaced without loss, treat this as an `our-role` / business-value risk and map it to communication/client or QA-process dimensions as appropriate.
- If the project is paused, contract end is near, tender horizon is known, or client dissatisfaction has already affected continuation, reflect that in the overall level and action plan.
- If a junior or newly onboarded QA is placed into a senior/project-critical expectation, classify the risk by project impact, not by personal criticism.

## Rule

Keep this skill scoped to one project-risk document format only.
