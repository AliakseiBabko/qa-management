"""Scaffold the M2-only dashboard artifacts for one project: qa_process_metrics,
individual_risk (per person), m2_input, action_items, and (only if
entirely missing) a placeholder project_metrics.

This creates structure, not judgment. project_metrics rows and m2_input
rounds need M2's actual read of the project to be worth anything (see
m2-role/m2-project-rollups.md, Project-Level Rollups) — this script only fills in the
schema and placeholder text so that work has somewhere to go. It never
overwrites an existing project_metrics; if one is already there (even on
an older schema), it's left alone and reported as skipped.

Safe to rerun: every artifact is created only if missing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials
from sync_m2_source_docs_to_sheets import (
    ROOT_FOLDER_ID,
    find_or_create_folder,
    find_sheet_in_folder,
    create_sheet,
)
from sync_m2_plans_to_docs import (
    DOC_MIME_TYPE,
    find_file_in_folder,
    create_doc,
    clear_doc_body,
    parse_blocks,
    build_doc_requests,
)
from m2_workspace_layout import ensure_document_folder, list_project_people

EMPTY_ROUND_PLACEHOLDER = "(placeholder - раунд создан автоматически, вопросов ещё нет)"

# Legacy 7-column shape still used for the project_metrics placeholder this
# script writes; the real project_metrics schema is 12 columns and gets built
# conversationally by M2 (see project-metrics-schema.md).
PROJECT_METRICS_HEADER = ["Проект", "Период", "Метрика", "Показатель", "Пояснение", "Owner", "Тренд"]

# qa_process_metrics is a wide sheet: three fixed columns, then one column per
# sprint appended on the right (2026-09-09). It used to be a long 7-column
# table with a `Период` column and one row per (metric, period), which buried
# each metric's own history in a pile of rows instead of showing it as a line.
# The scaffold cannot know the project's sprint calendar - that lives in
# project_metrics' `Ритм спринтов` row and is filled by M2 - so it lays down a
# single placeholder sprint column for the team to rename.
QA_PROCESS_FIXED_HEADER = ["Метрика", "Пояснение", "Owner"]
SPRINT_COLUMN_PLACEHOLDER = "<спринт 1: 2026-Sxx (дд.мм-дд.мм)>"
INTERNAL_RISK_HEADER = [
    "Проект", "Сотрудник", "Дата обновления",
    "Риск с нашей стороны (мы недовольны)", "Риск со стороны сотрудника (он недоволен)",
    "Комментарии", "План действий",
]
ACTION_ITEMS_HEADER = ["Проект", "Дата события", "Тип", "Что нужно сделать", "Статус", "Owner", "Источник", "Комментарии"]

# Tier 0 Baseline (3 rows, mandatory on every project, never removed) plus the
# Core 6 (added where the project has any tooling for them), grouped so the
# sheet reads top-down: what every project can count, then automation, then
# defects. The Extended catalog is never scaffolded blank - a row is added by
# hand once the project actually has the supporting tooling (see
# Templates\\метрики_проекта_qa.md §2).
QA_BASELINE_TEMPLATE = [
    ("Тикеты за спринт (QA)",
     "Количество задач, закрытых QA за спринт. Где искать: фильтр в трекере по спринту и "
     "исполнителю/типу задачи. Если отдельных QA-тикетов на проекте нет и QA-работа зашита внутрь "
     "задач разработки - считай задачи разработки, которые QA реально провёл через тестирование, и "
     "пометь здесь: относительная величина, отдельных QA-тикетов нет."),
    ("Story points за спринт (QA)",
     "Только если проект вообще использует SP. Если не использует - значения по спринтам пустые, а "
     "здесь причина: проект не использует story points. Оценку задним числом ради заполнения строки "
     "не заводим."),
    ("Git-активность за спринт (AQA)",
     "Коммиты и добавленные/удалённые строки за спринт, суммарно по AQA-стриму проекта. Только когда "
     "_metrics_collector_registry помечает Metrics validity участников как Reliable (см. "
     "m2-git-metrics-onboarding). На чисто ручном проекте: Не применимо (manual QA stream)."),
]

QA_AUTOMATION_TEMPLATE = [
    ("Покрытие (грубая оценка)",
     "(число автотестов) / (грубая оценка функциональной поверхности - страницы/компоненты/эндпоинты, что "
     "подходит стеку). Не сертифицированный %, явно оценка. Собирается через "
     "Templates\\qa_repo_metrics_prompt.md - промпт для любого доступного кодинг-агента против своего "
     "репозитория с тестами, не ручной подсчёт."),
    ("Количество автотестов",
     "Общее число автотестов на конец спринта - тот же запуск qa_repo_metrics_prompt.md, что и для покрытия выше. "
     "Даже без деноминатора рост числа тестов - рабочий сигнал прогресса."),
    ("Pass rate последнего прогона",
     "Доля прошедших тестов в последнем прогоне спринта (regression или обычный CI). Одна цифра, которую "
     "QA-инженер обычно и так знает."),
    ("Ощущение по flaky-тестам",
     "Не точный процент, а короткая качественная оценка одним предложением (\"стабильно\" / \"есть заметные "
     "flaky-падения, мешают доверять прогону\")."),
]

QA_DEFECT_TEMPLATE = [
    ("Снимок открытых/известных багов",
     "Сырое число на конец спринта, если трекер (Jira и т.п.) доступен; если недоступен или баги не тегируются "
     "системно - значения по спринтам пустые, а здесь причина (\"нет доступа к трекеру\" и т.п.) - это тоже "
     "валидный результат."),
    ("Production bug leakage (Баги, утекшие в прод)",
     "Отдельно от снимка открытых багов выше - дефекты, найденные ПОСЛЕ релиза/в проде/пользователями/"
     "клиентом/бизнесом/продакт-оунером, не найденные QA до релиза. Где возможно, классифицируй каждый "
     "случай: пропуск QA / пробел в требованиях-продукте / проблема окружения-данных-конфигурации / "
     "известный принятый риск / неясно-требует триажа. Если точное число неизвестно - качественное "
     "значение с опорой на свидетельства: \"нет данных\" / \"утечек не подтверждено\" / \"подтверждённые "
     "случаи есть, число неизвестно\" / \"N подтверждённых случаев\"."),
]

# The 6 Core rows as one flat list (automation + defects), for callers that
# only care about the tooling-gated tier.
QA_METRICS_TEMPLATE = QA_AUTOMATION_TEMPLATE + QA_DEFECT_TEMPLATE

QA_PROCESS_GROUPS = [
    ("[Базовые метрики: каждый спринт, обязательны на любом проекте]", QA_BASELINE_TEMPLATE),
    ("[Автоматизация: заводится, если на проекте есть автотесты]", QA_AUTOMATION_TEMPLATE),
    ("[Дефекты]", QA_DEFECT_TEMPLATE),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project folder name under 20_M2_Project_Management.")
    parser.add_argument(
        "--person",
        action="append",
        default=[],
        dest="people",
        help="A person's name to scaffold individual_risk for. Repeat for multiple people; if "
        "omitted, every existing people/<Person> subfolder is used.",
    )
    parser.add_argument(
        "--owner",
        default=None,
        help="Named owner for qa_process_metrics. Defaults to the sole person if there's exactly one, "
        "otherwise must be given explicitly (see m2-role/m2-metrics-attribution.md on picking an owner for multi-person "
        "projects).",
    )
    parser.add_argument(
        "--sprint",
        default=SPRINT_COLUMN_PLACEHOLDER,
        help="Header for the first sprint column of qa_process_metrics, e.g. "
        "\"2026-S14 (19.08-01.09)\". Defaults to a placeholder, since the sprint calendar "
        "comes from project_metrics' `Ритм спринтов` row, which M2 fills in later.",
    )
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def qa_process_rows(owner: str) -> list[list[str]]:
    """Wide rows: (Метрика, Пояснение, Owner) plus one empty sprint cell.

    Group label rows are plain text rows in the Метрика column - they keep the
    sheet readable for the team that fills it in, and carry no values.
    """
    rows: list[list[str]] = []
    for label, metrics in QA_PROCESS_GROUPS:
        rows.append([label, "", "", ""])
        rows.extend([metric, text, owner, ""] for metric, text in metrics)
    return rows


def scaffold_qa_process_metrics(services: dict, project_folder_id: str, owner: str, sprint: str) -> str:
    drive = services["drive"]
    if find_sheet_in_folder(drive, project_folder_id, "qa_process_metrics"):
        return "qa_process_metrics: already exists, skipped"
    values = [QA_PROCESS_FIXED_HEADER + [sprint]] + qa_process_rows(owner)
    create_sheet(services, "qa_process_metrics", project_folder_id, values)
    return "qa_process_metrics: created"


def scaffold_individual_risk(services: dict, person_folder_id: str, project: str, person: str) -> str:
    drive = services["drive"]
    if find_sheet_in_folder(drive, person_folder_id, "individual_risk"):
        return f"individual_risk ({person}): already exists, skipped"
    # Single placeholder row, not a blank header only - this Sheet is a living,
    # one-row-per-person current-state record (see Templates/individual_risk.csv
    # and m2-individual-qa-metrics-report/references/internal-variant.md), not a
    # log; scaffolding still leaves the row's judgment cells blank for M2 to fill.
    placeholder_row = [project, person, "", "", "", "", ""]
    create_sheet(services, "individual_risk", person_folder_id, [INTERNAL_RISK_HEADER, placeholder_row])
    return f"individual_risk ({person}): created"


def scaffold_project_metrics(services: dict, project_folder_id: str, project: str, people: list[str], period: str) -> str:
    drive = services["drive"]
    if find_sheet_in_folder(drive, project_folder_id, "project_metrics"):
        return "project_metrics: already exists, left untouched (rebuild is a manual/conversational M2 task)"
    rows = [
        [project, period, "Горизонт совместной работы", "Неизвестно",
         "Контрактный/тендерный горизонт клиента ещё не зафиксирован. Требуется уточнить у клиента/аккаунт-менеджера.", "M2"],
        [project, period, "Бизнес-риск продукта клиента (оценка M2)", "",
         "Пока не оценено.", "M2"],
    ]
    for person in people:
        rows.append([project, period, f"Вклад в проект: {person}", "Неизвестно",
                     "Данных пока недостаточно для оценки.", "M2"])
    rows.append([project, period, "Качество QA-процесса", "",
                 "Пока не оценено — qa_process_metrics ещё не заполнен командой.", "M2"])
    create_sheet(services, "project_metrics", project_folder_id, [PROJECT_METRICS_HEADER] + rows)
    return "project_metrics: created (placeholder rows only, needs real M2 judgment)"


def scaffold_action_items(services: dict, project_folder_id: str, project: str) -> str:
    drive = services["drive"]
    if find_sheet_in_folder(drive, project_folder_id, "action_items"):
        return "action_items: already exists, skipped"
    create_sheet(services, "action_items", project_folder_id, [ACTION_ITEMS_HEADER])
    return "action_items: created (empty, ready for M2 to log events/deadlines/follow-ups)"


def scaffold_m2_input(services: dict, project_folder_id: str, project: str, period: str) -> str:
    drive = services["drive"]
    docs = services["docs"]
    m2in = find_or_create_folder(drive, project_folder_id, "m2_input")
    if find_file_in_folder(drive, m2in["id"], "m2_input", DOC_MIME_TYPE):
        return "m2_input: already exists, skipped"
    markdown = "\n".join([
        f"## {project} - входные данные M2",
        f"## Раунд: {period}",
        "### Вопросы от предварительного анализа",
        f"- {EMPTY_ROUND_PLACEHOLDER}",
        "### Ответ и общие соображения M2",
        "",
    ])
    doc_id = create_doc(services, "m2_input", m2in["id"])
    clear_doc_body(docs, doc_id)
    _, requests = build_doc_requests(parse_blocks(markdown))
    docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    return "m2_input: created (empty round, ready for the preliminary-analysis pass)"


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    period = dt.date.today().isoformat()

    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]

    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    project_folder = find_or_create_folder(drive, m2_root["id"], args.project)

    people = args.people
    if not people:
        people = list_project_people(drive, project_folder["id"])
    if not people:
        raise SystemExit("No people found or given via --person; pass at least one --person for a new project.")

    owner = args.owner
    if owner is None:
        if len(people) == 1:
            owner = people[0]
        else:
            raise SystemExit(
                f"{len(people)} people on {args.project} ({', '.join(people)}) — pass --owner explicitly. "
                "See m2-role/m2-metrics-attribution.md for how to pick one."
            )

    print(f"Scaffolding {args.project} ({len(people)} people, qa_process_metrics owner: {owner})")
    private_folder = ensure_document_folder(drive, project_folder["id"], "project_metrics")
    team_folder = ensure_document_folder(drive, project_folder["id"], "qa_process_metrics")
    print(" ", scaffold_project_metrics(services, private_folder["id"], args.project, people, period))
    print(" ", scaffold_qa_process_metrics(services, team_folder["id"], owner, args.sprint))
    for person in people:
        private_person = ensure_document_folder(
            drive, project_folder["id"], "individual_risk", person
        )
        print(" ", scaffold_individual_risk(
            services, private_person["id"], args.project, person
        ))
    print(" ", scaffold_m2_input(services, private_folder["id"], args.project, period))
    print(" ", scaffold_action_items(services, private_folder["id"], args.project))
    return 0


if __name__ == "__main__":
    sys.exit(main())
