"""Unit tests for sync_m2_source_docs_to_sheets.py's multi-tab project_risk support and pure logic.

Pure logic only - no Google APIs.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sync_m2_source_docs_to_sheets import (
    build_project_risk_tabs_data,
    col_label,
    merge_evidence,
    merge_individual_metrics,
    upsert_multi_tab_sheet,
)


class MultiTabProjectRiskTests(unittest.TestCase):
    def setUp(self):
        self.summary_header = [
            "Проект", "Дата обновления", "Общий уровень риска", "Риск delivery",
            "Риск QA process", "Риск staffing / continuity", "Риск communication / client",
            "Ключевой ранний сигнал", "Статус прогнозирования", "Обоснование статуса",
            "План действий M2", "Уверенность в данных", "Owner", "Следующий review"
        ]
        self.items_header = [
            "Risk ID", "Проект", "Формулировка риска", "Категория", "Уровень риска (Severity)",
            "Дата первого сигнала", "Дата фиксации риска", "Ожидаемая дата наступления (Expected Impact)",
            "Дата материализации", "Дата закрытия (Closed Date)", "Дата последнего review (Last Reviewed)",
            "Дата последнего изменения (Last Changed)", "Статус прогнозирования", "Обоснование статуса",
            "Migration State", "Уверенность в доказательствах (Evidence Confidence)", "Ссылка на evidence_log",
            "Митигация", "Owner", "Текущий статус"
        ]

    def test_build_project_risk_tabs_data_structure(self):
        summary_rows = [
            ["<Project>", "2026-08-17", "Высокий", "Высокий", "Низкий", "Низкий", "Низкий", "Signal", "Detected Early", "x", "Action", "Высокая", "M2", "2026-08-24"]
        ]
        tabs_data = build_project_risk_tabs_data(
            summary_header=self.summary_header,
            items_header=self.items_header,
            summary_rows=summary_rows,
        )

        self.assertIn("Summary", tabs_data)
        self.assertIn("Risk Items", tabs_data)
        self.assertEqual(len(tabs_data["Summary"]), 2)
        self.assertEqual(tabs_data["Summary"][0], self.summary_header)
        self.assertEqual(tabs_data["Summary"][1], summary_rows[0])
        self.assertEqual(len(tabs_data["Risk Items"]), 1)
        self.assertEqual(tabs_data["Risk Items"][0], self.items_header)

    def test_build_project_risk_tabs_data_with_items(self):
        summary_rows = [
            ["<Project>", "2026-08-17", "Низкий", "Низкий", "Низкий", "Низкий", "Низкий", "", "", "", "", "Высокая", "M2", "2026-08-24"]
        ]
        items_rows = [
            ["RSK-01", "<Project>", "Delivery delay", "delivery", "Средний", "2026-08-01", "2026-08-05", "2026-09-01", "", "", "2026-08-17", "2026-08-17", "Detected Early", "x", "Normal", "Высокая", "", "Action", "M2", "Open"]
        ]
        tabs_data = build_project_risk_tabs_data(
            summary_header=self.summary_header,
            items_header=self.items_header,
            summary_rows=summary_rows,
            items_rows=items_rows,
        )
        self.assertEqual(len(tabs_data["Risk Items"]), 2)
        self.assertEqual(tabs_data["Risk Items"][1][0], "RSK-01")

    def test_col_label_computation(self):
        self.assertEqual(col_label(1), "A")
        self.assertEqual(col_label(14), "N")
        self.assertEqual(col_label(20), "T")
        self.assertEqual(col_label(26), "Z")
        self.assertEqual(col_label(27), "AA")


class MergeLogicTests(unittest.TestCase):
    def test_merge_individual_metrics_deduplication(self):
        header = ["Проект", "Сотрудник", "Период", "Role / Stream", "Метрика", "Показатель", "Baseline", "Target", "Evidence Status", "Data Confidence", "Пояснение", "Owner", "Тренд"]
        existing = [
            header,
            ["<P>", "<Person>", "2026-08", "AQA", "Автопокрытие", "60%", "40%", "80%", "observed", "Высокая", "old", "M2", "Позитивный"]
        ]
        new_rows = [
            ["<P>", "<Person>", "2026-08", "AQA", "Автопокрытие", "65%", "40%", "80%", "observed", "Высокая", "updated", "M2", "Позитивный"]
        ]
        merged = merge_individual_metrics(existing, new_rows, header)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[1][5], "65%")
        self.assertEqual(merged[1][10], "updated")

    def test_merge_evidence_deduplication(self):
        existing = [
            ["date", "source", "source_type", "project", "routed_to", "notes"],
            ["2026-08-01", "file.txt", "1to1", "<P>", "project_risk", "note 1"],
        ]
        new_rows = [
            ["2026-08-01", "file.txt", "1to1", "<P>", "project_risk", "duplicate attempt"],
            ["2026-08-17", "file2.txt", "chat", "<P>", "project_metrics", "new source"],
        ]
        merged = merge_evidence(existing, new_rows)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[2][1], "file2.txt")


if __name__ == "__main__":
    unittest.main()
