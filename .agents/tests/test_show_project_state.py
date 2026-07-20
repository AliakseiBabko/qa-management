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

    def test_json_parser_error(self):
        with patch("sys.argv", ["show_project_state.py", "--limit", "0", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = show_project_state.main()
                self.assertEqual(code, 1)
                output = mock_out.getvalue()
                res = json.loads(output)
                self.assertFalse(res["ok"])
                self.assertIn("Invalid --limit", res["errors"][0])

    def test_legacy_json_output_captured(self):
        with patch("sys.argv", ["show_project_state.py", "--project", "MyProject", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                with patch("show_project_state.do_run") as mock_run:
                    mock_run.return_value = (show_project_state.build_json_envelope(True, "cmd", {"output": "buffered data here"}, [], []), 0)
                    code = show_project_state.main()
                    
                self.assertEqual(code, 0)
                output = mock_out.getvalue()
                res = json.loads(output)
                self.assertTrue(res["ok"])
                self.assertEqual(res["data"]["output"], "buffered data here")

    def test_validation_registry_rejects_project(self):
        with patch("sys.argv", ["show_project_state.py", "--document", "_people_registry", "--project", "Proj", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                with patch("show_project_state.get_services") as mock_get_services:
                    mock_get_services.return_value = self.mock_services
                    with patch("show_project_state.find_folder") as mock_find_folder:
                        mock_find_folder.return_value = {"id": "m2_root"}
                        code = show_project_state.main()
                        self.assertEqual(code, 1)
                        res = json.loads(mock_out.getvalue())
                        self.assertFalse(res["ok"])
                        self.assertIn("does not accept --project or --person", res["errors"][0])

    def test_incompatible_options(self):
        with patch("sys.argv", ["show_project_state.py", "--document", "doc", "--summary", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = show_project_state.main()
                self.assertEqual(code, 1)
                res = json.loads(mock_out.getvalue())
                self.assertIn("Incompatible options", res["errors"][0])

    def test_targeted_options_without_document(self):
        with patch("sys.argv", ["show_project_state.py", "--person", "Bob", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = show_project_state.main()
                self.assertEqual(code, 1)
                res = json.loads(mock_out.getvalue())
                self.assertIn("require --document", res["errors"][0])

    def test_unexpected_exception_envelope(self):
        with patch("sys.argv", ["show_project_state.py", "--project", "Proj", "--json"]):
            with patch("show_project_state.parse_args") as mock_args:
                mock_args.side_effect = Exception("Surprise!")
                with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                    code = show_project_state.main()
                    self.assertEqual(code, 1)
                    res = json.loads(mock_out.getvalue())
                    self.assertIn("Surprise!", res["errors"][0])

if __name__ == '__main__':
    unittest.main()
