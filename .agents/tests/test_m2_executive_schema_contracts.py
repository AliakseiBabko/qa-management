"""Executable schema, enum, lifecycle, and prediction contracts for M2 Executive Architecture (Phase 2 & Phase 3 readiness).

Tests:
1. Exact column count, names, ordering, and uniqueness for:
   - Templates/метрики_проекта_qa.csv (12 columns)
   - Templates/светофор_рисков_проекта.csv (14 columns)
   - Templates/project_risk_items.csv (20 columns)
2. Canonical enum validation across all metrics and risk fields.
3. Risk lifecycle date rules (conditional consistency, required closure/materialization dates).
4. Prediction classification logic and incomplete date handling.
5. Synthetic risk fixture validating early, late, not-detectable, and legacy behavior.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = REPO_ROOT / "Templates"

EXPECTED_PROJECT_METRICS_COLS = [
    "Проект",
    "Период",
    "Метрика",
    "Role / Stream",
    "Показатель",
    "Baseline",
    "Target",
    "Evidence Status",
    "Data Confidence",
    "Пояснение",
    "Owner",
    "Тренд",
]

EXPECTED_PROJECT_RISK_SUMMARY_COLS = [
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

EXPECTED_PROJECT_RISK_ITEMS_COLS = [
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

ALLOWED_SEVERITIES = {"Низкий", "Средний", "Высокий"}
ALLOWED_CATEGORIES = {"delivery", "QA process", "staffing / continuity", "communication / client", "role / value"}
ALLOWED_CURRENT_STATUSES = {"Open", "Mitigating", "Materialized", "Accepted", "Closed"}
ALLOWED_PREDICTION_STATUSES = {"Detected Early", "Detected Late", "Not Detectable", "Not Reviewed", ""}
ALLOWED_MIGRATION_STATES = {"Normal", "Legacy — detection status unavailable"}
ALLOWED_EVIDENCE_STATUSES = {"observed", "estimated", "projected", "assumption-based"}
ALLOWED_CONFIDENCES = {"Высокая", "Средняя", "Низкая"}
ALLOWED_ALIGNMENT_STATUSES = {"Согласовано", "В процессе калибровки", "Расхождение ожиданий"}


def _read_csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        return next(reader)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _parse_iso_date(val: str | None) -> date | None:
    if not val or not val.strip():
        return None
    return date.fromisoformat(val.strip())


class CsvHeaderAndOrderingContractTests(unittest.TestCase):
    def test_project_metrics_template_columns(self):
        csv_path = TEMPLATES_DIR / "метрики_проекта_qa.csv"
        self.assertTrue(csv_path.is_file(), f"Missing template: {csv_path}")
        header = _read_csv_header(csv_path)
        self.assertEqual(
            header,
            EXPECTED_PROJECT_METRICS_COLS,
            f"Project metrics CSV header mismatch. Expected {EXPECTED_PROJECT_METRICS_COLS}, got {header}",
        )
        self.assertEqual(len(header), len(set(header)), "Duplicate column in project_metrics.csv")

    def test_project_risk_summary_template_columns(self):
        csv_path = TEMPLATES_DIR / "светофор_рисков_проекта.csv"
        self.assertTrue(csv_path.is_file(), f"Missing template: {csv_path}")
        header = _read_csv_header(csv_path)
        self.assertEqual(
            header,
            EXPECTED_PROJECT_RISK_SUMMARY_COLS,
            f"Project risk summary CSV header mismatch. Expected {EXPECTED_PROJECT_RISK_SUMMARY_COLS}, got {header}",
        )
        self.assertEqual(len(header), len(set(header)), "Duplicate column in светофор_рисков_проекта.csv")

    def test_project_risk_items_template_columns(self):
        csv_path = TEMPLATES_DIR / "project_risk_items.csv"
        self.assertTrue(csv_path.is_file(), f"Missing template: {csv_path}")
        header = _read_csv_header(csv_path)
        self.assertEqual(
            header,
            EXPECTED_PROJECT_RISK_ITEMS_COLS,
            f"Project risk items CSV header mismatch. Expected {EXPECTED_PROJECT_RISK_ITEMS_COLS}, got {header}",
        )
        self.assertEqual(len(header), len(set(header)), "Duplicate column in project_risk_items.csv")


class TemplatePlaceholderRowValidationTests(unittest.TestCase):
    def test_project_metrics_placeholder_rows_valid(self):
        rows = _read_csv_rows(TEMPLATES_DIR / "метрики_проекта_qa.csv")
        self.assertGreater(len(rows), 0, "метрики_проекта_qa.csv has no rows")
        for row in rows:
            self.assertIn(row["Evidence Status"], ALLOWED_EVIDENCE_STATUSES)
            self.assertIn(row["Data Confidence"], ALLOWED_CONFIDENCES)
            self.assertTrue(row["Проект"].strip())
            self.assertTrue(row["Метрика"].strip())
            self.assertTrue(row["Role / Stream"].strip())

    def test_project_risk_summary_placeholder_rows_valid(self):
        rows = _read_csv_rows(TEMPLATES_DIR / "светофор_рисков_проекта.csv")
        self.assertGreater(len(rows), 0, "светофор_рисков_проекта.csv has no rows")
        for row in rows:
            self.assertIn(row["Общий уровень риска"], ALLOWED_SEVERITIES)
            self.assertIn(row["Статус прогнозирования"], ALLOWED_PREDICTION_STATUSES)
            self.assertIn(row["Уверенность в данных"], ALLOWED_CONFIDENCES)

    def test_project_risk_items_placeholder_rows_valid(self):
        rows = _read_csv_rows(TEMPLATES_DIR / "project_risk_items.csv")
        self.assertGreater(len(rows), 0, "project_risk_items.csv has no rows")
        for row in rows:
            self.assertIn(row["Категория"], ALLOWED_CATEGORIES)
            self.assertIn(row["Уровень риска (Severity)"], ALLOWED_SEVERITIES)
            self.assertIn(row["Статус прогнозирования"], ALLOWED_PREDICTION_STATUSES)
            self.assertIn(row["Migration State"], ALLOWED_MIGRATION_STATES)
            self.assertIn(row["Уверенность в доказательствах (Evidence Confidence)"], ALLOWED_CONFIDENCES)
            self.assertIn(row["Текущий статус"], ALLOWED_CURRENT_STATUSES)


class RiskLifecycleAndDateRulesTests(unittest.TestCase):
    def validate_risk_item(self, item: dict[str, str]) -> list[str]:
        """Validate an itemized risk according to canonical lifecycle rules."""
        errors: list[str] = []
        d_first = _parse_iso_date(item.get("Дата первого сигнала"))
        d_logged = _parse_iso_date(item.get("Дата фиксации риска"))
        d_expected = _parse_iso_date(item.get("Ожидаемая дата наступления (Expected Impact)"))
        d_mat = _parse_iso_date(item.get("Дата материализации"))
        d_closed = _parse_iso_date(item.get("Дата закрытия (Closed Date)"))

        status = item.get("Текущий статус", "")
        pred_status = item.get("Статус прогнозирования", "")
        mig_state = item.get("Migration State", "Normal")

        # Required dates for terminal/transition states
        if status == "Materialized" and not d_mat:
            errors.append("Status Materialized requires 'Дата материализации'")
        if status == "Closed" and not d_closed:
            errors.append("Status Closed requires 'Дата закрытия (Closed Date)'")

        # Unmaterialized forecast risk chronological ordering
        if status in {"Open", "Mitigating"} and d_first and d_logged and d_expected:
            if not (d_first <= d_logged <= d_expected):
                errors.append(f"Unmaterialized risk date order violated: first({d_first}) <= logged({d_logged}) <= expected({d_expected})")

        # Materialized or late-detected risk consistency
        if d_expected and d_mat:
            if d_expected > d_mat:
                errors.append(f"Expected impact ({d_expected}) is after materialization date ({d_mat})")

        # Incomplete date handling: Detected Early requires expected impact
        if pred_status == "Detected Early":
            if not d_first or not d_expected:
                errors.append("Detected Early strictly requires both 'Дата первого сигнала' and 'Ожидаемая дата наступления (Expected Impact)'")
            elif d_first > d_expected:
                errors.append(f"Detected Early invalid: first signal ({d_first}) is after expected impact ({d_expected})")

        # Migration State separation
        if mig_state == "Legacy — detection status unavailable" and pred_status != "":
            errors.append("Legacy rows must have empty Prediction Status")

        return errors

    def test_valid_synthetic_fixtures(self):
        fixtures = [
            {
                "Risk ID": "RSK-01",
                "Проект": "<Project>",
                "Формулировка риска": "Payment gateway failure",
                "Категория": "QA process",
                "Уровень риска (Severity)": "Средний",
                "Дата первого сигнала": "2026-08-01",
                "Дата фиксации риска": "2026-08-05",
                "Ожидаемая дата наступления (Expected Impact)": "2026-09-15",
                "Дата материализации": "",
                "Дата закрытия (Closed Date)": "",
                "Статус прогнозирования": "Detected Early",
                "Migration State": "Normal",
                "Текущий статус": "Mitigating",
            },
            {
                "Risk ID": "RSK-02",
                "Проект": "<Project>",
                "Формулировка риска": "Late discovered client escalation",
                "Категория": "communication / client",
                "Уровень риска (Severity)": "Высокий",
                "Дата первого сигнала": "2026-08-10",
                "Дата фиксации риска": "2026-08-10",
                "Ожидаемая дата наступления (Expected Impact)": "2026-08-05",
                "Дата материализации": "2026-08-05",
                "Дата закрытия (Closed Date)": "2026-08-15",
                "Статус прогнозирования": "Detected Late",
                "Migration State": "Normal",
                "Текущий статус": "Closed",
            },
            {
                "Risk ID": "RSK-03",
                "Проект": "<Project>",
                "Формулировка риска": "Third-party vendor outage",
                "Категория": "delivery",
                "Уровень риска (Severity)": "Средний",
                "Дата первого сигнала": "2026-08-12",
                "Дата фиксации риска": "2026-08-12",
                "Ожидаемая дата наступления (Expected Impact)": "2026-08-12",
                "Дата материализации": "2026-08-12",
                "Дата закрытия (Closed Date)": "",
                "Статус прогнозирования": "Not Detectable",
                "Migration State": "Normal",
                "Текущий статус": "Materialized",
            },
            {
                "Risk ID": "RSK-04",
                "Проект": "<Project>",
                "Формулировка риска": "Legacy risk from prior import",
                "Категория": "staffing / continuity",
                "Уровень риска (Severity)": "Низкий",
                "Дата первого сигнала": "",
                "Дата фиксации риска": "2026-05-01",
                "Ожидаемая дата наступления (Expected Impact)": "",
                "Дата материализации": "",
                "Дата закрытия (Closed Date)": "2026-06-01",
                "Статус прогнозирования": "",
                "Migration State": "Legacy — detection status unavailable",
                "Текущий статус": "Closed",
            },
        ]

        for item in fixtures:
            errors = self.validate_risk_item(item)
            self.assertEqual(errors, [], f"Fixture {item['Risk ID']} failed validation: {errors}")

    def test_invalid_detected_early_without_expected_impact(self):
        bad_item = {
            "Risk ID": "RSK-FAIL-1",
            "Текущий статус": "Open",
            "Дата первого сигнала": "2026-08-01",
            "Дата фиксации риска": "2026-08-05",
            "Ожидаемая дата наступления (Expected Impact)": "",
            "Статус прогнозирования": "Detected Early",
            "Migration State": "Normal",
        }
        errors = self.validate_risk_item(bad_item)
        self.assertTrue(any("strictly requires" in e for e in errors), f"Expected validation error, got: {errors}")

    def test_invalid_materialized_without_date(self):
        bad_item = {
            "Risk ID": "RSK-FAIL-2",
            "Текущий статус": "Materialized",
            "Дата материализации": "",
            "Migration State": "Normal",
        }
        errors = self.validate_risk_item(bad_item)
        self.assertTrue(any("Materialized requires 'Дата материализации'" in e for e in errors), f"Expected validation error, got: {errors}")


if __name__ == "__main__":
    unittest.main()
