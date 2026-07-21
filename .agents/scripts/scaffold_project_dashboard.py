"""Scaffold the M2-only dashboard artifacts for one project: qa_process_metrics,
individual_metrics_internal (per person), m2_input, action_items, and (only if
entirely missing) a placeholder project_metrics.

This creates structure, not judgment. project_metrics rows and m2_input
rounds need M2's actual read of the project to be worth anything (see
m2-role-rules.md, Project-Level Rollups) — this script only fills in the
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

QA_HEADER = ["Проект", "Период", "Метрика", "Показатель", "Пояснение", "Owner", "Тренд"]
INTERNAL_HEADER = ["Проект", "Сотрудник", "Дата", "Сторона", "Метрика", "Показатель", "Пояснение", "Тренд"]
ACTION_ITEMS_HEADER = ["Проект", "Дата события", "Тип", "Что нужно сделать", "Статус", "Owner", "Источник", "Комментарии"]

# Core 5 only (2026-07-17) - the old 16-metric full catalog was scaffolded
# onto every new project by default, which is exactly the unrealistic-ask
# problem that prompted the Core/Extended split (see
# Templates\метрики_проекта_qa.md §2 History). Extended-catalog metrics are
# still valid but only get added by hand once a project actually has the
# supporting tooling - never scaffolded blank.
QA_METRICS_TEMPLATE = [
    ("Покрытие (грубая оценка)",
     "(число автотестов) / (грубая оценка функциональной поверхности - страницы/компоненты/эндпоинты, что "
     "подходит стеку). Не сертифицированный %, явно оценка. Собирается через "
     "Templates\\qa_repo_metrics_prompt.md - промпт для любого доступного кодинг-агента против своего "
     "репозитория с тестами, не ручной подсчёт."),
    ("Количество автотестов (тренд)",
     "Общее число автотестов, помесячно - тот же запуск qa_repo_metrics_prompt.md, что и для покрытия выше. "
     "Даже без деноминатора рост числа тестов - рабочий сигнал прогресса."),
    ("Pass rate последнего прогона",
     "Доля прошедших тестов в последнем прогоне (regression или обычный CI). Одна цифра, которую QA-инженер "
     "обычно и так знает."),
    ("Ощущение по flaky-тестам",
     "Не точный процент, а короткая качественная оценка одним предложением (\"стабильно\" / \"есть заметные "
     "flaky-падения, мешают доверять прогону\")."),
    ("Снимок открытых/известных багов",
     "Сырое число, если трекер (Jira и т.п.) доступен; если недоступен или баги не тегируются системно - "
     "оставь пустым с причиной (\"нет доступа к трекеру\" и т.п.) - это тоже валидный результат."),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project folder name under 20_M2_Project_Management.")
    parser.add_argument(
        "--person",
        action="append",
        default=[],
        dest="people",
        help="A person's name to scaffold individual_metrics_internal for. Repeat for multiple people; if "
        "omitted, every existing people/<Person> subfolder is used.",
    )
    parser.add_argument(
        "--owner",
        default=None,
        help="Named owner for qa_process_metrics. Defaults to the sole person if there's exactly one, "
        "otherwise must be given explicitly (see m2-role-rules.md on picking an owner for multi-person "
        "projects).",
    )
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def qa_process_rows(project: str, owner: str, period: str) -> list[list[str]]:
    return [[project, period, metric, "", text, owner] for metric, text in QA_METRICS_TEMPLATE]


def scaffold_qa_process_metrics(services: dict, project_folder_id: str, project: str, owner: str, period: str) -> str:
    drive = services["drive"]
    if find_sheet_in_folder(drive, project_folder_id, "qa_process_metrics"):
        return "qa_process_metrics: already exists, skipped"
    values = [QA_HEADER] + qa_process_rows(project, owner, period)
    create_sheet(services, "qa_process_metrics", project_folder_id, values)
    return "qa_process_metrics: created"


def scaffold_individual_metrics_internal(services: dict, person_folder_id: str, project: str, person: str) -> str:
    drive = services["drive"]
    if find_sheet_in_folder(drive, person_folder_id, "individual_metrics_internal"):
        return f"individual_metrics_internal ({person}): already exists, skipped"
    create_sheet(services, "individual_metrics_internal", person_folder_id, [INTERNAL_HEADER])
    return f"individual_metrics_internal ({person}): created"


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
    create_sheet(services, "project_metrics", project_folder_id, [QA_HEADER] + rows)
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
                "See m2-role-rules.md for how to pick one."
            )

    print(f"Scaffolding {args.project} ({len(people)} people, qa_process_metrics owner: {owner})")
    private_folder = ensure_document_folder(drive, project_folder["id"], "project_metrics")
    team_folder = ensure_document_folder(drive, project_folder["id"], "qa_process_metrics")
    print(" ", scaffold_project_metrics(services, private_folder["id"], args.project, people, period))
    print(" ", scaffold_qa_process_metrics(services, team_folder["id"], args.project, owner, period))
    for person in people:
        private_person = ensure_document_folder(
            drive, project_folder["id"], "individual_metrics_internal", person
        )
        print(" ", scaffold_individual_metrics_internal(
            services, private_person["id"], args.project, person
        ))
    print(" ", scaffold_m2_input(services, private_folder["id"], args.project, period))
    print(" ", scaffold_action_items(services, private_folder["id"], args.project))
    return 0


if __name__ == "__main__":
    sys.exit(main())
