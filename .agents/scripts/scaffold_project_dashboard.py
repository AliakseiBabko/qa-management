"""Scaffold the M2-only dashboard artifacts for one project: qa_process_metrics,
individual_metrics_internal (per person), m2_input, and (only if entirely
missing) a placeholder project_metrics.

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

QA_HEADER = ["Проект", "Период", "Метрика", "Показатель", "Пояснение", "Owner", "Тренд"]
INTERNAL_HEADER = ["Проект", "Сотрудник", "Дата", "Сторона", "Метрика", "Показатель", "Пояснение", "Тренд"]

QA_METRICS_TEMPLATE = [
    ("Defect Escape Rate / Bug leakage rate",
     "Доля багов, дошедших до прода, от всех найденных за последний календарный месяц. "
     "Формула: найдено_на_проде / (найдено_на_проде + найдено_до_релиза) x 100%. Худший сигнал набора."),
    ("Баги, найденные в проде за месяц",
     "Сырое число (не rate) за последний календарный месяц. Источник тот же, что для Defect Escape Rate выше."),
    ("Defect Density",
     "Багов на фичу/модуль/страницу. Нужен доступ к структуре модулей продукта — уточни у dev-команды; если "
     "недоступно, оставь пустым."),
    ("Распределение багов по критичности и по частям приложения",
     "Не просто % Critical/Major/Minor, а в связке с тем, в какой части продукта они найдены — цель увидеть "
     "системно слабые зоны."),
    ("Покрытие по функциональным зонам (manual + automation)",
     "Раздели продукт на функциональные зоны и укажи долю, реально покрытую ручными тест-кейсами и/или "
     "автотестами."),
    ("Automation Coverage", "Доля согласованного critical path, покрытого автотестами."),
    ("Automation Stability (flaky rate)",
     "Доля падений автотестов, не связанных с реальным багом. Ориентир: не более 5%."),
    ("Regression Pass Rate", "Доля пройденных тестов в прогоне перед релизом."),
    ("CI Pipeline Pass Rate",
     "Доля успешных прогонов CI за месяц. Если CI ещё нет, так и укажи — это факт о проекте, не пробел заполнения."),
    ("Release Stability", "Количество хотфиксов/найденных проблем сразу после релиза (post-deploy) за месяц."),
    ("Mean Time to Fix", "Среднее время жизни багтикета: от открытия до закрытия/подтверждения фикса, за месяц."),
    ("Количество созданных тикетов/задач за месяц",
     "Источник: трекер задач, фильтр по дате создания за последний календарный месяц."),
    ("Скорость создания тест-кейсов",
     "Сколько новых ручных тест-кейсов добавлено за месяц. Если TMS нет, оценка на глаз допустима — отметь явно, "
     "что это оценка."),
    ("Скорость создания автотестов", "Сколько новых автотестов добавлено за месяц."),
    ("Количество прогонов тестов (test runs) за месяц",
     "Сколько раз реально запускался тестовый набор (ручной и/или автоматический) за месяц."),
    ("Фактическая длительность прогона автотестов",
     "Сколько реально занимает автоматизированный прогон (smoke/regression) по факту, не по плану."),
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


def scaffold_individual_metrics_internal(services: dict, people_folder_id: str, project: str, person: str) -> str:
    drive = services["drive"]
    person_folder = find_or_create_folder(drive, people_folder_id, person)
    if find_sheet_in_folder(drive, person_folder["id"], "individual_metrics_internal"):
        return f"individual_metrics_internal ({person}): already exists, skipped"
    create_sheet(services, "individual_metrics_internal", person_folder["id"], [INTERNAL_HEADER])
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
    people_folder = find_or_create_folder(drive, project_folder["id"], "people")

    people = args.people
    if not people:
        people = sorted(
            item["name"]
            for item in drive.files()
            .list(
                q=f"'{people_folder['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="files(name)",
            )
            .execute()
            .get("files", [])
        )
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
    print(" ", scaffold_project_metrics(services, project_folder["id"], args.project, people, period))
    print(" ", scaffold_qa_process_metrics(services, project_folder["id"], args.project, owner, period))
    for person in people:
        print(" ", scaffold_individual_metrics_internal(services, people_folder["id"], args.project, person))
    print(" ", scaffold_m2_input(services, project_folder["id"], args.project, period))
    return 0


if __name__ == "__main__":
    sys.exit(main())
