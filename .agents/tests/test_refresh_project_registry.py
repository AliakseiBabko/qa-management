"""Unit tests for refresh_project_registry.py's pure aggregation logic.

Covers a real defect: a duplicate "Вклад в проект: <Имя>" row for the same
person in project_metrics (one intake updated the wrong row instead of the
existing one) rendered as "<Имя>, <Имя>" in _project_registry. These tests
cover contribution_summary()'s defensive dedupe-by-person behavior so a
future upstream duplicate can't corrupt the registry again.

Pure logic only - no Google APIs.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from refresh_project_registry import build_registry_row, contribution_summary, project_status_warning


def contribution_row(date: str, name: str, status: str, explanation: str = "x") -> list[str]:
    return ["<Project>", date, f"Вклад в проект: {name}", status, explanation, "M2"]


def status_row(status: str, date: str = "2026-01-01") -> list[str]:
    return ["<Project>", date, "Статус проекта", status, "x", "M2"]


class ContributionSummaryDedupeTests(unittest.TestCase):
    def test_single_row_per_person_unaffected(self) -> None:
        rows = [contribution_row("2026-01-01", "<Имя1>", "Позитивный")]
        label, people, warnings = contribution_summary(rows)
        self.assertEqual(label, "Позитивный (<Имя1>)")
        self.assertEqual(people, ["<Имя1>"])

    def test_duplicate_rows_for_same_person_keep_latest_only(self) -> None:
        # Same defect shape as the real incident: an older current-value
        # row plus a newer one appended for the same person instead of
        # updating the older row in place.
        rows = [
            contribution_row("2026-07-09", "<Имя1>", "Смешанный", "older synthesis"),
            contribution_row("2026-07-20", "<Имя1>", "Смешанный", "newer synthesis"),
        ]
        label, people, warnings = contribution_summary(rows)
        self.assertEqual(label, "Смешанный (<Имя1>)")
        self.assertEqual(people, ["<Имя1>"], "duplicate must collapse to one name, not '<Имя1>, <Имя1>'")

    def test_duplicate_rows_keep_latest_status_even_if_it_changed(self) -> None:
        rows = [
            contribution_row("2026-01-01", "<Имя1>", "Негативный", "old"),
            contribution_row("2026-02-01", "<Имя1>", "Позитивный", "improved"),
        ]
        label, people, warnings = contribution_summary(rows)
        self.assertEqual(label, "Позитивный (<Имя1>)")
        self.assertEqual(people, ["<Имя1>"])

    def test_out_of_order_rows_still_resolve_to_latest_date(self) -> None:
        # Defensive against append order not matching date order.
        rows = [
            contribution_row("2026-02-01", "<Имя1>", "Позитивный", "newer"),
            contribution_row("2026-01-01", "<Имя1>", "Негативный", "older"),
        ]
        label, people, warnings = contribution_summary(rows)
        self.assertEqual(label, "Позитивный (<Имя1>)")

    def test_multiple_distinct_people_each_kept_once(self) -> None:
        rows = [
            contribution_row("2026-01-01", "<Имя1>", "Позитивный"),
            contribution_row("2026-01-01", "<Имя2>", "Негативный"),
            contribution_row("2026-02-01", "<Имя1>", "Позитивный"),
        ]
        label, people, warnings = contribution_summary(rows)
        self.assertEqual(label, "Негативный (<Имя2>)")
        self.assertEqual(sorted(people), ["<Имя1>", "<Имя2>"])

    def test_unknown_status_kept_separate_and_deduped(self) -> None:
        rows = [
            contribution_row("2026-01-01", "<Имя1>", ""),
            contribution_row("2026-02-01", "<Имя1>", ""),
        ]
        label, people, warnings = contribution_summary(rows)
        self.assertEqual(label, "Неизвестно (данных недостаточно по <Имя1>)")
        self.assertEqual(people, ["<Имя1>"])
        self.assertEqual(warnings, [], "a blank value is a recognized missing-data marker, not a warning case")


class ContributionSummaryNonCanonicalValueWarningTests(unittest.TestCase):
    """A real project once had 'Позитивный (по самоотчёту)' in project_metrics -
    a suffixed variant of a canonical value. contribution_summary() correctly
    treated it as unknown (never guess a verdict), but did so silently; that
    silence is exactly what let the stale registry value go unnoticed until a
    manual diff caught it. These tests guard the warning that now surfaces it."""

    def test_canonical_values_produce_no_warnings(self) -> None:
        for status in ("Позитивный", "Смешанный", "Негативный"):
            with self.subTest(status=status):
                rows = [contribution_row("2026-01-01", "<Имя1>", status)]
                _, _, warnings = contribution_summary(rows, project="<Проект>")
                self.assertEqual(warnings, [])

    def test_non_canonical_suffixed_value_warns(self) -> None:
        rows = [contribution_row("2026-01-01", "<Имя1>", "Позитивный (по самоотчёту)")]
        label, people, warnings = contribution_summary(rows, project="<Проект>")
        self.assertEqual(label, "Неизвестно (данных недостаточно по <Имя1>)")
        self.assertEqual(len(warnings), 1)
        warning = warnings[0]
        self.assertIn("<Проект>", warning)
        self.assertIn("<Имя1>", warning)
        self.assertIn("Позитивный (по самоотчёту)", warning)
        self.assertIn("not auto-normalized", warning)

    def test_non_canonical_value_is_not_silently_remapped_to_canonical(self) -> None:
        # The warning is the whole point - contribution_summary must never
        # guess that "Позитивный (по самоотчёту)" means "Позитивный".
        rows = [contribution_row("2026-01-01", "<Имя1>", "Позитивный (по самоотчёту)")]
        label, _, _ = contribution_summary(rows, project="<Проект>")
        self.assertNotIn("Позитивный (", label)
        self.assertTrue(label.startswith("Неизвестно"))

    def test_blank_value_does_not_warn(self) -> None:
        rows = [contribution_row("2026-01-01", "<Имя1>", "")]
        _, _, warnings = contribution_summary(rows, project="<Проект>")
        self.assertEqual(warnings, [])

    def test_neizvestno_marker_does_not_warn(self) -> None:
        rows = [contribution_row("2026-01-01", "<Имя1>", "Неизвестно")]
        _, _, warnings = contribution_summary(rows, project="<Проект>")
        self.assertEqual(warnings, [])

    def test_warning_omits_project_prefix_when_project_not_given(self) -> None:
        rows = [contribution_row("2026-01-01", "<Имя1>", "Позитивный (typo)")]
        _, _, warnings = contribution_summary(rows)
        self.assertEqual(len(warnings), 1)
        self.assertFalse(warnings[0].startswith(": "))

    def test_multiple_non_canonical_values_each_produce_their_own_warning(self) -> None:
        rows = [
            contribution_row("2026-01-01", "<Имя1>", "Позитивный (по самоотчёту)"),
            contribution_row("2026-01-01", "<Имя2>", "Негативный?"),
        ]
        _, _, warnings = contribution_summary(rows, project="<Проект>")
        self.assertEqual(len(warnings), 2)


class ProjectStatusWarningTests(unittest.TestCase):
    def test_canonical_active_produces_no_warning(self) -> None:
        self.assertIsNone(project_status_warning("<Проект>", "Активен"))

    def test_canonical_inactive_produces_no_warning(self) -> None:
        self.assertIsNone(project_status_warning("<Проект>", "Не активен"))

    def test_non_canonical_value_warns(self) -> None:
        warning = project_status_warning("<Проект>", "Стоп")
        assert warning is not None
        self.assertIn("<Проект>", warning)
        self.assertIn("Стоп", warning)
        self.assertIn("not normalized", warning)


class BuildRegistryRowInactiveExclusionTests(unittest.TestCase):
    """Covers the archival mechanism (Templates/метрики_проекта_qa.md §1.0):
    a project's `Статус проекта = Не активен` must exclude it from the
    rebuilt `_project_registry` entirely, not just copy the value through
    like the other three dashboard metrics."""

    def test_active_status_produces_a_row(self) -> None:
        rows = [status_row("Активен"), contribution_row("2026-01-01", "<Имя1>", "Позитивный")]
        row, warnings = build_registry_row("<Project>", rows)
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "<Project>")
        self.assertEqual(row[2], "Активен")
        self.assertEqual(warnings, [])

    def test_inactive_status_excludes_the_project(self) -> None:
        rows = [status_row("Не активен"), contribution_row("2026-01-01", "<Имя1>", "Позитивный")]
        row, warnings = build_registry_row("<Project>", rows)
        self.assertIsNone(row, "Не активен must exclude the project, not just copy the status through")
        self.assertEqual(warnings, [])

    def test_missing_status_row_defaults_to_active_and_produces_a_row(self) -> None:
        rows = [contribution_row("2026-01-01", "<Имя1>", "Позитивный")]
        row, warnings = build_registry_row("<Project>", rows)
        self.assertIsNotNone(row)
        self.assertEqual(row[2], "Активен")

    def test_non_canonical_status_still_warns_even_though_excluded_is_not_triggered(self) -> None:
        rows = [status_row("Стоп")]
        row, warnings = build_registry_row("<Project>", rows)
        self.assertIsNotNone(row, "a non-canonical value is copied through as-is, not treated as inactive")
        self.assertEqual(len(warnings), 1)
        self.assertIn("Стоп", warnings[0])

    def test_inactive_status_warning_is_not_raised_since_it_is_canonical(self) -> None:
        rows = [status_row("Не активен")]
        _, warnings = build_registry_row("<Project>", rows)
        self.assertEqual(warnings, [], "Не активен is a canonical value, not a warning case")


if __name__ == "__main__":
    unittest.main()
