# Document Contract

Primary final output is a Google Sheet in `20_M2_Project_Management`, with local
CSV fallback. Preserve the CSV template layout as the Sheet layout/schema.

## Purpose

Use this reference for M2 monthly KPI report Google Sheet generation, with CSV fallback.

## Template

`<repo-root>\Templates\m2_monthly_report.csv`

## Expected Output

One CSV per M2 manager and reporting month.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management`

Suggested naming pattern:

`m2_monthly_report_<Manager>_YYYY-MM.csv`

## Versioning

- Do not overwrite an existing final monthly report by default.
- If the target manager/month file already exists, create the next versioned file with a `_vN` suffix before `.csv`, for example `_v2` or `_v3`.
- Update an existing monthly report in place only when the user explicitly asks for revision.

## Layout

Use the 2D CSV grid in `Templates\m2_monthly_report.csv`; it mirrors the workbook layout rather than a normalized table.

Preserve:

- report title row
- manager/month row
- base/final bonus row
- section title rows
- Section 1 obligation table
- Section 1 status row
- Section 2 KPI / bonus / penalty table
- total row
- instruction row

Do not add a `Missing Data Question` column to the CSV. Ask missing-data questions in the conversation or leave the relevant cells blank.

## Source Workbook Structure

The current source workbook is an example and contains:

- title row: `ЕЖЕМЕСЯЧНЫЙ ОТЧЁТ М2 — КАЛЬКУЛЯТОР KPI`
- manager/month/base/final bonus header rows
- `РАЗДЕЛ 1 — БАЗОВЫЕ ОБЯЗАННОСТИ`
- `РАЗДЕЛ 2 — KPI / БОНУСЫ / ШТРАФЫ`
- final total row: `ИТОГО — сумма по KPI`

## Section 1 Obligations Observed

- Staffing на свои проекты
- Определение и сбор метрик качества работы на проекте для каждого сотрудника
- Статус в чат стратегии по статусу проекта и его команде
- Онбординг на проект + статус в чат стратегии об итоге онбординга
- Каждый сотрудник имеет план развития проекта и себя в рамках проекта
- Актуальный план развития каждого проекта
- Отсутствие негативных фидбеков с проекта по QA команде
- Оффбординг сотрудника с проекта
- Саппорт сотрудников по любым проектным вопросам
- Заполнение статус-ботов
- Контроль легенды и Security на проекте
- Регулярный сбор фидбеков с проекта
- Отсутствие стопа ставок по нашей вине
- Постоянно держать up to date таблицу загрузки
- 12 единиц проекты + FTE

## Section 2 KPI / Bonus / Penalty Rows Observed

- Позитивные фидбеки с проекта по сотруднику
- Подготовка команды ко встрече с клиентом
- Организация передачи техники
- Сотрудник на проекте поднял грейд
- Сотрудник на проекте занял Lead/Manager позицию
- Маркетинг кейс проекта
- Подготовка и сдача на сертификат, нужный для проекта
- Проведение воркшопов/митапов на проекте
- Внедрение улучшений на проекте
- Успешный релиз
- Успешное завершение проекта
- Выход на клиента напрямую
- Увеличили рейт на проекте
- Провёл замену нерентабельной ставки
- Больше 12 единиц проекты + FTE
- Вырастил DC на проекте
- Вырастил М2
- Upsale на проекте — сотрудник сам
- Upsale на проекте — совместная работа М2 и сотрудника
- Upsale на проекте — М2 сам всё проверил
- Подготовка к старту проекта
- За каждые 1000 пейдов на 1 ставку FTE
- Таймшиты заполнены вовремя
- Незапланированный уход инженера с проекта
- Меньше 12 единиц проекты + FTE
- Нарушение требований Security
- Слёт ставки БЕЗ предупреждения
- Слёт ставки С предупреждением
- Плохой фидбек с проекта
- Плохой фидбек с проекта повторно
- Каждая FTE в инвест фонде
- Таймшиты заполнены не вовремя

## Capacity-Points Rule ("N единиц проекты + FTE")

Internal M2 compensation rule behind the `12 единиц проекты + FTE` /
`Больше 12 единиц проекты + FTE` / `Меньше 12 единиц проекты + FTE` rows:

- Each project M2 owns counts as **1 point**, plus **1 additional point per
  person staffed on that project** — a project with one person is 2 points
  (1 project + 1 person), a project with three people is 4 points, and so
  on. This is not a headcount total and not "1 point per project
  regardless of size" — both the project itself and each person on it
  count separately.
- Target is **12 points total** across an M2's whole block of projects.
  Exactly 12 satisfies the base obligation (Section 1, no bonus). Above 12
  is the KPI bonus trigger (Section 2, `Больше 12 единиц проекты + FTE`).
  Below 12 is the penalty trigger (Section 2, `Меньше 12 единиц проекты +
  FTE`).
- This is purely an internal capacity/compensation calculation — it does
  not appear on the department's "Auto staff. Светофор проектов" tracker
  (`m2-department-traffic-light`'s `FTE` column there is plain headcount,
  a different, unrelated field with the same name) and is not derived from
  `_project_registry`'s `People` column without applying this formula.

## Missing Data Rules

- Ask for manager name when absent.
- Ask for reporting month when absent or ambiguous.
- Ask for project/FTE unit count when rows depend on `projects + FTE`.
- Ask for links or source names for status-thread, client-feedback, release, upsale, rate, staffing, onboarding, offboarding, and improvement claims.
- Ask for security, timesheet, stop-rate, negative-feedback, and unplanned-exit status if the report requires final bonus/penalty calculation and no source exists.
- Leave cells blank instead of guessing.
