# Document Contract

Primary final output is one workspace-wide Google Sheet directly under
`10_M1_People_Management`, with local CSV fallback. Preserve the CSV
template columns as the Sheet schema.

## Purpose

Use this reference for the M1 timeline/events document family: tracking
dated events (Performance Reviews, OKR cycle closures, monthly-report
deadlines, 1to1s, follow-ups) so nothing gets forgotten across the team,
and seeing what's due today/tomorrow/this week in one place.

## Template

`<repo-root>\Templates\m1_timeline.csv`

## Expected Output

One `_m1_timeline` Sheet directly under `10_M1_People_Management`, next to
`<Person> 1to1` Sheets and dated `светофор_рисков_*` snapshots.

Suggested target folder:

`G:\My Drive\QA_Management\10_M1_People_Management`

Local CSV fallback filename: `_m1_timeline.csv`.

Unlike `m2-timeline`, there is no per-project (per-person) source Sheet to
roll up from — this is the single living Sheet, edited directly. Do not
create per-person `action_items`-style Sheets for this purpose; M1's team
size (3-8 people, see `m1-role-rules.md`) doesn't need the two-tier
structure M2 uses to avoid one giant cross-project Sheet.

## Versioning

- `_m1_timeline` is a living canonical file: edit rows in place (date
  slips, status changes) rather than appending duplicates or creating
  dated snapshots.
- `scan_m1_events.py` creates `_m1_timeline` (header row only) the first
  time it's run with `--write` if it doesn't exist yet; it never overwrites
  existing rows, only appends new candidates not already present by
  `Источник` tag.

## Schema

Use exactly the columns in `Templates\m1_timeline.csv`:

1. `Сотрудник` — the person the event is about. Use `M1` (or the M1
   manager's own name) for team-wide items that aren't about one specific
   person, e.g. a monthly-report deadline.
2. `Дата события` — ISO `YYYY-MM-DD`. Never blank; if the real date is
   unknown, use the nearest concrete placeholder and record the
   uncertainty in `Комментарии`.
3. `Тип` — free text but keep to a small consistent set: `Performance
   Review` (PR/OKR cycle closing), `OKR` (missing or overdue OKR),
   `Monthly report` (m1_monthly_report deadline), `Встреча` (1to1 or other
   meeting), `Follow-up`, `Прочее`.
4. `Что нужно сделать` — concrete, one action, not a vague intention.
5. `Статус` — `Открыто`, `Выполнено`, or `Отменено`.
6. `Owner` — who acts on it: `M1` or a named QA. Never blank.
7. `Источник` — name what produced the item (an OKR Doc title, a
   monthly-report filename check, a conversation). Scan-derived rows use
   `scan:<kind>:<key>`, matching the `scan_open_questions.py` convention.
8. `Комментарии` — optional context, including any date-uncertainty note.

## Inputs

- OKR Doc titles (`m1-individual-development-plan`) — the PR date encoded
  in `OKR к Perfomance review DD.MM.YY` is the primary source for
  Performance Review events.
- `_people_registry`'s `Дата трудоустройства`/`Дата последнего PR` columns
  (see `google-workspace-rules.md`) — an independent, cadence-based way to
  compute the expected next PR date (`performance-review-rules.md`,
  "Deriving Expected Next PR Date"), used both to track people before their
  first OKR Doc exists and to cross-check an existing Doc's title date.
- `m1_monthly_report_<Manager>_YYYY-MM` presence/absence — the source for
  Monthly report deadline events.
- Direct conversational instructions from M1 ("remind me to check X's OKR
  before the PR", "1to1 with Y is on Friday").
- `scan_m1_events.py` — mechanically surfaces PR-date, PR-cadence-mismatch,
  and missing-OKR/missing-monthly-report candidates across the whole team
  at once. Always review its placeholder wording before logging (see
  `SKILL.md`, "Deriving events from team state").

## Evidence Rules

- Log only concrete, datable items — not general people-risk commentary
  (that belongs in the risk traffic-light Sheet).
- Keep one row per event; don't bundle multiple people's PR dates into one
  row.
- Close (`Выполнено`/`Отменено`) rather than delete resolved items — the
  closed history is still useful context for the next 1to1 or monthly
  report, even though it's no longer "upcoming."

## Rule

Keep this skill scoped to the timeline/events document family only. Do not
use it to draft OKR content (`m1-individual-development-plan`), fill in
monthly-report KPI cells (`m1-monthly-report`), or record risk judgment
(`m1-people-risk-report`) — it only tracks that those are due.
