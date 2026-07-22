"""Unit tests for pipeline_common.py's non-canonical `documents_touched`
warning, added after a real miss: a pass logged a Google Doc's literal
title and a summary's filename instead of the canonical document_graph.yaml
node ids (`pk_knowledge_base`, `pk_summary`), which silently broke
check_cascade_closure.py --from-log's matching until caught and fixed by
hand. This is advisory only (a warning, never a hard failure) - historical/
manual `_skill_invocations` rows sometimes hold free text in this field.

Only placeholder document/run identifiers appear here - no real names,
projects, or transcript content.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pipeline_common as pc  # noqa: E402
import sync_m2_source_docs_to_sheets as sync_docs  # noqa: E402


class WarnUnknownDocumentsTouchedTests(unittest.TestCase):
    """Pure-function tests - no Drive access, real document_graph.yaml read
    from disk (a public-repo structural file, not a business document)."""

    def test_no_warning_for_canonical_node_ids(self):
        warnings = pc.warn_unknown_documents_touched(
            "pk_knowledge_base,pk_summary,pk_source_index"
        )
        self.assertEqual(warnings, [])

    def test_warns_for_unknown_placeholder_token(self):
        warnings = pc.warn_unknown_documents_touched("totally_made_up_document_xyz")
        self.assertEqual(len(warnings), 1)
        self.assertIn("totally_made_up_document_xyz", warnings[0])
        self.assertIn("document_graph.yaml", warnings[0])

    def test_mix_of_known_and_unknown_tokens_warns_only_for_unknown(self):
        warnings = pc.warn_unknown_documents_touched(
            "pk_knowledge_base,not_a_real_node,pk_summary"
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("not_a_real_node", warnings[0])

    def test_resolves_known_alias(self):
        # "_timeline" is an alias for the canonical `timeline_views` node -
        # see document_graph.yaml's `aliases:` section.
        warnings = pc.warn_unknown_documents_touched("_timeline")
        self.assertEqual(warnings, [])

    def test_case_insensitive_match(self):
        warnings = pc.warn_unknown_documents_touched("PK_Knowledge_Base")
        self.assertEqual(warnings, [])

    def test_ignores_empty_and_blank_tokens(self):
        warnings = pc.warn_unknown_documents_touched(",, ,pk_summary, ,")
        self.assertEqual(warnings, [])

    def test_ignores_prose_note_tokens(self):
        # A token containing whitespace reads as a free-text note, not a
        # document id - historical rows sometimes hold this shape.
        warnings = pc.warn_unknown_documents_touched(
            "pk_summary,no change this pass see notes"
        )
        self.assertEqual(warnings, [])

    def test_empty_string_returns_no_warnings(self):
        self.assertEqual(pc.warn_unknown_documents_touched(""), [])

    def test_graph_load_failure_returns_no_warnings_not_an_error(self):
        with mock.patch.object(pc, "_canonical_document_tokens", return_value=None):
            warnings = pc.warn_unknown_documents_touched("anything_at_all")
        self.assertEqual(warnings, [])


class LogSkillInvocationWiringTests(unittest.TestCase):
    """Confirms the warning actually fires from log_skill_invocation()
    itself, not just from the helper in isolation - with every Drive call
    it makes mocked out."""

    def _mock_services(self):
        sheets_api = mock.MagicMock()
        sheets_api.spreadsheets.return_value.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "Sheet1"}}]
        }
        return {"drive": mock.MagicMock(), "sheets": sheets_api}

    def _call(self, documents_touched: str) -> str:
        services = self._mock_services()
        with mock.patch.object(pc, "get_skill_invocations_sheet", return_value={"id": "fake-sheet-id"}), \
             mock.patch.object(sync_docs, "read_sheet_values", return_value=[pc.SKILL_INVOCATIONS_HEADER]), \
             mock.patch.object(pc, "reformat_sheet"):
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                pc.log_skill_invocation(
                    services,
                    date="2026-01-01",
                    source="run:fake-run-id",
                    source_type="project_knowledge_notes",
                    skills="fake-skill",
                    documents_touched=documents_touched,
                )
        return buf.getvalue()

    def test_warns_for_unknown_token(self):
        stderr = self._call("totally_made_up_document_xyz")
        self.assertIn("totally_made_up_document_xyz", stderr)

    def test_no_warning_for_canonical_tokens(self):
        stderr = self._call("pk_knowledge_base,pk_summary,pk_source_index")
        self.assertNotIn("does not match", stderr)


if __name__ == "__main__":
    unittest.main()
