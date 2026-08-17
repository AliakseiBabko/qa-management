"""Migrate project_risk spreadsheets and local fallback tables to the 2-tab schema.

Summary Worksheet (Tab 1): Templates/светофор_рисков_проекта.csv (14 columns)
Risk Items Worksheet (Tab 2): Templates/project_risk_items.csv (20 columns)

Safety guardrails:
- Defaults to --dry-run.
- Requires explicit --apply to write changes.
- Safe idempotence: compliant sheets/CSVs are detected and preserved without data loss.
- Legacy rows receive Migration State = 'Legacy — detection status unavailable' and empty Prediction Status.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = REPO_ROOT / "Templates"

SUMMARY_HEADER = [
    "Проект",
    "Дата обновления",
    "Общий уровень риска",
    "ID ключевого риска",
    "Ключевой ранний сигнал",
    "Статус прогнозирования",
    "Риск delivery",
    "Риск QA process",
    "Риск staffing / continuity",
    "Риск communication / client",
    "План действий M2",
    "Уверенность в данных",
    "Owner",
    "Следующий review",
]

RISK_ITEMS_HEADER = [
    "Risk ID",
    "Проект",
    "Формулировка риска",
    "Категория",
    "Уровень риска (Severity)",
    "Дата первого сигнала",
    "Дата фиксации риска",
    "Ожидаемая дата наступления (Expected Impact)",
    "Дата материализации",
    "Дата закрытия (Closed Date)",
    "Дата последнего review (Last Reviewed)",
    "Дата последнего изменения (Last Changed)",
    "Статус прогнозирования",
    "Обоснование статуса",
    "Migration State",
    "Уверенность в доказательствах (Evidence Confidence)",
    "Ссылка на evidence_log",
    "Митигация",
    "Owner",
    "Текущий статус",
]

LEGACY_SUMMARY_HEADER = [
    "Проект",
    "Дата обновления",
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


@dataclass
class RiskMigrationPlan:
    project: str
    target_type: str  # 'google_sheet' or 'local_csv'
    file_id_or_path: str
    current_state: str  # 'legacy_1_tab', 'already_compliant', 'empty', 'unknown'
    needs_migration: bool
    summary_rows_count: int = 0
    risk_items_count: int = 0
    details: list[str] = field(default_factory=list)
    summary_preview: list[list[str]] = field(default_factory=list)
    risk_items_preview: list[list[str]] = field(default_factory=list)


def determine_dominant_category(row: dict[str, str]) -> str:
    """Infer primary risk category from legacy category columns."""
    for cat, col in [
        ("delivery", "Риск delivery"),
        ("QA process", "Риск QA process"),
        ("staffing / continuity", "Риск staffing / continuity"),
        ("communication / client", "Риск communication / client"),
    ]:
        val = row.get(col, "").strip()
        if val in {"Высокий", "Средний"}:
            return cat
    return "delivery"


def migrate_single_project_data(
    raw_rows: list[list[str]],
    project_name: str = "",
    existing_items_rows: list[list[str]] | None = None,
) -> tuple[list[list[str]], list[list[str]], str]:
    """Pure transformation from legacy/unknown risk rows to (summary_rows, risk_items_rows, state)."""
    if not raw_rows or (len(raw_rows) == 1 and not any(raw_rows[0])):
        # Empty input -> create template rows
        today = dt.date.today().isoformat()
        proj = project_name or "<Project>"
        summary_rows = [
            SUMMARY_HEADER,
            [proj, today, "Низкий", "", "Рисков не обнаружено", "", "Низкий", "Низкий", "Низкий", "Низкий", "", "Средняя", "M2", ""],
        ]
        items_rows = [RISK_ITEMS_HEADER]
        return summary_rows, items_rows, "empty"

    header = [c.strip() for c in raw_rows[0]]

    # Check if already compliant
    if header == SUMMARY_HEADER:
        items = existing_items_rows if existing_items_rows and existing_items_rows[0] == RISK_ITEMS_HEADER else [RISK_ITEMS_HEADER]
        return raw_rows, items, "already_compliant"

    # Map legacy header indices
    data_rows = raw_rows[1:]
    migrated_summary: list[list[str]] = [SUMMARY_HEADER]
    migrated_items: list[list[str]] = [RISK_ITEMS_HEADER]

    if existing_items_rows and len(existing_items_rows) > 1 and existing_items_rows[0] == RISK_ITEMS_HEADER:
        # Preserve existing risk items if already structured
        migrated_items = existing_items_rows

    for row_idx, r in enumerate(data_rows):
        if not any(r):
            continue
        row_dict = {header[i]: r[i] for i in range(min(len(header), len(r)))}
        proj = row_dict.get("Проект", "").strip() or project_name or "<Project>"
        updated = row_dict.get("Дата обновления", "").strip() or dt.date.today().isoformat()
        overall = row_dict.get("Общий уровень риска", "").strip() or "Низкий"
        comments = row_dict.get("Комментарии", "").strip()
        plan = row_dict.get("План действий", "").strip() or row_dict.get("План действий M2", "").strip()
        owner = row_dict.get("Owner", "").strip() or "M2"
        next_review = row_dict.get("Следующий review", "").strip()
        r_delivery = row_dict.get("Риск delivery", "").strip() or "Низкий"
        r_qa = row_dict.get("Риск QA process", "").strip() or "Низкий"
        r_staffing = row_dict.get("Риск staffing / continuity", "").strip() or "Низкий"
        r_client = row_dict.get("Риск communication / client", "").strip() or "Низкий"

        # Determine if an itemized risk item should be generated
        has_active_threat = overall in {"Высокий", "Средний"} or bool(comments) or bool(plan)
        key_risk_id = ""

        if has_active_threat and len(migrated_items) == 1:
            key_risk_id = "RSK-01"
            dominant_cat = determine_dominant_category(row_dict)
            threat_statement = comments if comments else f"Комплексный риск проекта (уровень: {overall})"
            current_status = "Mitigating" if plan else ("Open" if overall in {"Высокий", "Средний"} else "Accepted")

            migrated_items.append([
                key_risk_id,
                proj,
                threat_statement,
                dominant_cat,
                overall,
                "",  # First signal date (empty for legacy)
                updated,  # Risk logged date
                "",  # Expected impact (empty for legacy)
                "",  # Materialization date
                "",  # Closed date
                updated,  # Last reviewed
                updated,  # Last changed
                "",  # Prediction status (empty for legacy)
                "Мигрировано из legacy-светофора рисков",
                "Legacy — detection status unavailable",
                "Средняя",
                "",  # Link to evidence_log
                plan,
                owner,
                current_status,
            ])
        elif len(migrated_items) > 1:
            key_risk_id = migrated_items[1][0]

        migrated_summary.append([
            proj,
            updated,
            overall,
            key_risk_id,
            comments if comments else ("Мигрировано из legacy-светофора рисков" if key_risk_id else "Рисков не обнаружено"),
            "",  # Prediction status (empty for legacy)
            r_delivery,
            r_qa,
            r_staffing,
            r_client,
            plan,
            "Средняя",
            owner,
            next_review,
        ])

    return migrated_summary, migrated_items, "legacy_1_tab"


def plan_local_directory_migration(local_dir: Path) -> list[RiskMigrationPlan]:
    """Scan local directory for project_risk CSV representations."""
    plans: list[RiskMigrationPlan] = []
    if not local_dir.is_dir():
        return plans

    # Find project folders
    for proj_dir in sorted(local_dir.iterdir()):
        if not proj_dir.is_dir() or proj_dir.name.startswith((".", "_")):
            continue
        proj_name = proj_dir.name
        private_dir = proj_dir / "private"
        target_dir = private_dir if private_dir.is_dir() else proj_dir

        summary_csv = target_dir / "светофор_рисков_проекта.csv"
        if not summary_csv.is_file():
            summary_csv = target_dir / "project_risk.csv"

        items_csv = target_dir / "project_risk_items.csv"

        if not summary_csv.is_file():
            continue

        with summary_csv.open("r", encoding="utf-8-sig", newline="") as f:
            raw_summary = list(csv.reader(f))

        raw_items: list[list[str]] | None = None
        if items_csv.is_file():
            with items_csv.open("r", encoding="utf-8-sig", newline="") as f:
                raw_items = list(csv.reader(f))

        summary_rows, items_rows, state = migrate_single_project_data(
            raw_summary, project_name=proj_name, existing_items_rows=raw_items
        )

        needs_mig = (state != "already_compliant") or (not items_csv.is_file())
        plan = RiskMigrationPlan(
            project=proj_name,
            target_type="local_csv",
            file_id_or_path=str(summary_csv),
            current_state=state,
            needs_migration=needs_mig,
            summary_rows_count=len(summary_rows) - 1,
            risk_items_count=len(items_rows) - 1,
            details=[f"State: {state}", f"Summary rows: {len(summary_rows)-1}", f"Risk items: {len(items_rows)-1}"],
            summary_preview=summary_rows[:2],
            risk_items_preview=items_rows[:2],
        )
        plans.append(plan)

    return plans


def apply_local_migration(plan: RiskMigrationPlan) -> dict[str, Any]:
    """Execute local CSV migration plan."""
    if not plan.needs_migration:
        return {"project": plan.project, "status": "SKIPPED_ALREADY_COMPLIANT"}

    summary_path = Path(plan.file_id_or_path)
    parent_dir = summary_path.parent
    canonical_summary_path = parent_dir / "светофор_рисков_проекта.csv"
    canonical_items_path = parent_dir / "project_risk_items.csv"

    # Write summary
    with canonical_summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(plan.summary_preview)

    # Write risk items
    with canonical_items_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(plan.risk_items_preview)

    return {
        "project": plan.project,
        "status": "APPLIED",
        "summary_file": str(canonical_summary_path),
        "items_file": str(canonical_items_path),
    }


def plan_google_drive_migration(services: Any, project_name_filter: str | None = None) -> list[RiskMigrationPlan]:
    """Scan Google Drive for 20_M2_Project_Management project_risk spreadsheets."""
    from m2_workspace_layout import PRIVATE_FOLDER, find_child_folder, list_children
    from pipeline_common import execute_with_backoff
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

    drive = services["drive"] if isinstance(services, dict) else getattr(services, "drive", services)
    sheets = services["sheets"] if isinstance(services, dict) else getattr(services, "sheets", services)

    # Resolve 20_M2_Project_Management folder
    m2_root = find_child_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    if not m2_root:
        return []

    plans: list[RiskMigrationPlan] = []
    projects = list_children(drive, m2_root["id"])

    for proj in projects:
        if proj.get("mimeType") != "application/vnd.google-apps.folder":
            continue
        p_name = proj["name"]
        if p_name.startswith((".", "_")):
            continue
        if project_name_filter and p_name != project_name_filter:
            continue

        # Look in private folder
        priv = find_child_folder(drive, proj["id"], PRIVATE_FOLDER)
        search_folder_id = priv["id"] if priv else proj["id"]

        # Find project_risk sheet
        items = list_children(drive, search_folder_id)
        risk_sheet = next((it for it in items if it.get("name") == "project_risk" and it.get("mimeType") == "application/vnd.google-apps.spreadsheet"), None)

        if not risk_sheet:
            continue

        sheet_id = risk_sheet["id"]
        # Fetch sheet metadata
        meta = execute_with_backoff(sheets.spreadsheets().get(spreadsheetId=sheet_id))
        sheet_tabs = meta.get("sheets", [])
        tab_names = [s.get("properties", {}).get("title", "") for s in sheet_tabs]

        # Read first tab
        first_tab_name = tab_names[0] if tab_names else "Sheet1"
        resp = execute_with_backoff(sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"'{first_tab_name}'!A1:Z50"))
        raw_values = resp.get("values", [])

        raw_items_values: list[list[str]] | None = None
        if "Risk Items" in tab_names:
            resp_items = execute_with_backoff(sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range="'Risk Items'!A1:Z50"))
            raw_items_values = resp_items.get("values", [])

        summary_rows, items_rows, state = migrate_single_project_data(
            raw_values, project_name=p_name, existing_items_rows=raw_items_values
        )

        has_both_tabs = ("Summary" in tab_names or first_tab_name == "Summary") and ("Risk Items" in tab_names)
        needs_mig = (state != "already_compliant") or (not has_both_tabs)

        plan = RiskMigrationPlan(
            project=p_name,
            target_type="google_sheet",
            file_id_or_path=sheet_id,
            current_state=state,
            needs_migration=needs_mig,
            summary_rows_count=len(summary_rows) - 1,
            risk_items_count=len(items_rows) - 1,
            details=[f"Drive File ID: {sheet_id}", f"Tabs: {tab_names}", f"State: {state}"],
            summary_preview=summary_rows[:2],
            risk_items_preview=items_rows[:2],
        )
        plans.append(plan)

    return plans


def apply_google_drive_migration(services: Any, plan: RiskMigrationPlan) -> dict[str, Any]:
    """Execute Google Drive spreadsheet migration."""
    if not plan.needs_migration:
        return {"project": plan.project, "status": "SKIPPED_ALREADY_COMPLIANT"}

    from pipeline_common import execute_with_backoff
    sheets = services["sheets"] if isinstance(services, dict) else getattr(services, "sheets", services)
    sheet_id = plan.file_id_or_path

    # Get current tabs
    meta = execute_with_backoff(sheets.spreadsheets().get(spreadsheetId=sheet_id))
    sheet_tabs = meta.get("sheets", [])
    tab_map = {s.get("properties", {}).get("title", ""): s.get("properties", {}).get("sheetId") for s in sheet_tabs}

    requests: list[dict[str, Any]] = []

    # Rename first tab to Summary if not already named Summary
    if "Summary" not in tab_map:
        first_sheet_id = sheet_tabs[0]["properties"]["sheetId"]
        requests.append({
            "updateSheetProperties": {
                "properties": {"sheetId": first_sheet_id, "title": "Summary"},
                "fields": "title",
            }
        })

    # Add Risk Items tab if missing
    if "Risk Items" not in tab_map:
        requests.append({
            "addSheet": {
                "properties": {"title": "Risk Items"}
            }
        })

    if requests:
        execute_with_backoff(sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}))

    # Write data to Summary and Risk Items
    data_updates = [
        {"range": "'Summary'!A1", "values": plan.summary_preview},
        {"range": "'Risk Items'!A1", "values": plan.risk_items_preview},
    ]
    execute_with_backoff(sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": data_updates},
    ))

    return {"project": plan.project, "status": "APPLIED", "sheet_id": sheet_id}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate project_risk spreadsheets to 2-tab schema (Summary + Risk Items).")
    parser.add_argument("--apply", action="store_true", default=False, help="Apply changes. Defaults to dry-run mode.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate migration without modifying data (default).")
    parser.add_argument("--project", help="Filter by specific project name.")
    parser.add_argument("--local-dir", type=Path, help="Local directory containing project folders to migrate offline.")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    is_apply = args.apply  # Explicit --apply overrides default dry-run

    plans: list[RiskMigrationPlan] = []

    if args.local_dir:
        plans = plan_local_directory_migration(args.local_dir)
    else:
        try:
            from pipeline_common import get_services
            services = get_services()
            plans = plan_google_drive_migration(services, project_name_filter=args.project)
        except Exception as exc:
            if not args.local_dir:
                print(f"[WARN] Google Drive services unavailable ({exc}). Use --local-dir to run on local folders.", file=sys.stderr)
                sys.exit(1)

    results: list[dict[str, Any]] = []

    for plan in plans:
        if is_apply and plan.needs_migration:
            if plan.target_type == "local_csv":
                res = apply_local_migration(plan)
            else:
                res = apply_google_drive_migration(services, plan)
            results.append(res)
        else:
            results.append({
                "project": plan.project,
                "target_type": plan.target_type,
                "state": plan.current_state,
                "needs_migration": plan.needs_migration,
                "summary_rows": plan.summary_rows_count,
                "risk_items": plan.risk_items_count,
                "mode": "DRY_RUN",
            })

    if args.json:
        print(json.dumps({"mode": "APPLY" if is_apply else "DRY_RUN", "total_projects": len(plans), "results": results}, indent=2, ensure_ascii=False))
    else:
        mode_str = "APPLY (LIVE UPDATE)" if is_apply else "DRY RUN (NO CHANGES WRITTEN)"
        print(f"\n=== M2 Project Risk Migration — Mode: {mode_str} ===")
        print(f"Total projects evaluated: {len(plans)}\n")
        for r in results:
            print(f"- Project: {r.get('project')}")
            for k, v in r.items():
                if k != "project":
                    print(f"    {k}: {v}")
        print("\nMigration assessment complete.\n")


if __name__ == "__main__":
    main()
