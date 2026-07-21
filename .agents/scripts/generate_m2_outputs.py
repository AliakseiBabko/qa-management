#!/usr/bin/env python3
"""Generate first-pass M2 CSV outputs from extracted QA source corpus.

This is a conservative normalizer: it preserves source evidence and uses
fallback rows when a document is narrative rather than table-shaped.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_RISK_HEADER = [
    "Проект",
    "Период / snapshot date",
    "Общий уровень риска",
    "Риск delivery",
    "Риск QA process",
    "Риск staffing / continuity",
    "Риск communication / client",
    "Комментарии",
    "План действий",
    "Owner",
    "Следующий review",
]

PROJECT_METRICS_HEADER = [
    "Проект",
    "Период",
    "Метрика",
    "Показатель / score",
    "Уровень внимания",
    "Тренд",
    "Статус данных",
    "Evidence / источник",
    "Owner",
    "Следующее действие",
    "Комментарии",
]

INDIVIDUAL_METRICS_HEADER = [
    "Проект",
    "Сотрудник",
    "Дата",
    "Роль / stream",
    "Метрика",
    "Показатель",
    "Пояснение",
    "Тренд",
]

PROJECT_PLAN_HEADER = [
    "Проект",
    "Период",
    "Review cycle",
    "Краткое резюме",
    "Текущее состояние",
    "Фокус / initiative",
    "Почему важно",
    "Действие",
    "Ответственный",
    "Срок",
    "Критерий успеха",
    "Риск если не сделать",
    "Следующий review",
    "Evidence / источник",
]

INDIVIDUAL_PLAN_HEADER = [
    "Проект",
    "Сотрудник",
    "Роль / stream",
    "Период",
    "Review cycle",
    "Цель на период",
    "Фокус развития",
    "Почему важно",
    "Действие сотрудника",
    "Поддержка менеджера",
    "Срок",
    "Критерий успеха",
    "Текущий прогресс",
    "Следующий review",
    "Evidence / источник",
]


def parse_args() -> argparse.Namespace:
    today = dt.date.today().isoformat()
    parser = argparse.ArgumentParser(description="Generate M2 output CSVs from extracted source corpus.")
    parser.add_argument(
        "--extract-root",
        default=rf"G:\My Drive\QA_Management\90_Storage\_System\extracts\source\{today}",
        help="Dated extraction folder containing manifest.csv.",
    )
    parser.add_argument(
        "--output-root",
        default=rf"G:\My Drive\QA_Management\20_M2_Project_Management\generated_from_source_{today}",
        help="Output folder for generated M2 CSV files.",
    )
    parser.add_argument("--snapshot-date", default=today, help="Snapshot date used in filenames and rows.")
    parser.add_argument("--overwrite", action="store_true", help="Allow writing into a non-empty output folder.")
    return parser.parse_args()


def safe_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned.rstrip(". _") or "unnamed"


def compact(value: str, limit: int = 900) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def norm(value: str) -> str:
    return re.sub(r"[^a-zа-я0-9]+", "", (value or "").casefold())


def find_header(rows: list[list[str]]) -> tuple[int, dict[str, int]] | None:
    aliases = {
        "metric": {"метрика", "metric", "dimension", "показатель"},
        "indicator": {"score", "показатель", "значение", "status", "уровень"},
        "attention": {"уровеньвнимания", "attention", "уровень", "risk"},
        "trend": {"тренд", "trend"},
        "data_status": {"статусданных", "datastatus"},
        "evidence": {"evidence", "источник", "source"},
        "owner": {"owner", "ответственный"},
        "next_action": {"следующеедействие", "nextaction", "пландействий", "action"},
        "comments": {"комментарий", "comments", "анализпричины"},
    }
    for idx, row in enumerate(rows[:12]):
        normalized = [norm(cell) for cell in row]
        if not any(cell in aliases["metric"] for cell in normalized):
            continue
        mapping: dict[str, int] = {}
        for key, names in aliases.items():
            for col, cell in enumerate(normalized):
                if cell in names:
                    mapping[key] = col
                    break
        if "metric" in mapping:
            return idx, mapping
    return None


def get(row: list[str], mapping: dict[str, int], key: str) -> str:
    idx = mapping.get(key)
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


def metadata_value(rows: list[list[str]], *labels: str) -> str:
    wanted = {norm(label) for label in labels}
    for row in rows[:8]:
        if len(row) >= 2 and norm(row[0]) in wanted:
            return row[1].strip()
    return ""


def rows_from_metric_csv(rows: list[list[str]]) -> list[dict[str, str]]:
    header = find_header(rows)
    if not header:
        return []
    header_idx, mapping = header
    output = []
    for row in rows[header_idx + 1 :]:
        non_empty = [cell for cell in row if cell.strip()]
        if not non_empty:
            continue
        if len(non_empty) == 1:
            # A lone populated cell marks the start of the next narrative
            # section (e.g. "Data gaps", "Stream metrics baseline") rather
            # than another row of this table, so the scorecard ends here.
            break
        metric = get(row, mapping, "metric")
        if not metric:
            continue
        output.append(
            {
                "metric": metric,
                "indicator": get(row, mapping, "indicator"),
                "attention": get(row, mapping, "attention"),
                "trend": get(row, mapping, "trend"),
                "data_status": get(row, mapping, "data_status") or "Есть данные",
                "evidence": get(row, mapping, "evidence"),
                "owner": get(row, mapping, "owner"),
                "next_action": get(row, mapping, "next_action"),
                "comments": get(row, mapping, "comments"),
            }
        )
    return output


def read_manifest(extract_root: Path) -> list[dict[str, str]]:
    with (extract_root / "manifest.csv").open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_markdown(text: str) -> str:
    lines = []
    in_frontmatter = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if stripped.startswith("source_file:") or stripped.startswith("document_role:") or stripped.startswith("extracted_at:"):
            continue
        lines.append(line)
    return "\n".join(lines)


def period_from_text(text: str, default: str) -> str:
    match = re.search(r"(20\d{2}[-.]\d{2}[-.]\d{2}|\d{2}\.\d{2}\.\d{4})", text)
    return match.group(1) if match else default


def extract_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = defaultdict(list)
    current = "intro"
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line or line == "---" or line.startswith("source_file:") or line.startswith("document_role:"):
            continue
        if line.startswith("#"):
            current = line.lstrip("#").strip().casefold()
            continue
        sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def section_contains(sections: dict[str, str], *needles: str) -> str:
    for title, body in sections.items():
        if any(needle.casefold() in title for needle in needles):
            return body
    return ""


def bullet_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        cleaned = re.sub(r"^[-•]\s*", "", line.strip())
        if cleaned:
            items.append(cleaned)
    return items


def first_heading_person(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("## ") and " - " in line:
            return line[3:].split(" - ", 1)[0].strip(" >")
    name = re.sub(r"^(План развития|Метрики)\s+", "", fallback, flags=re.IGNORECASE).strip()
    return name


def review_value(markdown: str, label: str) -> str:
    pattern = re.compile(rf"{re.escape(label)}\s*:?\s*([^|\n]+)", re.IGNORECASE)
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def source_label(row: dict[str, str]) -> str:
    return row["source_file"]


def generate_metrics(
    extract_root: Path,
    rows: list[dict[str, str]],
    role: str,
    snapshot_date: str,
) -> dict[str, list[list[str]]]:
    outputs: dict[str, list[list[str]]] = defaultdict(list)
    for item in rows:
        if item["document_role"] != role or item["status"] != "ok":
            continue
        project = item["project"]
        extract_file = extract_root / item["extract_file"]
        metric_rows: list[dict[str, str]] = []
        person = ""
        role_stream = ""

        if extract_file.suffix == ".json":
            workbook = read_json(extract_file)
            for sheet in workbook.get("sheets", []):
                csv_path = extract_file.parent / sheet["csv_file"]
                sheet_rows = read_csv(csv_path)
                person = person or metadata_value(sheet_rows, "Сотрудник")
                role_stream = role_stream or metadata_value(sheet_rows, "Stream", "Роль")
                for metric in rows_from_metric_csv(sheet_rows):
                    metric["evidence"] = metric["evidence"] or f"{source_label(item)} / {sheet['sheet_name']}"
                    metric_rows.append(metric)
        elif extract_file.suffix == ".md":
            text = clean_markdown(extract_file.read_text(encoding="utf-8"))
            sections = extract_sections(text)
            # Scope to the Scorecard section only, matching the XLSX branch's
            # scorecard-boundary behavior. Without this, any "- label: value"
            # bullet anywhere in the document gets treated as a metric,
            # including data-gap notes and source citations that happen to
            # contain a colon.
            scorecard_text = section_contains(sections, "scorecard")
            for line in scorecard_text.splitlines():
                stripped = line.strip()
                if not stripped.startswith("- ") or ":" not in stripped:
                    continue
                name, rest = stripped[2:].split(":", 1)
                rest = rest.strip()
                next_action_match = re.search(r"Следующее действие\s*:\s*(.+)$", rest, flags=re.IGNORECASE)
                next_action = ""
                if next_action_match:
                    next_action = next_action_match.group(1).strip().rstrip(".")
                    rest = rest[: next_action_match.start()].strip(" .;")
                evidence_match = re.search(r"Evidence\s*:\s*(.+)$", rest, flags=re.IGNORECASE)
                evidence_text = ""
                if evidence_match:
                    evidence_text = evidence_match.group(1).strip().rstrip(".")
                    rest = rest[: evidence_match.start()].strip(" .;")
                metric_rows.append(
                    {
                        "metric": name.strip(),
                        "indicator": compact(rest, 220),
                        "attention": "",
                        "trend": "",
                        "data_status": "Есть данные",
                        "evidence": compact(evidence_text, 220) or source_label(item),
                        "owner": "",
                        "next_action": compact(next_action, 220),
                        "comments": "",
                    }
                )
            person = first_heading_person(text, Path(item["source_file"]).stem)

        if not metric_rows:
            continue

        if role == "project_metrics":
            key = project
            for metric in metric_rows:
                outputs[key].append(
                    [
                        project,
                        snapshot_date,
                        metric["metric"],
                        metric["indicator"],
                        metric["attention"] or "Unknown",
                        metric["trend"],
                        metric["data_status"] or "Есть данные",
                        metric["evidence"],
                        metric["owner"],
                        metric["next_action"],
                        metric["comments"],
                    ]
                )
        else:
            person = person or re.sub(r"^Метрики\s+", "", Path(item["source_file"]).stem, flags=re.IGNORECASE)
            key = f"{project}__{person}"
            for metric in metric_rows:
                outputs[key].append(
                    [
                        project,
                        person,
                        snapshot_date,
                        role_stream,
                        metric["metric"],
                        metric["indicator"],
                        metric["evidence"],
                        metric["trend"],
                    ]
                )
    return outputs


def generate_project_plans(extract_root: Path, rows: list[dict[str, str]], snapshot_date: str) -> dict[str, list[list[str]]]:
    outputs: dict[str, list[list[str]]] = defaultdict(list)
    for item in rows:
        if item["document_role"] != "project_development_plan" or item["status"] != "ok":
            continue
        path = extract_root / item["extract_file"]
        text = clean_markdown(path.read_text(encoding="utf-8"))
        sections = extract_sections(text)
        summary = compact(section_contains(sections, "краткое резюме", "резюме"), 700)
        current = compact(section_contains(sections, "текущее состояние", "контекст"), 700)
        focus_text = (
            section_contains(sections, "фокус", "инициатив")
            or section_contains(sections, "план", "следующие шаги")
            or current
        )
        focus_items = bullet_items(focus_text)[:12] or [compact(focus_text, 500) or summary]
        review_cycle = review_value(text, "Review cycle")
        next_review = review_value(text, "Следующий review")
        for index, focus in enumerate(focus_items):
            outputs[item["project"]].append(
                [
                    item["project"],
                    snapshot_date,
                    review_cycle,
                    summary if index == 0 else "",
                    current if index == 0 else "",
                    compact(focus, 450),
                    "",
                    compact(focus, 450),
                    "",
                    "",
                    "",
                    "",
                    next_review,
                    source_label(item),
                ]
            )
    return outputs


def generate_individual_plans(extract_root: Path, rows: list[dict[str, str]], snapshot_date: str) -> dict[str, list[list[str]]]:
    outputs: dict[str, list[list[str]]] = defaultdict(list)
    for item in rows:
        if item["document_role"] != "individual_development_plan" or item["status"] != "ok":
            continue
        path = extract_root / item["extract_file"]
        text = clean_markdown(path.read_text(encoding="utf-8"))
        sections = extract_sections(text)
        person = first_heading_person(text, Path(item["source_file"]).stem)
        goal = compact(section_contains(sections, "цель"), 700)
        focus_text = section_contains(sections, "фокус развития", "фокус") or section_contains(sections, "сильные стороны")
        focus_items = bullet_items(focus_text)[:12] or [compact(focus_text, 500) or goal]
        progress = compact(section_contains(sections, "текущий прогресс", "прогресс"), 500)
        review_cycle = review_value(text, "Review cycle")
        next_review = review_value(text, "Следующий review")
        stream = review_value(text, "Stream")
        key = f"{item['project']}__{person}"
        for index, focus in enumerate(focus_items):
            outputs[key].append(
                [
                    item["project"],
                    person,
                    stream,
                    snapshot_date,
                    review_cycle,
                    goal if index == 0 else "",
                    compact(focus, 450),
                    "",
                    compact(focus, 450),
                    "",
                    "",
                    "",
                    progress if index == 0 else "",
                    next_review,
                    source_label(item),
                ]
            )
    return outputs


def risk_level(text: str) -> str:
    lower = text.casefold()
    critical_patterns = (
        "critical risk",
        "risk: critical",
        "критический риск",
        "критичный риск",
        "уровень риска: critical",
    )
    if any(pattern in lower for pattern in critical_patterns):
        return "Critical"
    if (
        "high risk" in lower
        or "high-risk" in lower
        or "high operational risk" in lower
        or "высоким operational risk" in lower
        or "высокий operational risk" in lower
        or "риск остается высоким" in lower
        or "at risk" in lower
    ):
        return "High"
    if "medium" in lower or "средн" in lower:
        return "Medium"
    if "low risk" in lower or "низкий риск" in lower:
        return "Low"
    return "Unknown"


def sentences_with(text: str, *keywords: str) -> str:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    found = []
    for chunk in chunks:
        cleaned = chunk.strip("- • #>| ")
        if len(cleaned) < 12:
            continue
        if any(k.casefold() in cleaned.casefold() for k in keywords):
            found.append(cleaned)
    return compact(" ".join(found[:4]), 700)


def generate_project_risk(extract_root: Path, rows: list[dict[str, str]], snapshot_date: str) -> list[list[str]]:
    by_project: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in rows:
        if item["status"] == "ok" and item["document_role"] in {
            "project_risk",
            "project_summary",
            "project_development_plan",
            "project_metrics",
        }:
            by_project[item["project"]].append(item)

    output = []
    for project, items in sorted(by_project.items()):
        md_items = [row for row in items if (extract_root / row["extract_file"]).suffix == ".md"]
        selected = sorted(
            md_items,
            key=lambda row: {
                "project_risk": 0,
                "project_summary": 1,
                "project_development_plan": 2,
            }.get(row["document_role"], 9),
        )[:3]
        texts = []
        for item in selected:
            path = extract_root / item["extract_file"]
            if path.suffix == ".md":
                texts.append(clean_markdown(path.read_text(encoding="utf-8")))
        combined = "\n".join(texts)
        output.append(
            [
                project,
                snapshot_date,
                risk_level(combined),
                sentences_with(combined, "delivery", "релиз", "release", "scope", "срок"),
                sentences_with(combined, "qa", "test", "regression", "automation", "traceability", "документ"),
                sentences_with(combined, "staff", "lead", "continuity", "отпуск", "увольн", "overlap", "ставк"),
                sentences_with(combined, "client", "customer", "клиент", "communication", "коммуникац"),
                compact(sentences_with(combined, "риск", "risk", "blocker", "gap"), 700),
                compact(sentences_with(combined, "action", "действ", "следующ", "минимум", "план"), 700),
                "",
                review_value(combined, "Следующий review"),
            ]
        )
    return output


def main() -> int:
    args = parse_args()
    extract_root = Path(args.extract_root)
    output_root = Path(args.output_root)
    if not (extract_root / "manifest.csv").exists():
        raise SystemExit(f"Missing manifest.csv under {extract_root}")
    if output_root.exists() and any(output_root.iterdir()) and not args.overwrite:
        raise SystemExit(f"Output folder is not empty; pass --overwrite: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    manifest = read_manifest(extract_root)

    write_csv(
        output_root / "project_risk" / f"светофор_рисков_проекта_{args.snapshot_date}.csv",
        PROJECT_RISK_HEADER,
        generate_project_risk(extract_root, manifest, args.snapshot_date),
    )

    for project, rows in generate_metrics(extract_root, manifest, "project_metrics", args.snapshot_date).items():
        write_csv(
            output_root / "project_metrics" / f"метрики_проекта_qa_{safe_name(project)}_{args.snapshot_date}.csv",
            PROJECT_METRICS_HEADER,
            rows,
        )

    for key, rows in generate_metrics(extract_root, manifest, "individual_metrics", args.snapshot_date).items():
        project, person = key.split("__", 1)
        write_csv(
            output_root / "individual_metrics" / f"метрики_qa_{safe_name(project)}_{safe_name(person)}_{args.snapshot_date}.csv",
            INDIVIDUAL_METRICS_HEADER,
            rows,
        )

    for project, rows in generate_project_plans(extract_root, manifest, args.snapshot_date).items():
        write_csv(
            output_root / "project_development_plans" / f"план_развития_проекта_{safe_name(project)}_{args.snapshot_date}.csv",
            PROJECT_PLAN_HEADER,
            rows,
        )

    for key, rows in generate_individual_plans(extract_root, manifest, args.snapshot_date).items():
        project, person = key.split("__", 1)
        write_csv(
            output_root / "individual_development_plans" / f"план_развития_qa_{safe_name(project)}_{safe_name(person)}_{args.snapshot_date}.csv",
            INDIVIDUAL_PLAN_HEADER,
            rows,
        )

    count = len([path for path in output_root.rglob("*.csv")])
    print(f"Generated {count} M2 CSV files into {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
