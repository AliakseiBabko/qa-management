"""Unit tests for Phase 12 (retrieval usability improvements):

- route_description surfaced by classify/pack/guide (Part B)
- validate_repo.py's check_graph rejecting a routed variant with no
  description (Part B)
- qa_manage.py's read-only `gates` command: pure grouping/sorting/filtering
  helpers, Drive-mocked integration, read-only enforcement, JSON envelope
  (Part C)

All fixture text uses placeholders - no real names/projects.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import qa_manage  # noqa: E402
import validate_repo  # noqa: E402


# ---------------------------------------------------------------------------
# Part B: route_description
# ---------------------------------------------------------------------------

ROUTE_DESC_GRAPH = {
    "sources": {
        "meeting_transcript": {
            "routes": {
                "multi_project": {
                    "description": "Placeholder description for multi_project.",
                    "skills": ["skill-a"],
                    "entry": ["m2_input_doc"],
                },
                "single_project": {
                    "description": "Placeholder description for single_project.",
                    "skills": ["skill-b"],
                    "entry": ["m2_input_doc"],
                },
            }
        },
    },
    "documents": {
        "m2_input_doc": {"scope": "project", "downstream": []},
    },
}


def _row(run_id, status="discovered", stage="", **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/{run_id}.txt",
        "Current source": f"00_Inbox/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "meeting_transcript", "Route variant": "multi_project",
        "Project": "<Project1>", "Person": "",
        "Scopes": '[["<Project1>", ""]]',
        "Status": status, "Stage": stage, "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "", "Last mutation": "2026-01-01 00:00",
        "Completed": "", "Snapshot": "", "Reason": "", "Summary": "", "Source text version": "",
    }
    base.update(extra)
    return base


def _ready_eval() -> qa_manage.EvaluationResult:
    return qa_manage.EvaluationResult(
        ready_for_completion=True, entry_problems=[], unresolved_edges=[],
        warnings=[], snapshot_sha="deadbeef", snapshot_problem="", invocation_present=True,
    )


class GuideArgs:
    def __init__(self, run_id, json=True, debug=False):
        self.run_id = run_id
        self.json = json
        self.debug = debug


class PackArgs:
    def __init__(self, run_id, json=True, debug=False, max_preview_chars=None):
        self.run_id = run_id
        self.json = json
        self.debug = debug
        self.max_preview_chars = max_preview_chars


class ClassifyArgs:
    def __init__(self, run_id, json=True, debug=False, max_preview_chars=None):
        self.run_id = run_id
        self.json = json
        self.debug = debug
        self.max_preview_chars = max_preview_chars


class RouteDescriptionInClassifyTests(unittest.TestCase):
    def test_classify_candidate_routes_includes_route_description(self):
        signals = {
            "text_readable": True,
            "distinct_speaker_prefixes": 0,
            "bracketed_speaker_marker_count": 3,
            "timestamp_turn_marker_count": 0,
            "distinct_turn_identities": 0,
        }
        candidates = qa_manage.classify_candidate_routes(ROUTE_DESC_GRAPH, signals, _row("r1"))
        self.assertTrue(candidates)
        for c in candidates:
            self.assertIn("route_description", c)
            self.assertTrue(c["route_description"], f"candidate {c} has an empty route_description")


class RouteDescriptionInGuideTests(unittest.TestCase):
    def test_guide_interpretation_includes_route_description(self):
        r = _row("r1", status="processing", stage="analysis")

        def fake_load_review_context(services, run_id, rows=None):
            return SimpleNamespace(row=next(x for x in (rows or []) if x["Run ID"] == run_id), all_rows=[])

        mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
        with patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=[r]), \
             patch("qa_manage.load_graph", return_value=ROUTE_DESC_GRAPH), \
             patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
             patch("qa_manage.evaluate_run", return_value=_ready_eval()):
            res = qa_manage.cmd_guide(GuideArgs("r1"))

        self.assertTrue(res.ok)
        self.assertEqual(res.data["interpretation"]["route_description"],
                          "Placeholder description for multi_project.")
        self.assertTrue(any("route:" in line for line in res.human_lines))


class RouteDescriptionInPackTests(unittest.TestCase):
    def test_pack_interpretation_and_graph_context_include_route_description(self):
        r = _row("r1", status="processing", stage="analysis")

        def fake_load_review_context(services, run_id, rows=None):
            return SimpleNamespace(row=next(x for x in (rows or []) if x["Run ID"] == run_id), all_rows=[])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00_Inbox").mkdir(parents=True, exist_ok=True)
            (root / "00_Inbox" / "r1.txt").write_text("placeholder content", encoding="utf-8")

            mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
            with patch("qa_manage.get_services_cached", return_value=mock_services), \
                 patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
                 patch("qa_manage.read_queue", return_value=[r]), \
                 patch("qa_manage.load_graph", return_value=ROUTE_DESC_GRAPH), \
                 patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
                 patch("qa_manage.evaluate_run", return_value=_ready_eval()), \
                 patch("qa_manage.DATA_ROOT", root):
                res = qa_manage.cmd_pack(PackArgs("r1"))

        self.assertTrue(res.ok)
        self.assertEqual(res.data["interpretation"]["route_description"],
                          "Placeholder description for multi_project.")
        self.assertEqual(res.data["graph_context"]["route_description"],
                          "Placeholder description for multi_project.")


class ValidatorRejectsMissingDescriptionTests(unittest.TestCase):
    def test_check_graph_fails_on_missing_route_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph_path = Path(tmp) / "document_graph.yaml"
            graph_path.write_text(
                "sources:\n"
                "  meeting_transcript:\n"
                "    routes:\n"
                "      multi_project:\n"
                "        skills: [skill-a]\n"
                "        entry: [m2_input_doc]\n"
                "documents:\n"
                "  m2_input_doc:\n"
                "    scope: project\n"
                "    downstream: []\n",
                encoding="utf-8",
            )
            validate_repo.failures.clear()
            validate_repo.warnings.clear()
            with patch.object(validate_repo, "GRAPH", graph_path):
                validate_repo.check_graph({"meeting_transcript"})
            self.assertTrue(
                any("no 'description'" in f for f in validate_repo.failures),
                validate_repo.failures,
            )

    def test_check_graph_passes_when_description_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph_path = Path(tmp) / "document_graph.yaml"
            graph_path.write_text(
                "sources:\n"
                "  meeting_transcript:\n"
                "    routes:\n"
                "      multi_project:\n"
                "        description: Placeholder description.\n"
                "        skills: [skill-a]\n"
                "        entry: [m2_input_doc]\n"
                "documents:\n"
                "  m2_input_doc:\n"
                "    scope: project\n"
                "    downstream: []\n",
                encoding="utf-8",
            )
            validate_repo.failures.clear()
            validate_repo.warnings.clear()
            with patch.object(validate_repo, "GRAPH", graph_path):
                validate_repo.check_graph({"meeting_transcript"})
            self.assertFalse(
                any("no 'description'" in f for f in validate_repo.failures),
                validate_repo.failures,
            )

    def test_real_document_graph_has_no_missing_descriptions(self):
        source_types = validate_repo.load_source_types()
        validate_repo.failures.clear()
        validate_repo.warnings.clear()
        validate_repo.check_graph(source_types)
        description_failures = [f for f in validate_repo.failures if "no 'description'" in f]
        self.assertEqual(description_failures, [])


# ---------------------------------------------------------------------------
# Part C: qa_manage.py gates
# ---------------------------------------------------------------------------

class ComputeRecommendedActionTests(unittest.TestCase):
    def test_no_action_yet_for_effectively_empty_round(self):
        action = qa_manage.compute_recommended_action(block_chars=10, has_open_queue_run=False, age_days=30)
        self.assertEqual(action, "no action yet")

    def test_process_existing_source_first_when_open_queue_run_exists(self):
        action = qa_manage.compute_recommended_action(block_chars=500, has_open_queue_run=True, age_days=1)
        self.assertEqual(action, "process existing source first")

    def test_ask_m2_for_answers_when_old_and_no_open_source(self):
        action = qa_manage.compute_recommended_action(block_chars=500, has_open_queue_run=False, age_days=10)
        self.assertEqual(action, "ask M2/user for answers")

    def test_manual_review_required_fallback(self):
        action = qa_manage.compute_recommended_action(block_chars=500, has_open_queue_run=False, age_days=0)
        self.assertEqual(action, "manual review required")

    def test_manual_review_required_when_age_unknown(self):
        action = qa_manage.compute_recommended_action(block_chars=500, has_open_queue_run=False, age_days=None)
        self.assertEqual(action, "manual review required")


class BuildGateRowTests(unittest.TestCase):
    def test_none_when_round_not_pending(self):
        summary = {"round_date": "2026-01-01", "pending": False, "addenda_count": 0,
                   "block_chars": 0, "first_heading": None}
        self.assertIsNone(qa_manage.build_gate_row("<Project1>", summary, False, dt.date(2026, 1, 15)))

    def test_none_when_pending_is_none(self):
        summary = {"round_date": None, "pending": None, "addenda_count": 0,
                   "block_chars": 0, "first_heading": None}
        self.assertIsNone(qa_manage.build_gate_row("<Project1>", summary, False, dt.date(2026, 1, 15)))

    def test_row_includes_age_days_and_gated_documents(self):
        summary = {"round_date": "2026-01-01", "pending": True, "addenda_count": 2,
                   "block_chars": 400, "first_heading": "Addendum (2026-01-05) - placeholder"}
        row = qa_manage.build_gate_row("<Project1>", summary, False, dt.date(2026, 1, 15))
        self.assertEqual(row["project"], "<Project1>")
        self.assertEqual(row["age_days"], 14)
        self.assertEqual(row["addenda_count"], 2)
        self.assertEqual(row["gated_documents"], ["project_risk", "project_development_plan"])
        self.assertEqual(row["gated_documents_secondary"], ["action_items"])
        self.assertEqual(row["recommended_action"], "ask M2/user for answers")
        # never the raw question/addendum text - only the heading label
        self.assertNotIn("notes", row)

    def test_row_age_days_none_when_round_date_unparseable(self):
        summary = {"round_date": "not-a-date", "pending": True, "addenda_count": 0,
                   "block_chars": 400, "first_heading": None}
        row = qa_manage.build_gate_row("<Project1>", summary, False, dt.date(2026, 1, 15))
        self.assertIsNone(row["age_days"])


def _gate_row(project, age_days, block_chars=400):
    return {
        "project": project, "round_date": "2026-01-01", "age_days": age_days,
        "addenda_count": 0, "first_heading": None, "block_chars": block_chars,
        "gated_documents": ["project_risk", "project_development_plan"],
        "gated_documents_secondary": ["action_items"],
        "recommended_action": "ask M2/user for answers",
    }


class SortAndFilterGatesTests(unittest.TestCase):
    def test_sorts_oldest_first(self):
        rows = [_gate_row("<Project1>", 2), _gate_row("<Project2>", 10), _gate_row("<Project3>", 5)]
        out = qa_manage.sort_and_filter_gates(rows)
        self.assertEqual([r["project"] for r in out], ["<Project2>", "<Project3>", "<Project1>"])

    def test_missing_age_sorts_last(self):
        rows = [_gate_row("<Project1>", None), _gate_row("<Project2>", 5)]
        out = qa_manage.sort_and_filter_gates(rows)
        self.assertEqual([r["project"] for r in out], ["<Project2>", "<Project1>"])

    def test_filters_by_project_case_insensitive(self):
        rows = [_gate_row("<Project1>", 2), _gate_row("<Project2>", 10)]
        out = qa_manage.sort_and_filter_gates(rows, project_filter="<project2>")
        self.assertEqual([r["project"] for r in out], ["<Project2>"])

    def test_filters_by_min_age_days(self):
        rows = [_gate_row("<Project1>", 2), _gate_row("<Project2>", 10)]
        out = qa_manage.sort_and_filter_gates(rows, min_age_days=5)
        self.assertEqual([r["project"] for r in out], ["<Project2>"])

    def test_applies_limit_after_sort(self):
        rows = [_gate_row("<Project1>", 2), _gate_row("<Project2>", 10), _gate_row("<Project3>", 5)]
        out = qa_manage.sort_and_filter_gates(rows, limit=1)
        self.assertEqual([r["project"] for r in out], ["<Project2>"])

    def test_no_rows_matches_project_filter_returns_empty(self):
        rows = [_gate_row("<Project1>", 2)]
        out = qa_manage.sort_and_filter_gates(rows, project_filter="<ProjectMissing>")
        self.assertEqual(out, [])


class GatesArgs:
    def __init__(self, project="", limit=0, min_age_days=0, json=True, debug=False):
        self.project = project
        self.limit = limit
        self.min_age_days = min_age_days
        self.json = json
        self.debug = debug


def _fake_folder(name):
    return {"id": f"folder-{name}", "name": name}


def _fake_project_folders(names):
    return [{"id": f"folder-{n}", "name": n, "mimeType": "application/vnd.google-apps.folder"} for n in names]


def run_gates(project_summaries: dict, queue_rows=None, args=None):
    """project_summaries: {project_name: get_pending_round_summary()-shaped dict}.
    Projects not in the dict have no m2_input doc (find_document returns None)."""
    queue_rows = queue_rows or []
    args = args or GatesArgs()
    mock_services = {"drive": MagicMock(), "sheets": MagicMock(), "docs": MagicMock()}

    def fake_find_document(drive, folder_id, role, name, mime_type, person=""):
        project = folder_id.replace("folder-", "")
        return {"id": f"doc-{project}"} if project in project_summaries else None

    def fake_get_pending_round_summary(docs, doc_id):
        project = doc_id.replace("doc-", "")
        return project_summaries[project]

    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=queue_rows), \
         patch("m2_workspace_layout.find_folder_path", return_value=_fake_folder("root")), \
         patch("m2_workspace_layout.list_children",
               return_value=_fake_project_folders(list(project_summaries))), \
         patch("m2_workspace_layout.find_document", side_effect=fake_find_document), \
         patch("pipeline_common.get_pending_round_summary", side_effect=fake_get_pending_round_summary):
        res = qa_manage.cmd_gates(args)
    return res, mock_services


class CmdGatesIntegrationTests(unittest.TestCase):
    def test_groups_and_sorts_pending_rounds_by_age(self):
        today = dt.date.today()
        summaries = {
            "<Project1>": {"round_date": (today - dt.timedelta(days=3)).isoformat(), "pending": True,
                           "addenda_count": 0, "block_chars": 300, "first_heading": None},
            "<Project2>": {"round_date": (today - dt.timedelta(days=10)).isoformat(), "pending": True,
                           "addenda_count": 1, "block_chars": 300, "first_heading": "Addendum (x)"},
            "<Project3>": {"round_date": today.isoformat(), "pending": False,
                           "addenda_count": 0, "block_chars": 0, "first_heading": None},
        }
        res, _ = run_gates(summaries)
        self.assertTrue(res.ok)
        projects = [g["project"] for g in res.data["gates"]]
        # Project3's round is answered (pending=False) - excluded entirely.
        self.assertEqual(projects, ["<Project2>", "<Project1>"])
        self.assertEqual(res.data["pending_rounds_total"], 2)
        self.assertEqual(res.data["projects_scanned"], 3)

    def test_filters_by_project_and_min_age_days(self):
        today = dt.date.today()
        summaries = {
            "<Project1>": {"round_date": (today - dt.timedelta(days=3)).isoformat(), "pending": True,
                           "addenda_count": 0, "block_chars": 300, "first_heading": None},
            "<Project2>": {"round_date": (today - dt.timedelta(days=10)).isoformat(), "pending": True,
                           "addenda_count": 1, "block_chars": 300, "first_heading": None},
        }
        res, _ = run_gates(summaries, args=GatesArgs(min_age_days=5))
        self.assertEqual([g["project"] for g in res.data["gates"]], ["<Project2>"])

        res2, _ = run_gates(summaries, args=GatesArgs(project="<Project1>"))
        self.assertEqual([g["project"] for g in res2.data["gates"]], ["<Project1>"])

    def test_recommends_process_existing_source_first_for_open_queue_project(self):
        today = dt.date.today()
        summaries = {
            "<Project1>": {"round_date": (today - dt.timedelta(days=10)).isoformat(), "pending": True,
                           "addenda_count": 0, "block_chars": 300, "first_heading": None},
        }
        queue_row = _row("qrun1", status="discovered", **{"Project": "<Project1>", "Scopes": ""})
        res, _ = run_gates(summaries, queue_rows=[queue_row])
        self.assertEqual(res.data["gates"][0]["recommended_action"], "process existing source first")

    def test_json_envelope_shape_via_main(self):
        today = dt.date.today()
        summaries = {
            "<Project1>": {"round_date": (today - dt.timedelta(days=3)).isoformat(), "pending": True,
                           "addenda_count": 0, "block_chars": 300, "first_heading": None},
        }
        mock_services = {"drive": MagicMock(), "sheets": MagicMock(), "docs": MagicMock()}

        def fake_find_document(drive, folder_id, role, name, mime_type, person=""):
            return {"id": "doc-<Project1>"}

        def fake_get_pending_round_summary(docs, doc_id):
            return summaries["<Project1>"]

        with patch("sys.argv", ["qa_manage.py", "gates", "--json"]), \
             patch("qa_manage.get_services_cached", return_value=mock_services), \
             patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
             patch("qa_manage.read_queue", return_value=[]), \
             patch("m2_workspace_layout.find_folder_path", return_value=_fake_folder("root")), \
             patch("m2_workspace_layout.list_children", return_value=_fake_project_folders(["<Project1>"])), \
             patch("m2_workspace_layout.find_document", side_effect=fake_find_document), \
             patch("pipeline_common.get_pending_round_summary", side_effect=fake_get_pending_round_summary):
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                code = qa_manage.main()
        self.assertEqual(code, 0)
        envelope = json.loads(buf.getvalue())
        self.assertEqual(envelope["schema_version"], 1)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["command"], "gates")
        self.assertIn("gates", envelope["data"])

    def test_read_only_no_write_queue_or_drive_sheet_writes(self):
        today = dt.date.today()
        summaries = {
            "<Project1>": {"round_date": (today - dt.timedelta(days=3)).isoformat(), "pending": True,
                           "addenda_count": 0, "block_chars": 300, "first_heading": None},
        }
        with patch("qa_manage.write_queue") as mock_write_queue, \
             patch("qa_manage.export_queue_terminal") as mock_export:
            res, mock_services = run_gates(summaries)
        mock_write_queue.assert_not_called()
        mock_export.assert_not_called()
        mock_services["sheets"].spreadsheets().values().update.assert_not_called()
        mock_services["sheets"].spreadsheets().values().append.assert_not_called()
        mock_services["sheets"].spreadsheets().values().clear.assert_not_called()
        mock_services["drive"].files().create.assert_not_called()
        mock_services["drive"].files().update.assert_not_called()
        self.assertTrue(res.ok)

    def test_no_real_names_in_fixture_projects(self):
        # Every project name used across this test module's fixtures is a
        # placeholder - never a real client/project name.
        for name in ("<Project1>", "<Project2>", "<Project3>", "<ProjectMissing>"):
            self.assertTrue(name.startswith("<") and name.endswith(">"))


if __name__ == "__main__":
    unittest.main()
