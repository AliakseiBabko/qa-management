"""Unit tests for the pure logic of cascade closure checking.

Covers the false-closure paths found in cross-model review: diamond
traversal (required must dominate conditional), duplicate-row precedence,
stale stored kinds/outcomes, scope isolation, and strict-mode semantics.
Pure logic only - no Google APIs.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_cascade_closure import build_resolved, walk
from closure_outcomes import REASON_REQUIRED, VALID_OUTCOMES, row_matches_scope


def run_walk(graph, touched, resolved=None, strict=False):
    open_items: list[str] = []
    lines: list[str] = []
    visited_req = set(touched)
    visited_cond: set[str] = set()
    for node in sorted(touched):
        walk(graph, node, touched, visited_req, visited_cond, 0, False, strict,
             resolved or {}, open_items, lines)
    return open_items


def rec(source, target, outcome, run="r1", project="", person="", variant=""):
    return {"Run ID": run, "Project": project, "Person": person,
            "Route variant": variant, "Source node": source,
            "Target node": target, "Outcome": outcome, "Edge kind": "?"}


DIAMOND = {"documents": {
    "A": {"downstream": [{"to": "X", "kind": "judgment"}]},
    "B": {"downstream": [{"to": "X", "kind": "judgment"}]},
    "X": {"downstream": [{"to": "Y", "kind": "direct"}]},
    "Y": {"downstream": []},
}}


class TestDiamondTraversal(unittest.TestCase):
    def test_required_dominates_conditional(self):
        # A->X no_change (conditional branch walked first), B->X updated:
        # X changed, so X->Y is required and must surface as open.
        resolved = {("A", "X"): "no_change", ("B", "X"): "updated"}
        open_items = run_walk(DIAMOND, {"A", "B"}, resolved, strict=True)
        self.assertIn("X -> Y [direct]", open_items)

    def test_no_change_everywhere_leaves_descendants_conditional(self):
        resolved = {("A", "X"): "no_change", ("B", "X"): "no_change"}
        open_items = run_walk(DIAMOND, {"A", "B"}, resolved, strict=True)
        self.assertEqual(open_items, [])

    def test_open_items_not_duplicated(self):
        open_items = run_walk(DIAMOND, {"A", "B"}, {}, strict=True)
        self.assertEqual(open_items.count("A -> X [judgment]"), 1)
        self.assertEqual(open_items.count("B -> X [judgment]"), 1)


class TestStrictMode(unittest.TestCase):
    GRAPH = {"documents": {
        "A": {"downstream": [{"to": "T", "kind": "direct"}]},
        "T": {"downstream": []},
    }}

    def test_touched_target_closes_edge_in_legacy_mode(self):
        self.assertEqual(run_walk(self.GRAPH, {"A", "T"}, {}, strict=False), [])

    def test_touched_target_does_not_close_edge_in_strict_mode(self):
        self.assertEqual(run_walk(self.GRAPH, {"A", "T"}, {}, strict=True),
                         ["A -> T [direct]"])

    def test_recorded_outcome_closes_edge_in_strict_mode(self):
        self.assertEqual(
            run_walk(self.GRAPH, {"A", "T"}, {("A", "T"): "updated"}, strict=True), [])


class TestBuildResolved(unittest.TestCase):
    GRAPH = {"documents": {
        "A": {"downstream": [{"to": "T", "kind": "gated"}]},
        "T": {"downstream": []},
    }}

    def test_latest_row_wins_for_same_identity(self):
        rows = [rec("A", "T", "gated", project="P1"),
                rec("A", "T", "updated", project="P1")]
        resolved, warns = build_resolved(rows, self.GRAPH)
        self.assertEqual(resolved[("A", "T")], "updated")
        self.assertEqual(warns, [])

    def test_different_scope_is_a_different_identity(self):
        rows = [rec("A", "T", "gated", project="P1"),
                rec("A", "T", "updated", project="P2")]
        # Scope filtering happens in fetch; if both scopes slip through, the
        # later one wins deterministically rather than merging silently.
        resolved, _ = build_resolved(rows, self.GRAPH)
        self.assertEqual(resolved[("A", "T")], "updated")

    def test_stale_edge_is_warned_and_ignored(self):
        resolved, warns = build_resolved([rec("A", "GONE", "updated")], self.GRAPH)
        self.assertEqual(resolved, {})
        self.assertTrue(any("no longer exists" in w for w in warns))

    def test_outcome_invalid_for_current_kind_is_warned_and_ignored(self):
        resolved, warns = build_resolved([rec("A", "T", "no_change")], self.GRAPH)
        self.assertEqual(resolved, {})
        self.assertTrue(any("not valid for current edge kind" in w for w in warns))


class TestScopeIsolation(unittest.TestCase):
    def test_other_project_never_matches(self):
        self.assertFalse(row_matches_scope(rec("A", "T", "updated", project="P1"),
                                           "P2", "", ""))

    def test_other_person_never_matches(self):
        self.assertFalse(row_matches_scope(rec("A", "T", "updated", person="Alice"),
                                           "", "Bob", ""))

    def test_other_variant_never_matches(self):
        self.assertFalse(row_matches_scope(rec("A", "T", "updated", variant="m1"),
                                           "", "", "m2"))

    def test_empty_row_scope_matches_any_filter(self):
        self.assertTrue(row_matches_scope(rec("A", "T", "updated"), "P1", "Bob", "m2"))

    def test_matching_scope_case_insensitive(self):
        self.assertTrue(row_matches_scope(rec("A", "T", "updated", project="p1"),
                                          "P1", "", ""))


class TestOutcomeContract(unittest.TestCase):
    def test_kind_outcome_matrix(self):
        self.assertEqual(VALID_OUTCOMES["direct"], {"updated"})
        self.assertEqual(VALID_OUTCOMES["judgment"], {"updated", "no_change"})
        self.assertEqual(VALID_OUTCOMES["gated"], {"gated", "updated"})
        self.assertEqual(VALID_OUTCOMES["script"], {"regenerated"})
        self.assertEqual(REASON_REQUIRED, {"no_change", "gated"})


if __name__ == "__main__":
    unittest.main()
