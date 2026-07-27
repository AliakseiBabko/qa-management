"""Unit tests for qa_manage.py's `mark-superseded` command and the
superseded-row detection it shares with dashboard/triage/guide/pack/classify.

A stale pre-processing row is one whose own Reason already carries scan's
"content changed - supersedes <run-id>" note (from a later rescan of an
intentionally-edited inbox file) where the referenced newer run actually
completed. `mark-superseded` closes such a row out via the existing
`ignored` terminal state; dashboard/triage must stop listing it as
actionable once closed; guide/pack/classify should proactively recommend
the command while it's still open. All fixtures use placeholder names -
no real names/projects.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import qa_manage

GRAPH = {
    "sources": {
        "qa_1to1": {
            "routes": {
                "m2": {"skills": ["skill-a"], "entry": ["doc_one"]},
            }
        }
    },
    "documents": {
        "doc_one": {"scope": "project", "downstream": []},
    },
}


def row(run_id, status, stage="", **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/<Project1>/{run_id}.txt", "Source hash": "abc123",
        "Current source": f"00_Inbox/<Project1>/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "", "Route variant": "",
        "Project": "", "Person": "", "Scopes": "",
        "Status": status, "Stage": stage, "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "", "Last mutation": "2026-01-01 00:00",
        "Completed": "", "Snapshot": "", "Reason": "", "Summary": "",
        "Source text version": "",
    }
    base.update(extra)
    return base


SHARED_SOURCE_PATH = "00_Inbox/<Project1>/shared-source.txt"


def old_row(run_id="old-run", status="discovered", by_run="new-run", **extra):
    extra.setdefault("Reason", f"content changed - supersedes {by_run}")
    extra.setdefault("Source", SHARED_SOURCE_PATH)
    extra.setdefault("Current source", SHARED_SOURCE_PATH)
    return row(run_id, status, **extra)


def new_row(run_id="new-run", status="completed", source_suffix=None, **extra):
    # Same path as old_row by default - realistically the SAME rescanned
    # inbox file. Pass source_suffix to simulate a genuinely different
    # path (the --allow-path-change test cases).
    extra.setdefault("Source", source_suffix if source_suffix is not None else SHARED_SOURCE_PATH)
    extra.setdefault("Current source", source_suffix if source_suffix is not None else SHARED_SOURCE_PATH)
    return row(run_id, status, **extra)


class Args:
    def __init__(self, run_id, by_run="new-run", reason="edited and rescanned", json=True, debug=False,
                allow_path_change=False, path_change_evidence=""):
        self.run_id = run_id
        self.by_run = by_run
        self.reason = reason
        self.json = json
        self.debug = debug
        self.allow_path_change = allow_path_change
        self.path_change_evidence = path_change_evidence


def run_mark_superseded(rows, **arg_overrides):
    args_kwargs = {"run_id": "old-run"}
    args_kwargs.update(arg_overrides)
    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.write_queue") as mock_write_queue:
        res = qa_manage.cmd_mark_superseded(Args(**args_kwargs))
    return res, mock_write_queue


class PureHelperTests(unittest.TestCase):
    def test_parse_supersedes_run_id_extracts_id(self):
        reason = "content changed - supersedes 20260722-example-run-abc123"
        self.assertEqual(qa_manage.parse_supersedes_run_id(reason), "20260722-example-run-abc123")

    def test_parse_supersedes_run_id_returns_empty_without_marker(self):
        self.assertEqual(qa_manage.parse_supersedes_run_id("duplicate content of some-run"), "")
        self.assertEqual(qa_manage.parse_supersedes_run_id(""), "")

    def test_find_superseding_run_returns_completed_match(self):
        rows = [old_row(), new_row(status="completed")]
        found = qa_manage.find_superseding_run(rows, rows[0])
        assert found is not None
        self.assertEqual(found["Run ID"], "new-run")

    def test_find_superseding_run_none_when_not_completed(self):
        rows = [old_row(), new_row(status="processing")]
        self.assertIsNone(qa_manage.find_superseding_run(rows, rows[0]))

    def test_find_superseding_run_none_when_reason_has_no_marker(self):
        rows = [row("old-run", "discovered", Reason="unrelated note"), new_row()]
        self.assertIsNone(qa_manage.find_superseding_run(rows, rows[0]))

    def test_find_superseding_run_none_when_referenced_run_missing(self):
        rows = [old_row(by_run="does-not-exist")]
        self.assertIsNone(qa_manage.find_superseding_run(rows, rows[0]))

    def test_paths_overlap_true_for_shared_source(self):
        a = row("a", "discovered", Source="00_Inbox/X.txt", **{"Current source": "00_Inbox/X.txt"})
        b = row("b", "completed", Source="00_Inbox/X.txt", **{"Current source": "90_Storage/Processed/X.txt"})
        self.assertTrue(qa_manage.paths_overlap(a, b))

    def test_paths_overlap_false_for_different_paths(self):
        a = row("a", "discovered", Source="00_Inbox/X.txt", **{"Current source": "00_Inbox/X.txt"})
        b = row("b", "completed", Source="00_Inbox/Y.txt", **{"Current source": "00_Inbox/Y.txt"})
        self.assertFalse(qa_manage.paths_overlap(a, b))


class MarkSupersededHappyPathTests(unittest.TestCase):
    def test_succeeds_and_writes_standardized_reason(self):
        rows = [old_row(), new_row()]
        res, mock_write_queue = run_mark_superseded(rows)
        self.assertTrue(res.ok)
        self.assertEqual(res.data["status"], "ignored")
        self.assertEqual(res.data["superseded_by"], "new-run")
        self.assertTrue(mock_write_queue.called)
        written_rows = mock_write_queue.call_args[0][2]
        written = next(r for r in written_rows if r["Run ID"] == "old-run")
        self.assertEqual(written["Status"], "ignored")
        self.assertIn("superseded by newer run new-run", written["Reason"])
        self.assertIn("edited and rescanned", written["Reason"])

    def test_succeeds_from_needs_scope_and_ready_too(self):
        for status in ("needs_scope", "ready"):
            rows = [old_row(status=status), new_row()]
            res, _ = run_mark_superseded(rows)
            self.assertTrue(res.ok, f"status={status}")


class MarkSupersededRefusalTests(unittest.TestCase):
    def test_refuses_processing_old_row(self):
        rows = [old_row(status="processing", Stage="analysis"), new_row()]
        with self.assertRaises(SystemExit):
            run_mark_superseded(rows)

    def test_refuses_completed_old_row(self):
        rows = [old_row(status="completed"), new_row()]
        with self.assertRaises(SystemExit):
            run_mark_superseded(rows)

    def test_refuses_missing_new_run(self):
        rows = [old_row(by_run="ghost-run")]
        with self.assertRaises(SystemExit):
            run_mark_superseded(rows, by_run="ghost-run")

    def test_refuses_non_completed_new_run(self):
        for status in ("discovered", "needs_scope", "ready", "processing", "blocked", "finalizing"):
            rows = [old_row(), new_row(status=status)]
            with self.assertRaises(SystemExit):
                run_mark_superseded(rows)

    def test_refuses_blank_reason(self):
        rows = [old_row(), new_row()]
        with self.assertRaises(SystemExit):
            run_mark_superseded(rows, reason="")

    def test_refuses_same_run_id_for_old_and_new(self):
        rows = [old_row(run_id="same-run", by_run="same-run")]
        with self.assertRaises(SystemExit):
            run_mark_superseded(rows, run_id="same-run", by_run="same-run")

    def test_refuses_path_mismatch_without_allow_path_change(self):
        rows = [old_row(), new_row(source_suffix="00_Inbox/<Project1>/completely-different.txt")]
        with self.assertRaises(SystemExit):
            run_mark_superseded(rows)

    def test_allow_path_change_requires_evidence(self):
        rows = [old_row(), new_row(source_suffix="00_Inbox/<Project1>/completely-different.txt")]
        with self.assertRaises(SystemExit):
            run_mark_superseded(rows, allow_path_change=True, path_change_evidence="")

    def test_allow_path_change_with_evidence_succeeds(self):
        rows = [old_row(), new_row(source_suffix="00_Inbox/<Project1>/completely-different.txt")]
        res, _ = run_mark_superseded(
            rows, allow_path_change=True,
            path_change_evidence="file renamed as part of the same edit, confirmed with owner",
        )
        self.assertTrue(res.ok)

    def test_never_touches_source_file_only_the_queue_row(self):
        # No Drive file-move helper is imported/called anywhere in
        # cmd_mark_superseded - structural guard against a future change
        # accidentally wiring one in.
        import inspect
        src = inspect.getsource(qa_manage.cmd_mark_superseded)
        for forbidden in ("move_item", "move_file_to_folder", "drive.files().delete"):
            self.assertNotIn(forbidden, src)


class DashboardTriageExclusionTests(unittest.TestCase):
    def test_dashboard_excludes_superseded_row_from_action_required(self):
        rows = [old_row(status="ignored", Reason="superseded by newer run new-run; edited and rescanned"),
                new_row()]

        def fake_load_review_context(services, run_id, rows=None):
            return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id))

        ready_eval = qa_manage.EvaluationResult(
            ready_for_completion=True, entry_problems=[], unresolved_edges=[],
            warnings=[], snapshot_sha="deadbeef", snapshot_problem="", invocation_present=True,
        )
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
             patch("qa_manage.evaluate_run", return_value=ready_eval), \
             patch("qa_manage.inbox_snapshot", return_value={"total_files": 0, "by_source_type": {}}), \
             patch("qa_manage.storage_snapshot", return_value={"total_processed_runs": 0, "by_month": {}}):
            res = qa_manage.cmd_dashboard(SimpleNamespace(
                limit=qa_manage.DEFAULT_DASHBOARD_LIMIT, include_completed=True, include_ignored=True,
                project="", person="", json=True,
            ))
        action_ids = {r["run_id"] for r in res.data["action_required"]}
        self.assertNotIn("old-run", action_ids)
        self.assertEqual(res.data["ignored_historical_counts"].get("ignored"), 1)

    def test_triage_excludes_superseded_row(self):
        rows = [old_row(status="ignored", Reason="superseded by newer run new-run; edited and rescanned"),
                new_row()]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.DATA_ROOT", Path(".")):
            res = qa_manage.cmd_triage(SimpleNamespace(
                project="", person="", category="all", limit=qa_manage.DEFAULT_DASHBOARD_LIMIT, json=True,
            ))
        triaged_ids = {item["run_id"] for item in res.data["items"]}
        self.assertNotIn("old-run", triaged_ids)


class GuidePackClassifyRecommendationTests(unittest.TestCase):
    def _guide(self, rows):
        def fake_load_review_context(services, run_id, rows=None):
            return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id), all_rows=[])

        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        eval_res = qa_manage.EvaluationResult(
            ready_for_completion=False, entry_problems=["Run cannot be completed from state 'discovered'."],
            unresolved_edges=[], warnings=[], snapshot_sha="", snapshot_problem="", invocation_present=None,
        )
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.load_graph", return_value=GRAPH), \
             patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
             patch("qa_manage.evaluate_run", return_value=eval_res):
            return qa_manage.cmd_guide(SimpleNamespace(run_id="old-run", json=True, debug=False))

    def test_guide_recommends_mark_superseded_for_stale_duplicate(self):
        rows = [old_row(), new_row()]
        res = self._guide(rows)
        self.assertTrue(any("mark-superseded" in c for c in res.data["commands"]))
        self.assertTrue(any("superseded" in c.lower() for c in res.data["checklist"]))
        self.assertEqual(res.data["superseded_by"], "new-run")

    def test_guide_does_not_recommend_it_for_an_ordinary_discovered_row(self):
        rows = [row("old-run", "discovered")]
        res = self._guide(rows)
        self.assertFalse(any("mark-superseded" in c for c in res.data["commands"]))
        self.assertNotIn("superseded_by", res.data)

    def test_guide_does_not_recommend_it_when_newer_run_not_completed_yet(self):
        rows = [old_row(), new_row(status="processing")]
        res = self._guide(rows)
        self.assertFalse(any("mark-superseded" in c for c in res.data["commands"]))

    def _pack(self, rows):
        def fake_load_review_context(services, run_id, rows=None):
            return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id), all_rows=[])

        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        eval_res = qa_manage.EvaluationResult(
            ready_for_completion=False, entry_problems=["Run cannot be completed from state 'discovered'."],
            unresolved_edges=[], warnings=[], snapshot_sha="", snapshot_problem="", invocation_present=None,
        )
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.load_graph", return_value=GRAPH), \
             patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
             patch("qa_manage.evaluate_run", return_value=eval_res), \
             patch("qa_manage.build_source_preview",
                   return_value=({"source_path_used": "00_Inbox/x.txt", "source_path_field_used": "current_source",
                                 "extension": ".txt", "size_bytes": 10, "text_readable": True,
                                 "line_count": 1, "preview_truncated": False, "file_exists": True}, "hi", [])):
            return qa_manage.cmd_pack(SimpleNamespace(run_id="old-run", json=True, debug=False,
                                                      max_preview_chars=None))

    def test_pack_recommends_mark_superseded_for_stale_duplicate(self):
        rows = [old_row(), new_row()]
        res = self._pack(rows)
        self.assertTrue(any("mark-superseded" in c for c in res.data["commands"]))
        self.assertIsNotNone(res.data["classify"]["superseded_suggestion"])
        self.assertEqual(res.data["classify"]["superseded_suggestion"]["by_run"], "new-run")

    def test_classify_commands_includes_mark_superseded_when_suggested(self):
        commands = qa_manage.classify_commands(
            "old-run", [], None, {"by_run": "new-run", "reason_hint": "content changed - supersedes new-run"},
        )
        self.assertTrue(any(c.startswith("mark-superseded old-run --by-run new-run") for c in commands))

    def test_classify_commands_omits_mark_superseded_when_not_suggested(self):
        commands = qa_manage.classify_commands("old-run", [], None, None)
        self.assertFalse(any("mark-superseded" in c for c in commands))


if __name__ == "__main__":
    unittest.main()
