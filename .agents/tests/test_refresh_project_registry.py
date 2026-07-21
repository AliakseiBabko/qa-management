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

from refresh_project_registry import contribution_summary


def contribution_row(date: str, name: str, status: str, explanation: str = "x") -> list[str]:
    return ["<Project>", date, f"Вклад в проект: {name}", status, explanation, "M2"]


class ContributionSummaryDedupeTests(unittest.TestCase):
    def test_single_row_per_person_unaffected(self) -> None:
        rows = [contribution_row("2026-01-01", "<Имя1>", "Позитивный")]
        label, people = contribution_summary(rows)
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
        label, people = contribution_summary(rows)
        self.assertEqual(label, "Смешанный (<Имя1>)")
        self.assertEqual(people, ["<Имя1>"], "duplicate must collapse to one name, not '<Имя1>, <Имя1>'")

    def test_duplicate_rows_keep_latest_status_even_if_it_changed(self) -> None:
        rows = [
            contribution_row("2026-01-01", "<Имя1>", "Негативный", "old"),
            contribution_row("2026-02-01", "<Имя1>", "Позитивный", "improved"),
        ]
        label, people = contribution_summary(rows)
        self.assertEqual(label, "Позитивный (<Имя1>)")
        self.assertEqual(people, ["<Имя1>"])

    def test_out_of_order_rows_still_resolve_to_latest_date(self) -> None:
        # Defensive against append order not matching date order.
        rows = [
            contribution_row("2026-02-01", "<Имя1>", "Позитивный", "newer"),
            contribution_row("2026-01-01", "<Имя1>", "Негативный", "older"),
        ]
        label, people = contribution_summary(rows)
        self.assertEqual(label, "Позитивный (<Имя1>)")

    def test_multiple_distinct_people_each_kept_once(self) -> None:
        rows = [
            contribution_row("2026-01-01", "<Имя1>", "Позитивный"),
            contribution_row("2026-01-01", "<Имя2>", "Негативный"),
            contribution_row("2026-02-01", "<Имя1>", "Позитивный"),
        ]
        label, people = contribution_summary(rows)
        self.assertEqual(label, "Негативный (<Имя2>)")
        self.assertEqual(sorted(people), ["<Имя1>", "<Имя2>"])

    def test_unknown_status_kept_separate_and_deduped(self) -> None:
        rows = [
            contribution_row("2026-01-01", "<Имя1>", ""),
            contribution_row("2026-02-01", "<Имя1>", ""),
        ]
        label, people = contribution_summary(rows)
        self.assertEqual(label, "Неизвестно (данных недостаточно по <Имя1>)")
        self.assertEqual(people, ["<Имя1>"])


if __name__ == "__main__":
    unittest.main()
