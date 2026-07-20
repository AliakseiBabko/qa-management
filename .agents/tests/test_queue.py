"""Unit tests for qa_manage.py's pure state-machine logic: transition
validation, run-id minting, route resolution, scope requirements, and
per-run scope enumeration. No Google APIs.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from qa_manage import (STATES, TRANSITIONS, enumerate_run_scopes, mint_run_id,
                       needed_scopes, resolve_route, validate_transition)

GRAPH = {
    "documents": {
        "proj_doc": {"scope": "project"},
        "pers_doc": {"scope": "person"},
        "ws_doc": {"scope": "workspace"},
    },
    "sources": {
        "flat_type": {"skills": ["s1"], "entry": ["ws_doc"]},
        "routed_type": {"routes": {
            "m1": {"skills": ["s1"], "entry": ["pers_doc"]},
            "m2": {"skills": ["s2"], "entry": ["proj_doc", "pers_doc"]},
        }},
    },
}


class TestTransitions(unittest.TestCase):
    def test_happy_path(self):
        for a, b in [("discovered", "processing"), ("discovered", "needs_scope"),
                     ("needs_scope", "processing"), ("processing", "blocked"),
                     ("blocked", "processing"), ("processing", "completed"),
                     ("processing", "failed")]:
            validate_transition(a, b)  # must not raise

    def test_completed_is_terminal(self):
        for target in STATES:
            with self.assertRaises(SystemExit):
                validate_transition("completed", target)

    def test_cannot_skip_to_completed(self):
        with self.assertRaises(SystemExit):
            validate_transition("discovered", "completed")

    def test_unknown_state_rejected(self):
        with self.assertRaises(SystemExit):
            validate_transition("processing", "done")

    def test_every_transition_target_is_a_state(self):
        for source, targets in TRANSITIONS.items():
            self.assertIn(source, STATES)
            self.assertTrue(targets <= STATES)


class TestMintRunId(unittest.TestCase):
    def test_deterministic_and_slugged(self):
        rid = mint_run_id(r"02_Transcripts_Inbox\Aslan 1to1 2026-07-17.txt",
                          "abcdef0123456789", date="20260719")
        self.assertEqual(rid, "20260719-aslan-1to1-2026-07-17-abcdef")

    def test_hash_suffix_disambiguates_same_name(self):
        a = mint_run_id("x/meeting.txt", "aaaa111122223333", date="20260719")
        b = mint_run_id("y/meeting.txt", "bbbb111122223333", date="20260719")
        self.assertNotEqual(a, b)


class TestResolveRoute(unittest.TestCase):
    def test_flat_type_resolves_without_variant(self):
        self.assertEqual(resolve_route(GRAPH, "flat_type", "")["skills"], ["s1"])

    def test_flat_type_rejects_variant(self):
        with self.assertRaises(SystemExit):
            resolve_route(GRAPH, "flat_type", "m1")

    def test_routed_type_requires_variant(self):
        with self.assertRaises(SystemExit):
            resolve_route(GRAPH, "routed_type", "")

    def test_routed_type_resolves_variant(self):
        self.assertEqual(resolve_route(GRAPH, "routed_type", "m2")["entry"],
                         ["proj_doc", "pers_doc"])

    def test_unknown_variant_rejected(self):
        with self.assertRaises(SystemExit):
            resolve_route(GRAPH, "routed_type", "m3")

    def test_unrouted_type_rejected(self):
        with self.assertRaises(SystemExit):
            resolve_route(GRAPH, "raw_transcript", "")


class TestNeededScopes(unittest.TestCase):
    def test_project_and_person_detected(self):
        self.assertEqual(needed_scopes(GRAPH, ["proj_doc", "pers_doc"]),
                         {"project", "person"})

    def test_workspace_needs_nothing(self):
        self.assertEqual(needed_scopes(GRAPH, ["ws_doc"]), set())


class TestEnumerateRunScopes(unittest.TestCase):
    def test_declared_multi_values_cross_product(self):
        row = {"Project": "P1, P2", "Person": "Alice", "Route variant": "m2"}
        scopes = enumerate_run_scopes([], row)
        self.assertIn(("P1", "Alice", "m2"), scopes)
        self.assertIn(("P2", "Alice", "m2"), scopes)

    def test_outcome_scopes_are_added(self):
        row = {"Project": "P1", "Person": "", "Route variant": ""}
        outcome = {"Project": "P2", "Person": "Bob", "Route variant": "m1"}
        scopes = enumerate_run_scopes([outcome], row)
        self.assertIn(("P1", "", ""), scopes)
        self.assertIn(("P2", "Bob", "m1"), scopes)

    def test_empty_row_yields_workspace_scope(self):
        self.assertEqual(enumerate_run_scopes([], {"Project": "", "Person": "",
                                                   "Route variant": ""}),
                         [("", "", "")])


if __name__ == "__main__":
    unittest.main()
