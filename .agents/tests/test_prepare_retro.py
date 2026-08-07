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

from prepare_retro import check_telemetry_staleness, find_direct_script_misses

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


class CheckTelemetryStalenessTests(unittest.TestCase):
    def test_no_prior_retro_marker_skips_the_check(self):
        # since_date=None - no meaningful window to compare against yet.
        warnings = check_telemetry_staleness(
            queue_completed_dates=["2026-08-01 10:00"],
            operator_runs_dates=[],
            agent_session_dates=[],
            since_date=None,
        )
        self.assertEqual(warnings, [])

    def test_no_completions_in_window_is_silent(self):
        # Real incident this guards: nothing to flag if the queue itself
        # was genuinely idle in the window - only flag when real
        # completed work exists with no matching telemetry.
        warnings = check_telemetry_staleness(
            queue_completed_dates=["2026-07-01 10:00"],  # before the window
            operator_runs_dates=[],
            agent_session_dates=[],
            since_date="2026-08-01",
        )
        self.assertEqual(warnings, [])

    def test_real_incident_shape_flags_both_csvs(self):
        # The actual incident: 24 queue runs completed with zero rows in
        # either telemetry CSV for that whole window.
        warnings = check_telemetry_staleness(
            queue_completed_dates=["2026-07-24 22:56", "2026-08-06 23:19"],
            operator_runs_dates=["2026-07-20", "2026-07-23"],  # all before window
            agent_session_dates=["2026-07-22"],  # before window
            since_date="2026-07-24",
        )
        self.assertEqual(len(warnings), 2)
        self.assertTrue(any("operator-runs.csv" in w for w in warnings))
        self.assertTrue(any("agent-sessions.csv" in w for w in warnings))

    def test_matching_operator_runs_activity_clears_that_warning_only(self):
        warnings = check_telemetry_staleness(
            queue_completed_dates=["2026-08-02 10:00"],
            operator_runs_dates=["2026-08-02"],  # in window - covers this CSV
            agent_session_dates=[],  # still nothing - stays flagged
            since_date="2026-08-01",
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("agent-sessions.csv", warnings[0])

    def test_date_only_prefix_comparison_ignores_time_component(self):
        # Queue timestamps carry "%H:%M"; CSV dates don't - comparison
        # must key off the leading YYYY-MM-DD only, not fail on format.
        warnings = check_telemetry_staleness(
            queue_completed_dates=["2026-08-01 23:59"],
            operator_runs_dates=["2026-08-01"],
            agent_session_dates=["2026-08-01"],
            since_date="2026-08-01",
        )
        self.assertEqual(warnings, [])

    def test_blank_completed_dates_are_ignored(self):
        warnings = check_telemetry_staleness(
            queue_completed_dates=["", "  ", "2026-07-01 10:00"],
            operator_runs_dates=[],
            agent_session_dates=[],
            since_date="2026-08-01",
        )
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
