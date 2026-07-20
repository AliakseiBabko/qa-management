"""Unit tests for JSON contract and command regressions in qa_manage.py."""
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import argparse
import io

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import qa_manage

class TestJsonContract(unittest.TestCase):
    def test_json_argument_parser_error(self):
        parser = qa_manage.JsonArgumentParser(description="Test")
        parser.add_argument("--foo", required=True)

        with patch("sys.argv", ["script", "dummy", "--json"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                with self.assertRaises(SystemExit) as cm:
                    parser.parse_args()
                self.assertEqual(cm.exception.code, 1)
                output = mock_stdout.getvalue()
                data = json.loads(output)
                self.assertEqual(data["schema_version"], 1)
                self.assertFalse(data["ok"])
                self.assertEqual(data["command"], "dummy")
                self.assertTrue(len(data["errors"]) > 0)
                err_msg = data["errors"][0]
                self.assertTrue("--foo is required" in err_msg or "the following arguments are required: --foo" in err_msg)
                self.assertNotIn("human_lines", data)
                self.assertNotIn("exit_code", data)

    @patch("qa_manage.get_services_cached")
    @patch("qa_manage.find_queue")
    @patch("qa_manage.read_queue")
    @patch("qa_manage.write_queue")
    @patch("qa_manage.load_graph")
    def test_cmd_start_no_crash_after_write(self, mock_load_graph, mock_write_queue, mock_read_queue, mock_find_queue, mock_get_services):
        mock_find_queue.return_value = {"id": "sheet_id"}
        mock_read_queue.return_value = [{
            "Run ID": "test-run", "Status": "discovered", "Stage": "",
            "Scopes": "", "Source type": "raw_transcript", "Route variant": "",
            "Project": "", "Person": "", "Skills": "", "Entries": "",
            "Reason": ""
        }]
        mock_load_graph.return_value = {
            "sources": {"raw_transcript": {"skills": ["s1"], "entry": ["ws_doc"]}}
        }

        class Args:
            run_id = "test-run"
            source_type = "raw_transcript"
            variant = ""
            project = ""
            person = ""
            scope = []
            json = True

        with patch("pipeline_common.SKILL_INVOCATION_SOURCE_TYPES", {"raw_transcript"}):
            res = qa_manage.cmd_start(Args())

        self.assertTrue(res.ok)
        self.assertEqual(res.data["run_id"], "test-run")
        self.assertEqual(res.data["status"], "processing")
        self.assertEqual(res.exit_code, 0)
        self.assertTrue(mock_write_queue.called)

    @patch("qa_manage.get_services_cached")
    @patch("qa_manage.find_queue")
    @patch("qa_manage.read_queue")
    @patch("qa_manage.write_queue")
    @patch("closure_outcomes.get_or_create_sheet")
    def test_cmd_resolve_edge_no_crash_after_write(self, mock_get_or_create, mock_write_queue, mock_read_queue, mock_find_queue, mock_get_services):
        mock_find_queue.return_value = {"id": "sheet_id"}
        mock_read_queue.return_value = [{
            "Run ID": "test-run", "Status": "processing", "Stage": "closure",
            "Scopes": "", "Source type": "raw_transcript", "Route variant": "m1",
            "Project": "", "Person": "", "Skills": "", "Entries": "",
            "Reason": ""
        }]
        mock_sheet = MagicMock()
        mock_get_or_create.return_value = mock_sheet
        mock_services = MagicMock()
        mock_get_services.return_value = mock_services

        class Args:
            run_id = "test-run"
            source = "src"
            target = "tgt"
            outcome = "updated"
            reason = ""
            project = ""
            person = ""
            variant = ""
            actor = "agent"
            json = True

        with patch("closure_outcomes.edge_kind", return_value="direct"):
            with patch("closure_outcomes.require_scope"):
                res = qa_manage.cmd_resolve_edge(Args())

        self.assertTrue(res.ok)
        self.assertEqual(res.data["run_id"], "test-run")
        self.assertEqual(res.exit_code, 0)
        self.assertTrue(mock_write_queue.called)
        self.assertTrue(mock_services["sheets"].spreadsheets().values().append.called)

    @patch("qa_manage.get_services_cached")
    @patch("qa_manage.find_queue")
    @patch("qa_manage.read_queue")
    @patch("qa_manage.write_queue")
    @patch("qa_manage.load_review_context")
    @patch("qa_manage.evaluate_run")
    @patch("qa_manage.export_queue_terminal")
    def test_cmd_complete_tuple_unpacking_and_success(
        self, mock_export, mock_eval, mock_load_ctx, mock_write_queue,
        mock_read_queue, mock_find_queue, mock_get_services
    ):
        mock_find_queue.return_value = {"id": "sheet_id"}
        mock_read_queue.return_value = [{
            "Run ID": "test-run", "Status": "processing", "Stage": "closure",
            "Scopes": "", "Source type": "raw_transcript", "Route variant": "m1",
            "Project": "", "Person": "", "Skills": "", "Entries": "",
            "Reason": "", "Snapshot": "", "Completed": ""
        }]

        # Mock successful evaluation
        eval_res = qa_manage.EvaluationResult(
            ready_for_completion=True,
            entry_problems=[],
            unresolved_edges=[],
            warnings=[],
            snapshot_sha="12345678",
            snapshot_problem="",
            invocation_present=True
        )
        mock_eval.return_value = eval_res

        # Mock export returning tuple (sha, warnings)
        mock_export.return_value = ("commit-sha", ["bundle warning"])

        class Args:
            run_id = "test-run"
            json = True

        res = qa_manage.cmd_complete(Args())

        self.assertTrue(res.ok)
        self.assertEqual(res.data["completed"], True)
        self.assertEqual(res.data["terminal_commit"], "commit-sha")
        self.assertEqual(res.warnings, ["bundle warning"])
        self.assertEqual(res.exit_code, 0)

        # Verify completed state was written
        write_args = mock_write_queue.call_args[0][2]
        completed_row = next(r for r in write_args if r["Run ID"] == "test-run")
        self.assertEqual(completed_row["Status"], "completed")
        self.assertEqual(completed_row["Stage"], "done")

    @patch("qa_manage.get_services_cached")
    @patch("qa_manage.find_queue")
    @patch("qa_manage.read_queue")
    @patch("qa_manage.write_queue")
    @patch("qa_manage.load_review_context")
    @patch("qa_manage.evaluate_run")
    @patch("qa_manage.export_queue_terminal")
    def test_cmd_complete_failure_after_write(
        self, mock_export, mock_eval, mock_load_ctx, mock_write_queue,
        mock_read_queue, mock_find_queue, mock_get_services
    ):
        mock_find_queue.return_value = {"id": "sheet_id"}
        mock_read_queue.return_value = [{
            "Run ID": "test-run", "Status": "processing", "Stage": "closure",
            "Scopes": "", "Source type": "raw_transcript", "Route variant": "m1",
            "Project": "", "Person": "", "Skills": "", "Entries": "",
            "Reason": "", "Snapshot": "", "Completed": ""
        }]

        eval_res = qa_manage.EvaluationResult(
            ready_for_completion=True, entry_problems=[], unresolved_edges=[],
            warnings=[], snapshot_sha="12345678", snapshot_problem="", invocation_present=True
        )
        mock_eval.return_value = eval_res

        # Mock export failing (which means it raises SystemExit or Exception)
        mock_export.side_effect = SystemExit("mirror commit failed")

        class Args:
            run_id = "test-run"
            json = True

        with self.assertRaises(SystemExit) as cm:
            qa_manage.cmd_complete(Args())

        # The exception escapes to be caught by main(), but we verify the state BEFORE the crash was 'finalizing'
        write_args = mock_write_queue.call_args[0][2]
        row_written = next(r for r in write_args if r["Run ID"] == "test-run")
        self.assertEqual(row_written["Status"], "finalizing")
        self.assertEqual(row_written["Snapshot"], "12345678")


    def test_main_serialization(self):
        import qa_manage
        import json
        from io import StringIO

        test_cases = [
            (["qa_manage.py", "status", "--json"], "cmd_status", "status"),
            (["qa_manage.py", "--json", "status"], "cmd_status", "status"),
            (["qa_manage.py", "--json", "--debug", "status"], "cmd_status", "status"),
            (["qa_manage.py", "status", "--json", "--debug"], "cmd_status", "status"),
            (["qa_manage.py", "record-analysis", "run-1", "--summary", "x", "--json"], "cmd_record_analysis", "record-analysis"),
            (["qa_manage.py", "--json", "record-apply", "run-1", "--updated", "doc"], "cmd_record_apply", "record-apply"),
        ]

        for args, mock_cmd, cmd_name in test_cases:
            with patch("sys.argv", args), \
                 patch(f"qa_manage.{mock_cmd}", return_value=0), \
                 patch("sys.stdout", new_callable=StringIO) as mock_out:
                code = qa_manage.main()

            self.assertEqual(code, 0, f"Failed for args: {args}")
            output = mock_out.getvalue()
            data = json.loads(output)
            self.assertEqual(data["schema_version"], 1)
            self.assertTrue(data["ok"])
            self.assertEqual(data["command"], cmd_name)

if __name__ == "__main__":
    unittest.main()
