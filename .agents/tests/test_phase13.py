"""Unit tests for Phase 13.1 (Project Knowledge lane, 30_Project_Knowledge):

- document_graph.yaml: new source types, route descriptions, document nodes
- project_knowledge_workspace_layout.py: path/folder resolution (mocked)
- qa_manage.py classify: candidates for the 4 new source types
- show_project_state.py --lane project_knowledge (mocked); default m2 unchanged
- search_workspace.py: 30_Project_Knowledge accepted in CANONICAL_ROOTS
- Templates/pk_*.md, performance_test_plan.md, test_plan.md, test_strategy.md:
  required headings present
- no real names/projects in any fixture here

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import qa_manage  # noqa: E402
import validate_repo  # noqa: E402
import search_workspace  # noqa: E402
import project_knowledge_workspace_layout as pk_layout  # noqa: E402
import show_project_state  # noqa: E402


# ---------------------------------------------------------------------------
# document_graph.yaml
# ---------------------------------------------------------------------------

class DocumentGraphProjectKnowledgeTests(unittest.TestCase):
    def test_real_graph_has_pk_source_types_with_descriptions(self):
        graph = qa_manage.load_graph()
        sources = graph["sources"]
        for stype in ("project_knowledge_transcript", "project_knowledge_document",
                      "project_knowledge_chat", "project_knowledge_notes"):
            self.assertIn(stype, sources)
            self.assertTrue(sources[stype].get("description", "").strip(),
                             f"{stype} has no description")
            self.assertEqual(sources[stype].get("lane"), "project_knowledge")

    def test_real_graph_has_pk_document_nodes(self):
        graph = qa_manage.load_graph()
        docs = graph["documents"]
        for node in ("pk_source_index", "pk_summary", "pk_knowledge_base",
                     "pk_performance_test_plan", "pk_test_plan", "pk_test_strategy"):
            self.assertIn(node, docs)

    def test_real_graph_has_lanes_mapping(self):
        graph = qa_manage.load_graph()
        lanes = graph.get("lanes") or {}
        self.assertEqual(lanes["m2_project_management"]["root_folder"], "20_M2_Project_Management")
        self.assertEqual(lanes["project_knowledge"]["root_folder"], "30_Project_Knowledge")
        # Phase 14A: added so a future scoped-export mode can resolve
        # person-scoped M1 runs to a folder root the same way project-scoped
        # runs already resolve via the two lanes above.
        self.assertEqual(lanes["m1_people_management"]["root_folder"], "10_M1_People_Management")

    def test_pk_source_edges_match_spec(self):
        graph = qa_manage.load_graph()
        sources = graph["sources"]
        for stype in ("project_knowledge_transcript", "project_knowledge_document",
                      "project_knowledge_chat"):
            entry = sources[stype]["entry"]
            for expected in ("pk_source_index", "pk_summary", "pk_knowledge_base", "_skill_invocations"):
                self.assertIn(expected, entry, f"{stype} missing {expected}")
        notes_entry = sources["project_knowledge_notes"]["entry"]
        self.assertIn("pk_source_index", notes_entry)
        self.assertIn("pk_knowledge_base", notes_entry)
        self.assertIn("_skill_invocations", notes_entry)
        self.assertNotIn("pk_summary", notes_entry)

    def test_pk_summary_downstream_is_judgment_to_knowledge_base(self):
        graph = qa_manage.load_graph()
        downstream = graph["documents"]["pk_summary"]["downstream"]
        edge = next(e for e in downstream if e["to"] == "pk_knowledge_base")
        self.assertEqual(edge["kind"], "judgment")

    def test_pk_knowledge_base_downstream_edges_are_judgment(self):
        graph = qa_manage.load_graph()
        downstream = graph["documents"]["pk_knowledge_base"]["downstream"]
        targets = {e["to"]: e["kind"] for e in downstream}
        self.assertEqual(targets.get("pk_performance_test_plan"), "judgment")
        self.assertEqual(targets.get("pk_test_plan"), "judgment")
        self.assertEqual(targets.get("pk_test_strategy"), "judgment")

    def test_validate_repo_check_graph_passes_for_real_graph(self):
        source_types = validate_repo.load_source_types()
        validate_repo.failures.clear()
        validate_repo.warnings.clear()
        validate_repo.check_graph(source_types)
        self.assertEqual(validate_repo.failures, [])

    def test_pk_source_types_are_canonical(self):
        from pipeline_common import SKILL_INVOCATION_SOURCE_TYPES
        for stype in ("project_knowledge_transcript", "project_knowledge_document",
                      "project_knowledge_chat", "project_knowledge_notes"):
            self.assertIn(stype, SKILL_INVOCATION_SOURCE_TYPES)


# ---------------------------------------------------------------------------
# project_knowledge_workspace_layout.py
# ---------------------------------------------------------------------------

class ProjectKnowledgeWorkspaceLayoutTests(unittest.TestCase):
    def test_find_root_returns_none_when_missing(self):
        with patch.object(pk_layout, "find_child_folder", return_value=None) as mock_find:
            result = pk_layout.find_root(MagicMock())
        self.assertIsNone(result)
        mock_find.assert_called_once()
        _, args, kwargs = mock_find.mock_calls[0]
        self.assertEqual(args[-1], "30_Project_Knowledge")

    def test_ensure_project_folder_creates_project_and_subfolders(self):
        root = {"id": "root-id"}
        project_folder = {"id": "project-id"}
        with patch.object(pk_layout, "ensure_child_folder") as mock_ensure:
            mock_ensure.side_effect = [root, project_folder, {"id": "kb"}, {"id": "sm"}, {"id": "qd"}]
            result = pk_layout.ensure_project_folder(MagicMock(), "<Project1>")
        self.assertEqual(result, project_folder)
        self.assertEqual(mock_ensure.call_count, 5)
        created_names = [c.args[-1] for c in mock_ensure.mock_calls]
        self.assertEqual(created_names, ["30_Project_Knowledge", "<Project1>",
                                          "knowledge_base", "summaries", "qa_docs"])

    def test_find_document_resolves_knowledge_base_name_with_project(self):
        drive = MagicMock()
        with patch.object(pk_layout, "_find_subfolder", return_value={"id": "kb-folder"}), \
             patch.object(pk_layout, "drive_query", return_value=[{"id": "doc-1"}]) as mock_query:
            result = pk_layout.find_document(drive, "project-id", "pk_knowledge_base", project="<Project1>")
        self.assertEqual(result, {"id": "doc-1"})
        query_str = mock_query.call_args.args[1]
        self.assertIn("<Project1>_knowledge_base", query_str)

    def test_find_document_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            pk_layout.find_document(MagicMock(), "project-id", "not_a_real_role")

    def test_find_document_raises_on_duplicates(self):
        with patch.object(pk_layout, "_find_subfolder", return_value={"id": "folder"}), \
             patch.object(pk_layout, "drive_query", return_value=[{"id": "a"}, {"id": "b"}]):
            with self.assertRaises(RuntimeError):
                pk_layout.find_document(MagicMock(), "project-id", "pk_source_index")

    def test_find_document_returns_none_when_folder_missing(self):
        with patch.object(pk_layout, "_find_subfolder", return_value=None):
            result = pk_layout.find_document(MagicMock(), "project-id", "pk_test_plan")
        self.assertIsNone(result)

    def test_summary_document_name(self):
        self.assertEqual(pk_layout.summary_document_name("<source-slug>"), "<source-slug>_summary")

    def test_find_summary_document_uses_summaries_subfolder(self):
        with patch.object(pk_layout, "_find_subfolder", return_value={"id": "summaries-folder"}) as mock_sub, \
             patch.object(pk_layout, "drive_query", return_value=[{"id": "doc-1"}]) as mock_query:
            result = pk_layout.find_summary_document(MagicMock(), "project-id", "<source-slug>")
        self.assertEqual(result, {"id": "doc-1"})
        mock_sub.assert_called_once()
        self.assertEqual(mock_sub.call_args.args[-1], pk_layout.SUMMARY_FOLDER_PARTS)
        self.assertIn("<source-slug>_summary", mock_query.call_args.args[1])


# ---------------------------------------------------------------------------
# qa_manage.py classify candidates for the 4 new source types
# ---------------------------------------------------------------------------

def _row(run_id, **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/{run_id}.txt",
        "Current source": f"00_Inbox/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "", "Route variant": "",
        "Project": "", "Person": "", "Scopes": "",
        "Status": "discovered", "Stage": "", "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "", "Last mutation": "2026-01-01 00:00",
        "Completed": "", "Snapshot": "", "Reason": "", "Summary": "", "Source text version": "",
    }
    base.update(extra)
    return base


class ClassifyProjectKnowledgeCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.graph = qa_manage.load_graph()

    def test_transcript_like_signals_include_project_knowledge_transcript(self):
        signals = {
            "text_readable": True, "distinct_speaker_prefixes": 0,
            "bracketed_speaker_marker_count": 3, "timestamp_turn_marker_count": 0,
            "distinct_turn_identities": 0, "line_count": 100,
        }
        candidates = qa_manage.classify_candidate_routes(self.graph, signals, _row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertIn(("project_knowledge_transcript", ""), types)
        self.assertIn(("meeting_transcript", "multi_project"), types)

    def test_two_speaker_signals_include_project_knowledge_transcript(self):
        signals = {
            "text_readable": True, "distinct_speaker_prefixes": 2,
            "bracketed_speaker_marker_count": 0, "timestamp_turn_marker_count": 0,
            "distinct_turn_identities": 0, "line_count": 100,
        }
        candidates = qa_manage.classify_candidate_routes(self.graph, signals, _row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertIn(("project_knowledge_transcript", ""), types)
        self.assertIn(("qa_1to1", "m1"), types)

    def test_chat_like_signals_include_project_knowledge_chat(self):
        signals = {
            "text_readable": True, "distinct_speaker_prefixes": 0,
            "bracketed_speaker_marker_count": 0, "timestamp_turn_marker_count": 0,
            "distinct_turn_identities": 0, "likely_chat": True, "chat_header_line_count": 5,
            "line_count": 100,
        }
        candidates = qa_manage.classify_candidate_routes(self.graph, signals, _row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertIn(("project_knowledge_chat", ""), types)
        self.assertIn(("strategy_chat", ""), types)

    def test_plain_long_text_suggests_project_knowledge_document(self):
        signals = {
            "text_readable": True, "distinct_speaker_prefixes": 0,
            "bracketed_speaker_marker_count": 0, "timestamp_turn_marker_count": 0,
            "distinct_turn_identities": 0, "line_count": 200,
        }
        candidates = qa_manage.classify_candidate_routes(self.graph, signals, _row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertEqual(types, {("project_knowledge_document", "")})

    def test_short_plain_text_suggests_project_knowledge_notes(self):
        signals = {
            "text_readable": True, "distinct_speaker_prefixes": 0,
            "bracketed_speaker_marker_count": 0, "timestamp_turn_marker_count": 0,
            "distinct_turn_identities": 0, "line_count": 5,
        }
        candidates = qa_manage.classify_candidate_routes(self.graph, signals, _row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertEqual(types, {("project_knowledge_notes", "")})

    def test_candidates_never_pick_a_final_route_or_infer_project(self):
        signals = {"text_readable": True, "distinct_speaker_prefixes": 0,
                   "bracketed_speaker_marker_count": 3, "timestamp_turn_marker_count": 0,
                   "distinct_turn_identities": 0, "line_count": 100}
        candidates = qa_manage.classify_candidate_routes(self.graph, signals, _row("r1"))
        pk_candidates = [c for c in candidates if c["source_type"].startswith("project_knowledge")]
        self.assertTrue(pk_candidates)
        for c in pk_candidates:
            self.assertTrue(c["route_description"])
            self.assertNotIn("project", c)  # no inferred project field on the candidate dict


# ---------------------------------------------------------------------------
# show_project_state.py --lane
# ---------------------------------------------------------------------------

class ShowProjectStateLaneArgsTests(unittest.TestCase):
    def _parse(self, argv):
        with patch.object(sys, "argv", ["show_project_state.py"] + argv):
            return show_project_state.parse_args()

    def test_default_lane_is_m2(self):
        args = self._parse(["--project", "<Project1>"])
        self.assertEqual(args.lane, "m2")

    def test_project_knowledge_lane_requires_project(self):
        with self.assertRaises(show_project_state.ParserError):
            self._parse(["--lane", "project_knowledge"])

    def test_project_knowledge_lane_rejects_registries(self):
        with self.assertRaises(show_project_state.ParserError):
            self._parse(["--lane", "project_knowledge", "--project", "<Project1>", "--registries"])

    def test_project_knowledge_lane_rejects_summary(self):
        with self.assertRaises(show_project_state.ParserError):
            self._parse(["--lane", "project_knowledge", "--project", "<Project1>", "--summary"])

    def test_project_knowledge_lane_rejects_person(self):
        with self.assertRaises(show_project_state.ParserError):
            self._parse(["--lane", "project_knowledge", "--project", "<Project1>", "--person", "<Person1>"])

    def test_project_knowledge_lane_rejects_unknown_document(self):
        with self.assertRaises(show_project_state.ParserError):
            self._parse(["--lane", "project_knowledge", "--project", "<Project1>", "--document", "project_risk"])

    def test_project_knowledge_lane_accepts_known_document(self):
        args = self._parse(["--lane", "project_knowledge", "--project", "<Project1>",
                            "--document", "pk_knowledge_base"])
        self.assertEqual(args.document, ["pk_knowledge_base"])


class ShowProjectStateLaneRunTests(unittest.TestCase):
    def test_project_not_found_returns_error_envelope(self):
        args = MagicMock(project="<Project1>", lane="project_knowledge", document=[],
                          credentials=".local/google/credentials.json", token=".local/google/token.json",
                          json=True, limit=None)
        mock_services = {"drive": MagicMock(), "sheets": MagicMock(), "docs": MagicMock()}
        with patch.object(show_project_state, "get_services", return_value=mock_services), \
             patch.object(pk_layout, "find_project_folder", return_value=None):
            envelope, code = show_project_state.do_run_project_knowledge(args)
        self.assertFalse(envelope["ok"])
        self.assertEqual(code, 1)

    def test_targeted_document_read_returns_envelope_with_content(self):
        args = MagicMock(project="<Project1>", lane="project_knowledge",
                          document=["pk_knowledge_base"], credentials=".local/google/credentials.json",
                          token=".local/google/token.json", json=True, limit=None)
        mock_services = {"drive": MagicMock(), "sheets": MagicMock(), "docs": MagicMock()}
        with patch.object(show_project_state, "get_services", return_value=mock_services), \
             patch.object(pk_layout, "find_project_folder", return_value={"id": "project-id"}), \
             patch.object(pk_layout, "find_document", return_value={"id": "doc-1"}), \
             patch.object(show_project_state, "read_doc_paragraphs", return_value=["Overview paragraph."]):
            envelope, code = show_project_state.do_run_project_knowledge(args)
        self.assertTrue(envelope["ok"])
        self.assertEqual(code, 0)
        doc = envelope["data"]["documents"][0]
        self.assertEqual(doc["name"], "pk_knowledge_base")
        self.assertFalse(doc["missing"])
        self.assertEqual(doc["content"], ["Overview paragraph."])

    def test_full_listing_reports_fixed_docs_and_summaries(self):
        args = MagicMock(project="<Project1>", lane="project_knowledge", document=[],
                          credentials=".local/google/credentials.json", token=".local/google/token.json",
                          json=True, limit=None)
        mock_services = {"drive": MagicMock(), "sheets": MagicMock(), "docs": MagicMock()}

        def fake_find_document(drive, project_folder_id, role, project=""):
            return {"id": f"doc-{role}"} if role == "pk_knowledge_base" else None

        with patch.object(show_project_state, "get_services", return_value=mock_services), \
             patch.object(pk_layout, "find_project_folder", return_value={"id": "project-id"}), \
             patch.object(pk_layout, "find_document", side_effect=fake_find_document), \
             patch.object(pk_layout, "_find_subfolder", return_value=None):
            envelope, code = show_project_state.do_run_project_knowledge(args)
        self.assertTrue(envelope["ok"])
        self.assertEqual(code, 0)
        self.assertIsNotNone(envelope["data"]["documents"]["pk_knowledge_base"])
        self.assertIsNone(envelope["data"]["documents"]["pk_test_plan"])
        self.assertEqual(envelope["data"]["summaries"], [])

    def test_m2_lane_default_path_unaffected(self):
        # Confirms do_run still dispatches to the untouched M2 path when
        # lane is the default "m2" - do_run_project_knowledge is never
        # called in that case.
        args = MagicMock(lane="m2", project="", registries=False, summary=False, document=[])
        with patch.object(show_project_state, "do_run_project_knowledge") as mock_pk_run:
            envelope, code = show_project_state.do_run(args)
        mock_pk_run.assert_not_called()
        self.assertFalse(envelope["ok"])  # "nothing to do" - no project/registries/summary/document
        self.assertEqual(code, 1)


# ---------------------------------------------------------------------------
# search_workspace.py canonical roots
# ---------------------------------------------------------------------------

class SearchWorkspaceCanonicalRootsTests(unittest.TestCase):
    def test_project_knowledge_root_registered(self):
        self.assertIn("30_Project_Knowledge", search_workspace.CANONICAL_ROOTS)

    def test_canonical_md_under_project_knowledge_allowed(self):
        path = "30_Project_Knowledge/<Project1>/knowledge_base/<Project1>_knowledge_base.md"
        self.assertTrue(search_workspace.is_allowed_structurally(path, "canonical"))
        self.assertTrue(search_workspace.is_allowed_structurally(path, "all"))

    def test_canonical_csv_under_project_knowledge_allowed(self):
        path = "30_Project_Knowledge/<Project1>/source_index.csv"
        self.assertTrue(search_workspace.is_allowed_structurally(path, "canonical"))

    def test_path_filter_matches_project_knowledge_root(self):
        self.assertTrue(search_workspace.is_valid_filter_path("30_Project_Knowledge", "canonical"))
        self.assertTrue(search_workspace.is_valid_filter_path(
            "30_Project_Knowledge/<Project1>", "canonical"))

    def test_outside_any_canonical_root_rejected(self):
        path = "40_Something_Else/<Project1>/notes.md"
        self.assertFalse(search_workspace.is_allowed_structurally(path, "canonical"))


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

class TemplateHeadingTests(unittest.TestCase):
    TEMPLATES_DIR = REPO_ROOT / "Templates"

    def _read(self, name: str) -> str:
        return (self.TEMPLATES_DIR / name).read_text(encoding="utf-8")

    def test_pk_knowledge_base_headings(self):
        text = self._read("pk_knowledge_base.md")
        for heading in ("Overview", "Business Goals", "Stakeholders/Roles",
                        "System/Architecture", "Core Workflows", "Data/Integrations",
                        "QA Scope", "Performance-Critical Scenarios", "Known Constraints",
                        "Glossary", "Open Questions", "Source Index", "Change Log"):
            self.assertIn(heading, text, f"missing heading: {heading}")

    def test_pk_summary_headings(self):
        text = self._read("pk_summary.md")
        for heading in ("Source", "Date", "Source Type", "Context", "Key Topics",
                        "Extracted Facts", "Decisions/Constraints", "Open Questions",
                        "Knowledge Base Sections Updated"):
            self.assertIn(heading, text, f"missing heading: {heading}")

    def test_pk_source_index_csv_header(self):
        text = self._read("pk_source_index.csv")
        header = text.strip().splitlines()[0]
        for col in ("Date", "Source", "Source type", "Summary doc link",
                    "Knowledge base sections touched", "Open questions count", "Status", "Notes"):
            self.assertIn(col, header)

    def test_performance_test_plan_exists_and_has_headings(self):
        text = self._read("performance_test_plan.md")
        for heading in ("Scope", "Test Types", "Environment/Tooling", "Success Criteria",
                        "Risks", "Schedule", "Open Questions"):
            self.assertIn(heading, text)

    def test_test_plan_exists_and_has_headings(self):
        text = self._read("test_plan.md")
        for heading in ("Scope", "Test Levels", "Entry/Exit Criteria", "Risks", "Open Questions"):
            self.assertIn(heading, text)

    def test_test_strategy_exists_and_has_headings(self):
        text = self._read("test_strategy.md")
        for heading in ("Overall Approach", "Tooling", "Automation Approach",
                        "Reporting/Metrics", "Risks", "Open Questions"):
            self.assertIn(heading, text)

    def test_templates_have_no_real_names(self):
        # These templates must stay abstract - only placeholder-style
        # <Project> tokens, no concrete example content.
        for name in ("pk_knowledge_base.md", "pk_summary.md", "performance_test_plan.md",
                     "test_plan.md", "test_strategy.md"):
            text = self._read(name)
            self.assertNotIn("CyberProAi", text)
            self.assertNotIn("McKinsey", text)
            self.assertNotIn("Hamkorbank", text)


# ---------------------------------------------------------------------------
# No real names/projects in this test module's own fixtures
# ---------------------------------------------------------------------------

class NoRealNamesInFixturesTests(unittest.TestCase):
    def test_fixture_placeholders_are_angle_bracketed(self):
        for name in ("<Project1>", "<Person1>", "<source-slug>"):
            self.assertTrue(name.startswith("<") and name.endswith(">"))


if __name__ == "__main__":
    unittest.main()
