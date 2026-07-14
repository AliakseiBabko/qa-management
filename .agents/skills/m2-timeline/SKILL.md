---
name: m2-timeline
description: Maintain the per-project action_items Google Sheet (events, deadlines, follow-ups, reminders) and refresh the workspace-wide _timeline rollup, with CSV fallback. Also covers deriving new action items from open questions/gaps already sitting in m2_input, project_risk, and project_metrics via scan_open_questions.py. Use when M2 needs to log an upcoming meeting/report/deadline/follow-up, close one out, answer "what's due today/tomorrow/this week" across projects, or find every open question across all projects in one place.
---

# M2 Timeline / Action Items

Use this skill for one output family only:

- per-project `action_items` Google Sheet, with CSV fallback
- workspace-wide `_timeline` rollup Sheet (open items across all projects, sorted by date)

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace-rules.md`.
3. Identify the target project (or "all projects" for a cross-project read).

## Workflow

### Logging or updating an item

1. Read the project's current `action_items` (via `show_project_state.py --project <Name>` or a direct Sheet read) before adding a row — check whether the same event is already logged rather than duplicating it.
2. Append one row per concrete, datable thing: a meeting, a report/status-in-chat commitment, a deadline, a follow-up/clarification owed to or from someone. Do not log vague intentions with no date.
3. Fill `Дата события` as an ISO date (`YYYY-MM-DD`). If only a week/month is known, use the nearest concrete date and say the uncertainty in `Комментарии` — do not leave the date blank; a dateless row can't be triaged by "what's due when."
4. Set `Статус` to `Открыто` when creating the row. Move it to `Выполнено` or `Отменено` when it resolves — do not delete rows; this is a living list, not an append-only log, so editing a row in place (date slip, status change) is normal and expected, unlike `evidence_log`.
5. `Owner` is who acts on the item — usually M2, sometimes a named QA or the client side. Never leave blank.
6. `Источник` follows the same discipline as `evidence_log`: name the source (chat, transcript, meeting) that produced the item.
7. After editing any project's `action_items`, run `refresh_timeline_registry.py` so `_timeline` reflects the change — it is a mechanical mirror, not a judgment step.

### Answering "what's due today/tomorrow/this week"

1. Prefer reading `_timeline` (one place, already sorted, already cross-project) over opening each project's `action_items`.
2. `_timeline` only lists `Статус = Открыто` rows — a project with nothing due does not appear.
3. If `_timeline` looks stale (an item you know is closed still shows), refresh the source project's `action_items` first, then rerun `refresh_timeline_registry.py`.

### Deriving action items from project state (open-questions scan)

M2 rarely starts from a blank page — most open items already exist as
signals in other documents: an unanswered `m2_input` round, a `project_risk`
row with an action plan nobody has turned into a dated task, a
`project_metrics` row still `Неизвестно`. `scan_open_questions.py` is a
single command that reads all three across every project and surfaces
candidates in one place, instead of opening each project's documents by
hand.

1. Run `scan_open_questions.py` (add `--project <Name>` to scope it). It
   prints candidates grouped by project and writes a bundle to
   `80_Exports/open_questions_review/YYYY-MM-DD.md`. It skips anything
   already logged (matched by a `scan:<kind>:<key>` tag in `Источник`), so a
   rerun only shows genuinely new items.
2. The script's `Тип`/`Owner`/`Дата события` are mechanical placeholders,
   not real judgment — always review each candidate:
   - An `m2_input` pending-round candidate means a round is sitting
     unanswered; read the actual question text (included in the bundle) and
     answer it via `pipeline_common.add_answer`, or turn it into a
     concrete `action_items` row if answering needs more than a sentence
     (e.g. a scheduled 1:1) — see the worked example below.
   - A `project_risk` candidate already carries a real Owner/date from the
     `План действий`/`Следующий review` cells — usually just needs logging
     into `action_items` as-is.
   - A `project_metrics` "Неизвестно" candidate is a clarification gap.
     Read its `Пояснение` cell (included as a note) to decide *how* it gets
     clarified — if that requires a live conversation with a specific
     person rather than an async check, upgrade `Тип` to `Встреча` and
     write `Что нужно сделать` as the scheduling action itself, not the
     underlying question. Example: `project_metrics` shows "Вклад в
     проект: Иван" as `Неизвестно` because current benchmark status isn't
     known → log `Тип: Встреча`, `Что нужно сделать: Запланировать 1:1 с
     Иваном — уточнить текущий статус по бенчмаркам`, `Owner: M2`, a real
     near-term `Дата события` — not `Что нужно сделать: Уточнить
     бенчмарки` with no path to actually getting the answer.
3. Log the reviewed/rewritten candidates into the owning project's
   `action_items` per "Logging or updating an item" above, then run
   `refresh_timeline_registry.py`.
4. `--write` appends the raw (unreviewed) candidates straight into each
   project's `action_items` instead of just printing them — only use this
   when you intend to review/rewrite each row in the Sheet immediately
   afterward, not as a substitute for step 2's judgment.

## Guardrails

- Do not use this Sheet for project health/risk judgment — that's `project_risk`. An action item is a dated to-do, not an assessment.
- Do not use it for the append-only evidence trail — that's `evidence_log`. `action_items` rows get edited/closed in place; `evidence_log` rows never do.
- Do not fabricate a due date. If genuinely unknown, that itself is worth a row with `Комментарии` stating the date is unknown and who owes clarifying it — don't skip logging just because the date is fuzzy.
- `_timeline` is a generated rollup, never edited directly — edits always go into the owning project's `action_items`, then `refresh_timeline_registry.py`.
- `scan_open_questions.py` only reads `m2_input`, `project_risk`, and `project_metrics` — it does not read status reports, strategy chats, or raw transcripts. A real open item mentioned only in a chat/transcript still needs manual logging; the scan is a floor, not a complete list.
- Never treat a scan candidate's placeholder wording/date as final without the review in step 2 above — writing it into `action_items` unreviewed defeats the point of picking a concrete, actionable next step.
