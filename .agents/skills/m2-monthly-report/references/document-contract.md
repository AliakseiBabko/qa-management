# Document Contract

## Purpose

Use this reference for M2 monthly KPI report CSV generation.

## Template

`<repo-root>\Templates\m2_monthly_report.csv`

## Expected Output

One CSV per M2 manager and reporting month.

Suggested target folder:

`G:\My Drive\QA_Management\20_M2_Project_Management`

Suggested naming pattern:

`m2_monthly_report_<Manager>_YYYY-MM.csv`

## Schema

Use exactly the columns in `Templates\m2_monthly_report.csv`:

1. `Report Type`
2. `Manager`
3. `Period`
4. `Base Bonus ($)`
5. `Final Bonus ($)`
6. `Section`
7. `Item No`
8. `Item / Condition`
9. `Coefficient / Bonus`
10. `Completed (Да/Нет)`
11. `Quantity`
12. `Amount ($)`
13. `Note`
14. `Evidence / Comment`
15. `Missing Data Question`

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

## Missing Data Rules

- Ask for manager name when absent.
- Ask for reporting month when absent or ambiguous.
- Ask for project/FTE unit count when rows depend on `projects + FTE`.
- Ask for links or source names for status-thread, client-feedback, release, upsale, rate, staffing, onboarding, offboarding, and improvement claims.
- Ask for security, timesheet, stop-rate, negative-feedback, and unplanned-exit status if the report requires final bonus/penalty calculation and no source exists.
- Leave cells blank instead of guessing.
