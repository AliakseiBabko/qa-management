# Document Contract

## Purpose

Use this reference for M1 monthly KPI report CSV generation.

## Template

`<repo-root>\Templates\m1_monthly_report.csv`

## Expected Output

One CSV per M1 manager and reporting month.

Suggested target folder:

`G:\My Drive\QA_Management\10_M1_People_Management`

Suggested naming pattern:

`m1_monthly_report_<Manager>_YYYY-MM.csv`

## Schema

Use exactly the columns in `Templates\m1_monthly_report.csv`:

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

The current source workbook contains one sheet per month. Each sheet has:

- title row: `ЕЖЕМЕСЯЧНЫЙ ОТЧЁТ М1 — Подтверждение выполнения КПИ`
- manager/month/base/final bonus header rows
- `РАЗДЕЛ 1 — БАЗОВЫЕ ОБЯЗАННОСТИ`
- `РАЗДЕЛ 2 — КПИ (начисление бонуса)`
- final total row: `ИТОГО — сумма по КПИ`

## Section 1 Obligations Observed

- Оценивать сотрудников на соответствие портрета
- Являться примером и проводником наших ценностей и миссии
- Развивать культуру в команде
- 1x1 с сотрудником не реже 1 раза в месяц
- Подготовка к запросам
- Онбординг новых людей в команду
- Работа с ОКР
- Подготовка и проведение PR
- Сбор фидбеков по сотруднику
- Сбор фидбеков от сотрудников и от команды
- Взаимодействие с М2, М3, RM, HR по сотрудникам команды
- Участие в собеседовании людей в свою команду
- Шаринг информации от компании и от уровней выше на команду
- Шаринг информации от команды на уровни выше
- Security (Zadarma, MDM, VPN, Google acc)

## Section 2 KPI Rows Observed

- Проведение Assessment
- Подготовил сотрудника к сдаче на грейд; сотрудник прошёл ассессмент и получил грейд
- Митап для команды/дела
- Команда больше 7 человек
- Команда меньше 7 человек
- Нарушение требований Security
- За каждое FTE на проекте
- Подготовка к старту проекта
- Незапланированное увольнение / не по нашей инициативе
- Провёл синк по Security
- Таймшиты заполнены вовремя
- Таймшиты заполнены НЕ вовремя
- Вырастил нового M1
- Вырастил нового лида процесса

## Missing Data Rules

- Ask for manager name when absent.
- Ask for reporting month when absent or ambiguous.
- Ask for direct evidence/links/counts needed for a `Да` KPI row.
- Ask for team size and project FTE counts when bonus rows depend on counts.
- Ask about security violations, unplanned resignations, and timesheet status if the report requires final bonus calculation and no source exists.
- Leave cells blank instead of guessing.
