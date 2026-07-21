"""Unit tests for qa_manage.py's read-only `pack <run-id>` command.

pack is the cross-agent handoff/resume packet for one run: identity,
dashboard's category, guide's checklist/guardrails, review's evaluate_run
summary, a classify-style signals+candidate_routes block only when the
route isn't resolved yet, graph context, a capped source preview, and a
concise agent_handoff text block. Covers unresolved vs. resolved routes,
a completed run, preview truncation/no-leakage, Current-source
preference, a missing source file, read-only enforcement, and the JSON
envelope. All fixtures use placeholder names - no real names/projects.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import inspect
import io
import json
import sys
import tempfile
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
                "m1": {"skills": ["m1-skill"], "entry": ["m1_doc"]},
                "m2": {"skills": ["m2-skill"], "entry": ["m2_doc", "evidence_log_doc"]},
                "mixed": {"skills": ["m1-skill", "m2-skill"], "entry": ["m1_doc", "m2_doc"]},
            }
        },
        "meeting_transcript": {
            "routes": {
                "multi_project": {"skills": ["meeting-skill"], "entry": ["m2_input_doc"]},
                "single_project": {"skills": ["shared-rules"], "entry": ["m2_input_doc"]},
            }
        },
        "strategy_chat": {"skills": ["strategy-skill"], "entry": ["m2_input_doc"]},
        "admin_note": {"skills": ["admin-skill"], "entry": ["people_registry_doc"]},
        "people_case_chat": {"skills": ["risk-skill"], "entry": ["m1_risk_doc"], "scope_required": ["person"]},
    },
    "documents": {
        "m1_doc": {"scope": "person", "downstream": []},
        "m2_doc": {"scope": "project", "downstream": [{"to": "project_registry_doc", "kind": "direct"}]},
        "evidence_log_doc": {"scope": "project", "downstream": []},
        "m2_input_doc": {"scope": "project", "downstream": []},
        "people_registry_doc": {"scope": "workspace", "downstream": []},
        "m1_risk_doc": {"scope": "workspace", "downstream": []},
        "project_registry_doc": {"scope": "workspace", "downstream": []},
    },
}

TRANSCRIPT_TWO_SPEAKERS = (
    "<Person1>:\n"
    "Hello, how are things going on <Project1>?\n\n"
    "<Person2>:\n"
    "Good, we shipped the fix yesterday.\n\n"
    "<Person1>:\n"
    "Great, let's continue next week.\n"
)


def row(run_id, status="processing", stage="closure", **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/{run_id}.txt",
        "Current source": f"00_Inbox/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "qa_1to1", "Route variant": "m2",
        "Project": "<Project1>", "Person": "<Person1>",
        "Scopes": '[["<Project1>", "<Person1>"]]',
        "Status": status, "Stage": stage, "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "2026-01-01 00:00",
        "Last mutation": "2026-01-01 00:00", "Completed": "", "Snapshot": "",
        "Reason": "", "Summary": "", "Source text version": "", "Source hash": "abc123",
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
    def __init__(self, run_id, json=True, debug=False, max_preview_chars=None):
        self.run_id = run_id
        self.json = json
        self.debug = debug
        self.max_preview_chars = max_preview_chars


def write_file(root: Path, relative_path: str, content: str) -> None:
    full = root / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def run_pack(target_row, data_root, other_rows=None, eval_res=None, max_preview_chars=None):
    rows = (other_rows or []) + [target_row]
    eval_res = eval_res or ready_eval()

    def fake_load_review_context(services, run_id, rows=None):
        return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id), all_rows=[])

    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.load_graph", return_value=GRAPH), \
         patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
         patch("qa_manage.evaluate_run", return_value=eval_res), \
         patch("qa_manage.DATA_ROOT", data_root):
        res = qa_manage.cmd_pack(Args(target_row["Run ID"], max_preview_chars=max_preview_chars))
    return res, mock_services


class UnresolvedRouteTests(unittest.TestCase):
    def test_discovered_unresolved_includes_classify_block_and_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", status="discovered", stage="", **{"Source type": "", "Route variant": ""})
            res, _ = run_pack(r, root)
            self.assertTrue(res.ok)
            self.assertIsNotNone(res.data["classify"])
            self.assertGreaterEqual(len(res.data["classify"]["candidate_routes"]), 1)
            types = {c["source_type"] for c in res.data["classify"]["candidate_routes"]}
            self.assertIn("qa_1to1", types)
            self.assertFalse(res.data["source_preview"]["preview_truncated"])
            self.assertGreater(len(res.data["source_preview"]["preview"]), 0)
            self.assertFalse(res.data["graph_context"]["route_resolved"])
            self.assertIn("qa_1to1", res.data["graph_context"]["candidate_source_types"])
            self.assertEqual(res.data["dashboard_category"], "action_required")
            # candidate_source_types is deduped even though qa_1to1 has 3 variants
            self.assertEqual(res.data["graph_context"]["candidate_source_types"].count("qa_1to1"), 1)
            # the "cannot be completed from state 'discovered'" boilerplate is
            # expected for any non-active run, never a real finding - not just
            # for completed rows.
            self.assertEqual(res.data["review_summary"]["problems"], [])

    def test_needs_scope_still_shows_classify_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", status="needs_scope", stage="", **{"Source type": "", "Route variant": ""})
            res, _ = run_pack(r, root)
            self.assertIsNotNone(res.data["classify"])


class ResolvedRouteTests(unittest.TestCase):
    def test_started_route_includes_guide_review_and_graph_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            eval_res = broken_eval(unresolved_edges=[
                "scope (<Project1>, <Person1>, m2): unresolved edge m2_doc -> project_registry_doc [direct]"
            ])
            r = row("r1", status="processing", stage="closure")
            res, _ = run_pack(r, root, eval_res=eval_res)
            self.assertIsNone(res.data["classify"])
            self.assertTrue(res.data["graph_context"]["route_resolved"])
            self.assertEqual(res.data["graph_context"]["skills"], ["m2-skill"])
            self.assertIn("evidence_log_doc", res.data["graph_context"]["entry_documents"])
            self.assertIn({"from": "m2_doc", "to": "project_registry_doc", "kind": "direct"},
                         res.data["graph_context"]["closure_expectations"])
            self.assertEqual(len(res.data["review_summary"]["unresolved_edges"]), 1)
            self.assertTrue(any("resolve-edge r1" in c for c in res.data["commands"]))

    def test_analysis_stage_includes_record_analysis_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", status="processing", stage="analysis")
            res, _ = run_pack(r, root)
            self.assertTrue(any(c.startswith("record-analysis r1") for c in res.data["commands"]))
            self.assertIsNone(res.data["classify"])


class CompletedRunTests(unittest.TestCase):
    def test_completed_healthy_run_has_no_mutation_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            eval_res = broken_eval(entry_problems=["Run cannot be completed from state 'completed'."],
                                   snapshot_sha="deadbeef")
            r = row("r1", status="completed", stage="done", Completed="2026-01-02 00:00", Snapshot="deadbeef")
            res, _ = run_pack(r, root, eval_res=eval_res)
            self.assertEqual(res.data["commands"], [])
            self.assertEqual(res.data["review_summary"]["problems"], [])
            self.assertEqual(res.data["review_summary"]["snapshot_sha"], "deadbeef")
            self.assertIsNone(res.data["classify"])
            self.assertEqual(res.data["dashboard_category"], "completed")

    def test_completed_run_with_real_problem_surfaces_it_without_mutation_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            eval_res = broken_eval(
                entry_problems=["Run cannot be completed from state 'completed'."],
                snapshot_problem="snapshot predates last mutation",
            )
            r = row("r1", status="completed", stage="done", Completed="2026-01-02 00:00")
            res, _ = run_pack(r, root, eval_res=eval_res)
            self.assertIn("snapshot predates last mutation", res.data["review_summary"]["problems"])
            self.assertNotIn("Run cannot be completed from state 'completed'.",
                             res.data["review_summary"]["problems"])
            for c in res.data["commands"]:
                self.assertTrue(c.startswith("review "), f"unexpected mutation-looking command: {c!r}")


class PreviewTests(unittest.TestCase):
    def test_preview_truncated_and_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_text = "<Person1>:\n" + ("filler placeholder text\n" * 500)
            write_file(root, "00_Inbox/r1.txt", long_text)
            r = row("r1", status="discovered", stage="", **{"Source type": "", "Route variant": ""})
            res, _ = run_pack(r, root, max_preview_chars=80)
            preview = res.data["source_preview"]
            self.assertEqual(len(preview["preview"]), 80)
            self.assertTrue(preview["preview_truncated"])
            self.assertLess(len(preview["preview"]), len(long_text))
            # no leakage anywhere else in the packet either
            packed_json = json.dumps(res.data, ensure_ascii=False)
            self.assertNotIn(long_text, packed_json)

    def test_current_source_preferred_over_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/live.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", Source="00_Source_Docs\\legacy\\gone.txt",
                    **{"Current source": "00_Inbox/live.txt"})
            res, _ = run_pack(r, root)
            self.assertEqual(res.data["identity"]["source_path_field_used"], "current_source")
            self.assertEqual(res.data["identity"]["source_path_used"], "00_Inbox/live.txt")
            self.assertEqual(res.data["source_preview"]["source_path_used"], "00_Inbox/live.txt")

    def test_missing_source_file_is_a_warning_not_a_hard_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)  # nothing written
            r = row("r1", **{"Current source": "00_Inbox/does-not-exist.txt"})
            res, _ = run_pack(r, root)
            self.assertTrue(res.ok)
            self.assertTrue(any("not found" in w for w in res.warnings))
            self.assertFalse(res.data["source_preview"]["file_exists"])


class ReadOnlyEnforcementTests(unittest.TestCase):
    FORBIDDEN_SUBSTRINGS = [
        "write_queue(", "export_queue_terminal(", "mirror_git(MIRROR, \"add\"",
        "mirror_git(MIRROR, \"commit\"", ".values().update(", ".values().clear(",
        ".values().append(", "files().create(", "files().update(", ".write_text(", ".write_bytes(",
    ]

    def test_cmd_pack_source_never_calls_write_functions(self):
        source = inspect.getsource(qa_manage.cmd_pack)
        for needle in self.FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(needle, source, f"cmd_pack source contains forbidden call: {needle!r}")

    def test_cmd_pack_never_invokes_write_queue_or_sheet_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1")
            with patch("qa_manage.write_queue") as mock_write_queue, \
                 patch("qa_manage.export_queue_terminal") as mock_export:
                res, mock_services = run_pack(r, root)

            mock_write_queue.assert_not_called()
            mock_export.assert_not_called()
            mock_services["sheets"].spreadsheets().values().update.assert_not_called()
            mock_services["sheets"].spreadsheets().values().append.assert_not_called()
            mock_services["sheets"].spreadsheets().values().clear.assert_not_called()
            mock_services["drive"].files().create.assert_not_called()
            mock_services["drive"].files().update.assert_not_called()
            self.assertTrue(res.ok)
            self.assertEqual((root / "00_Inbox" / "r1.txt").read_text(encoding="utf-8"), TRANSCRIPT_TWO_SPEAKERS)


class JsonEnvelopeTests(unittest.TestCase):
    def test_json_envelope_shape_via_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            rows = [row("r1")]

            def fake_load_review_context(services, run_id, rows=None):
                return SimpleNamespace(row=next(x for x in (rows or []) if x["Run ID"] == run_id), all_rows=[])

            mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
            with patch("sys.argv", ["qa_manage.py", "pack", "r1", "--json"]), \
                 patch("qa_manage.get_services_cached", return_value=mock_services), \
                 patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
                 patch("qa_manage.read_queue", return_value=rows), \
                 patch("qa_manage.load_graph", return_value=GRAPH), \
                 patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
                 patch("qa_manage.evaluate_run", return_value=ready_eval()), \
                 patch("qa_manage.DATA_ROOT", root):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    code = qa_manage.main()
            self.assertEqual(code, 0)
            envelope = json.loads(buf.getvalue())
            self.assertEqual(envelope["schema_version"], 1)
            self.assertTrue(envelope["ok"])
            self.assertEqual(envelope["command"], "pack")
            for key in ("run_id", "identity", "interpretation", "dashboard_category", "checklist",
                        "commands", "guardrails", "review_summary", "classify", "graph_context",
                        "source_preview", "agent_handoff"):
                self.assertIn(key, envelope["data"])
            self.assertIsInstance(envelope["data"]["agent_handoff"], str)
            self.assertEqual(envelope["errors"], [])


if __name__ == "__main__":
    unittest.main()
