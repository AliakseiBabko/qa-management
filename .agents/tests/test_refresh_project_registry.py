"""Unit tests for refresh_project_registry.py's 13-column executive layout and pure aggregation logic.

Covers:
1. 13-column REGISTRY_HEADER structure.
2. Inactive project exclusion gate (Статус проекта = 'Не активен' -> None).
3. Deterministic Top-Risk Selection (Severity -> Expected Impact Date -> Late over Early -> Last Changed).
4. Composite outcome derivation (Baseline -> Current -> Target with evidence status).
5. Confidence synthesis (min(outcome_conf, risk_conf) with breakdown).
6. Privacy-safe 'People requiring attention' derivation with >30d stale review tag.
7. Contribution deduplication and non-canonical warning preservation.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from refresh_project_registry import (
    REGISTRY_HEADER,
    build_composite_outcome,
    build_registry_row,
    contribution_summary,
    derive_people_attention,
    project_status_warning,
    select_top_risk_item,
    synthesize_confidence,
)


def contribution_row(date: str, name: str, status: str, explanation: str = "x", role: str = "") -> list[str]:
    return ["<Project>", date, f"Вклад в проект: {name}", role or "Project-wide", status, "—", "—", "observed", "Высокая", explanation, "M2", "—"]


def status_row(status: str, date: str = "2026-01-01") -> list[str]:
    return ["<Project>", date, "Статус проекта", "Project-wide", status, "—", "—", "observed", "Высокая", "x", "M2", "—"]


class Executive13ColumnLayoutTests(unittest.TestCase):
    def test_registry_header_has_13_columns(self):
        self.assertEqual(len(REGISTRY_HEADER), 13)
        expected = [
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
        self.assertEqual(REGISTRY_HEADER, expected)

    def test_build_registry_row_emits_13_columns(self):
        pm_rows = [
            [
                "Проект", "Период", "Метрика", "Role / Stream", "Показатель", "Baseline", "Target",
                "Evidence Status", "Data Confidence", "Пояснение", "Owner", "Тренд"
            ],
            ["<Project>", "2026-08", "Статус проекта", "Project-wide", "Активен", "—", "—", "observed", "Высокая", "x", "M2", "—"],
            ["<Project>", "2026-08", "Engagement outlook", "Project-wide", "2026-12-31 [Contractual] — Continuation likely (High)", "—", "—", "observed", "Высокая", "x", "M2", "—"],
            ["<Project>", "2026-08", "Цель клиента / Ценность QA", "Project-wide", "Сокращение регресса", "—", "—", "observed", "Высокая", "x", "M2", "—"],
            ["<Project>", "2026-08", "Статус согласования (Alignment)", "Project-wide", "Согласовано", "—", "—", "observed", "Высокая", "x", "M2", "—"],
            ["<Project>", "2026-08", "Outcome proxy: Regression duration", "AQA", "2d", "5d", "1d", "observed", "Высокая", "x", "M2", "Позитивный"],
            ["<Project>", "2026-08", "Вклад в проект: <Person 1>", "AQA", "Позитивный", "—", "—", "observed", "Высокая", "x", "M2", "Позитивный"],
        ]

        row, warnings = build_registry_row(project="<Project>", pm_rows=pm_rows)
        self.assertIsNotNone(row)
        self.assertEqual(len(row), 13)
        self.assertEqual(row[0], "<Project>")
        self.assertIn("<Person 1> (AQA)", row[1])
        self.assertEqual(row[2], "2026-12-31 [Contractual] — Continuation likely (High)")
        self.assertEqual(row[3], "Сокращение регресса [Согласовано]")
        self.assertIn("Regression duration: 5d → 2d [observed]", row[4])
        self.assertEqual(row[5], "Низкий")
        self.assertEqual(warnings, [])


class InactiveProjectGateTests(unittest.TestCase):
    def test_inactive_project_is_excluded(self):
        pm_rows = [
            ["Проект", "Период", "Метрика", "Role / Stream", "Показатель", "Baseline", "Target", "Evidence Status", "Data Confidence", "Пояснение", "Owner", "Тренд"],
            ["<Project>", "2026-08", "Статус проекта", "Project-wide", "Не активен", "—", "—", "observed", "Высокая", "Client pause", "M2", "—"],
        ]
        row, warnings = build_registry_row(project="<Project>", pm_rows=pm_rows)
        self.assertIsNone(row, "Не активен project must return None to exclude from registry")
        self.assertEqual(warnings, [])

    def test_non_canonical_status_warns_and_includes(self):
        pm_rows = [
            ["Проект", "Период", "Метрика", "Role / Stream", "Показатель", "Baseline", "Target", "Evidence Status", "Data Confidence", "Пояснение", "Owner", "Тренд"],
            ["<Project>", "2026-08", "Статус проекта", "Project-wide", "На паузе", "—", "—", "observed", "Высокая", "x", "M2", "—"],
        ]
        row, warnings = build_registry_row(project="<Project>", pm_rows=pm_rows)
        self.assertIsNotNone(row)
        self.assertEqual(len(warnings), 1)
        self.assertIn("non-canonical value 'На паузе'", warnings[0])


class TopRiskSelectionTests(unittest.TestCase):
    def setUp(self):
        self.header = [
            "Risk ID", "Проект", "Формулировка риска", "Категория", "Уровень риска (Severity)",
            "Дата первого сигнала", "Дата фиксации риска", "Ожидаемая дата наступления (Expected Impact)",
            "Дата материализации", "Дата закрытия (Closed Date)", "Дата последнего review (Last Reviewed)",
            "Дата последнего изменения (Last Changed)", "Статус прогнозирования", "Обоснование статуса",
            "Migration State", "Уверенность в доказательствах (Evidence Confidence)", "Ссылка на evidence_log",
            "Митигация", "Owner", "Текущий статус"
        ]

    def test_severity_tie_breaking(self):
        rows = [
            self.header,
            ["RSK-01", "<P>", "Medium threat", "QA process", "Средний", "2026-08-01", "2026-08-05", "2026-09-01", "", "", "2026-08-17", "2026-08-17", "Detected Early", "", "Normal", "Высокая", "", "", "", "Open"],
            ["RSK-02", "<P>", "High threat", "delivery", "Высокий", "2026-08-01", "2026-08-05", "2026-10-01", "", "", "2026-08-17", "2026-08-17", "Detected Early", "", "Normal", "Высокая", "", "", "", "Open"],
        ]
        top, warnings = select_top_risk_item(rows)
        self.assertIsNotNone(top)
        self.assertEqual(top["Risk ID"], "RSK-02", "Higher severity must win")

    def test_earliest_expected_impact_tie_breaking(self):
        rows = [
            self.header,
            ["RSK-01", "<P>", "Later impact", "delivery", "Высокий", "2026-08-01", "2026-08-05", "2026-11-01", "", "", "2026-08-17", "2026-08-17", "Detected Early", "", "Normal", "Высокая", "", "", "", "Open"],
            ["RSK-02", "<P>", "Earlier impact", "delivery", "Высокий", "2026-08-01", "2026-08-05", "2026-09-15", "", "", "2026-08-17", "2026-08-17", "Detected Early", "", "Normal", "Высокая", "", "", "", "Open"],
        ]
        top, warnings = select_top_risk_item(rows)
        self.assertIsNotNone(top)
        self.assertEqual(top["Risk ID"], "RSK-02", "Earlier expected impact date must win")

    def test_detected_late_over_detected_early(self):
        rows = [
            self.header,
            ["RSK-01", "<P>", "Early detected", "delivery", "Высокий", "2026-08-01", "2026-08-05", "2026-09-15", "", "", "2026-08-17", "2026-08-17", "Detected Early", "", "Normal", "Высокая", "", "", "", "Open"],
            ["RSK-02", "<P>", "Late detected", "delivery", "Высокий", "2026-08-01", "2026-08-05", "2026-09-15", "", "", "2026-08-17", "2026-08-17", "Detected Late", "", "Normal", "Высокая", "", "", "", "Open"],
        ]
        top, warnings = select_top_risk_item(rows)
        self.assertIsNotNone(top)
        self.assertEqual(top["Risk ID"], "RSK-02", "Detected Late must be prioritized over Detected Early on equal severity/impact")

    def test_excludes_closed_and_legacy_items(self):
        rows = [
            self.header,
            ["RSK-01", "<P>", "Closed high threat", "delivery", "Высокий", "2026-08-01", "2026-08-05", "2026-08-10", "2026-08-10", "2026-08-15", "2026-08-17", "2026-08-17", "Detected Early", "", "Normal", "Высокая", "", "", "", "Closed"],
            ["RSK-02", "<P>", "Legacy item", "delivery", "Высокий", "", "2026-05-01", "", "", "", "2026-08-17", "2026-08-17", "", "", "Legacy — detection status unavailable", "Средняя", "", "", "", "Open"],
            ["RSK-03", "<P>", "Active medium threat", "delivery", "Средний", "2026-08-01", "2026-08-05", "2026-09-20", "", "", "2026-08-17", "2026-08-17", "Detected Early", "", "Normal", "Высокая", "", "", "", "Mitigating"],
        ]
        top, warnings = select_top_risk_item(rows)
        self.assertIsNotNone(top)
        self.assertEqual(top["Risk ID"], "RSK-03", "Closed and Legacy items must be excluded")


class ConfidenceSynthesisTests(unittest.TestCase):
    def test_matching_confidences(self):
        self.assertEqual(synthesize_confidence("Высокая", "Высокая"), "Высокая")
        self.assertEqual(synthesize_confidence("Средняя", "Средняя"), "Средняя")

    def test_divergent_confidences_returns_min_with_breakdown(self):
        res = synthesize_confidence("Высокая", "Низкая")
        self.assertEqual(res, "Низкая (Out: Высокая, Risk: Низкая)")

        res2 = synthesize_confidence("Средняя", "Высокая")
        self.assertEqual(res2, "Средняя (Out: Средняя, Risk: Высокая)")


class PeopleRequiringAttentionTests(unittest.TestCase):
    def test_fresh_people_signals(self):
        signals = [{"person": "<Person A>", "last_reviewed": "2026-08-10"}]
        res = derive_people_attention(signals, today_date="2026-08-17")
        self.assertEqual(res, "<Person A>")

    def test_stale_people_signal_over_30_days(self):
        signals = [{"person": "<Person A>", "last_reviewed": "2026-07-01"}]
        res = derive_people_attention(signals, today_date="2026-08-17")
        self.assertEqual(res, "<Person A> [Stale: review required]")

    def test_empty_signals(self):
        self.assertEqual(derive_people_attention([]), "—")
        self.assertEqual(derive_people_attention(None), "—")


class ContributionSummaryDedupeTests(unittest.TestCase):
    def test_single_row_per_person_unaffected(self) -> None:
        rows = [
            ["Проект", "Период", "Метрика", "Role / Stream", "Показатель", "Baseline", "Target", "Evidence Status", "Data Confidence", "Пояснение", "Owner", "Тренд"],
            contribution_row("2026-01-01", "<Имя1>", "Позитивный", role="AQA"),
        ]
        label, people, warnings = contribution_summary(rows)
        self.assertEqual(label, "Позитивный (<Имя1>)")
        self.assertEqual(people, ["<Имя1> (AQA)"])

    def test_duplicate_rows_for_same_person_keep_latest_only(self) -> None:
        rows = [
            ["Проект", "Период", "Метрика", "Role / Stream", "Показатель", "Baseline", "Target", "Evidence Status", "Data Confidence", "Пояснение", "Owner", "Тренд"],
            contribution_row("2026-07-09", "<Имя1>", "Смешанный", "older synthesis"),
            contribution_row("2026-07-20", "<Имя1>", "Смешанный", "newer synthesis"),
        ]
        label, people, warnings = contribution_summary(rows)
        self.assertEqual(label, "Смешанный (<Имя1>)")
        self.assertEqual(people, ["<Имя1>"], "duplicate must collapse to one name")


class ContributionSummaryNonCanonicalValueWarningTests(unittest.TestCase):
    def test_canonical_values_produce_no_warnings(self) -> None:
        for status in ("Позитивный", "Смешанный", "Негативный"):
            with self.subTest(status=status):
                rows = [
                    ["Проект", "Период", "Метрика", "Role / Stream", "Показатель", "Baseline", "Target", "Evidence Status", "Data Confidence", "Пояснение", "Owner", "Тренд"],
                    contribution_row("2026-01-01", "<Имя1>", status),
                ]
                _, _, warnings = contribution_summary(rows, project="<Проект>")
                self.assertEqual(warnings, [])

    def test_non_canonical_suffixed_value_warns(self) -> None:
        rows = [
            ["Проект", "Период", "Метрика", "Role / Stream", "Показатель", "Baseline", "Target", "Evidence Status", "Data Confidence", "Пояснение", "Owner", "Тренд"],
            contribution_row("2026-01-01", "<Имя1>", "Позитивный (по самоотчёту)"),
        ]
        label, people, warnings = contribution_summary(rows, project="<Проект>")
        self.assertEqual(label, "Неизвестно (данных недостаточно по <Имя1>)")
        self.assertEqual(len(warnings), 1)
        self.assertIn("not auto-normalized", warnings[0])


if __name__ == "__main__":
    unittest.main()
