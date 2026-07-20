import argparse
import datetime
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import show_project_state

class TestShowProjectStateTargeted(unittest.TestCase):
    def setUp(self):
        self.mock_services = {
            "drive": MagicMock(),
            "docs": MagicMock(),
            "sheets": MagicMock(),
        }
        
    @patch("show_project_state.get_services")
    @patch("show_project_state.find_folder")
    def test_read_only_isolation(self, mock_find_folder, mock_get_services):
        mock_get_services.return_value = self.mock_services
        mock_find_folder.return_value = {"id": "m2_root"}
        
        test_args = ["--project", "MyProject", "--document", "project_metrics", "--limit", "20"]
        with patch("sys.argv", ["show_project_state.py"] + test_args):
            with patch("show_project_state.find_sheet_in_folder") as mock_find_sheet:
                mock_find_sheet.return_value = {"id": "fake_id"}
                with patch("show_project_state.read_sheet_values") as mock_read:
                    mock_read.return_value = [["H1"], ["V1"]]
                    res = show_project_state.do_run()
                    
        self.mock_services["drive"].files().create.assert_not_called()
        self.mock_services["sheets"].spreadsheets().create.assert_not_called()
        self.mock_services["docs"].documents().create.assert_not_called()
        self.mock_services["sheets"].spreadsheets().values().update.assert_not_called()

    @patch("show_project_state.get_services")
    @patch("show_project_state.find_folder")
    def test_json_envelope_output(self, mock_find_folder, mock_get_services):
        mock_get_services.return_value = self.mock_services
        mock_find_folder.return_value = {"id": "m2_root"}
        
        test_args = ["--summary", "--json"]
        with patch("sys.argv", ["show_project_state.py"] + test_args):
            with patch("show_project_state.project_people_counts") as mock_counts:
                mock_counts.return_value = {"ProjectA": "Bob"}
                with patch("show_project_state.summarize_project") as mock_sum:
                    mock_sum.return_value = "ProjectA sum"
                    res = show_project_state.do_run()
                    
        self.assertTrue(res["ok"])
        self.assertIn("output", res["data"])
        self.assertEqual(res["data"]["output"], ["ProjectA sum"])

    @patch("show_project_state.find_folder")
    def test_validation_registry_rejects_project(self, mock_find_folder):
        mock_find_folder.return_value = {"id": "m2_root"}
        args = argparse.Namespace(
            project="MyProject", person=None, summary=False, registries=False,
            document=["_people_registry"], since=None, limit=20, json=True,
            credentials="fake", token="fake"
        )
        
        res = show_project_state.fetch_targeted_docs(self.mock_services, args, "m2_root")
        self.assertEqual(len(res["doc_results"]), 0)
        self.assertIn("does not accept --project or --person", res["errors"][0])

    @patch("show_project_state.find_folder")
    def test_validation_person_doc_requires_person(self, mock_find_folder):
        mock_find_folder.return_value = {"id": "m2_root"}
        args = argparse.Namespace(
            project="MyProject", person=None, summary=False, registries=False,
            document=["individual_metrics"], since=None, limit=20, json=True,
            credentials="fake", token="fake"
        )
        
        res = show_project_state.fetch_targeted_docs(self.mock_services, args, "m2_root")
        self.assertEqual(len(res["doc_results"]), 0)
        self.assertIn("requires both --project and --person", res["errors"][0])
        
    @patch("show_project_state.find_folder")
    def test_validation_since_rejection_for_docs(self, mock_find_folder):
        mock_find_folder.return_value = {"id": "m2_root"}
        args = argparse.Namespace(
            project="MyProject", person=None, summary=False, registries=False,
            document=["project_development_plan"], since="2023-10-01", limit=20, json=True,
            credentials="fake", token="fake"
        )
        
        res = show_project_state.fetch_targeted_docs(self.mock_services, args, "m2_root")
        self.assertEqual(len(res["doc_results"]), 0)
        self.assertIn("does not support --since filtering", res["errors"][0])

    @patch("show_project_state.find_folder")
    @patch("show_project_state.find_sheet_in_folder")
    @patch("show_project_state.read_sheet_values")
    def test_date_filtering_and_limits(self, mock_read, mock_find_sheet, mock_find_folder):
        mock_find_folder.return_value = {"id": "some_folder"}
        mock_find_sheet.return_value = {"id": "evidence_sheet"}
        mock_read.return_value = [
            ["Date", "Entry"],
            ["2023-09-01", "Old"],
            ["2023-10-01", "Match 1"],
            ["not-a-date", "Match invalid ignored"],
            ["2023-10-03", "Match 3"],
            ["2023-10-04", "Match 4"],
        ]
        
        args = argparse.Namespace(
            project="MyProject", person=None, summary=False, registries=False,
            document=["evidence_log"], since="2023-10-01", limit=2, json=True,
            credentials="fake", token="fake", evidence_tail=10
        )
        
        res = show_project_state.fetch_targeted_docs(self.mock_services, args, "m2_root")
        self.assertEqual(len(res["errors"]), 0)
        doc = res["doc_results"][0]
        self.assertFalse(doc["missing"])
        self.assertEqual(doc["total_count"], 3) # Match 1, Match 3, Match 4
        self.assertEqual(doc["returned_count"], 2)
        self.assertTrue(doc["truncated"])
        self.assertEqual(doc["content"], [
            ["Date", "Entry"],
            ["2023-10-03", "Match 3"],
            ["2023-10-04", "Match 4"],
        ])
        
    @patch("show_project_state.find_folder")
    @patch("show_project_state.find_doc")
    @patch("show_project_state.read_doc_paragraphs")
    def test_doc_paragraphs_limit(self, mock_read_doc, mock_find_doc, mock_find_folder):
        mock_find_folder.return_value = {"id": "some_folder"}
        mock_find_doc.return_value = {"id": "plan_doc"}
        mock_read_doc.return_value = ["Para 1", "Para 2", "Para 3", "Para 4"]
        
        args = argparse.Namespace(
            project="MyProject", person=None, summary=False, registries=False,
            document=["project_development_plan"], since=None, limit=2, json=True,
            credentials="fake", token="fake", evidence_tail=10
        )
        
        res = show_project_state.fetch_targeted_docs(self.mock_services, args, "m2_root")
        self.assertEqual(len(res["errors"]), 0)
        doc = res["doc_results"][0]
        self.assertEqual(doc["total_count"], 4)
        self.assertEqual(doc["returned_count"], 2)
        self.assertTrue(doc["truncated"])
        self.assertEqual(doc["content"], ["Para 1", "Para 2"])
        
    def test_invalid_date_parse_args(self):
        with patch("sys.argv", ["show_project_state.py", "--since", "bad-date"]):
            with self.assertRaises(SystemExit):
                show_project_state.parse_args()

if __name__ == '__main__':
    unittest.main()
