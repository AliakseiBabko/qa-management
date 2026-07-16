---
name: m1-timeline
description: Maintain the workspace-wide M1 `_m1_timeline` Google Sheet (upcoming Performance Reviews, OKR cycle closures, monthly-report deadlines, 1to1 follow-ups, reminders) and the companion `_m1_pr_calendar` PR-only view, with CSV fallback. Also covers deriving new events from OKR Doc titles, real PR cadence (via `_m1_people_registry` hire/last-PR dates), and monthly-report presence via scan_m1_events.py. Use when M1 needs to log an upcoming PR/1to1/deadline, close one out, answer "what's due today/tomorrow/this week" across the team, find every person missing a current OKR or a filed monthly report, or work out when someone's next Performance Review is actually due.
---

# M1 Timeline

Use this skill for two output families:

- workspace-wide `_m1_timeline` Google Sheet in `10_M1_People_Management`, with CSV fallback — every event type together
- workspace-wide `_m1_pr_calendar` Google Sheet in `10_M1_People_Management` — a PR-only view, mechanically generated from `_m1_people_registry`, never hand-edited (see `refresh_m1_pr_calendar.py`)

This is M1's counterpart to `m2-timeline`, but scoped to people instead of
projects — one flat living Sheet, not a per-project Sheet plus rollup.
M1's team is small (3-8 people per `m1-role-rules.md`), so a single Sheet
with a `Сотрудник` column already answers "what's due when" without the
two-tier structure M2 needs to avoid one giant cross-project Sheet.

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Read `../qa-management-roles/references/performance-review-rules.md` for the real PR cadence and its "Deriving Expected Next PR Date" formula.
4. Read `../m1-individual-development-plan/references/okr-process-rules.md` for PR/OKR cadence rules.

## Workflow

### Logging or updating an item

1. Read `_m1_timeline` before adding a row — check whether the same event is already logged rather than duplicating it.
2. Append one row per concrete, datable thing: a Performance Review, an OKR cycle closing, a monthly-report deadline, a 1to1, a follow-up owed to or from someone. Do not log vague intentions with no date.
3. Fill `Дата события` as an ISO date (`YYYY-MM-DD`). If only a month is known (e.g. "monthly report for June"), use the nearest concrete date and note the uncertainty in `Комментарии`.
4. Set `Статус` to `Открыто` when creating the row. Move it to `Выполнено` or `Отменено` when it resolves — edit rows in place; this is a living list, not an append-only log, same as `action_items`.
5. `Owner` is who acts on the item — usually `M1`, sometimes a named QA (e.g. for "operationalize your OKR after the PR"). Never leave blank.
6. `Источник` names what produced the item (an OKR Doc title, a monthly-report check, a conversation).

### Answering "what's due today/tomorrow/this week"

1. Read `_m1_timeline`, filter to `Статус = Открыто`, sort by `Дата события`.
2. If it looks stale, rerun `scan_m1_events.py` and re-check against what's already logged (the scan dedups by source tag, so a rerun only surfaces genuinely new/changed items).

### Deriving events from team state (scan)

`scan_m1_events.py` surfaces three mechanical signal types instead of M1 tracking PR dates and monthly-report cadence by memory:

1. **Performance Review / OKR cycle dates** — reads every person's OKR Doc title (`OKR к Perfomance review DD.MM.YY`, see `m1-individual-development-plan`) under `10_M1_People_Management\<Person>\` and surfaces the parsed date as a `Performance Review` event. A person with a 1to1 Sheet but no OKR Doc at all is surfaced as its own candidate — "draft OKR for X" — since every employee is required to have one (see `okr-process-rules.md`). A person whose OKR Doc exists but carries the `(дата уточняется)` placeholder title (no PR/hire date was confirmed at draft time) is surfaced as a distinct `undated_draft` candidate — "update the title once a date is confirmed," not "draft one from scratch."
2. **PR-cadence cross-check** — independently computes the expected next PR *window* from `_m1_people_registry`'s `Дата трудоустройства`/`Дата последнего PR` (see `performance-review-rules.md`, "Deriving the Expected Next PR Window": opens at last PR + 6 months, or hire date + 3 months if no PR has happened yet; closes 1 month after it opens). If there's no OKR Doc yet, the window's open date becomes the due date instead of "today" — so a person is tracked even before their first OKR Doc exists. If an OKR Doc *does* exist but its title date falls outside the computed window, that mismatch is surfaced in `Комментарии` instead of silently trusting the Doc.
3. **Monthly report cadence** — checks whether `m1_monthly_report_<Manager>_YYYY-MM` exists for the current and previous reporting month; a missing previous-month report is surfaced as an overdue candidate, tagged with a reminder that the report's `Работа с ОКР` obligation row needs real OKR-activity evidence (see `m1-monthly-report`), not just a filed sheet.

