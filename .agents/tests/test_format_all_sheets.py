"""Unit tests for format_all_sheets.py's formatting profiles, column widths, and exact conditional formatting rules.

Pure logic only - no Google APIs.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from format_all_sheets import (
    COLOR_BLUE_BG,
    COLOR_GRAY_BG,
    COLOR_GREEN_BG,
    COLOR_RED_BG,
    COLOR_YELLOW_BG,
    PROFILES,
    build_conditional_rule_requests,
    build_tab_formatting_requests,
    resolve_profile_for_tab,
)


class FormattingProfilesTests(unittest.TestCase):
    def test_all_expected_profiles_exist(self):
        expected_keys = ["_project_registry", "project_metrics", "project_risk_summary", "project_risk_items"]
        for key in expected_keys:
            self.assertIn(key, PROFILES)

    def test_project_registry_profile_budget(self):
        profile = PROFILES["_project_registry"]
        widths = profile["widths"]
        self.assertEqual(len(widths), 13, "13-column executive layout")
        self.assertEqual(sum(widths), 1680, "1,680 px display budget")
        self.assertEqual(profile["freeze_rows"], 1)

    def test_project_metrics_profile_budget(self):
        profile = PROFILES["project_metrics"]
        widths = profile["widths"]
        self.assertEqual(len(widths), 12, "12-column metrics layout")
        self.assertEqual(sum(widths), 1600, "1,600 px display budget")
        self.assertEqual(profile["freeze_rows"], 1)

    def test_project_risk_summary_profile_budget(self):
        profile = PROFILES["project_risk_summary"]
        widths = profile["widths"]
        self.assertEqual(len(widths), 14, "14-column summary risk layout")
        self.assertEqual(sum(widths), 1600, "1,600 px display budget")
        self.assertEqual(profile["freeze_rows"], 1)

    def test_project_risk_items_profile_budget(self):
        profile = PROFILES["project_risk_items"]
        widths = profile["widths"]
        self.assertEqual(len(widths), 20, "20-column risk items layout")
        self.assertEqual(sum(widths), 2420, "2,420 px total width")
        self.assertEqual(profile["freeze_rows"], 1)


class ProfileResolutionTests(unittest.TestCase):
    def test_resolves_project_registry(self):
        self.assertEqual(resolve_profile_for_tab("_project_registry", "Sheet1"), PROFILES["_project_registry"])
        self.assertEqual(resolve_profile_for_tab("anything", "_project_registry"), PROFILES["_project_registry"])

    def test_resolves_project_metrics(self):
        self.assertEqual(resolve_profile_for_tab("project_metrics", "Sheet1"), PROFILES["project_metrics"])

    def test_resolves_project_risk_tabs(self):
        self.assertEqual(resolve_profile_for_tab("project_risk", "Summary"), PROFILES["project_risk_summary"])
        self.assertEqual(resolve_profile_for_tab("project_risk", "Risk Items"), PROFILES["project_risk_items"])
        self.assertEqual(resolve_profile_for_tab("custom_sheet", "Risk Items"), PROFILES["project_risk_items"])

    def test_unknown_sheet_returns_none_for_dynamic_fallback(self):
        self.assertIsNone(resolve_profile_for_tab("random_notes", "Sheet1"))


class ExactConditionalFormattingRangeTests(unittest.TestCase):
    """Guards exact column ranges for each conditional formatting rule to prevent styling misalignments."""

    def test_project_registry_conditional_ranges(self):
        rules = PROFILES["_project_registry"]["conditional_rules"]
        # Col F (idx 5:6): Общий уровень риска
        risk_rules = [r for r in rules if r["col_start"] == 5 and r["col_end"] == 6]
        self.assertEqual(len(risk_rules), 3)
        self.assertEqual({r["val"] for r in risk_rules}, {"Высокий", "Средний", "Низкий"})

        # Col I (idx 8:9): People requiring attention
        stale_rules = [r for r in rules if r["col_start"] == 8 and r["col_end"] == 9]
        self.assertEqual(len(stale_rules), 1)
        self.assertEqual(stale_rules[0]["val"], "[Stale: review required]")

    def test_project_metrics_conditional_ranges(self):
        rules = PROFILES["project_metrics"]["conditional_rules"]
        # Col I (idx 8:9): Data Confidence
        conf_rules = [r for r in rules if r["col_start"] == 8 and r["col_end"] == 9]
        self.assertEqual(len(conf_rules), 3)
        self.assertEqual({r["val"] for r in conf_rules}, {"Высокая", "Средняя", "Низкая"})

        # Col L (idx 11:12): Тренд
        trend_rules = [r for r in rules if r["col_start"] == 11 and r["col_end"] == 12]
        self.assertEqual(len(trend_rules), 3)
        self.assertEqual({r["val"] for r in trend_rules}, {"Позитивный", "Смешанный", "Негативный"})

    def test_project_risk_summary_exact_conditional_ranges(self):
        rules = PROFILES["project_risk_summary"]["conditional_rules"]

        # 1. Col C (idx 2:3): Общий уровень риска
        overall_risk_rules = [r for r in rules if r["col_start"] == 2 and r["col_end"] == 3]
        self.assertEqual(len(overall_risk_rules), 3)
        self.assertEqual({r["val"] for r in overall_risk_rules}, {"Высокий", "Средний", "Низкий"})

        # 2. Col F (idx 5:6): Статус прогнозирования (Prediction Status)
        pred_rules = [r for r in rules if r["col_start"] == 5 and r["col_end"] == 6]
        self.assertEqual(len(pred_rules), 4)
        self.assertEqual({r["val"] for r in pred_rules}, {"Detected Early", "Detected Late", "Not Reviewed", "Not Detectable"})

        # 3. Cols G:J (idx 6:10): 4 Risk dimensions (delivery, QA process, staffing/continuity, communication/client)
        dim_rules = [r for r in rules if r["col_start"] == 6 and r["col_end"] == 10]
        self.assertEqual(len(dim_rules), 3)
        self.assertEqual({r["val"] for r in dim_rules}, {"Высокий", "Средний", "Низкий"})

        # 4. Col L (idx 11:12): Уверенность в данных (Data Confidence)
        conf_rules = [r for r in rules if r["col_start"] == 11 and r["col_end"] == 12]
        self.assertEqual(len(conf_rules), 3)
        self.assertEqual({r["val"] for r in conf_rules}, {"Высокая", "Средняя", "Низкая"})

    def test_project_risk_items_exact_conditional_ranges(self):
        rules = PROFILES["project_risk_items"]["conditional_rules"]

        # Col E (idx 4:5): Уровень риска (Severity)
        sev_rules = [r for r in rules if r["col_start"] == 4 and r["col_end"] == 5]
        self.assertEqual(len(sev_rules), 3)
        self.assertEqual({r["val"] for r in sev_rules}, {"Высокий", "Средний", "Низкий"})

        # Col M (idx 12:13): Статус прогнозирования
        pred_rules = [r for r in rules if r["col_start"] == 12 and r["col_end"] == 13]
        self.assertEqual(len(pred_rules), 4)
        self.assertEqual({r["val"] for r in pred_rules}, {"Detected Early", "Detected Late", "Not Reviewed", "Not Detectable"})

        # Col T (idx 19:20): Текущий статус (Status)
        status_rules = [r for r in rules if r["col_start"] == 19 and r["col_end"] == 20]
        self.assertEqual(len(status_rules), 4)
        self.assertEqual({r["val"] for r in status_rules}, {"Closed", "Materialized", "Mitigating", "Open"})


class TabFormattingRequestsTests(unittest.TestCase):
    def test_build_requests_for_project_registry(self):
        profile = PROFILES["_project_registry"]
        header = [
            "Проект", "People", "Engagement outlook", "Цель клиента / Ценность QA", "Текущий результат",
            "Общий уровень риска", "Ранний сигнал / Прогноз", "Качество QA-процесса",
            "People requiring attention", "Действие M2", "Уверенность в данных", "Owner", "Следующий review"
        ]
        row1 = ["<Project>", "<Person>", "2026-12-31", "Goal", "Outcome", "Высокий", "RSK-01", "—", "—", "Action", "Высокая", "M2", "2026-08-24"]
        values = [header, row1]

        requests, widths = build_tab_formatting_requests(
            grid_id=0,
            row_count=100,
            col_count=13,
            values=values,
            profile=profile,
        )

        self.assertEqual(len(widths), 13)
        self.assertEqual(list(widths.values()), profile["widths"])

        # Check frozen row request
        freeze_reqs = [r for r in requests if "updateSheetProperties" in r]
        self.assertEqual(len(freeze_reqs), 1)
        self.assertEqual(freeze_reqs[0]["updateSheetProperties"]["properties"]["gridProperties"]["frozenRowCount"], 1)

        # Check conditional formatting rules
        cond_reqs = [r for r in requests if "addConditionalFormatRule" in r]
        self.assertEqual(len(cond_reqs), len(profile["conditional_rules"]))

    def test_build_requests_for_risk_summary(self):
        profile = PROFILES["project_risk_summary"]
        header = [
            "Проект", "Дата обновления", "Общий уровень риска", "ID ключевого риска",
            "Ключевой ранний сигнал", "Статус прогнозирования", "Риск delivery",
            "Риск QA process", "Риск staffing / continuity", "Риск communication / client",
            "План действий M2", "Уверенность в данных", "Owner", "Следующий review"
        ]
        values = [header]

        requests, widths = build_tab_formatting_requests(
            grid_id=0,
            row_count=100,
            col_count=14,
            values=values,
            profile=profile,
        )

        self.assertEqual(len(widths), 14)
        self.assertEqual(list(widths.values()), profile["widths"])

        cond_reqs = [r for r in requests if "addConditionalFormatRule" in r]
        self.assertEqual(len(cond_reqs), 13)  # 3 overall + 4 prediction + 3 dimensions + 3 confidence

        # Check ranges inside requests
        rule_ranges = [r["addConditionalFormatRule"]["rule"]["ranges"][0] for r in cond_reqs]
        col_spans = [(r["startColumnIndex"], r["endColumnIndex"]) for r in rule_ranges]
        self.assertIn((2, 3), col_spans)    # Col C (Общий уровень риска)
        self.assertIn((5, 6), col_spans)    # Col F (Статус прогнозирования)
        self.assertIn((6, 10), col_spans)   # Cols G:J (Risk dimensions)
        self.assertIn((11, 12), col_spans)  # Col L (Уверенность в данных)

    def test_build_requests_for_risk_items(self):
        profile = PROFILES["project_risk_items"]
        header = [
            "Risk ID", "Проект", "Формулировка риска", "Категория", "Уровень риска (Severity)",
            "Дата первого сигнала", "Дата фиксации риска", "Ожидаемая дата наступления (Expected Impact)",
            "Дата материализации", "Дата закрытия (Closed Date)", "Дата последнего review (Last Reviewed)",
            "Дата последнего изменения (Last Changed)", "Статус прогнозирования", "Обоснование статуса",
            "Migration State", "Уверенность в доказательствах (Evidence Confidence)", "Ссылка на evidence_log",
            "Митигация", "Owner", "Текущий статус"
        ]
        values = [header]

        requests, widths = build_tab_formatting_requests(
            grid_id=1,
            row_count=100,
            col_count=20,
            values=values,
            profile=profile,
        )

        self.assertEqual(len(widths), 20)
        self.assertEqual(list(widths.values()), profile["widths"])

        cond_reqs = [r for r in requests if "addConditionalFormatRule" in r]
        self.assertEqual(len(cond_reqs), 11)  # 3 severity + 4 prediction + 4 status


if __name__ == "__main__":
    unittest.main()
