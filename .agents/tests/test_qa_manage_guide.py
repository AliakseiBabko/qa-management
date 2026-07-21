"""Unit tests for qa_manage.py's read-only `guide <run-id>` command.

guide answers "exactly what do I do next for THIS run" (dashboard answers
"what needs attention across the whole queue"). Covers each status/stage's
checklist+commands, read-only enforcement, JSON envelope, an unknown
run_id, and no real names/projects in any fixture.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import inspect
import io
import json
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
                "m2": {"skills": ["skill-a", "skill-b"],
                       "entry": ["doc_one", "doc_two", "doc_three"]}
            }
        }
    },
    "documents": {
        "doc_one": {"scope": "person", "downstream": [{"to": "doc_two", "kind": "direct"}]},
        "doc_two": {"scope": "project", "downstream": []},
        "doc_three": {"scope": "project", "downstream": []},
    },
}


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
    def __init__(self, run_id, json=True, debug=False):
        self.run_id = run_id
        self.json = json
        self.debug = debug


def run_guide(target_row, other_rows=None, eval_res=None):
    rows = (other_rows or []) + [target_row]
    eval_res = eval_res or ready_eval()

    def fake_load_review_context(services, run_id, rows=None):
        return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id),
                               all_rows=[])

    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.load_graph", return_value=GRAPH), \
         patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
         patch("qa_manage.evaluate_run", return_value=eval_res):
        res = qa_manage.cmd_guide(Args(target_row["Run ID"]))
    return res, mock_services


class DiscoveredGuideTests(unittest.TestCase):
    def test_discovered_checklist_and_command(self):
        r = row("r1", "discovered", **{"Source type": "", "Route variant": ""})
        res, _ = run_guide(r)
        self.assertTrue(res.ok)
        self.assertEqual(res.data["identity"]["status"], "discovered")
        self.assertTrue(any("classify" in c.lower() for c in res.data["checklist"]))
        self.assertTrue(res.data["commands"][0].startswith("start r1 "))
        self.assertIn("qa_1to1", res.data["routed_source_types"])
        # scope guardrail applies to discovered
        self.assertTrue(any("default" in g.lower() for g in res.data["guardrails"]))

    def test_checklist_reads_current_source_when_it_differs_from_source(self):
        r = row("r1", "discovered",
                Source="00_Source_Docs\\01_Meeting_Transcripts\\legacy name.txt",
                **{"Current source": "00_Inbox/legacy name.txt"})
        res, _ = run_guide(r)
        self.assertEqual(res.data["identity"]["source"], "00_Source_Docs\\01_Meeting_Transcripts\\legacy name.txt")
        self.assertEqual(res.data["identity"]["current_source"], "00_Inbox/legacy name.txt")
        read_step = res.data["checklist"][0]
        self.assertIn("Current source: 00_Inbox/legacy name.txt", read_step)
        self.assertNotIn("00_Source_Docs", read_step)

    def test_checklist_falls_back_to_source_when_current_source_blank(self):
        r = row("r1", "discovered", Source="00_Inbox/original name.txt",
                **{"Current source": ""})
        res, _ = run_guide(r)
        read_step = res.data["checklist"][0]
        self.assertIn("Current source is blank", read_step)
        self.assertIn("read original Source: 00_Inbox/original name.txt", read_step)

    def test_human_output_never_says_ambiguous_path_above(self):
        r = row("r1", "discovered",
                Source="00_Source_Docs\\01_Meeting_Transcripts\\legacy name.txt",
                **{"Current source": "00_Inbox/legacy name.txt"})
        rows = [r]
        eval_res = ready_eval()

        def fake_load_review_context(services, run_id, rows=None):
            return SimpleNamespace(row=next(x for x in (rows or []) if x["Run ID"] == run_id), all_rows=[])

        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.load_graph", return_value=GRAPH), \
             patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
             patch("qa_manage.evaluate_run", return_value=eval_res):
            res = qa_manage.cmd_guide(Args("r1", json=False))

        human_text = "\n".join(res.human_lines)
        self.assertNotIn("path above", human_text)
        self.assertIn("Current source: 00_Inbox/legacy name.txt", human_text)

    def test_json_identity_keeps_both_fields_while_checklist_names_current_source(self):
        r = row("r1", "discovered",
                Source="00_Source_Docs\\01_Meeting_Transcripts\\legacy name.txt",
                **{"Current source": "00_Inbox/legacy name.txt"})
        res, _ = run_guide(r)
        self.assertEqual(res.data["identity"]["source"], "00_Source_Docs\\01_Meeting_Transcripts\\legacy name.txt")
        self.assertEqual(res.data["identity"]["current_source"], "00_Inbox/legacy name.txt")
        self.assertIn("Current source: 00_Inbox/legacy name.txt", res.data["checklist"][0])

    def test_discovered_guardrails_include_current_source_and_summary_rules(self):
        r = row("r1", "discovered")
        res, _ = run_guide(r)
        joined = " ".join(res.data["guardrails"]).lower()
        self.assertIn("current source", joined)
        self.assertIn("immutable discovery identity", joined)
        self.assertIn("short summaries", joined)
        self.assertIn("never full transcript", joined)


class NeedsScopeGuideTests(unittest.TestCase):
    def test_needs_scope_shows_missing_fields_and_command(self):
        r = row("r1", "needs_scope", Reason="route entry documents are project/person-scoped")
        res, _ = run_guide(r)
        self.assertEqual(res.data["missing_scope_fields"], [])  # scope already fully declared here
        self.assertTrue(res.data["commands"][0].startswith("start r1 --source-type qa_1to1"))

    def test_needs_scope_reports_actually_missing_fields(self):
        r = row("r1", "needs_scope", Scopes="", Project="", Person="")
        res, _ = run_guide(r)
        self.assertEqual(sorted(res.data["missing_scope_fields"]), ["person", "project"])


class ProcessingAnalysisGuideTests(unittest.TestCase):
    def test_processing_analysis_recommends_record_analysis(self):
        r = row("r1", "processing", "analysis")
        res, _ = run_guide(r)
        self.assertIn("skill-a", res.data["checklist"][0])
        self.assertEqual(res.data["commands"], ['record-analysis r1 --summary "..."'])


class ProcessingApplyGuideTests(unittest.TestCase):
    def test_processing_apply_missing_record_apply(self):
        r = row("r1", "processing", "apply", Entries='{"<Project1>|<Person1>": {"doc_one": ["updated", ""]}}')
        res, _ = run_guide(r)
        missing = res.data["missing_entry_documents_by_scope"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(sorted(missing[0]["missing_documents"]), ["doc_three", "doc_two"])
        self.assertTrue(any("record-apply r1" in c and "--project" in c for c in res.data["commands"]))

    def test_processing_apply_all_recorded_shows_no_missing(self):
        r = row("r1", "processing", "apply",
                Entries='{"<Project1>|<Person1>": {"doc_one": ["updated", ""], '
                        '"doc_two": ["updated", ""], "doc_three": ["no_change", "n/a"]}}')
        res, _ = run_guide(r)
        self.assertEqual(res.data["commands"], [])
        self.assertIn("All entry documents already have an outcome", " ".join(res.data["checklist"]))


class ProcessingClosureGuideTests(unittest.TestCase):
    def test_closure_unresolved_edges_shown_with_resolve_edge_command(self):
        eval_res = broken_eval(unresolved_edges=[
            "scope (<Project1>, <Person1>, m2): unresolved edge doc_one -> doc_two [direct]"
        ])
        r = row("r1", "processing", "closure")
        res, _ = run_guide(r, eval_res=eval_res)
        edges = res.data["unresolved_edges"]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0], {"project": "<Project1>", "person": "<Person1>", "variant": "m2",
                                    "source": "doc_one", "target": "doc_two", "kind": "direct"})
        cmd = res.data["commands"][0]
        self.assertIn("resolve-edge r1 --source doc_one --target doc_two", cmd)
        self.assertIn('--project "<Project1>" --person "<Person1>"', cmd)

    def test_closure_ready_but_missing_snapshot_recommends_commit_workspace_state(self):
        eval_res = broken_eval(snapshot_problem="no mirror commit mentions r1")
        r = row("r1", "processing", "closure")
        res, _ = run_guide(r, eval_res=eval_res)
        self.assertTrue(any("commit_workspace_state.py" in c and "r1" in c for c in res.data["commands"]))

    def test_closure_missing_invocation_recommends_commit_workspace_state(self):
        eval_res = broken_eval(invocation_present=False)
        r = row("r1", "processing", "closure")
        res, _ = run_guide(r, eval_res=eval_res)
        self.assertTrue(any("commit_workspace_state.py" in c for c in res.data["commands"]))

    def test_closure_missing_entry_outcome_recommends_record_apply(self):
        eval_res = broken_eval(entry_problems=[
            "scope (<Project1>, <Person1>, m2): entry document 'doc_two' has no recorded outcome "
            "(record-apply --updated/--no-change/--not-applicable)"
        ])
        r = row("r1", "processing", "closure")
        res, _ = run_guide(r, eval_res=eval_res)
        self.assertEqual(res.data["missing_entry_documents"],
                         [{"project": "<Project1>", "person": "<Person1>", "variant": "m2", "doc": "doc_two"}])
        self.assertTrue(any("record-apply r1" in c and "doc_two" in c for c in res.data["commands"]))

    def test_closure_archive_needed_recommends_archive_source(self):
        eval_res = broken_eval(entry_problems=[
            "Source original is still in 00_Inbox; run archive-source before snapshotting."
        ])
        r = row("r1", "processing", "closure")
        res, _ = run_guide(r, eval_res=eval_res)
        self.assertEqual(res.data["commands"][0], "archive-source r1")
        self.assertTrue(any("archive-source must run BEFORE" in g for g in res.data["guardrails"]))

    def test_closure_ready_recommends_complete(self):
        r = row("r1", "processing", "closure")
        res, _ = run_guide(r, eval_res=ready_eval())
        self.assertEqual(res.data["commands"], ["complete r1"])
        self.assertTrue(any("run:<run-id>" in g for g in res.data["guardrails"]))


class BlockedGuideTests(unittest.TestCase):
    def test_blocked_shows_reason_and_resume(self):
        r = row("r1", "blocked", Reason="waiting on client answer")
        res, _ = run_guide(r)
        self.assertIn("waiting on client answer", res.data["checklist"][0])
        self.assertEqual(res.data["commands"], ["resume r1 --continue"])


class FinalizingGuideTests(unittest.TestCase):
    def test_finalizing_recommends_complete_retry(self):
        eval_res = broken_eval(snapshot_problem="pending")
        r = row("r1", "finalizing")
        res, _ = run_guide(r, eval_res=eval_res)
        self.assertEqual(res.data["commands"], ["complete r1"])
        self.assertTrue(any("retry" in c.lower() for c in res.data["checklist"]))


class CompletedGuideTests(unittest.TestCase):
    def test_completed_healthy_run_recommends_no_action(self):
        eval_res = broken_eval(entry_problems=["Run cannot be completed from state 'completed'."])
        r = row("r1", "completed", "done", Completed="2026-01-01 00:00")
        res, _ = run_guide(r, eval_res=eval_res)
        self.assertEqual(res.data["commands"], [])
        self.assertIn("no operational action needed", " ".join(res.data["checklist"]).lower())

    def test_completed_run_with_integrity_issue_surfaces_repair_guidance(self):
        eval_res = broken_eval(
            entry_problems=["Run cannot be completed from state 'completed'."],
            snapshot_problem="snapshot predates last mutation",
        )
        r = row("r1", "completed", "done", Completed="2026-01-01 00:00")
        res, _ = run_guide(r, eval_res=eval_res)
        self.assertIn("snapshot predates last mutation", res.data["problems"])
        self.assertNotIn("Run cannot be completed from state 'completed'.", res.data["problems"])
        joined = " ".join(res.data["checklist"]).lower()
        self.assertIn("do not edit", joined)
        self.assertTrue(any("repair" in c.lower() for c in res.data["checklist"]))
        self.assertTrue(any("immutable" in g.lower() for g in res.data["guardrails"]))
        # never a mutation command - only review/audit guidance
        self.assertTrue(all(c.startswith("review ") for c in res.data["commands"]))


class TerminalStatesGuideTests(unittest.TestCase):
    def test_historical_shows_terminal_state_no_action(self):
        r = row("r1", "historical", Reason="pre-queue history: evidence")
        res, _ = run_guide(r)
        self.assertEqual(res.data["commands"], [])
        self.assertIn("historical", res.data["checklist"][0])

    def test_ignored_shows_terminal_state_no_action(self):
        r = row("r1", "ignored", Reason="ignored (reference_material)")
        res, _ = run_guide(r)
        self.assertEqual(res.data["commands"], [])

    def test_failed_offers_historical_correction(self):
        r = row("r1", "failed", Reason="gave up")
        res, _ = run_guide(r)
        self.assertEqual(res.data["commands"], ['mark-historical r1 --evidence "..."'])


class ReadOnlyEnforcementTests(unittest.TestCase):
    FORBIDDEN_SUBSTRINGS = [
        "write_queue(", "export_queue_terminal(", "mirror_git(MIRROR, \"add\"",
        "mirror_git(MIRROR, \"commit\"", ".values().update(", ".values().clear(",
        ".values().append(", "files().create(", "files().update(",
    ]

    def test_cmd_guide_source_never_calls_write_functions(self):
        source = inspect.getsource(qa_manage.cmd_guide)
        for needle in self.FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(needle, source, f"cmd_guide source contains forbidden call: {needle!r}")

    def test_cmd_guide_never_invokes_write_queue_or_sheet_writes(self):
        r = row("r1", "discovered")
        with patch("qa_manage.write_queue") as mock_write_queue, \
             patch("qa_manage.export_queue_terminal") as mock_export:
            res, mock_services = run_guide(r)

        mock_write_queue.assert_not_called()
        mock_export.assert_not_called()
        mock_services["sheets"].spreadsheets().values().update.assert_not_called()
        mock_services["sheets"].spreadsheets().values().append.assert_not_called()
        mock_services["sheets"].spreadsheets().values().clear.assert_not_called()
        mock_services["drive"].files().create.assert_not_called()
        mock_services["drive"].files().update.assert_not_called()
        self.assertTrue(res.ok)


class JsonEnvelopeTests(unittest.TestCase):
    def test_json_envelope_shape_via_main(self):
        rows = [row("r1", "discovered")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}

        def fake_load_review_context(services, run_id, rows=None):
            return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id), all_rows=[])

        with patch("sys.argv", ["qa_manage.py", "guide", "r1", "--json"]), \
             patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.load_graph", return_value=GRAPH), \
             patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
             patch("qa_manage.evaluate_run", return_value=ready_eval()):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = qa_manage.main()
        self.assertEqual(code, 0)
        envelope = json.loads(buf.getvalue())
        self.assertEqual(envelope["schema_version"], 1)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["command"], "guide")
        for key in ("run_id", "identity", "interpretation", "checklist", "commands", "guardrails"):
            self.assertIn(key, envelope["data"])
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual(envelope["errors"], [])


class UnknownRunTests(unittest.TestCase):
    def test_unknown_run_id_returns_ok_false_with_useful_error(self):
        rows = [row("real-run", "discovered")]
        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("sys.argv", ["qa_manage.py", "guide", "does-not-exist", "--json"]), \
             patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=rows), \
             patch("qa_manage.load_graph", return_value=GRAPH):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = qa_manage.main()
        self.assertEqual(code, 1)
        envelope = json.loads(buf.getvalue())
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["command"], "guide")
        self.assertEqual(len(envelope["errors"]), 1)
        self.assertIn("does-not-exist", envelope["errors"][0])
        self.assertIn("No queue row", envelope["errors"][0])


class ParserHelperTests(unittest.TestCase):
    def test_parse_unresolved_edge_entry(self):
        parsed = qa_manage.parse_unresolved_edge_entry(
            "scope (-, <Person1>, m2): unresolved edge doc_one -> doc_two [judgment]"
        )
        self.assertEqual(parsed, {"project": "", "person": "<Person1>", "variant": "m2",
                                  "source": "doc_one", "target": "doc_two", "kind": "judgment"})

    def test_parse_unresolved_edge_entry_no_match_returns_none(self):
        self.assertIsNone(qa_manage.parse_unresolved_edge_entry("not a matching string"))

    def test_parse_missing_entry_document(self):
        parsed = qa_manage.parse_missing_entry_document(
            "scope (<Project1>, -, m2): entry document 'doc_two' has no recorded outcome "
            "(record-apply --updated/--no-change/--not-applicable)"
        )
        self.assertEqual(parsed, {"project": "<Project1>", "person": "", "variant": "m2", "doc": "doc_two"})

    def test_parse_missing_entry_document_no_match_returns_none(self):
        self.assertIsNone(qa_manage.parse_missing_entry_document(
            "Source original is still in 00_Inbox; run archive-source before snapshotting."))

    def test_guide_scope_cli_args_both_empty(self):
        self.assertEqual(qa_manage.guide_scope_cli_args("", ""), "")

    def test_guide_scope_cli_args_emits_both_when_either_present(self):
        self.assertIn('--project "<Project1>"', qa_manage.guide_scope_cli_args("<Project1>", ""))
        self.assertIn('--person ""', qa_manage.guide_scope_cli_args("<Project1>", ""))


if __name__ == "__main__":
    unittest.main()
