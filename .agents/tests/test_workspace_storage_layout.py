import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import migrate_workspace_storage_layout as migration  # noqa: E402


class WorkspaceStorageLayoutTests(unittest.TestCase):
    def test_plan_consolidates_legacy_roots(self):
        root = {
            "90_Archive": {"id": "archive"},
            "30_Reference": {"id": "reference"},
            "_System": {"id": "system"},
        }
        archive_children = {
            "Processed_Sources": {"id": "processed"},
            "_git_mirror_backups": {"id": "backups"},
            "legacy_output": {"id": "legacy"},
        }
        with patch.object(migration, "child_folders", side_effect=[root, archive_children]):
            plan, errors = migration.build_plan({"drive": object()})

        self.assertEqual(errors, [])
        triples = {(item.action, item.source, item.target) for item in plan}
        self.assertIn(("rename", "90_Archive", "90_Storage"), triples)
        self.assertIn(("move_rename", "30_Reference", "90_Storage/Reference"), triples)
        self.assertIn(("move", "_System", "90_Storage/_System"), triples)
        self.assertIn(("rename", "90_Storage/_git_mirror_backups", "90_Storage/Backups"), triples)
        self.assertIn(("move_rename", "90_Storage/legacy_output", "90_Storage/Retired/legacy_output"), triples)

    def test_plan_fails_when_both_storage_roots_exist(self):
        root = {
            "90_Archive": {"id": "archive"},
            "90_Storage": {"id": "storage"},
        }
        with patch.object(migration, "child_folders", return_value=root):
            plan, errors = migration.build_plan({"drive": object()})
        self.assertEqual(plan, [])
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
