# M2 Project Development Plan Sources And Normalization

Scope: which evidence to prioritize and how to write each section well, including the Upsell section's evidence rule.

## Source Priority

1. Existing project development plan.
2. `m2_input` — the latest round's answers. If the latest round's answer
   section is empty, this is a rollup and you must stop and run the
   preliminary-analysis round first (see `m2-role/m2-project-rollups.md`
   Project-Level Rollups) rather than proceeding on metrics alone.
3. Business/project context, client expectations, strategy-chat statuses, and
   project goals.
4. Project risk summary.
5. Project metrics, including the `Команда: ...` rollup rows and each
   person's `Вклад в проект`.
6. Workbook status/context rows.
7. Individual plans only when they reveal a project-level capability or
   continuity gap.
8. `presale-upsell-rules.md`'s diagnostic markers, cross-checked against
   this project's actual metrics/risk/status evidence — for the
   Возможности расширения (Upsell) section only. This reference supplies
   the criteria and framing, not the evidence itself.

## Normalization

- State the executive summary and current-state context once; do not repeat
  it before every action item the way a spreadsheet row would require.
- Use exact review dates when provided by the source.
- Every initiative should answer: what project/business problem it solves,
  what value it brings, how success is measured, and where progress will be
  synchronized.
- Do not describe the project's business flow as a functional use-case
  ("user does X, then Y"). Business flow is how the product earns money: who
  buys, why, through what channel, what drives revenue.
- Do not attribute the whole product's value to QA. State the value that
  would specifically be missing without QA's work.
- Do not call the project "successful" because work shipped. State the
  business criteria the client cares about and whether they were met.
- Do not force every plan item into a fixed 30/60/90-day bucket. Split into
  date-bound near-term commitments and undated directional goals instead —
  matches how Agile teams actually plan.
- Include topology/context initiatives when needed for project control:
  clarify streams, real team size, DC/PM ownership, vendor/intermediary
  chain, client path, tender/contract horizon, security/location
  constraints, or feedback route.
- If the project needs better visibility before detailed improvement work is
  possible, write a visibility initiative with an owner, date, and expected
  artifact instead of inventing downstream actions.
- If QA value or project-side trust is under question, include an initiative
  that proves QA business value through metrics, accepted improvements,
  defect/risk prevention, or client/team feedback.
- Reviewer feedback belongs in native Google Docs comments tied to the
  relevant paragraph (mirroring how the original homework documents were
  reviewed in Word), not as an extra column or appended text block.
- An expansion/upsell item must name the specific diagnostic signal or
  conversation it's built from (e.g. "regression bugs up this sprint, no
  automation coverage — raised as a POC candidate at Thursday's retro"),
  not a generic "there may be room to grow this account" statement.
