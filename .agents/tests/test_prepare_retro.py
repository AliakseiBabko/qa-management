"""Unit tests for prepare_retro.py's pure cascade-closure-miss check.

Covers: same-row closure, cross-row closure (a later pass on the same
project closes what an earlier one left open), project-scope isolation,
judgment/gated edges never flagged, periodic/unknown-name handling, and
rows with no project column.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from prepare_retro import find_direct_script_misses

GRAPH = {
    "documents": {
        "individual_metrics": {
            "downstream": [{"to": "project_metrics", "kind": "direct"}]
        },
        "project_metrics": {
            "downstream": [{"to": "_project_registry", "kind": "direct"}]
        },
        "action_items": {
            "downstream": [{"to": "timeline_views", "kind": "script"}]
        },
        "pk_knowledge_base": {
            "downstream": [{"to": "pk_performance_test_plan", "kind": "judgment"}]
        },
        "_project_registry": {"downstream": []},
        "timeline_views": {"downstream": []},
        "pk_performance_test_plan": {"downstream": []},
    },
    "periodic": ["timeline_views"],
    "aliases": {},
}


def row(project, docs, source_type="qa_1to1"):
    """Build a padded-style _skill_invocations row: date, source, type,
    project, person, skills, docs, notes."""
    return ["2026-08-08", "src", source_type, project, "", "skill", docs, ""]


class FindDirectScriptMissesTests(unittest.TestCase):
    def test_same_row_closure_not_flagged(self):
        rows = [row("Proj", "individual_metrics, project_metrics")]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertEqual([m for m in misses if m[1] == "individual_metrics"], [])

    def test_unclosed_direct_edge_flagged(self):
        rows = [row("Proj", "individual_metrics")]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertIn(("Proj", "individual_metrics", "project_metrics", "direct"), misses)

    def test_cross_row_closure_in_same_project(self):
        rows = [
            row("Proj", "individual_metrics"),
            row("Proj", "project_metrics, _project_registry"),
        ]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertEqual(misses, [])

    def test_two_hop_chain_flags_the_still_open_hop(self):
        rows = [row("Proj", "individual_metrics, project_metrics")]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertEqual(
            misses,
            [("Proj", "project_metrics", "_project_registry", "direct")],
        )

    def test_project_scope_isolation(self):
        rows = [
            row("ProjA", "individual_metrics"),
            row("ProjB", "project_metrics"),
        ]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertIn(("ProjA", "individual_metrics", "project_metrics", "direct"), misses)
        # ProjB touching project_metrics does not close ProjA's edge.
        self.assertNotIn(("ProjB", "individual_metrics", "project_metrics", "direct"), misses)

    def test_judgment_edge_never_flagged(self):
        rows = [row("Proj", "pk_knowledge_base")]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertEqual(misses, [])

    def test_periodic_target_never_flagged(self):
        rows = [row("Proj", "action_items")]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertEqual(misses, [])

    def test_row_with_no_project_ignored(self):
        rows = [row("", "individual_metrics")]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertEqual(misses, [])

    def test_unknown_document_name_ignored_not_crashed(self):
        rows = [row("Proj", "individual_metrics, some_made_up_doc")]
        misses = find_direct_script_misses(rows, GRAPH)
        self.assertIn(("Proj", "individual_metrics", "project_metrics", "direct"), misses)

    def test_empty_window_returns_empty(self):
        self.assertEqual(find_direct_script_misses([], GRAPH), [])


if __name__ == "__main__":
    unittest.main()
