"""Unit tests for migrate_project_risk_schema.py.

Tests:
1. Pure migration transformation on legacy, clean, empty, and compliant inputs.
2. Idempotence: already compliant 2-tab data is preserved unchanged.
3. Safe dry-run behavior: no files written in dry-run mode.
4. Apply mode execution: writes compliant 14-col summary and 20-col risk items.
5. Legacy status handling: Migration State = 'Legacy — detection status unavailable', empty Prediction Status.
"""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / ".agents" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from migrate_project_risk_schema import (
    LEGACY_SUMMARY_HEADER,
    RISK_ITEMS_HEADER,
    SUMMARY_HEADER,
    apply_local_migration,
    migrate_single_project_data,
    plan_local_directory_migration,
)


class PureRiskMigrationTests(unittest.TestCase):
    def test_legacy_row_with_threat_generates_rsk_01(self):
        legacy_rows = [
            LEGACY_SUMMARY_HEADER,
            [
                "<Project>",
                "2026-07-15",
                "Средний",
                "Низкий",
                "Средний",
                "Низкий",
                "Низкий",
                "Недостаточное покрытие автотестами платежного шлюза",
                "Написать e2e тесты",
                "<Owner>",
                "2026-08-01",
            ],
        ]

        summary, items, state = migrate_single_project_data(legacy_rows, project_name="<Project>")

        self.assertEqual(state, "legacy_1_tab")
        self.assertEqual(summary[0], SUMMARY_HEADER)
        self.assertEqual(items[0], RISK_ITEMS_HEADER)

        # Summary row checks
        self.assertEqual(len(summary), 2)
        s_row = summary[1]
        self.assertEqual(s_row[0], "<Project>")
        self.assertEqual(s_row[1], "2026-07-15")
        self.assertEqual(s_row[2], "Средний")
        self.assertEqual(s_row[3], "RSK-01")  # Key risk ID assigned
        self.assertEqual(s_row[4], "Недостаточное покрытие автотестами платежного шлюза")
        self.assertEqual(s_row[5], "")  # Prediction status empty for legacy
        self.assertEqual(s_row[10], "Написать e2e тесты")
        self.assertEqual(s_row[11], "Средняя")
        self.assertEqual(s_row[12], "<Owner>")
        self.assertEqual(s_row[13], "2026-08-01")

        # Risk item row checks
        self.assertEqual(len(items), 2)
        i_row = items[1]
        self.assertEqual(i_row[0], "RSK-01")
        self.assertEqual(i_row[1], "<Project>")
        self.assertEqual(i_row[2], "Недостаточное покрытие автотестами платежного шлюза")
        self.assertEqual(i_row[3], "QA process")  # Dominant category inferred
        self.assertEqual(i_row[4], "Средний")
        self.assertEqual(i_row[5], "")  # First signal date empty for legacy
        self.assertEqual(i_row[6], "2026-07-15")  # Risk logged
        self.assertEqual(i_row[12], "")  # Prediction status empty for legacy
        self.assertEqual(i_row[14], "Legacy — detection status unavailable")
        self.assertEqual(i_row[17], "Написать e2e тесты")
        self.assertEqual(i_row[18], "<Owner>")
        self.assertEqual(i_row[19], "Mitigating")

    def test_legacy_row_clean_low_risk(self):
        legacy_rows = [
            LEGACY_SUMMARY_HEADER,
            [
                "<Project>",
                "2026-07-15",
                "Низкий",
                "Низкий",
                "Низкий",
                "Низкий",
                "Низкий",
                "",
                "",
                "<Owner>",
                "2026-08-01",
            ],
        ]

        summary, items, state = migrate_single_project_data(legacy_rows, project_name="<Project>")
        self.assertEqual(state, "legacy_1_tab")
        self.assertEqual(len(summary), 2)
        self.assertEqual(summary[1][3], "")  # No key risk ID needed
        self.assertEqual(len(items), 1)  # Only header in items

    def test_already_compliant_is_idempotent(self):
        compliant_summary = [
            SUMMARY_HEADER,
            [
                "<Project>",
                "2026-08-17",
                "Низкий",
                "RSK-01",
                "Стабильный релизный цикл",
                "Detected Early",
                "Низкий",
                "Низкий",
                "Низкий",
                "Низкий",
                "Мониторинг",
                "Высокая",
                "<Owner>",
                "2026-09-01",
            ],
        ]
        compliant_items = [
            RISK_ITEMS_HEADER,
            [
                "RSK-01",
                "<Project>",
                "Statement",
                "QA process",
                "Низкий",
                "2026-08-01",
                "2026-08-05",
                "2026-09-15",
                "",
                "",
                "2026-08-17",
                "2026-08-17",
                "Detected Early",
                "Early signal",
                "Normal",
                "Высокая",
                "evidence_log: row 1",
                "Mitigation",
                "<Owner>",
                "Mitigating",
            ],
        ]

        summary, items, state = migrate_single_project_data(
            compliant_summary, project_name="<Project>", existing_items_rows=compliant_items
        )
        self.assertEqual(state, "already_compliant")
        self.assertEqual(summary, compliant_summary)
        self.assertEqual(items, compliant_items)


class LocalDirectoryMigrationLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create a mock legacy project folder
        self.proj_dir = self.root / "Project_Alpha"
        self.private_dir = self.proj_dir / "private"
        self.private_dir.mkdir(parents=True)

        self.legacy_csv = self.private_dir / "светофор_рисков_проекта.csv"
        with self.legacy_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(LEGACY_SUMMARY_HEADER)
            writer.writerow([
                "Project_Alpha",
                "2026-06-01",
                "Высокий",
                "Высокий",
                "Низкий",
                "Низкий",
                "Низкий",
                "Отставание по релизному графику на 3 недели",
                "Пересмотр скоупа релиза",
                "Lead M2",
                "2026-06-15",
            ])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_plan_and_apply_lifecycle(self):
        # 1. Plan dry-run
        plans = plan_local_directory_migration(self.root)
        self.assertEqual(len(plans), 1)
        plan = plans[0]
        self.assertEqual(plan.project, "Project_Alpha")
        self.assertTrue(plan.needs_migration)
        self.assertEqual(plan.current_state, "legacy_1_tab")
        self.assertEqual(plan.risk_items_count, 1)

        # Confirm no items file created yet in dry-run
        items_csv = self.private_dir / "project_risk_items.csv"
        self.assertFalse(items_csv.is_file())

        # 2. Apply migration
        res = apply_local_migration(plan)
        self.assertEqual(res["status"], "APPLIED")
        self.assertTrue(items_csv.is_file())

        # Read back applied files
        with self.legacy_csv.open("r", encoding="utf-8-sig") as f:
            updated_summary = list(csv.reader(f))
        with items_csv.open("r", encoding="utf-8-sig") as f:
            updated_items = list(csv.reader(f))

        self.assertEqual(updated_summary[0], SUMMARY_HEADER)
        self.assertEqual(updated_summary[1][3], "RSK-01")
        self.assertEqual(updated_items[0], RISK_ITEMS_HEADER)
        self.assertEqual(updated_items[1][0], "RSK-01")
        self.assertEqual(updated_items[1][14], "Legacy — detection status unavailable")

        # 3. Idempotent re-plan
        re_plans = plan_local_directory_migration(self.root)
        self.assertEqual(len(re_plans), 1)
        self.assertFalse(re_plans[0].needs_migration)
        self.assertEqual(re_plans[0].current_state, "already_compliant")


if __name__ == "__main__":
    unittest.main()
