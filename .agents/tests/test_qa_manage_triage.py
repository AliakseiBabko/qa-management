"""Unit tests for qa_manage.py's Phase 10 backlog triage workflow:
`triage` (read-only overview), `triage-one` (read-only per-run detail),
and the tightened `ignore`/`mark-historical` explicit terminal actions.

Covers: transition restrictions (mark-historical invalid once processing
has started), mandatory --reason/--evidence, read-only enforcement for
triage/triage-one, Current-source preference, and JSON envelope shape.
All fixtures use placeholder names - no real names/projects.

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
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import qa_manage

GRAPH = {
    "sources": {
        "qa_1to1": {
            "routes": {
                "m1": {"skills": ["m1-skill"], "entry": ["m1_doc"]},
                "m2": {"skills": ["m2-skill"], "entry": ["m2_doc"]},
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
        "m2_doc": {"scope": "project", "downstream": []},
        "m2_input_doc": {"scope": "project", "downstream": []},
        "people_registry_doc": {"scope": "workspace", "downstream": []},
        "m1_risk_doc": {"scope": "workspace", "downstream": []},
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


def row(run_id, status="discovered", stage="", **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/{run_id}.txt",
        "Current source": f"00_Inbox/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "", "Route variant": "",
        "Project": "", "Person": "", "Scopes": "",
        "Status": status, "Stage": stage, "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "", "Last mutation": "2026-01-01 00:00",
        "Completed": "", "Snapshot": "", "Reason": "", "Summary": "",
        "Source text version": "", "Source hash": "abc123",
    }
    base.update(extra)
    return base


class Args:
    def __init__(self, run_id=None, json=True, debug=False, **extra):
        self.run_id = run_id
        self.json = json
        self.debug = debug
        for k, v in extra.items():
            setattr(self, k, v)


def write_file(root: Path, relative_path: str, content: str) -> None:
    full = root / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def run_triage(rows, data_root, **arg_overrides):
    defaults = {"project": "", "person": "", "category": "discovered",
                "limit": qa_manage.DEFAULT_DASHBOARD_LIMIT}
    defaults.update(arg_overrides)
    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.DATA_ROOT", data_root):
        res = qa_manage.cmd_triage(Args(**defaults))
    return res, mock_services


def run_triage_one(target_row, data_root, other_rows=None, max_preview_chars=None):
    rows = (other_rows or []) + [target_row]
    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.load_graph", return_value=GRAPH), \
         patch("qa_manage.DATA_ROOT", data_root):
        res = qa_manage.cmd_triage_one(Args(target_row["Run ID"], max_preview_chars=max_preview_chars))
    return res, mock_services


class TransitionRestrictionTests(unittest.TestCase):
    def test_mark_historical_invalid_from_processing(self):
        with self.assertRaises(SystemExit):
            qa_manage.validate_transition("processing", "historical")

    def test_mark_historical_invalid_from_blocked(self):
        with self.assertRaises(SystemExit):
            qa_manage.validate_transition("blocked", "historical")

    def test_mark_historical_valid_from_pre_processing_states(self):
        for status in ("discovered", "needs_scope", "ready"):
            qa_manage.validate_transition(status, "historical")  # must not raise

    def test_mark_historical_still_valid_as_failed_correction(self):
        qa_manage.validate_transition("failed", "historical")  # must not raise

    def test_ignore_only_from_pre_processing_states(self):
        for status in ("discovered", "needs_scope", "ready"):
            qa_manage.validate_transition(status, "ignored")  # must not raise
        for status in ("processing", "blocked", "failed", "finalizing", "completed"):
            with self.assertRaises(SystemExit):
                qa_manage.validate_transition(status, "ignored")

    def test_allowed_terminal_actions_for_status(self):
        self.assertEqual(qa_manage.allowed_terminal_actions_for_status("discovered"),
                         ["ignore", "mark-historical"])
        self.assertEqual(qa_manage.allowed_terminal_actions_for_status("failed"), ["mark-historical"])
        self.assertEqual(qa_manage.allowed_terminal_actions_for_status("processing"), [])
        self.assertEqual(qa_manage.allowed_terminal_actions_for_status("blocked"), [])
        self.assertEqual(qa_manage.allowed_terminal_actions_for_status("completed"), [])


class IgnoreCommandTests(unittest.TestCase):
    def test_ignore_requires_reason(self):
        rows = [row("r1", status="discovered")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.write_queue") as mock_write_queue:
            with self.assertRaises(SystemExit):
                qa_manage.cmd_ignore(Args("r1", category="reference_material", reason="", evidence=""))
        mock_write_queue.assert_not_called()

    def test_ignore_with_reason_succeeds_and_preserves_audit_trail(self):
        rows = [row("r1", status="discovered")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.write_queue") as mock_write_queue:
            res = qa_manage.cmd_ignore(Args("r1", category="reference_material",
                                            reason="course material, not a real intake source",
                                            evidence="matches 90_Storage/Reference layout"))
        self.assertTrue(res.ok)
        self.assertEqual(res.data["status"], "ignored")
        self.assertTrue(mock_write_queue.called)
        written_rows = mock_write_queue.call_args[0][2]
        written = next(r for r in written_rows if r["Run ID"] == "r1")
        self.assertEqual(written["Status"], "ignored")
        self.assertIn("course material, not a real intake source", written["Reason"])
        self.assertIn("matches 90_Storage/Reference layout", written["Reason"])

    def test_ignore_rejected_from_processing_status(self):
        rows = [row("r1", status="processing", stage="analysis")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.write_queue") as mock_write_queue:
            with self.assertRaises(SystemExit):
                qa_manage.cmd_ignore(Args("r1", category="other", reason="changed my mind", evidence=""))
        mock_write_queue.assert_not_called()


class MarkHistoricalCommandTests(unittest.TestCase):
    def test_mark_historical_requires_evidence(self):
        rows = [row("r1", status="discovered")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.write_queue") as mock_write_queue:
            with self.assertRaises(SystemExit):
                qa_manage.cmd_mark_historical(Args("r1", evidence=""))
        mock_write_queue.assert_not_called()

    def test_mark_historical_with_evidence_succeeds(self):
        rows = [row("r1", status="discovered")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.write_queue") as mock_write_queue:
            res = qa_manage.cmd_mark_historical(
                Args("r1", evidence="evidence_log row 2025-01-01, <Project1>"))
        self.assertTrue(res.ok)
        self.assertEqual(res.data["status"], "historical")
        written_rows = mock_write_queue.call_args[0][2]
        written = next(r for r in written_rows if r["Run ID"] == "r1")
        self.assertIn("evidence_log row 2025-01-01", written["Reason"])

    def test_mark_historical_rejected_once_processing_started(self):
        rows = [row("r1", status="processing", stage="closure")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.write_queue") as mock_write_queue:
            with self.assertRaises(SystemExit):
                qa_manage.cmd_mark_historical(Args("r1", evidence="I remember this being done already"))
        mock_write_queue.assert_not_called()

    def test_mark_historical_rejected_from_blocked(self):
        rows = [row("r1", status="blocked", Reason="waiting on answer")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.write_queue") as mock_write_queue:
            with self.assertRaises(SystemExit):
                qa_manage.cmd_mark_historical(Args("r1", evidence="some evidence"))
        mock_write_queue.assert_not_called()


class TriageOverviewTests(unittest.TestCase):
    def test_lists_discovered_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                row("r1", status="discovered"),
                row("r2", status="needs_scope"),
                row("r3", status="blocked"),
                row("r4", status="completed", stage="done"),
            ]
            res, _ = run_triage(rows, root)
            self.assertTrue(res.ok)
            ids = {i["run_id"] for i in res.data["items"]}
            self.assertEqual(ids, {"r1"})
            self.assertEqual(res.data["counts"], {"discovered": 1, "needs_scope": 1, "blocked": 1})

    def test_category_all_lists_all_three_buckets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [row("r1", status="discovered"), row("r2", status="needs_scope"),
                    row("r3", status="blocked"), row("r4", status="completed", stage="done")]
            res, _ = run_triage(rows, root, category="all")
            ids = {i["run_id"] for i in res.data["items"]}
            self.assertEqual(ids, {"r1", "r2", "r3"})

    def test_invalid_category_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(SystemExit):
                run_triage([row("r1")], root, category="bogus")

    def test_items_show_allowed_terminal_actions_per_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [row("r1", status="blocked", Reason="waiting")]
            res, _ = run_triage(rows, root, category="blocked")
            item = res.data["items"][0]
            self.assertEqual(item["allowed_terminal_actions"], [])
            self.assertEqual(item["terminal_action_commands"], [])

    def test_discovered_items_show_ignore_and_mark_historical_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [row("r1", status="discovered")]
            res, _ = run_triage(rows, root)
            item = res.data["items"][0]
            self.assertEqual(item["allowed_terminal_actions"], ["ignore", "mark-historical"])
            self.assertTrue(any(c.startswith("ignore r1") for c in item["terminal_action_commands"]))
            self.assertTrue(any(c.startswith("mark-historical r1") for c in item["terminal_action_commands"]))

    def test_current_source_preferred_in_file_exists_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/live.txt", TRANSCRIPT_TWO_SPEAKERS)
            rows = [row("r1", Source="00_Source_Docs\\legacy\\gone.txt",
                        **{"Current source": "00_Inbox/live.txt"})]
            res, _ = run_triage(rows, root)
            item = res.data["items"][0]
            self.assertEqual(item["source_path_field_used"], "current_source")
            self.assertEqual(item["source_path_used"], "00_Inbox/live.txt")
            self.assertTrue(item["file_exists"])

    def test_limit_caps_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [row(f"r{i}", status="discovered") for i in range(5)]
            res, _ = run_triage(rows, root, limit=2)
            self.assertEqual(len(res.data["items"]), 2)
            self.assertEqual(res.data["total_candidates"], 5)


class TriageOneTests(unittest.TestCase):
    def test_includes_classify_block_and_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", status="discovered")
            res, _ = run_triage_one(r, root)
            self.assertTrue(res.ok)
            self.assertIsNotNone(res.data["classify"])
            types = {c["source_type"] for c in res.data["classify"]["candidate_routes"]}
            self.assertIn("qa_1to1", types)
            self.assertGreater(len(res.data["source_preview"]["preview"]), 0)
            self.assertIsNotNone(res.data["identity"]["age_days"])

    def test_allowed_terminal_actions_and_commands_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", status="discovered")
            res, _ = run_triage_one(r, root)
            self.assertEqual(res.data["allowed_terminal_actions"], ["ignore", "mark-historical"])
            self.assertTrue(any(c.startswith("ignore r1") for c in res.data["terminal_action_commands"]))
            self.assertTrue(any(c.startswith("mark-historical r1")
                               for c in res.data["terminal_action_commands"]))
            self.assertTrue(any(c.startswith("classify r1") for c in res.data["process_commands"]))

    def test_blocked_run_has_no_terminal_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", status="blocked", Reason="waiting on client answer")
            res, _ = run_triage_one(r, root)
            self.assertEqual(res.data["allowed_terminal_actions"], [])
            self.assertEqual(res.data["terminal_action_commands"], [])

    def test_current_source_preferred_over_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/live.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", Source="00_Source_Docs\\legacy\\gone.txt",
                    **{"Current source": "00_Inbox/live.txt"})
            res, _ = run_triage_one(r, root)
            self.assertEqual(res.data["source_preview"]["source_path_field_used"], "current_source")
            self.assertEqual(res.data["source_preview"]["source_path_used"], "00_Inbox/live.txt")

    def test_missing_source_file_degrades_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)  # nothing written
            r = row("r1", **{"Current source": "00_Inbox/does-not-exist.txt"})
            res, _ = run_triage_one(r, root)
            self.assertTrue(res.ok)
            self.assertFalse(res.data["source_preview"]["file_exists"])
            self.assertTrue(any("not found" in w for w in res.warnings))

    def test_duplicate_reason_surfaces_ignore_suggestion_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", status="discovered", Reason="duplicate content of 20260101-other-abc123")
            res, _ = run_triage_one(r, root)
            self.assertIn("row Reason already flags", res.data["terminal_action_commands"][0])


class ReadOnlyEnforcementTests(unittest.TestCase):
    FORBIDDEN_SUBSTRINGS = [
        "write_queue(", "export_queue_terminal(", "mirror_git(MIRROR, \"add\"",
        "mirror_git(MIRROR, \"commit\"", ".values().update(", ".values().clear(",
        ".values().append(", "files().create(", "files().update(", ".write_text(", ".write_bytes(",
    ]

    def test_cmd_triage_source_never_calls_write_functions(self):
        source = inspect.getsource(qa_manage.cmd_triage)
        for needle in self.FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(needle, source, f"cmd_triage source contains forbidden call: {needle!r}")

    def test_cmd_triage_one_source_never_calls_write_functions(self):
        source = inspect.getsource(qa_manage.cmd_triage_one)
        for needle in self.FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(needle, source, f"cmd_triage_one source contains forbidden call: {needle!r}")

    def test_cmd_triage_never_invokes_write_queue_or_sheet_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [row("r1", status="discovered")]
            with patch("qa_manage.write_queue") as mock_write_queue, \
                 patch("qa_manage.export_queue_terminal") as mock_export:
                res, mock_services = run_triage(rows, root)
            mock_write_queue.assert_not_called()
            mock_export.assert_not_called()
            mock_services["sheets"].spreadsheets().values().update.assert_not_called()
            mock_services["drive"].files().create.assert_not_called()
            self.assertTrue(res.ok)

    def test_cmd_triage_one_never_invokes_write_queue_or_sheet_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", status="discovered")
            with patch("qa_manage.write_queue") as mock_write_queue, \
                 patch("qa_manage.export_queue_terminal") as mock_export:
                res, mock_services = run_triage_one(r, root)
            mock_write_queue.assert_not_called()
            mock_export.assert_not_called()
            mock_services["sheets"].spreadsheets().values().update.assert_not_called()
            mock_services["drive"].files().create.assert_not_called()
            self.assertTrue(res.ok)
            self.assertEqual((root / "00_Inbox" / "r1.txt").read_text(encoding="utf-8"),
                             TRANSCRIPT_TWO_SPEAKERS)


class JsonEnvelopeTests(unittest.TestCase):
    def test_triage_json_envelope_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [row("r1", status="discovered")]
            mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
            with patch("sys.argv", ["qa_manage.py", "triage", "--json"]), \
                 patch("qa_manage.get_services_cached", return_value=mock_services), \
                 patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
                 patch("qa_manage.read_queue", return_value=rows), \
                 patch("qa_manage.DATA_ROOT", root):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    code = qa_manage.main()
            self.assertEqual(code, 0)
            envelope = json.loads(buf.getvalue())
            self.assertEqual(envelope["schema_version"], 1)
            self.assertTrue(envelope["ok"])
            self.assertEqual(envelope["command"], "triage")
            for key in ("category", "counts", "items", "guardrails"):
                self.assertIn(key, envelope["data"])

    def test_triage_one_json_envelope_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            rows = [row("r1", status="discovered")]
            mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
            with patch("sys.argv", ["qa_manage.py", "triage-one", "r1", "--json"]), \
                 patch("qa_manage.get_services_cached", return_value=mock_services), \
                 patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
                 patch("qa_manage.read_queue", return_value=rows), \
                 patch("qa_manage.load_graph", return_value=GRAPH), \
                 patch("qa_manage.DATA_ROOT", root):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    code = qa_manage.main()
            self.assertEqual(code, 0)
            envelope = json.loads(buf.getvalue())
            self.assertEqual(envelope["schema_version"], 1)
            self.assertTrue(envelope["ok"])
            self.assertEqual(envelope["command"], "triage-one")
            for key in ("identity", "source_preview", "classify", "allowed_terminal_actions",
                        "terminal_action_commands", "process_commands", "guardrails"):
                self.assertIn(key, envelope["data"])

    def test_ignore_missing_reason_json_envelope_ok_false(self):
        # --reason is a required argparse argument, so argparse itself
        # rejects this before cmd_ignore ever runs - JsonArgumentParser's
        # own error() prints the envelope and exits (same convention as
        # test_json_argument_parser_error in test_qa_manage_json.py).
        rows = [row("r1", status="discovered")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("sys.argv", ["qa_manage.py", "ignore", "r1", "--category", "other", "--json"]), \
             patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.write_queue") as mock_write_queue:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                with self.assertRaises(SystemExit) as cm:
                    qa_manage.main()
        self.assertEqual(cm.exception.code, 1)
        envelope = json.loads(buf.getvalue())
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["command"], "ignore")
        mock_write_queue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
