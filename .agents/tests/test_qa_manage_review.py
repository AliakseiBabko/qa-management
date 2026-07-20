"""Unit tests for qa_manage evaluation contract."""
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import qa_manage

class TestEvaluateRun(unittest.TestCase):
    def setUp(self):
        self.mock_graph = {
            "sources": {
                "raw_transcript": {
                    "entry": ["10_M1_People_Management/<Person>/individual_development_plan.gdoc"],
                    "routes": {
                        "m1": {"skills": ["s1"]},
                        "m2": {"skills": ["s2"]}
                    }
                }
            },
            "documents": {
                "10_M1_People_Management/<Person>/individual_development_plan.gdoc": {
                    "downstream": [{"to": "_m1_timeline.csv", "kind": "direct"}]
                },
                "_m1_timeline.csv": {}
            }
        }

    def test_evaluate_run_success(self):
        ctx = MagicMock()
        ctx.row = {
            "Run ID": "test-run", "Status": "processing", "Stage": "closure",
            "Scopes": '[["", "Alice"]]', "Source type": "raw_transcript",
            "Route variant": "m1",
            "Entries": '{"|Alice": {"10_M1_People_Management/<Person>/individual_development_plan.gdoc": ["updated", ""]}}',
            "Started": "2023-10-01T10:00:00Z", "Last mutation": "2023-10-01T10:05:00Z"
        }
        ctx.graph = self.mock_graph
        ctx.all_rows = [
            {"Source": "10_M1_People_Management/Alice/individual_development_plan.gdoc",
             "Target": "_m1_timeline.csv", "Outcome": "updated", "Person": "Alice",
             "Project": "", "Route variant": "m1", "Timestamp": "2023-10-01T10:06:00Z",
             "Source node": "10_M1_People_Management/<Person>/individual_development_plan.gdoc",
             "Target node": "_m1_timeline.csv",
             "Run ID": "test-run"}
        ]
        ctx.inv_rows = [["Headers"], ["... run:test-run ..."]]
        ctx.dirty = False
        ctx.log_entries = [{"run": "test-run", "sha": "12345678"}]

        with patch("qa_manage.check_snapshot", return_value=("12345678", "")):
            res = qa_manage.evaluate_run(ctx)

        self.assertTrue(res.ready_for_completion)
        self.assertEqual(len(res.entry_problems), 0)
        self.assertEqual(len(res.unresolved_edges), 0)
        self.assertTrue(res.invocation_present)
        self.assertEqual(res.snapshot_sha, "12345678")
        self.assertEqual(res.snapshot_problem, "")

    def test_evaluate_run_unresolved_edge(self):
        ctx = MagicMock()
        ctx.row = {
            "Run ID": "test-run", "Status": "processing", "Stage": "closure",
            "Scopes": '[["", "Alice"]]', "Source type": "raw_transcript",
            "Route variant": "m1",
            "Entries": '{"|Alice": {"10_M1_People_Management/<Person>/individual_development_plan.gdoc": ["updated", ""]}}',
            "Started": "2023-10-01T10:00:00Z", "Last mutation": "2023-10-01T10:05:00Z"
        }
        ctx.graph = self.mock_graph
        ctx.all_rows = [] # Missing edge resolution
        ctx.inv_rows = [["Headers"], ["... run:test-run ..."]]
        ctx.dirty = False
        ctx.log_entries = [{"run": "test-run", "sha": "12345678"}]

        with patch("qa_manage.check_snapshot", return_value=("12345678", "")):
            res = qa_manage.evaluate_run(ctx)

        self.assertFalse(res.ready_for_completion)
        self.assertEqual(len(res.unresolved_edges), 1)
        self.assertIn("_m1_timeline.csv", res.unresolved_edges[0])

    def test_evaluate_run_missing_invocation(self):
        ctx = MagicMock()
        ctx.row = {
            "Run ID": "test-run", "Status": "processing", "Stage": "closure",
            "Scopes": '[["", "Alice"]]', "Source type": "raw_transcript",
            "Route variant": "m1",
            "Entries": '{"|Alice": {"10_M1_People_Management/<Person>/individual_development_plan.gdoc": ["updated", ""]}}',
            "Started": "2023-10-01T10:00:00Z", "Last mutation": "2023-10-01T10:05:00Z"
        }
        ctx.graph = self.mock_graph
        ctx.all_rows = [
            {"Source": "10_M1_People_Management/Alice/individual_development_plan.gdoc",
             "Target": "_m1_timeline.csv", "Outcome": "updated", "Person": "Alice",
             "Project": "", "Route variant": "m1", "Timestamp": "2023-10-01T10:06:00Z",
             "Source node": "10_M1_People_Management/<Person>/individual_development_plan.gdoc",
             "Target node": "_m1_timeline.csv",
             "Run ID": "test-run"}
        ]
        ctx.inv_rows = [["Headers"], ["some other note"]] # Missing token
        ctx.dirty = False
        ctx.log_entries = [{"run": "test-run", "sha": "12345678"}]

        with patch("qa_manage.check_snapshot", return_value=("12345678", "")):
            res = qa_manage.evaluate_run(ctx)

        self.assertFalse(res.ready_for_completion)
        self.assertFalse(res.invocation_present)

    def test_evaluate_run_case_insensitive_scope_match(self):
        ctx = MagicMock()
        ctx.row = {
            "Run ID": "test-run", "Status": "processing", "Stage": "closure",
            "Scopes": '[["", "Alice"]]', # Case insensitivity doesn't matter for variant here anymore because scopes cell doesn't store variant
            "Source type": "raw_transcript",
            "Route variant": "m1", # Lowercase m1
            "Entries": '{"|Alice": {"10_M1_People_Management/<Person>/individual_development_plan.gdoc": ["updated", ""]}}',
            "Started": "2023-10-01T10:00:00Z", "Last mutation": "2023-10-01T10:05:00Z"
        }
        ctx.graph = self.mock_graph
        # Edge outcome logged with lowercase 'm1'
        ctx.all_rows = [
            {"Source": "10_M1_People_Management/Alice/individual_development_plan.gdoc",
             "Target": "_m1_timeline.csv", "Outcome": "updated", "Person": "alice", # lowercase Alice
             "Project": "", "Route variant": "m1", "Timestamp": "2023-10-01T10:06:00Z",
             "Source node": "10_M1_People_Management/<Person>/individual_development_plan.gdoc",
             "Target node": "_m1_timeline.csv",
             "Run ID": "test-run"}
        ]
        ctx.inv_rows = [["Headers"], ["... run:test-run ..."]]
        ctx.dirty = False
        ctx.log_entries = [{"run": "test-run", "sha": "12345678"}]

        with patch("qa_manage.check_snapshot", return_value=("12345678", "")):
            res = qa_manage.evaluate_run(ctx)

        self.assertTrue(res.ready_for_completion)


    def test_evaluate_run_early_state_skips_validation(self):
        ctx = MagicMock()
        ctx.row = {
            "Run ID": "test-run", "Status": "discovered", "Stage": "",
            "Source type": "raw_transcript", "Route variant": "m1",
        }
        ctx.graph = {}
        ctx.all_rows = []
        ctx.inv_rows = []
        ctx.dirty = False
        ctx.log_entries = []

        res = qa_manage.evaluate_run(ctx)
        self.assertFalse(res.ready_for_completion)
        self.assertEqual(len(res.unresolved_edges), 0) # Skipped closure check
        self.assertEqual(len(res.entry_problems), 1)
        self.assertIn("Run cannot be completed from state", res.entry_problems[0])

    def test_evaluate_run_warnings_block_completion(self):
        ctx = MagicMock()
        ctx.row = {
            "Run ID": "test-run", "Status": "processing", "Stage": "closure",
            "Scopes": '[["", "Alice"]]', "Source type": "raw_transcript",
            "Route variant": "m1",
            "Entries": '{"|Alice": {"10_M1_People_Management/<Person>/individual_development_plan.gdoc": ["updated", ""]}}',
            "Started": "2023-10-01T10:00:00Z", "Last mutation": "2023-10-01T10:05:00Z"
        }
        ctx.graph = self.mock_graph
        ctx.all_rows = [
            {"Source": "10_M1_People_Management/Alice/individual_development_plan.gdoc",
             "Target": "_m1_timeline.csv", "Outcome": "invalid_outcome", "Person": "Alice",
             "Project": "", "Route variant": "m1", "Timestamp": "2023-10-01T10:06:00Z",
             "Source node": "10_M1_People_Management/<Person>/individual_development_plan.gdoc",
             "Target node": "_m1_timeline.csv",
             "Run ID": "test-run"}
        ]
        ctx.inv_rows = [["Headers"], ["... run:test-run ..."]]
        ctx.dirty = False
        ctx.log_entries = [{"run": "test-run", "sha": "12345678"}]

        with patch("qa_manage.check_snapshot", return_value=("12345678", "")):
            res = qa_manage.evaluate_run(ctx)

        self.assertFalse(res.ready_for_completion)
        self.assertTrue(len(res.warnings) > 0)

    def test_recommended_actions(self):
        # Discovered -> start
        self.assertEqual(qa_manage.get_recommended_action("discovered", "", False), "start")
        # Ready -> start
        self.assertEqual(qa_manage.get_recommended_action("ready", "", False), "start")
        # Blocked -> resume --continue
        self.assertEqual(qa_manage.get_recommended_action("blocked", "", False), "resume --continue")
        # Completed -> none
        self.assertEqual(qa_manage.get_recommended_action("completed", "done", False), "none")
        # Processing Analysis -> record-analysis
        self.assertEqual(qa_manage.get_recommended_action("processing", "analysis", False), "record-analysis")
        # Processing Apply -> record-apply
        self.assertEqual(qa_manage.get_recommended_action("processing", "apply", False), "record-apply")
        # Processing Closure (ready) -> complete
        self.assertEqual(qa_manage.get_recommended_action("processing", "closure", True), "complete")
        # Processing Closure (not ready) -> resolve unmet requirements
        self.assertEqual(qa_manage.get_recommended_action("processing", "closure", False), "resolve unmet requirements")

if __name__ == "__main__":
    unittest.main()
