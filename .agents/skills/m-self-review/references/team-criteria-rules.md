# Критерии оценки команды — Scoring Rules

Source: internal Confluence article "Критерии оценки команд" (Evgeny
<Name>). This is the Jira "Критерии оценки команды" task required for
M1/M2/M3's own Performance Review (see
`../../qa-management-roles/references/performance-review-rules.md`) — the
lead being reviewed collects and computes it for their own team, except
the first metric (collected by the grade above).

## Collection Rules

- Default collection window: **3 months**, unless a metric states otherwise.
- The team lead being reviewed collects and computes every metric **except**
  "Положительные фидбеки от членов команды," which the grade above collects
  (e.g. M2's own M3 collects it when M2 is being reviewed).
- Results are discussed with M+1 and M+2 **before** the PR (an M1 invites
  their own M2 and M3 to this pre-sync) — only the discussion summary goes
  to the main PR, per `performance-review-rules.md`'s "Timing Before the
  PR."
- File everything in a Jira "Ассессмент" card inside the reviewed lead's own
  PGROWTH epic.

## Effectiveness Threshold

`score = (points earned / 34) * 100`

A team scoring **70% or higher** is considered effective.

## Metrics (17 total, max 34 points)

Each entry: metric, scoring bands, collection method, who collects, window
(if not the 3-month default).

1. **Положительные фидбеки от членов команды** (M1/M2 teams only) — max 2.
   2 = all feedback positive; 1 = at most 1 negative; 0 = more than 1
   negative. Collector: the grade above (M+1). Method: questionnaire.
2. **Развитие экспертизы** (assessments / ISTQB certificates), 6-month
   window — max 2. 2 = ≥20% of the team passed an assessment; 1 = some
   passed but <20%; 0 = none passed. Method: PGROWTH.
3. **Загрузка команды** — max 3. 3 = 80-85% utilization + ≥1 fully free FTE
   on bench; 2 = 65-80% utilization + ≥1 fully free FTE; 1 = ≥65%
   utilization, no full FTE free; 0 = <65%. Method: промзагрузка
   (utilization tracker).
4. **Успешность работы на проектах** (positive project feedback) — max 3.
   3 = positive feedback from every project; 2 = at most 1 non-positive
   (neutral) feedback; 1 = more than 1 non-positive; 0 = any negative
   feedback, or more than 2 neutral. **Absence of feedback counts as
   neutral.** Method: project feedback collection — cross-reference
   `project_metrics`'s `Вклад в проект: <Имя>` rows for this manager's team
   members where this repo already tracks the project (see Normalization
   below) before asking the user for the rest.
5. **Отсутствие перегруза по ставкам** — max 2. 2 = nobody above 1.0 FTE
   load; 1 = at most one person up to 1.5 FTE; 0 = more than one person
   between 1.0-1.5 FTE, or anyone above 1.5 FTE. Method: промзагрузка.
6. **Наличие достаточного количества лидов** — max 3. 3 = each lead has
   5-8 direct reports AND at least one person growing into an M-track; 2 =
   one lead's span is <5 or >8, or nobody growing into leadership; 1 =
   span issue under 2+ leads; 0 = span issue under 2+ leads AND nobody
   growing into leadership. Method: team structure + OKRs of people
   growing toward an M-track.
7. **Наличие успешных и профессиональных менторов** (a lead counts if they
   can take interns), 6-month window — max 2. 2 = ≥20% of leads are
   mentors; 1 = some but <20%; 0 = none. Method: "intern passed to Junior
   within 6 months" record.
8. **Успешность тренировочных собесов** — max 2. 2 = nobody below 70% pass
   rate on their last 3 mock interviews; 1 = at most 1 person below 70%; 0
   = more than 1. Method: internal mock-interview tool.
9. **Успешность внешних собесов** — max 2. 2 = nobody below 70%; 1 = at
   most 1 person between 60-70%; 0 = more than 1 person between 60-70%, or
   anyone below 60%. Method: interview-report chat.
10. **Время нахождения на бенче** (staff employees) — max 2. 2 = nobody
    over 1 month on bench; 1 = someone over 3 months; 0 = someone over 3
    months (per source wording, the 1/3-month bands as given — apply as
    written, flag to the user if the source numbers look inconsistent
    rather than silently "fixing" them). Method: промзагрузка.
11. **Кол-во стажеров, перешедших в штат за ≤3 месяца** — max 2. Only
    trainees who finished the internship and converted to intern-staff
    ahead of the minimum term count. For M2 and above: 2 = ≥2 trainees, 1 =
    1 trainee, 0 = none. For M1: 2 = 1 trainee, 0 = none (no 1-point band
    for M1). Method: HRM, промзагрузка, bench table.
12. **Пропорция состава команды** (roughly 1 Senior : ≤3 Junior (interns
    count as Junior) : 3 Middle) — max 1. 1 = proportion roughly holds; 0 =
    disproportion at either the Junior or Middle level. Method: HRM,
    промзагрузка — cross-reference `_people_registry`'s `Internal rank`
    column for this manager's team before asking the user for the rest.
13. **Тимбилдинги** — max 1. 1 = at least one held in the period; 0 = none.
    Method: photo report.
14. **Кол-во увольнений** — max 1. 1 = no departures; 0 = any departure.
    Method: промзагрузка.
15. **Уровень английского в команде** — max 2. 2 = nobody below B2; 1 =
    nobody below B1+; 0 = someone below B1+. Method: HRM (must always
    reflect the current level).
16. **Ворк-лайф баланс** (overtime) — max 2. 2 = no overtime team-wide; 1 =
    ≤10% overtime; 0 = >10% overtime. Short-term overtime is acceptable;
    long-term is not. Untracked/unreported overtime is itself a problem to
    address, not a pass. Method: HRM.
17. **Уход сотрудников с проектов** (leaving or wanting to leave a project
    early) — max 2. 2 = no one left/wanted to leave before 1 year on a
    project (or before a short project's end); 1 = no one left/wanted to
    leave before 6 months (or a short project); 0 = someone left/wanted to
    leave earlier than that. Method: offboarding records, промзагрузка.

## Normalization

- Most metrics rely on external systems this repository does not track
  (промзагрузка/utilization tool, HRM, mock-interview tool, interview-report
  chat, offboarding records, photo reports). Ask the user for these numbers
  rather than inventing or estimating them.
- A few metrics have partial evidence already in this repo — use it as a
  starting point, not a substitute for the user confirming the number:
  - **Metric 4** (project feedback): read `project_metrics`'s `Вклад в
    проект: <Имя>` rows (see `qa-management-roles/references/
    google-workspace-rules.md`, M2 Project-Based Layout) for each team
    member's tracked project(s). A `Позитивный` row supports "positive," a
    `Смешанный` row is neutral, a `Негативный` row is negative — same
    3-level mapping already used elsewhere in this repo. Team members on
    projects this repo doesn't track still need the user's input.
  - **Metric 6** (leads / growth-into-M pipeline) and **metric 12**
    (Junior/Middle/Senior proportion): read `_people_registry`'s `Role` and
    `Internal rank` columns, filtered to this manager's team (`Project(s)`/
    `Notes` cross-project-duty rows per that file's own rules).
- Do not silently reinterpret a scoring band's wording — quote it back to
  the user as written if a real case doesn't cleanly fit one of the listed
  bands, and ask which band applies rather than guessing.
- Leave a metric's score blank (not 0) when its number is genuinely
  unknown — 0 is a real negative score, not a placeholder for "no data."
