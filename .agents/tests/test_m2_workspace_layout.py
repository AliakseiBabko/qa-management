from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import m2_workspace_layout as layout
import migrate_m2_visibility_layout as migration


class TestM2WorkspaceLayout(unittest.TestCase):
    def test_project_private_paths(self) -> None:
        for role in (
            "project_metrics",
            "project_risk",
            "process_checklist",
            "project_development_plan",
            "evidence_log",
            "action_items",
        ):
            self.assertEqual(("private",), layout.canonical_folder_parts(role))

    def test_team_shared_path(self) -> None:
        self.assertEqual(
            ("team_shared",), layout.canonical_folder_parts("qa_process_metrics")
        )

    def test_person_visibility_paths(self) -> None:
        self.assertEqual(
            ("people", "Person A", "shared"),
            layout.canonical_folder_parts("individual_metrics", "Person A"),
        )
        self.assertEqual(
            ("private", "people", "Person A"),
            layout.canonical_folder_parts("individual_metrics_internal", "Person A"),
        )

    def test_person_role_requires_scope(self) -> None:
        with self.assertRaises(ValueError):
            layout.canonical_folder_parts("individual_metrics")

    def test_document_candidates_prefer_canonical_and_deduplicate(self) -> None:
        canonical = {"id": "canonical"}
        legacy = {"id": "legacy"}
        with mock.patch.object(
            layout, "find_folder_path", side_effect=[canonical, legacy]
        ):
            result = layout.document_folder_candidates(
                object(), "project", "individual_metrics", "Person A"
            )
        self.assertEqual([canonical, legacy], result)

    def test_project_people_union_public_and_private(self) -> None:
        public = {"id": "public"}
        private = {"id": "private"}
        children = {
            "public": [
                {"name": "Person A", "mimeType": layout.FOLDER_MIME},
            ],
            "private": [
                {"name": "person a", "mimeType": layout.FOLDER_MIME},
                {"name": "Person B", "mimeType": layout.FOLDER_MIME},
            ],
        }
        with mock.patch.object(
            layout, "find_folder_path", side_effect=[public, private]
        ), mock.patch.object(
            layout, "list_children", side_effect=lambda _drive, folder_id: children[folder_id]
        ):
            people = layout.list_project_people(object(), "project")
        self.assertEqual(["Person A", "Person B"], people)

    def test_person_artifact_classification(self) -> None:
        self.assertEqual(
            "individual_metrics",
            migration.person_item_role(
                {"name": "individual_metrics", "mimeType": layout.SHEET_MIME},
                "Person A",
            ),
        )
        self.assertEqual(
            "m2_people_1to1_file",
            migration.person_item_role(
                {"name": "Person A 1to1", "mimeType": layout.SHEET_MIME},
                "Person A",
            ),
        )

    def test_unknown_person_artifact_is_not_moved(self) -> None:
        self.assertIsNone(
            migration.person_item_role(
                {"name": "unclassified", "mimeType": layout.DOC_MIME},
                "Person A",
            )
        )

    def test_folder_roles_move_under_private_parent(self) -> None:
        project = {"id": "project-id", "name": "Project A"}
        item = {
            "id": "folder-id",
            "name": "m2_input",
            "mimeType": layout.FOLDER_MIME,
        }
        with mock.patch.object(migration, "list_children", return_value=[item]):
            moves, ambiguous = migration.plan_project(object(), project)
        self.assertFalse(ambiguous)
        self.assertEqual(("private",), moves[0].target_parts)

    def test_predecessor_artifacts_are_archived(self) -> None:
        project = {"id": "project-id", "name": "Project A"}
        items = [
            {
                "id": "old-project",
                "name": "project_metrics_predecessor_2026-01-02",
                "mimeType": layout.SHEET_MIME,
            },
        ]
        with mock.patch.object(migration, "list_children", return_value=items):
            moves, ambiguous = migration.plan_project(object(), project)
        self.assertFalse(ambiguous)
        self.assertEqual("archive", moves[0].destination)
        self.assertEqual(("private",), moves[0].target_parts)

    def test_project_context_is_private(self) -> None:
        project = {"id": "project-id", "name": "Project A"}
        items = [
            {
                "id": "context",
                "name": "_PROJECT_CONTEXT.md",
                "mimeType": "text/markdown",
            },
        ]
        with mock.patch.object(migration, "list_children", return_value=items):
            moves, ambiguous = migration.plan_project(object(), project)
        self.assertFalse(ambiguous)
        self.assertEqual("live", moves[0].destination)
        self.assertEqual(("private",), moves[0].target_parts)


if __name__ == "__main__":
    unittest.main()
