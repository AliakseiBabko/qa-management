# People Registry

Scope: `_people_registry`'s schema, and how to map both person-card intake
shapes into it. Load this module for any skill that reads, writes, or
cross-checks a person's registry row.

## `_people_registry`

Keep `_people_registry` in its own top-level folder, `05_People_Management`
(not nested under `10_M1_People_Management` or `20_M2_Project_Management`),
as a single workspace-wide Google Sheet (CSV fallback) covering **every**
person who comes up — Internal employees under M1 management, M2-staffed
people, and client/vendor-side people across all projects. One person, one
row, regardless of which skill (M1 or M2) is the one touching them that day.

**History (2026-07-17 merge)**: this replaces two separate sheets,
`_m1_people_registry` (under `10_M1_People_Management`) and
`_m2_people_registry` (under `20_M2_Project_Management`), which duplicated
~10 of 13 columns between them with no principled rule for which sheet owned
which field. That let a field (e.g. `Name (EN)`) go missing in one sheet
while other fields for the same person got filled — a real bug, not a
hypothetical one. A dedicated top-level folder (rather than nesting the
merged sheet under either skill's folder) means a repo clone used for only
M1 or only M2 work still finds this registry without needing the other
skill's folder tree.

Columns:

- `Name (RU)`, `Name (EN)` — both, when the person has a known English-name
  form (useful since transcripts/chats mix scripts). First + last name only,
  no patronymic (patronymic goes in Notes if captured).
- `Email` — when known.
- `Side` — `Internal`, or `Client` / `Client — <company>` when the specific
  client-side or third-party vendor company is known (e.g. a client's own
  staff vs. a separate vendor supplying people on the same project). One
  column, not two — a person's affiliation and which company they're at is
  a single fact, and splitting it produced redundant-looking rows like
  `Internal, Internal` for every internal person.
- `Worker ID` — from an HRM worker-record card (see Person Card Intake,
  HRM Worker-Record Card shape below). Blank for client-side people — they
  have no Worker ID at all, not just an unknown one.
- `M1` — this person's current M1 manager, for internal people. Blank for
  client-side people, and for a person who is themselves a top-level M1
  with no manager on record.
- `Role` — M1 / M2 / M3 / M4 / HR / DC / QA / AQA / Team Lead / PM / Client
  stakeholder / Candidate / etc. Keep this to title/M-level/DC-status only —
  stream, tech stack, and secondary-project detail belong in `Project(s)` or
  `Notes`, not stuffed into `Role` (that drift is exactly what caused
  duplicate/conflicting Role text across the two now-merged sheets).
- `Internal rank` — the company's own internal level (Junior/Middle/Senior),
  for internal people only. This is distinct from a person's project-level
  grade fit (`Соответствие ожиданиям клиента (грейд)` in
  `individual_metrics`) — the two can differ, and neither substitutes for
  the other. Leave blank when not known; do not infer it from project-level
  grade.
- `Project(s)` — where the person is staffed/employed, comma-separated, or
  "all"/`Бенч` for company-wide roles or no current project. **Not** every
  project where they show up performing an M1/M2/DC duty for someone else's
  team — a person's main staffed project and a cross-project management hat
  they wear for other people are two different facts and must not be merged
  into one column. E.g. an AQA staffed on `<Project A>` who also acts as M2
  for a QA on `<Project B>` keeps `Project(s)` = `<Project A>`; the
  `<Project B>` M2 duty goes in `Notes`, naming the project(s) it covers.
  Multiple people commonly wear more than one hat (staffed role + M1/M2/DC
  duty elsewhere) — capture both, but don't let one overwrite or dilute the
  other.
- `Дата трудоустройства` — hire date (`YYYY-MM-DD`), for internal people
  only. Leave blank when not known; ask rather than guess — this is the
  anchor date for the probation-closing Performance Review (hire date + 3
  months, see `qa-management-roles/references/performance-review-rules.md`),
  so a wrong guess here silently mis-schedules a PR. Also the anchor
  `m1-timeline` and `m1-individual-development-plan` read from instead of
  re-deriving a date from transcripts each time.
- `Дата последнего PR` — the date of the person's most recently completed
  Performance Review (`YYYY-MM-DD`), internal people only. Blank means no
  PR has happened yet (still pre-probation-close), not "unknown" — do not
  fill it from a guess. M1 (or M2/M3 for their own PR) updates this cell
  right after a PR actually happens; `m1-timeline`'s cadence computation
  (expected next PR = this date + 6 months) depends on it staying current.
- `Первый коммерческий проект` — `Да` / `Нет`, whether this is the person's
  first-ever commercial (client-facing/production) project, distinct from
  hire date or internal rank — see `newcomer-support-rules.md` for the full
  detection and response rule. Ask rather than guess; leave blank only
  while genuinely unconfirmed.
- `Aliases / spelling variants` — alternate spellings/transliterations/STT
  mishearings confirmed for this person (e.g. a name transcribed three
  different ways across meeting recordings). Add to this column instead of
  burying an alias inside `Notes` prose, where a later Notes rewrite can
  silently drop it.
- `Notes` — anything uncertain, stated explicitly, including any
  cross-project management duty per the `Project(s)` rule above, citations,
  and confidence level on any estimated date.

No computed "next PR expected" column — `m1-timeline` already derives that
dynamically from `Дата последнего PR` + cadence rules
(`performance-review-rules.md`); storing it statically here would just go
stale.

## Person Card Intake

M2 sometimes hands over a person directly as a structured card rather than
via a transcript/chat, e.g.:

```
<Name (EN)>, <Имя (RU)>, <email>
Job Title - Data Engineer
M-level - P
Prof.Level - Senior
Mentor - No
DC - Yes
```

Map every field explicitly rather than re-deriving the mapping each time:

- Name (RU) / Name (EN) — from the given Russian/English (or transliterated)
  names directly.
- Email — as given.
- Side — `Internal` if the email domain matches the company's own domain
  (see `apply_person_card.py`'s `COMPANY_EMAIL_DOMAIN`); otherwise ask
  rather than guess.
- Role — `Job Title`, with `DC` prefixed if `DC - Yes` (e.g. `DC; Data
  Engineer`). Do not add `DC` to Role if the card says `DC - No`, even if
  the person is discussed alongside DC-shaped duties elsewhere. Separately,
  if `M-level` is a recognized internal management level (`M1`/`M2`/`M3`/
  `M4`), combine it into Role alongside Job Title too (e.g. `M3; DC
  Manager`), matching how existing M3 AQA rows are already written (`M3
  AQA`). If `M-level` is not one of those (e.g. `P`), its meaning isn't
  confirmed — leave Role alone and put it in Notes verbatim instead (see
  below); don't guess it belongs in Role.
- Internal rank — `Prof.Level` directly (Junior/Middle/Senior). This field
  already matches the `Internal rank` column's own scale.
- Project(s) — leave blank unless the card or its context states an actual
  staffed project; never infer it from which chat/project the card happened
  to arrive alongside (see the `Project(s)` rule above).
- `Первый коммерческий проект` — only if the card explicitly states it
  (e.g. a `First commercial project - Yes` line); do not infer it from
  `Prof.Level`, `M-level`, or the absence of prior `Project(s)` entries. If
  the card doesn't state it and the person is being staffed onto a project,
  ask rather than leave it silently blank — see `newcomer-support-rules.md`.
- Notes — `M-level` verbatim (only when it wasn't already folded into Role
  per above), flagged as unconfirmed in meaning; `Mentor` status in plain
  language; and a citation of the source (which chat/note the card came
  from).

If a card conflicts with an existing registry row for the same person (a
different Role, Side, or rank), treat it as a correction — the card is
direct, first-party information from M2, stronger evidence than an inferred
role from a transcript — but still fix every document that repeated the old
fact (see the Template Consistency note in `m2-role/m2-metrics-calibration.md`).

If a card's `Job Title` (e.g. AQA Engineer) conflicts with how that person's
actual on-project work reads in `individual_metrics`/`individual_development_plan`
(e.g. a fully manual scope), don't treat it as a contradiction to resolve
by picking a side — see `m2-role/m2-metrics-attribution.md`'s Вклад в проект Calibration,
client-driven scope-vs-track mismatch, which is very likely the actual
explanation.

When processing a transcript/chat and a role is unclear or contradicts this
registry, ask rather than guess — this registry exists specifically because
a wrong role guess (e.g. attributing a 1:1 to the wrong person's role) can
propagate into several documents before anyone notices.

### HRM Worker-Record Card (Second Card Shape)

A different card shape also comes up: an HRM system export with fields
like `First Name`/`Last Name`/`Patronymic name`/`First Name (EN)`/`Last
Name (EN)`, `Worker ID`, `Hire date`/`Employment date`, and an
`Org. structure` block (`Unit`/`Division`/`Department`/`Team`/`Group`).
This has no email and doesn't always include the `Job Title`/`M-level`/
`Prof.Level`/`Mentor`/`DC` block the other card shape has — `apply_person_card.py`
does not parse this shape; map it by hand. Since the 2026-07-17 merge there
is only one `_people_registry` row per person, so this card shape and the
primary card shape both write into the same row — no cross-link bookkeeping
needed anymore.

- `Дата трудоустройства` — `Hire date` (same as `Employment date` in every
  case seen so far). Convert to ISO `YYYY-MM-DD` when writing — the card
  gives `DD.MM.YYYY`, but the registry's documented convention is ISO;
  don't carry the card's raw format through unconverted.
- Name (RU)/(EN) — first + last name, matching the existing column
  convention (no patronymic in the Name columns); put the patronymic and
  full official name in Notes instead.
- `Group: <Surname> Team` — identifies that person's current **M1** (e.g.
  `Group: Mitsko Team` means M1 = Митько). Cross-check against any M1
  already on record for this person (e.g. from a Workload sheet) rather
  than overwriting silently — the two sources confirming each other is
  itself worth noting in Notes. Prefer the most recent M1-leads roster
  (e.g. an `M1 Leads <date>.xlsx` source doc) over this card's own
  `M-level` field when they disagree — HRM's `M-level` can lag a real
  promotion/handoff by weeks; say so explicitly in Notes rather than
  silently picking one.
- `Worker ID` — its own column; blank for client-side people (they were
  never in HRM at all, not just missing this field).
- `Department` / other org-structure fields — not mapped to a dedicated
  registry column; record in Notes if useful context.
- If `Job Title`/`M-level`/`Prof.Level`/`Mentor`/`DC` are present on this
  card shape too, map those fields the same way as the primary card shape
  above.
