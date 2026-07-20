import argparse
import datetime
import io
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
                    with patch("sys.stdout", new_callable=io.StringIO):
                        code = show_project_state.main()
                        self.assertEqual(code, 0)

        self.mock_services["drive"].files().create.assert_not_called()
        self.mock_services["sheets"].spreadsheets().create.assert_not_called()
        self.mock_services["docs"].documents().create.assert_not_called()
        self.mock_services["sheets"].spreadsheets().values().update.assert_not_called()

    @patch("show_project_state.get_services")
    def test_json_parser_error(self, mock_get_services):
        with patch("sys.argv", ["show_project_state.py", "--limit", "0", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = show_project_state.main()
                self.assertEqual(code, 1)
                output = mock_out.getvalue()
                res = json.loads(output)
                self.assertFalse(res["ok"])
                self.assertIn("Invalid --limit", res["errors"][0])
                self.assertEqual(res["command"], "show_project_state")
        mock_get_services.assert_not_called()

    def test_legacy_json_output_captured(self):
        with patch("sys.argv", ["show_project_state.py", "--project", "MyProject", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                with patch("show_project_state.do_run") as mock_run:
                    mock_run.return_value = (show_project_state.build_json_envelope(True, "show_project_state", {"output": "buffered data here"}, [], []), 0)
                    code = show_project_state.main()

                self.assertEqual(code, 0)
                output = mock_out.getvalue()
                res = json.loads(output)
                self.assertTrue(res["ok"])
                self.assertEqual(res["data"]["output"], "buffered data here")

    @patch("show_project_state.get_services")
    def test_validation_registry_rejects_project(self, mock_get_services):
        with patch("sys.argv", ["show_project_state.py", "--document", "_people_registry", "--project", "Proj", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = show_project_state.main()
                self.assertEqual(code, 1)
                res = json.loads(mock_out.getvalue())
                self.assertFalse(res["ok"])
                self.assertIn("does not accept --project or --person", res["errors"][0])
        mock_get_services.assert_not_called()

    @patch("show_project_state.get_services")
    def test_incompatible_options(self, mock_get_services):
        with patch("sys.argv", ["show_project_state.py", "--document", "doc", "--summary", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = show_project_state.main()
                self.assertEqual(code, 1)
                res = json.loads(mock_out.getvalue())
                self.assertIn("Incompatible options", res["errors"][0])
        mock_get_services.assert_not_called()

    @patch("show_project_state.get_services")
    def test_targeted_options_without_document(self, mock_get_services):
        with patch("sys.argv", ["show_project_state.py", "--person", "Bob", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = show_project_state.main()
                self.assertEqual(code, 1)
                res = json.loads(mock_out.getvalue())
                self.assertIn("require --document", res["errors"][0])
        mock_get_services.assert_not_called()

    def test_unexpected_exception_envelope(self):
        with patch("sys.argv", ["show_project_state.py", "--project", "Proj", "--json"]):
            with patch("show_project_state.parse_args") as mock_args:
                mock_args.side_effect = Exception("Surprise!")
                with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                    code = show_project_state.main()
                    self.assertEqual(code, 1)
                    res = json.loads(mock_out.getvalue())
                    self.assertIn("Surprise!", res["errors"][0])

    @patch("show_project_state.get_services")
    @patch("show_project_state.find_folder")
    def test_iso_date_filtering(self, mock_find_folder, mock_get_services):
        mock_get_services.return_value = self.mock_services
        mock_find_folder.return_value = {"id": "m2_root"}

        test_args = ["--project", "MyProject", "--document", "evidence_log", "--since", "2023-01-01", "--json"]
        with patch("sys.argv", ["show_project_state.py"] + test_args):
            with patch("show_project_state.find_sheet_in_folder") as mock_find_sheet:
                mock_find_sheet.return_value = {"id": "fake_id"}
                with patch("show_project_state.read_sheet_values") as mock_read:
                    mock_read.return_value = [
                        ["Date", "Entry"],
                        ["2022-12-31", "Old"],
                        ["2023-01-05", "New"],
                        ["invalid_date", "Ignored"]
                    ]
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                        code = show_project_state.main()
                        self.assertEqual(code, 0)
                        res = json.loads(mock_out.getvalue())
                        content = res["data"]["documents"][0]["content"]
                        self.assertEqual(len(content), 2)
                        self.assertEqual(content[1][0], "2023-01-05")

    @patch("show_project_state.get_services")
    @patch("show_project_state.find_folder")
    def test_sheet_truncation(self, mock_find_folder, mock_get_services):
        mock_get_services.return_value = self.mock_services
        mock_find_folder.return_value = {"id": "m2_root"}

        test_args = ["--project", "MyProject", "--document", "project_metrics", "--limit", "1", "--json"]
        with patch("sys.argv", ["show_project_state.py"] + test_args):
            with patch("show_project_state.find_sheet_in_folder") as mock_find_sheet:
                mock_find_sheet.return_value = {"id": "fake_id"}
                with patch("show_project_state.read_sheet_values") as mock_read:
                    mock_read.return_value = [["H1"], ["V1"], ["V2"]]
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                        code = show_project_state.main()
                        self.assertEqual(code, 0)
                        res = json.loads(mock_out.getvalue())
                        doc_res = res["data"]["documents"][0]
                        self.assertTrue(doc_res["truncated"])
                        self.assertEqual(doc_res["total_count"], 2)
                        self.assertEqual(doc_res["returned_count"], 1)
                        self.assertEqual(doc_res["content"][1][0], "V2")

    @patch("show_project_state.get_services")
    @patch("show_project_state.find_folder")
    def test_doc_truncation(self, mock_find_folder, mock_get_services):
        mock_get_services.return_value = self.mock_services
        mock_find_folder.return_value = {"id": "m2_root"}

        test_args = ["--project", "MyProject", "--document", "project_development_plan", "--limit", "1", "--json"]
        with patch("sys.argv", ["show_project_state.py"] + test_args):
            with patch("show_project_state.find_doc") as mock_find_doc:
                mock_find_doc.return_value = {"id": "fake_id"}
                with patch("show_project_state.read_doc_paragraphs") as mock_read:
                    mock_read.return_value = ["Para1", "Para2"]
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                        code = show_project_state.main()
                        self.assertEqual(code, 0)
                        res = json.loads(mock_out.getvalue())
                        doc_res = res["data"]["documents"][0]
                        self.assertTrue(doc_res["truncated"])
                        self.assertEqual(doc_res["total_count"], 2)
                        self.assertEqual(doc_res["returned_count"], 1)
                        self.assertEqual(doc_res["content"], ["Para1"])

    @patch("show_project_state.get_services")
    @patch("show_project_state.find_folder")
    def test_missing_document(self, mock_find_folder, mock_get_services):
        mock_get_services.return_value = self.mock_services
        mock_find_folder.return_value = {"id": "m2_root"}

        test_args = ["--project", "MyProject", "--document", "project_metrics", "--json"]
        with patch("sys.argv", ["show_project_state.py"] + test_args):
            with patch("show_project_state.find_sheet_in_folder") as mock_find_sheet:
                mock_find_sheet.return_value = None
                with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                    code = show_project_state.main()
                    self.assertEqual(code, 0)
                    res = json.loads(mock_out.getvalue())
                    doc_res = res["data"]["documents"][0]
                    self.assertTrue(doc_res["missing"])
                    self.assertEqual(doc_res["content"], [])

    @patch("show_project_state.get_services")
    @patch("show_project_state.find_folder")
    def test_legacy_combined_project_registries(self, mock_find_folder, mock_get_services):
        mock_get_services.return_value = self.mock_services
        mock_find_folder.return_value = {"id": "m2_root"}

        test_args = ["--project", "MyProject", "--registries", "--json"]
        with patch("sys.argv", ["show_project_state.py"] + test_args):
            with patch("show_project_state.dump_sheet") as mock_dump_sheet, patch("show_project_state.dump_project") as mock_dump_project:
                with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                    code = show_project_state.main()
                    self.assertEqual(code, 0)
                    res = json.loads(mock_out.getvalue())
                    self.assertTrue(res["ok"])
                    self.assertIn("===== _people_registry =====", res["data"]["output"])
                    mock_dump_project.assert_called_once()
                    self.assertEqual(mock_dump_sheet.call_count, 3)

if __name__ == '__main__':
    unittest.main()

    @patch("show_project_state.get_services")
    @patch("show_project_state.find_folder")
    def test_multiple_documents(self, mock_find_folder, mock_get_services):
        mock_get_services.return_value = self.mock_services
        mock_find_folder.side_effect = lambda drive, parent, name: {"id": "fake_id"}
        
        test_args = ["--project", "MyProject", "--document", "project_metrics", "--document", "project_risk", "--json"]
        with patch("sys.argv", ["show_project_state.py"] + test_args):
            with patch("show_project_state.find_sheet_in_folder") as mock_find_sheet:
                mock_find_sheet.return_value = {"id": "fake_sheet_id"}
                with patch("show_project_state.read_sheet_values") as mock_read:
                    mock_read.return_value = [["H1"], ["V1"]]
                    with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                        code = show_project_state.main()
                        self.assertEqual(code, 0)
                        out_json = json.loads(mock_out.getvalue())
                        self.assertTrue(out_json["ok"])
                        self.assertEqual(len(out_json["data"]["documents"]), 2)
                        self.assertEqual(out_json["data"]["documents"][0]["name"], "project_metrics")
                        self.assertEqual(out_json["data"]["documents"][1]["name"], "project_risk")
