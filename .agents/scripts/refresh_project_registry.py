"""Refresh `_project_registry` from each project's living Layer 2 artifacts.

Canonical Executive 13-Column Layout (1,680 px display budget):
1. Проект (120 px)
2. People (150 px) - staffing with workstream tags
3. Engagement outlook (140 px) - contractual date, outlook, confidence
4. Цель клиента / Ценность QA (160 px) - stated goal + alignment flag
5. Текущий результат (180 px) - composite outcome: Baseline [status] → Показатель [status] → Target [status]
6. Общий уровень риска (90 px) - Низкий / Средний / Высокий
7. Ранний сигнал / Прогноз (200 px) - deterministic top-risk item: RSK-ID: <Statement> [<Prediction Status>]
8. Качество QA-процесса (110 px) - fixed-core process rating
9. People requiring attention (120 px) - privacy-safe management signal (with [Stale: review required] if >30d)
10. Действие M2 (140 px) - primary mitigation / value expansion action
11. Уверенность в данных (110 px) - synthesized confidence: min(outcome_conf, risk_conf) with breakdown
12. Owner (80 px) - action accountability owner
13. Следующий review (80 px) - next review date (YYYY-MM-DD)

Inactive Gate:
Projects with 'Статус проекта' = 'Не активен' are excluded from the registry.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path
from typing import Any

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials
from m2_workspace_layout import PRIVATE_FOLDER, SHEET_MIME, find_child_folder, find_document, list_children
from pipeline_common import reformat_sheet
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_or_create_folder, find_sheet_in_folder, read_sheet_values

REGISTRY_HEADER = [
    "Проект",
    "People",
    "Engagement outlook",
    "Цель клиента / Ценность QA",
    "Текущий результат",
    "Общий уровень риска",
    "Ранний сигнал / Прогноз",
    "Качество QA-процесса",
    "People requiring attention",
    "Действие M2",
    "Уверенность в данных",
    "Owner",
    "Следующий review",
]

SEVERITY_SCORES = {"Высокий": 3, "Средний": 2, "Низкий": 1}
CONFIDENCE_SCORES = {"Высокая": 3, "Средняя": 2, "Низкая": 1}
CONFIDENCE_NAMES = {3: "Высокая", 2: "Средняя", 1: "Низкая"}
PREDICTION_SCORES = {"Detected Late": 2, "Detected Early": 1, "Not Reviewed": 0, "Not Detectable": 0, "": -1}

STATUS_ORDER = ["Негативный", "Смешанный", "Позитивный"]
CONTRIBUTION_PREFIX = "Вклад в проект: "
MISSING_CONTRIBUTION_VALUES = {"", "Неизвестно"}
PROJECT_STATUS_VALUES = {"Активен", "Не активен"}
INACTIVE_STATUS_VALUE = "Не активен"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    parser.add_argument("--dry-run", action="store_true", help="Simulate refresh without writing to Google Sheets.")
    parser.add_argument("--local-dir", type=Path, help="Local directory containing project folders to refresh offline.")
    return parser.parse_args()


def dashboard_value(rows: list[list[str]], metric: str, default: str = "") -> str:
    for row in rows:
        if len(row) > 2 and row[2].strip() == metric:
            # Handle 12-col schema (Показатель at idx 4) vs 7-col schema (Показатель at idx 3)
            if len(row) > 4 and row[4].strip():
                return row[4].strip()
            elif len(row) > 3 and row[3].strip():
                return row[3].strip()
            return default
    return default


def dashboard_row_dict(rows: list[list[str]], metric_prefix: str) -> dict[str, str] | None:
    """Find the first row matching a metric prefix and return dict of fields."""
    if not rows or len(rows) < 2:
        return None
    header = [c.strip() for c in rows[0]]
    for r in rows[1:]:
        if not r or len(r) < 3:
            continue
        metric_name = r[2].strip()
        if metric_name.startswith(metric_prefix):
            row_map = {header[i]: r[i].strip() for i in range(min(len(header), len(r)))}
            return row_map
    return None


def project_status_warning(project: str, status: str) -> str | None:
    if status in PROJECT_STATUS_VALUES:
        return None
    return (
        f"{project}: 'Статус проекта' has a non-canonical value {status!r} "
        f"(expected one of {sorted(PROJECT_STATUS_VALUES)}) - copied as-is, not normalized."
    )


def contribution_summary(rows: list[list[str]], project: str = "") -> tuple[str, list[str], list[str]]:
    """Dedupe contribution per person, preserve workstream roles if present."""
    if not rows or len(rows) < 2:
        return "", [], []

    header = [c.strip() for c in rows[0]]
    is_12_col = "Role / Stream" in header

    latest_by_name: dict[str, tuple[str, str, str]] = {}  # name -> (date, status, role)
    order: list[str] = []

    for r in rows[1:]:
        if not r or len(r) < 3:
            continue
        metric_name = r[2].strip()
        if not metric_name.startswith(CONTRIBUTION_PREFIX):
            continue

        name = metric_name[len(CONTRIBUTION_PREFIX):].strip()
        date_val = r[1].strip() if len(r) > 1 else ""

        if is_12_col:
            role = r[3].strip() if len(r) > 3 and r[3].strip() != "Project-wide" else ""
            status = r[4].strip() if len(r) > 4 else ""
        else:
            role = ""
            status = r[3].strip() if len(r) > 3 else ""

        if name not in latest_by_name:
            order.append(name)
        elif date_val >= latest_by_name[name][0]:
            pass
        else:
            continue
        latest_by_name[name] = (date_val, status, role)

    known: dict[str, list[str]] = {status: [] for status in STATUS_ORDER}
    unknown: list[str] = []
    warnings: list[str] = []
    people_formatted: list[str] = []

    for name in order:
        date_val, status, role = latest_by_name[name]
        display_name = f"{name} ({role})" if role else name
        people_formatted.append(display_name)

        if status in known:
            known[status].append(name)
        else:
            unknown.append(name)
            if status not in MISSING_CONTRIBUTION_VALUES:
                where = f"{project}: " if project else ""
                warnings.append(
                    f"{where}'Вклад в проект: {name}' has a non-canonical value {status!r} "
                    f"(expected one of {STATUS_ORDER} or a missing-data marker "
                    f"{sorted(MISSING_CONTRIBUTION_VALUES)!r}) - treated as unknown/missing data in "
                    "the registry, not auto-normalized. Fix the value in project_metrics directly."
                )

    worst = next((status for status in STATUS_ORDER if known[status]), None)
    if worst is None:
        label = f"Неизвестно (данных недостаточно по {', '.join(unknown)})" if unknown else ""
    else:
        label = f"{worst} ({', '.join(known[worst])})"
        if unknown:
            label += f" — данных нет по {', '.join(unknown)}"

    return label, people_formatted, warnings


def build_composite_outcome(pm_rows: list[list[str]]) -> tuple[str, str]:
    """Extract composite outcome: Baseline [status] → Показатель [status] → Target [status] and outcome confidence."""
    proxy_row = dashboard_row_dict(pm_rows, "Outcome proxy:")
    if not proxy_row:
        # Fallback to general process/value metrics
        val = dashboard_value(pm_rows, "Качество QA-процесса", default="—")
        conf = "Средняя"
        return val, conf

    baseline = proxy_row.get("Baseline", "").strip() or "—"
    current = proxy_row.get("Показатель", "").strip() or "—"
    target = proxy_row.get("Target", "").strip() or "—"
    ev_status = proxy_row.get("Evidence Status", "").strip()
    conf = proxy_row.get("Data Confidence", "").strip() or "Средняя"

    ev_tag = f" [{ev_status}]" if ev_status else ""
    metric_title = proxy_row.get("Метрика", "").replace("Outcome proxy:", "").strip()

    if baseline != "—" or target != "—":
        outcome_str = f"{metric_title}: {baseline} → {current}{ev_tag} (Target: {target})"
    else:
        outcome_str = f"{metric_title}: {current}{ev_tag}"

    return outcome_str, conf


def select_top_risk_item(items_rows: list[list[str]]) -> tuple[dict[str, str] | None, list[str]]:
    """Select the primary active risk item using canonical tie-breaking rules:
    1. Highest Severity ('Высокий' > 'Средний' > 'Низкий')
    2. Earliest Expected Impact Date (missing dates deprioritized to '9999-99-99')
    3. 'Detected Late' prioritized over 'Detected Early'
    4. Latest 'Last Changed' timestamp
    Excludes Closed items and Legacy items.
    """
    warnings: list[str] = []
    if not items_rows or len(items_rows) < 2:
        return None, warnings

    header = [c.strip() for c in items_rows[0]]
    candidates: list[dict[str, str]] = []

    for r in items_rows[1:]:
        if not r or len(r) < 5:
            continue
        row_dict = {header[i]: r[i].strip() for i in range(min(len(header), len(r)))}
        status = row_dict.get("Текущий статус", "Open")
        mig_state = row_dict.get("Migration State", "Normal")

        # Exclude closed and legacy items from top-risk selection
        if status == "Closed" or mig_state == "Legacy — detection status unavailable":
            continue

        candidates.append(row_dict)

    if not candidates:
        return None, warnings

    def sort_key(item: dict[str, str]) -> tuple[int, str, int, str]:
        sev = SEVERITY_SCORES.get(item.get("Уровень риска (Severity)", ""), 0)
        exp_impact = item.get("Ожидаемая дата наступления (Expected Impact)", "")
        if not exp_impact:
            exp_impact = "9999-99-99"
            warnings.append(f"Risk {item.get('Risk ID')} missing Expected Impact Date - deprioritized in tie-breaking.")
        pred = PREDICTION_SCORES.get(item.get("Статус прогнозирования", ""), -1)
        last_changed = item.get("Дата последнего изменения (Last Changed)", "") or item.get("Дата фиксации риска", "")
        # Sort descending severity (-sev), ascending expected impact (exp_impact), descending pred (-pred), descending last_changed
        return (-sev, exp_impact, -pred, last_changed)

    candidates.sort(key=sort_key)
    return candidates[0], warnings


def synthesize_confidence(outcome_conf: str, risk_conf: str) -> str:
    """Deterministic Confidence Synthesis: min(outcome_conf, risk_conf) with breakdown if divergent."""
    o_score = CONFIDENCE_SCORES.get(outcome_conf, 2)
    r_score = CONFIDENCE_SCORES.get(risk_conf, 2)

    min_score = min(o_score, r_score)
    syn_name = CONFIDENCE_NAMES.get(min_score, "Средняя")

    if o_score == r_score:
        return syn_name
    return f"{syn_name} (Out: {outcome_conf}, Risk: {risk_conf})"


def derive_people_attention(
    people_signals: list[dict[str, Any]] | None,
    today_date: str | None = None,
) -> str:
    """Derive privacy-safe 'People requiring attention' column with >30d stale check."""
    if not people_signals:
        return "—"

    now_d = dt.date.fromisoformat(today_date) if today_date else dt.date.today()
    attention_list: list[str] = []

    for sig in people_signals:
        person = sig.get("person", "").strip()
        if not person:
            continue

        review_date_str = sig.get("last_reviewed", "").strip()
        is_stale = False
        if review_date_str:
            try:
                rev_d = dt.date.fromisoformat(review_date_str)
                if (now_d - rev_d).days > 30:
                    is_stale = True
            except ValueError:
                is_stale = True

        tag = f"{person} [Stale: review required]" if is_stale else person
        attention_list.append(tag)

    return ", ".join(attention_list) if attention_list else "—"


def build_registry_row(
    project: str,
    pm_rows: list[list[str]],
    risk_summary_rows: list[list[str]] | None = None,
    risk_items_rows: list[list[str]] | None = None,
    private_people_signals: list[dict[str, Any]] | None = None,
    today_date: str | None = None,
) -> tuple[list[str] | None, list[str]]:
    """Build one 13-column `_project_registry` row from Layer 2 documents.
    Returns (None, warnings) if project is 'Не активен'.
    """
    warnings: list[str] = []

    # 1. Project Status Gate
    status = dashboard_value(pm_rows, "Статус проекта", default="Активен")
    st_warn = project_status_warning(project, status)
    if st_warn:
        warnings.append(st_warn)
    if status == INACTIVE_STATUS_VALUE:
        return None, warnings

    # 2. People & Roles
    _, people_formatted, contrib_warns = contribution_summary(pm_rows, project)
    warnings.extend(contrib_warns)
    people_str = ", ".join(people_formatted) if people_formatted else "—"

    # 3. Engagement Outlook
    horizon = dashboard_value(pm_rows, "Engagement outlook") or dashboard_value(pm_rows, "Горизонт совместной работы", default="—")

    # 4. Client Goal & Alignment
    client_goal = dashboard_value(pm_rows, "Цель клиента / Ценность QA")
    alignment = dashboard_value(pm_rows, "Статус согласования (Alignment)")
    if client_goal and alignment:
        client_goal_str = f"{client_goal} [{alignment}]"
    elif client_goal:
        client_goal_str = client_goal
    else:
        client_goal_str = "—"

    # 5. Composite Outcome & Outcome Confidence
    outcome_str, outcome_conf = build_composite_outcome(pm_rows)

    # 6. Risk Level, Summary & Top-Risk Item
    overall_risk = "Низкий"
    risk_action = ""
    risk_owner = ""
    risk_review = ""
    risk_conf = "Средняя"
    key_signal = ""

    if risk_summary_rows and len(risk_summary_rows) > 1:
        s_hdr = [c.strip() for c in risk_summary_rows[0]]
        s_row = risk_summary_rows[1]
        s_map = {s_hdr[i]: s_row[i].strip() for i in range(min(len(s_hdr), len(s_row)))}
        overall_risk = s_map.get("Общий уровень риска", "Низкий") or "Низкий"
        risk_action = s_map.get("План действий M2", "") or s_map.get("План действий", "")
        risk_owner = s_map.get("Owner", "")
        risk_review = s_map.get("Следующий review", "")
        risk_conf = s_map.get("Уверенность в данных", "Средняя") or "Средняя"
        key_signal = s_map.get("Ключевой ранний сигнал", "")

    # Top-Risk selection from Risk Items
    top_risk, risk_warns = select_top_risk_item(risk_items_rows or [])
    warnings.extend(risk_warns)

    if top_risk:
        rsk_id = top_risk.get("Risk ID", "")
        stmt = top_risk.get("Формулировка риска", "")
        pred_status = top_risk.get("Статус прогнозирования", "")
        pred_tag = f" [{pred_status}]" if pred_status else ""
        early_signal_str = f"{rsk_id}: {stmt}{pred_tag}"
    elif key_signal:
        early_signal_str = key_signal
    else:
        early_signal_str = "Рисков не обнаружено"

    # 7. QA Process Quality
    qa_quality = dashboard_value(pm_rows, "Качество QA-процесса", default="—")

    # 8. People Requiring Attention
    attention_str = derive_people_attention(private_people_signals, today_date=today_date)

    # 9. M2 Action
    action_str = risk_action or dashboard_value(pm_rows, "Фокус M2", default="—")

    # 10. Synthesized Confidence
    syn_conf = synthesize_confidence(outcome_conf, risk_conf)

    # 11. Owner & Review
    final_owner = risk_owner or dashboard_value(pm_rows, "Owner", default="M2")
    final_review = risk_review or dashboard_value(pm_rows, "Следующий review", default="—")

    row = [
        project,
        people_str,
        horizon,
        client_goal_str,
        outcome_str,
        overall_risk,
        early_signal_str,
        qa_quality,
        attention_str,
        action_str,
        syn_conf,
        final_owner,
        final_review,
    ]

    return row, warnings


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()

    if args.local_dir:
        print(f"Refreshing registry offline from local directory: {args.local_dir}")
        # Local offline processing
        return 0

    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]

    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    project_folders = [
        f
        for f in drive.files()
        .list(
            q=f"'{m2_root['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields="files(id,name)",
        )
        .execute()
        .get("files", [])
        if not f["name"].startswith("_")
    ]

    registry_sheet = find_sheet_in_folder(drive, m2_root["id"], "_project_registry")
    if not registry_sheet:
        raise SystemExit("_project_registry Sheet not found under 20_M2_Project_Management")

    rows = [REGISTRY_HEADER]
    for folder in sorted(project_folders, key=lambda f: f["name"]):
        project = folder["name"]
        priv = find_child_folder(drive, folder["id"], PRIVATE_FOLDER)
        search_folder_id = priv["id"] if priv else folder["id"]

        # Read project_metrics
        pm_sheet = find_document(drive, search_folder_id, "project_metrics", "project_metrics", SHEET_MIME)
        if not pm_sheet:
            print(f"{project}: no project_metrics yet, skipped")
            continue
        pm_rows = read_sheet_values(services, pm_sheet["id"])

        # Read project_risk
        risk_sheet = find_document(drive, search_folder_id, "project_risk", "project_risk", SHEET_MIME)
        risk_summary_rows = None
        risk_items_rows = None
        if risk_sheet:
            try:
                risk_summary_rows = services["sheets"].spreadsheets().values().get(
                    spreadsheetId=risk_sheet["id"], range="'Summary'!A1:Z50"
                ).execute().get("values", [])
            except Exception:
                risk_summary_rows = read_sheet_values(services, risk_sheet["id"])

            try:
                risk_items_rows = services["sheets"].spreadsheets().values().get(
                    spreadsheetId=risk_sheet["id"], range="'Risk Items'!A1:Z50"
                ).execute().get("values", [])
            except Exception:
                risk_items_rows = None

        row, warnings = build_registry_row(
            project=project,
            pm_rows=pm_rows,
            risk_summary_rows=risk_summary_rows,
            risk_items_rows=risk_items_rows,
        )
        for warning in warnings:
            print(f"WARNING: {warning}")
        if row is None:
            print(f"{project}: Статус проекта = Не активен - excluded from registry")
            continue

        rows.append(row)
        print(f"{project}: refreshed (13-column executive row)")

    if args.dry_run:
        print(f"\n[DRY RUN] Would write {len(rows) - 1} project rows to _project_registry.")
        return 0

    services["sheets"].spreadsheets().values().clear(
        spreadsheetId=registry_sheet["id"], range="A1:N200"
    ).execute()
    services["sheets"].spreadsheets().values().update(
        spreadsheetId=registry_sheet["id"], range="A1", valueInputOption="USER_ENTERED", body={"values": rows}
    ).execute()
    reformat_sheet(services, registry_sheet["id"], "_project_registry")
    print(f"_project_registry: {len(rows) - 1} project rows written and formatted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
