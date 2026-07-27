# M2 Project-Level Rollups

Scope: The two-phase project-level rollup process and the m2_input preliminary-analysis gate.

## Project-Level Rollups

`project_development_plan` and `project_risk` get updated by rolling up
every person's individual plan, individual metrics, and their `Вклад в
проект: <Имя>` conclusion from `project_metrics` — but that rollup
should never run purely mechanically. Metrics and per-person plans don't
carry the manager's own judgment (why a risk matters more or less than the
numbers suggest, context that isn't in any metric, how to weigh one
person's read of the project against another's). `m2_input` (see
Templates\m2_input.md) is the explicit place for that judgment, and the
rollup is a two-phase process built around it:

1. **Preliminary analysis round.** Before combining anything, review every
   person's individual plan and metrics on the project, and write down
   specific, answerable questions — gaps in data, contradictions between
   people's signals, risks visible in the metrics but with no clear owner,
   what to do about someone whose Core metrics aren't collectible yet.
   Append a new dated round to the project's `m2_input` Doc with these
   questions; leave "Ответ и общие соображения M2" empty.
2. **Wait for M2's answer.** Do not proceed to the rollup until the latest
   round's answer section is filled in. An empty answer section means the
   rollup for that round cannot happen yet — that's a stop condition, not
   something to route around by falling back to metrics alone.
3. **Rollup round.** Once answered, combine individual plans/metrics with
   that round's answers as an explicit input — on par with the metrics
   themselves, not a tie-breaker used only when metrics disagree — into the
   updated `project_development_plan` and `project_risk`.

`m2_input` is one living Doc per project, not a new file per cycle. Each
round is a new dated section appended to the same Doc; do not delete or
archive prior rounds — the visible history of questions and answers across
cycles is itself useful context for the next round, and Google Docs version
history is a backstop, not a substitute for keeping rounds visible in the
document.

A round left unanswered while new addenda keep stacking on top of it is
itself a signal, not just a growing backlog — `project_risk`/
`project_development_plan` stay frozen behind the gate the whole time,
even as real new evidence piles up unrolled-up. When appending an addendum
to an already-pending round, check how old the round is and how many
addenda it already has; if it's been open for multiple weeks or has
several addenda, say so explicitly to the user when you finish (e.g. "this
round has been open since <date> with N addenda — the rollup has been
frozen that whole time") rather than silently adding addendum N+1 as if
nothing's unusual. This doesn't mean answering it on the user's behalf —
it means surfacing the staleness so the user can decide to actually close
it out. `qa_manage.py gates` is the read-only inspection command for this
exact question across every project at once (round age, addenda count,
first addendum heading only) — use it to review staleness instead of
re-deriving age/addenda counts by hand.
