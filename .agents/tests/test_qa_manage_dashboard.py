"""Unit tests for qa_manage.py's read-only `dashboard` command.

Covers: status/stage grouping, recommended-command mapping, read-only
enforcement (no write/create calls, structural + mocked), --limit
behavior, the JSON envelope, project/person filters, an injected
integrity issue on a completed run, the finalizing retry recommendation,
and inbox/storage summary read-only filesystem behavior.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import qa_manage


def row(run_id, status, stage="", **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/{run_id}.txt", "Source hash": "abc123",
        "Current source": f"00_Inbox/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "qa_1to1", "Route variant": "m2",
        "Project": "<Project1>", "Person": "<Person1>",
        "Scopes": '[["<Project1>", "<Person1>"]]',
        "Status": status, "Stage": stage, "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "2026-01-01 00:00",
        "Last mutation": "2026-01-01 00:00", "Completed": "", "Snapshot": "",
        "Reason": "", "Summary": "", "Source text version": "",
    }
    base.update(extra)
    return base


def ready_eval() -> qa_manage.EvaluationResult:
    return qa_manage.EvaluationResult(
        ready_for_completion=True, entry_problems=[], unresolved_edges=[],
        warnings=[], snapshot_sha="deadbeef", snapshot_problem="", invocation_present=True,
    )


def broken_eval(**overrides) -> qa_manage.EvaluationResult:
    base = dict(ready_for_completion=False, entry_problems=[], unresolved_edges=[],
                warnings=[], snapshot_sha="", snapshot_problem="", invocation_present=True)
    base.update(overrides)
    return qa_manage.EvaluationResult(**base)


class Args:
    def __init__(self, limit=qa_manage.DEFAULT_DASHBOARD_LIMIT, include_completed=False,
                 include_ignored=False, project="", person="", json=True):
        self.limit = limit
        self.include_completed = include_completed
        self.include_ignored = include_ignored
        self.project = project
        self.person = person
        self.json = json


def run_dashboard(rows, eval_map=None, **arg_overrides):
    """Drive cmd_dashboard with a canned queue and a canned per-run
    evaluate_run() result, exactly like dashboard's own live callers would
    see it after review/evaluate."""
    eval_map = eval_map or {}

    def fake_load_review_context(services, run_id, rows=None):
        return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id))

    def fake_evaluate_run(ctx):
        return eval_map.get(ctx.row["Run ID"], ready_eval())

    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
         patch("qa_manage.evaluate_run", side_effect=fake_evaluate_run), \
         patch("qa_manage.inbox_snapshot", return_value={"total_files": 0, "by_source_type": {}}), \
         patch("qa_manage.storage_snapshot", return_value={"total_processed_runs": 0, "by_month": {}}):
        res = qa_manage.cmd_dashboard(Args(**arg_overrides))
    return res, mock_services


class DashboardGroupingTests(unittest.TestCase):
    def test_groups_by_status_and_stage(self):
        rows = [
            row("r-discovered", "discovered"),
            row("r-needs-scope", "needs_scope", Reason="missing person"),
            row("r-analysis", "processing", "analysis"),
            row("r-apply", "processing", "apply"),
            row("r-closure", "processing", "closure"),
            row("r-blocked", "blocked", Reason="waiting on client answer"),
            row("r-finalizing", "finalizing"),
            row("r-completed", "completed", "done", Completed="2026-01-02 00:00"),
            row("r-ignored", "ignored"),
            row("r-historical", "historical"),
        ]
        res, _ = run_dashboard(rows)
        self.assertTrue(res.ok)
        action_ids = {i["run_id"] for i in res.data["action_required"]}
        self.assertEqual(action_ids, {"r-discovered", "r-needs-scope", "r-analysis",
                                       "r-apply", "r-closure"})
        self.assertEqual([i["run_id"] for i in res.data["blocked"]], ["r-blocked"])
        self.assertEqual([i["run_id"] for i in res.data["finalizing"]], ["r-finalizing"])
        # completed/ignored/historical are excluded from action_required entirely
        self.assertNotIn("r-completed", action_ids)
        self.assertNotIn("r-ignored", action_ids)
        self.assertNotIn("r-historical", action_ids)

    def test_ignored_historical_hidden_without_flag(self):
        rows = [row("r-ignored", "ignored"), row("r-historical", "historical")]
        res, _ = run_dashboard(rows, include_ignored=False)
        self.assertEqual(res.data["ignored_historical"], [])
        self.assertEqual(res.data["ignored_historical_counts"], {})

    def test_ignored_historical_shown_with_flag(self):
        rows = [row("r-ignored", "ignored"), row("r-historical", "historical")]
        res, _ = run_dashboard(rows, include_ignored=True)
        ids = {i["run_id"] for i in res.data["ignored_historical"]}
        self.assertEqual(ids, {"r-ignored", "r-historical"})
        self.assertEqual(res.data["ignored_historical_counts"],
                         {"ignored": 1, "historical": 1})


class RecommendedCommandTests(unittest.TestCase):
    def test_discovered(self):
        cmd = qa_manage.dashboard_recommended_command(row("r1", "discovered"))
        self.assertTrue(cmd.startswith("start r1 "))

    def test_needs_scope(self):
        cmd = qa_manage.dashboard_recommended_command(
            row("r1", "needs_scope", **{"Source type": "qa_1to1", "Reason": "needs person"}))
        self.assertIn("start r1 --source-type qa_1to1 --scope", cmd)
        self.assertIn("needs person", cmd)

    def test_blocked(self):
        cmd = qa_manage.dashboard_recommended_command(row("r1", "blocked", Reason="waiting on answer"))
        self.assertIn("resume r1 --continue", cmd)
        self.assertIn("waiting on answer", cmd)

    def test_finalizing(self):
        cmd = qa_manage.dashboard_recommended_command(row("r1", "finalizing"))
        self.assertEqual(cmd, "complete r1")

    def test_processing_analysis(self):
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "analysis"))
        self.assertIn("record-analysis r1", cmd)

    def test_processing_apply(self):
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "apply"))
        self.assertIn("record-apply r1", cmd)

    def test_processing_closure_no_eval_asks_to_review(self):
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "closure"))
        self.assertIn("review r1 --json", cmd)

    def test_processing_closure_archive_needed(self):
        eval_res = broken_eval(entry_problems=["Source original is still in 00_Inbox; run archive-source before snapshotting."])
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "closure"), eval_res)
        self.assertEqual(cmd, "archive-source r1")

    def test_processing_closure_missing_entry_outcome(self):
        eval_res = broken_eval(entry_problems=["scope (P, X, m2): entry document 'evidence_log' has no recorded outcome (...)"])
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "closure"), eval_res)
        self.assertIn("record-apply r1", cmd)

    def test_processing_closure_unresolved_edge(self):
        eval_res = broken_eval(unresolved_edges=["scope (P, X, m2): unresolved edge m2_input->project_risk"])
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "closure"), eval_res)
        self.assertIn("resolve-edge r1", cmd)

    def test_processing_closure_snapshot_problem(self):
        eval_res = broken_eval(snapshot_problem="no mirror commit mentions r1")
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "closure"), eval_res)
        self.assertIn("commit_workspace_state.py", cmd)
        self.assertIn("r1", cmd)

    def test_processing_closure_missing_invocation(self):
        eval_res = broken_eval(invocation_present=False)
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "closure"), eval_res)
        self.assertIn("commit_workspace_state.py", cmd)

    def test_processing_closure_ready(self):
        cmd = qa_manage.dashboard_recommended_command(row("r1", "processing", "closure"), ready_eval())
        self.assertEqual(cmd, "complete r1")

    def test_terminal_states_no_action(self):
        for status in ("completed", "failed", "historical", "ignored"):
            self.assertEqual(qa_manage.dashboard_recommended_command(row("r1", status)), "none")


class ReadOnlyEnforcementTests(unittest.TestCase):
    FORBIDDEN_SUBSTRINGS = [
        "write_queue(", "export_queue_terminal(", "mirror_git(MIRROR, \"add\"",
        "mirror_git(MIRROR, \"commit\"", ".values().update(", ".values().clear(",
        ".values().append(", "files().create(", "files().update(",
    ]

    def test_cmd_dashboard_source_never_calls_write_functions(self):
        """Structural guard: cmd_dashboard's own source must never reference
        a write/create/mutate call, independent of any mocking."""
        source = inspect.getsource(qa_manage.cmd_dashboard)
        for needle in self.FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(needle, source, f"cmd_dashboard source contains forbidden call: {needle!r}")

    def test_cmd_dashboard_never_invokes_write_queue_or_sheet_writes(self):
        rows = [row("r1", "discovered"), row("r2", "blocked", Reason="x"),
                row("r3", "finalizing")]
        with patch("qa_manage.write_queue") as mock_write_queue, \
             patch("qa_manage.export_queue_terminal") as mock_export:
            res, mock_services = run_dashboard(rows)

        mock_write_queue.assert_not_called()
        mock_export.assert_not_called()
        mock_services["sheets"].spreadsheets().values().update.assert_not_called()
        mock_services["sheets"].spreadsheets().values().append.assert_not_called()
        mock_services["sheets"].spreadsheets().values().clear.assert_not_called()
        mock_services["drive"].files().create.assert_not_called()
        mock_services["drive"].files().update.assert_not_called()
        self.assertTrue(res.ok)


class LimitBehaviorTests(unittest.TestCase):
    def test_limit_caps_action_required_and_closure_evaluation(self):
        rows = [row(f"r{i}", "processing", "closure") for i in range(5)]
        eval_map = {r["Run ID"]: ready_eval() for r in rows}
        res, _ = run_dashboard(rows, eval_map=eval_map, limit=2)
        # Listing and the (expensive) evaluate_run pass share one budget -
        # only the first `limit` closure rows are listed/evaluated at all.
        self.assertEqual(len(res.data["action_required"]), 2)
        completed_recs = [i for i in res.data["action_required"] if i["recommended_command"].startswith("complete ")]
        self.assertEqual(len(completed_recs), 2)
        self.assertEqual(res.data["limit"], 2)

    def test_limit_caps_recent_completed_and_completed_integrity_scan(self):
        rows = [row(f"c{i}", "completed", "done", Completed=f"2026-01-{i+1:02d} 00:00") for i in range(5)]
        res, _ = run_dashboard(rows, limit=2, include_completed=True)
        self.assertEqual(len(res.data["recent_completed"]), 2)
        # newest first
        self.assertEqual(res.data["recent_completed"][0]["run_id"], "c4")

    def test_limit_zero_falls_back_to_default(self):
        rows = [row("r1", "discovered")]
        res, _ = run_dashboard(rows, limit=0)
        self.assertEqual(res.data["limit"], qa_manage.DEFAULT_DASHBOARD_LIMIT)


class JsonEnvelopeTests(unittest.TestCase):
    def test_json_envelope_shape_via_main(self):
        rows = [row("r1", "discovered")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("sys.argv", ["qa_manage.py", "dashboard", "--json"]), \
             patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.inbox_snapshot", return_value={"total_files": 0, "by_source_type": {}}), \
             patch("qa_manage.storage_snapshot", return_value={"total_processed_runs": 0, "by_month": {}}), \
             patch("sys.stdout") as _:
            import io
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = qa_manage.main()
        self.assertEqual(code, 0)
        envelope = json.loads(buf.getvalue())
        self.assertEqual(envelope["schema_version"], 1)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["command"], "dashboard")
        for key in ("action_required", "blocked", "finalizing", "integrity_issues",
                    "inbox_summary", "storage_summary", "recommendations"):
            self.assertIn(key, envelope["data"])
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual(envelope["errors"], [])


class ScopeFilterTests(unittest.TestCase):
    def test_row_matches_scope_filter_project_and_person(self):
        r = row("r1", "processing", "apply",
                Scopes='[["<Project1>", "<Person1>"], ["<Project2>", "<Person2>"]]')
        self.assertTrue(qa_manage.row_matches_scope_filter(r, "<Project1>", ""))
        self.assertTrue(qa_manage.row_matches_scope_filter(r, "", "<Person2>"))
        self.assertFalse(qa_manage.row_matches_scope_filter(r, "<Project1>", "<Person2>"))
        self.assertTrue(qa_manage.row_matches_scope_filter(r, "<project1>", "<person1>"))  # case-insensitive

    def test_row_matches_scope_filter_falls_back_to_plain_fields(self):
        r = row("r1", "needs_scope", Scopes="", Project="<Project1>", Person="")
        self.assertTrue(qa_manage.row_matches_scope_filter(r, "<Project1>", ""))
        self.assertFalse(qa_manage.row_matches_scope_filter(r, "<Project2>", ""))

    def test_dashboard_filters_by_project(self):
        rows = [
            row("r1", "discovered", Scopes="", Project="<Project1>", Person=""),
            row("r2", "discovered", Scopes="", Project="<Project2>", Person=""),
        ]
        with patch("qa_manage.inbox_snapshot", return_value={"total_files": 0, "by_source_type": {}}), \
             patch("qa_manage.storage_snapshot", return_value={"total_processed_runs": 0, "by_month": {}}):
            res, _ = run_dashboard(rows, project="<Project1>")
        self.assertEqual([i["run_id"] for i in res.data["action_required"]], ["r1"])

    def test_dashboard_filters_by_person(self):
        rows = [
            row("r1", "processing", "apply", Scopes='[["<Project1>", "<Person1>"]]'),
            row("r2", "processing", "apply", Scopes='[["<Project1>", "<Person2>"]]'),
        ]
        res, _ = run_dashboard(rows, person="<Person2>")
        self.assertEqual([i["run_id"] for i in res.data["action_required"]], ["r2"])


class IntegrityIssueTests(unittest.TestCase):
    def test_completed_run_with_injected_problem_appears_in_integrity_issues(self):
        rows = [row("c1", "completed", "done", Completed="2026-01-01 00:00")]
        eval_map = {"c1": broken_eval(snapshot_problem="snapshot predates last mutation")}
        res, _ = run_dashboard(rows, eval_map=eval_map)
        ids = {i["run_id"] for i in res.data["integrity_issues"]}
        self.assertIn("c1", ids)
        issue = next(i for i in res.data["integrity_issues"] if i["run_id"] == "c1")
        self.assertIn("snapshot predates last mutation", issue["problems"])

    def test_completed_run_without_problems_not_in_integrity_issues(self):
        rows = [row("c1", "completed", "done", Completed="2026-01-01 00:00")]
        res, _ = run_dashboard(rows, eval_map={"c1": ready_eval()})
        self.assertEqual(res.data["integrity_issues"], [])

    def test_completed_run_boilerplate_terminal_message_is_not_a_false_positive(self):
        # evaluate_run always appends this exact message for any completed
        # row (it's true and expected - a completed run can't be completed
        # again) - a healthy completed run's own evaluate_run() output looks
        # exactly like this, and it must not surface as an integrity issue.
        eval_map = {"c1": broken_eval(entry_problems=["Run cannot be completed from state 'completed'."])}
        rows = [row("c1", "completed", "done", Completed="2026-01-01 00:00")]
        res, _ = run_dashboard(rows, eval_map=eval_map)
        self.assertEqual(res.data["integrity_issues"], [])

    def test_completed_run_real_problem_survives_boilerplate_filter(self):
        eval_map = {"c1": broken_eval(entry_problems=["Run cannot be completed from state 'completed'."],
                                      invocation_present=False)}
        rows = [row("c1", "completed", "done", Completed="2026-01-01 00:00")]
        res, _ = run_dashboard(rows, eval_map=eval_map)
        ids = {i["run_id"] for i in res.data["integrity_issues"]}
        self.assertIn("c1", ids)
        issue = next(i for i in res.data["integrity_issues"] if i["run_id"] == "c1")
        self.assertNotIn("Run cannot be completed from state 'completed'.", issue["problems"])
        self.assertIn("Missing invocation token", issue["problems"])

    def test_completed_integrity_checked_even_without_include_completed_flag(self):
        rows = [row("c1", "completed", "done", Completed="2026-01-01 00:00")]
        eval_map = {"c1": broken_eval(unresolved_edges=["unresolved edge x->y"])}
        res, _ = run_dashboard(rows, eval_map=eval_map, include_completed=False)
        self.assertEqual(res.data["recent_completed"], [])  # not listed...
        ids = {i["run_id"] for i in res.data["integrity_issues"]}
        self.assertIn("c1", ids)  # ...but still integrity-audited


class FinalizingRetryTests(unittest.TestCase):
    def test_finalizing_recommends_complete_retry(self):
        rows = [row("f1", "finalizing")]
        res, _ = run_dashboard(rows, eval_map={"f1": broken_eval(snapshot_problem="pending")})
        item = res.data["finalizing"][0]
        self.assertEqual(item["recommended_command"], "complete f1")
        ids = {i["run_id"] for i in res.data["integrity_issues"]}
        self.assertIn("f1", ids)


class InboxStorageSnapshotTests(unittest.TestCase):
    def test_inbox_snapshot_counts_and_classifies_read_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "00_Inbox"
            inbox.mkdir()
            (inbox / "known.txt").write_text("x", encoding="utf-8")
            (inbox / "unknown.txt").write_text("x", encoding="utf-8")
            (inbox / "ignore.bin").write_text("x", encoding="utf-8")  # unsupported ext

            rows = [{"Current source": "00_Inbox/known.txt", "Source disposition": "inbox",
                     "Source type": "qa_1to1"}]
            snap = qa_manage.inbox_snapshot(root, rows)

            self.assertEqual(snap["total_files"], 2)
            self.assertEqual(snap["by_source_type"]["qa_1to1"], 1)
            self.assertEqual(snap["by_source_type"]["undiscovered (run scan)"], 1)
            # read-only: nothing was created/removed
            self.assertEqual(sorted(p.name for p in inbox.iterdir()),
                             ["ignore.bin", "known.txt", "unknown.txt"])

    def test_inbox_snapshot_missing_folder_is_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            snap = qa_manage.inbox_snapshot(Path(tmp), [])
            self.assertEqual(snap, {"total_files": 0, "by_source_type": {}})
            # read-only: no folder was created for the missing inbox
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_storage_snapshot_counts_by_month_read_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "90_Storage" / "Processed_Sources" / "2026" / "07"
            (base / "run-a").mkdir(parents=True)
            (base / "run-b").mkdir(parents=True)
            other = root / "90_Storage" / "Processed_Sources" / "2026" / "06"
            (other / "run-c").mkdir(parents=True)

            snap = qa_manage.storage_snapshot(root)

            self.assertEqual(snap["total_processed_runs"], 3)
            self.assertEqual(snap["by_month"]["2026-07"], 2)
            self.assertEqual(snap["by_month"]["2026-06"], 1)
            # read-only: exactly the fixture directories remain, nothing added
            self.assertEqual(sorted(p.name for p in base.iterdir()), ["run-a", "run-b"])

    def test_storage_snapshot_missing_root_is_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            snap = qa_manage.storage_snapshot(Path(tmp))
            self.assertEqual(snap, {"total_processed_runs": 0, "by_month": {}})


if __name__ == "__main__":
    unittest.main()
