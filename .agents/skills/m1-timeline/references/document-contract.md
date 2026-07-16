# Document Contract

Primary final output is one workspace-wide Google Sheet directly under
`10_M1_People_Management`, with local CSV fallback. Preserve the CSV
template columns as the Sheet schema.

## Purpose

Use this reference for the M1 timeline/events document family: tracking
dated events (Performance Reviews, OKR cycle closures, monthly-report
deadlines, 1to1s, follow-ups) so nothing gets forgotten across the team,
and seeing what's due today/tomorrow/this week in one place.

## Templates

`<repo-root>\Templates\m1_timeline.csv`
`<repo-root>\Templates\m1_pr_calendar.csv`

## Expected Output

Two Sheets directly under `10_M1_People_Management`, next to the living
`Светофор рисков` Sheet — `<Person>\1to1` Sheets live one level down,
inside each person's own subfolder:

- `_m1_timeline` — every event type together (Performance Review, OKR,
  Monthly report, Встреча, Follow-up, Прочее).
- `_m1_pr_calendar` — PR-only view, mechanically generated from
  `_m2_people_registry` by `refresh_m1_pr_calendar.py`, never hand-edited.

Suggested target folder:

`G:\My Drive\QA_Management\10_M1_People_Management`

Local CSV fallback filenames: `_m1_timeline.csv`, `_m1_pr_calendar.csv`.

Unlike `m2-timeline`, there is no per-project (per-person) source Sheet to
roll up `_m1_timeline` from — it's a single living Sheet, edited directly.
Do not create per-person `action_items`-style Sheets for this purpose;
M1's team size (3-8 people, see `m1-role-rules.md`) doesn't need the
two-tier structure M2 uses to avoid one giant cross-project Sheet.
`_m1_pr_calendar` *is* a generated rollup, but from `_m2_people_registry`
directly, not from per-person Sheets — same one-source-of-truth principle
as `_timeline` on the M2 side.

## Versioning

- `_m1_timeline` is a living canonical file: edit rows in place (date
  slips, status changes) rather than appending duplicates or creating
  dated snapshots.
- `scan_m1_events.py` creates `_m1_timeline` (header row only) the first
  time it's run with `--write` if it doesn't exist yet; it never overwrites
  existing rows, only appends new candidates not already present by
  `Источник` tag.
- `_m1_pr_calendar` is fully regenerated on every `refresh_m1_pr_calendar.py`
  run — never edit it directly, an edit there is silently overwritten on
  the next refresh. It never creates dated copies either; there is exactly
  one `_m1_pr_calendar` Sheet, always current as of the last refresh.

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

`_m1_pr_calendar` uses its own schema (`Templates\m1_pr_calendar.csv`),
one row per person with a computable window:

1. `Сотрудник`
2. `Основание расчёта` — `last_pr+6mo` or `hire+3mo(probation)`.
3. `Дата последнего PR / трудоустройства` — whichever date the window was
   anchored to.
4. `Окно начала` — ISO date, window open (anchor + 6 or + 3 months).
5. `Окно окончания` — ISO date, window close (open + 1 month).
6. `Статус` — `Не скоро` / `В окне` / `Просрочено` / `Нет данных`.
7. `Комментарий` — reserved for a stated exception when a real PR slips
   past the window for a specific, known reason; `refresh_m1_pr_calendar.py`
   itself never writes anything here beyond a data-gap note.

## Inputs

- OKR Doc titles (`m1-individual-development-plan`) — the PR date encoded
  in `OKR к Perfomance review DD.MM.YY` is the primary source for
  Performance Review events.
- `_m2_people_registry`'s `Дата трудоустройства`/`Дата последнего PR` columns
  (see `google-workspace-rules.md`) — an independent, cadence-based way to
  compute the expected next PR window (`performance-review-rules.md`,
  "Deriving the Expected Next PR Window"), used both to track people before
  their first OKR Doc exists and to cross-check an existing Doc's title date.
  `refresh_m1_pr_calendar.py` reads this same data to generate
  `_m1_pr_calendar`.
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