Review, don't blindly log:

1. Run `scan_m1_events.py` (`--person <Name>` to scope it). It prints candidates and writes a bundle to `80_Exports/open_questions_review/YYYY-MM-DD_m1.md`. It skips anything already logged (matched by a `scan:<kind>:<key>` tag in `Источник`).
2. A Performance Review candidate whose date has already passed means the OKR cycle should have closed — treat it as overdue, not a future reminder; confirm with M1 whether the PR happened and the OKR was actually closed before just re-logging the same date forward. Once confirmed, update `Дата последнего PR` in `_m1_people_registry` — this is what keeps the cadence cross-check accurate on the next run, and nothing else updates it automatically.
3. A missing-OKR candidate needs M1 to actually draft one (`m1-individual-development-plan`) — the scan only tells you it's missing, it doesn't draft it.
4. A cadence-mismatch note (registry-computed date vs. OKR Doc title date) needs a human call on which one is stale — don't just overwrite one from the other without checking which fact is actually wrong.
5. A missing-monthly-report candidate needs the report actually filled in (`m1-monthly-report`) — same discipline.
6. `--write` appends the raw candidates straight into `_m1_timeline` — only use when you intend to review each row immediately afterward.

### Answering "who's due for a PR, and when" (PR-only view)

1. Run `refresh_m1_pr_calendar.py` after any `_m1_people_registry` update (a new `Дата последнего PR`, a new hire) — it fully regenerates `_m1_pr_calendar` from that data, sorted by soonest-opening window first, and applies the workspace's standard formatting (wrap/align/column widths, see `format_all_sheets.py`) to it every time, so it never needs a separate manual formatting pass. No dry-run/candidate-review step, unlike `scan_m1_events.py` — there's no judgment involved, just recomputation, same as `refresh_project_registry.py` on the M2 side.
2. Read `_m1_pr_calendar` directly for a clean PR-only list (`Статус`: `Не скоро` / `В окне` / `Просрочено` / `Нет данных`) instead of filtering `_m1_timeline`'s mixed event types by hand.
3. Never hand-edit `_m1_pr_calendar` — it's fully overwritten on every refresh. If a row looks wrong, the fix is in `_m1_people_registry` (correct `Дата последнего PR`/`Дата трудоустройства`), then rerun the refresh — not editing the calendar row directly.

## Guardrails

- Do not use this Sheet for people-risk judgment — that's the people-risk traffic-light Sheet (`m1-people-risk-report`). An entry here is a dated to-do, not an assessment.
- Do not fabricate a due date. If genuinely unknown, log it anyway with the uncertainty stated in `Комментарии` rather than skipping it.
- `scan_m1_events.py` only reads OKR Doc titles and monthly-report filenames — it does not read 1to1 content or risk rows. A real upcoming event mentioned only in a 1to1 transcript still needs manual logging via `m1-1to1-prep`'s source order, not this scan.
- Never treat a scan candidate's date as final without checking it against the actual OKR Doc/monthly report state — the scan surfaces gaps, it does not decide the real next action.
- This skill does not create or edit OKR Docs or monthly reports — it only tracks the fact that one is due/missing. Route the actual drafting to `m1-individual-development-plan` or `m1-monthly-report`.
- If `_m1_people_registry` has neither `Дата трудоустройства` nor `Дата последнего PR` for a person, the scan cannot compute an expected PR window — it falls back to "today" with a note that both fields are missing (`_m1_pr_calendar` shows this as `Статус = Нет данных` instead). Treat that as a data-gap candidate (ask for the hire date) rather than trusting the "today" placeholder as real.
- `_m1_pr_calendar` is a generated rollup, never edited directly — same rule as M2's `_timeline`. Edits always go into `_m1_people_registry`, then `refresh_m1_pr_calendar.py`.
- This skill tracks PR dates for **M1's own QA team members**, not M1's (or M2's) own Performance Review as the employee being reviewed by the grade above — that's `m-self-review`'s territory (see `performance-review-rules.md`). Do not log an M-manager's own PR here as if it were a team event.
