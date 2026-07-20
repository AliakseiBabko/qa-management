"""Unit tests for qa_manage.py's pure state-machine logic: transitions,
run-id minting, discovery identity, route resolution, scope tuples,
per-scope entry outcomes, and snapshot verification. No Google APIs.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from qa_manage import (STATES, TRANSITIONS, check_snapshot, discovery_action,
                       entries_for_scope, enumerate_run_scopes, mint_run_id,
                       needed_scopes, parse_outcome_args, resolve_route,
                       seeds_for_scope, validate_entry_outcomes,
                       validate_transition)

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
                     ("processing", "failed"), ("discovered", "historical"),
                     ("failed", "historical")]:
            validate_transition(a, b)  # must not raise

    def test_completed_and_historical_are_terminal(self):
        for source in ("completed", "historical"):
            for target in STATES:
                with self.assertRaises(SystemExit):
                    validate_transition(source, target)

    def test_failed_only_corrects_to_historical(self):
        validate_transition("failed", "historical")
        for target in STATES - {"historical"}:
            with self.assertRaises(SystemExit):
                validate_transition("failed", target)

    def test_cannot_skip_to_completed(self):
        with self.assertRaises(SystemExit):
            validate_transition("discovered", "completed")

    def test_every_transition_target_is_a_state(self):
        for source, targets in TRANSITIONS.items():
            self.assertIn(source, STATES)
            self.assertTrue(targets <= STATES)


class TestDiscoveryIdentity(unittest.TestCase):
    PAIRS = {("a.txt", "h1")}
    BY_PATH = {"a.txt": "run-a"}
    BY_HASH = {"h1": "run-a"}

    def act(self, rel, digest):
        return discovery_action(rel, digest, self.PAIRS, self.BY_PATH, self.BY_HASH)

    def test_exact_pair_is_skipped(self):
        self.assertEqual(self.act("a.txt", "h1"), ("skip", ""))

    def test_changed_content_at_known_path_is_rediscovered(self):
        action, related = self.act("a.txt", "h2")
        self.assertEqual(action, "changed")
        self.assertEqual(related, "run-a")

    def test_same_content_at_new_path_is_a_duplicate(self):
        action, related = self.act("b.txt", "h1")
        self.assertEqual(action, "duplicate")
        self.assertEqual(related, "run-a")

    def test_unknown_pair_is_new(self):
        self.assertEqual(self.act("b.txt", "h2"), ("new", ""))


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
    def test_explicit_tuples_no_cartesian_product(self):
        # Correlated pairs stay pairs: P1/Alice and P2/Bob must NOT produce
        # P1/Bob or P2/Alice.
        scopes = enumerate_run_scopes([], [("P1", "Alice"), ("P2", "Bob")], {}, "m2")
        self.assertIn(("P1", "Alice", "m2"), scopes)
        self.assertIn(("P2", "Bob", "m2"), scopes)
        self.assertNotIn(("P1", "Bob", "m2"), scopes)
        self.assertNotIn(("P2", "Alice", "m2"), scopes)

    def test_outcome_and_entry_scopes_are_added(self):
        outcome = {"Project": "P2", "Person": "Bob", "Route variant": "m1"}
        entries = {"P3|Carol": {"doc": ["updated", ""]}}
        scopes = enumerate_run_scopes([outcome], [("P1", "")], entries, "")
        self.assertIn(("P1", "", ""), scopes)
        self.assertIn(("P2", "Bob", "m1"), scopes)
        self.assertIn(("P3", "Carol", ""), scopes)

    def test_no_declared_scope_yields_nothing_invented(self):
        self.assertEqual(enumerate_run_scopes([], [], {}, ""), [])


class TestEntriesForScope(unittest.TestCase):
    ENTRIES = {
        "P1|Alice": {"pers_doc": ["updated", ""]},
        "P2|Bob": {"pers_doc": ["no_change", "quiet week"]},
        "|": {"ws_doc": ["updated", ""]},
    }

    def test_scope_isolation_between_entries(self):
        scoped = entries_for_scope(self.ENTRIES, "P1", "Alice")
        self.assertEqual(scoped["pers_doc"], ["updated", ""])
        scoped2 = entries_for_scope(self.ENTRIES, "P2", "Bob")
        self.assertEqual(scoped2["pers_doc"], ["no_change", "quiet week"])

    def test_workspace_entry_applies_to_every_scope(self):
        self.assertIn("ws_doc", entries_for_scope(self.ENTRIES, "P1", "Alice"))
        self.assertIn("ws_doc", entries_for_scope(self.ENTRIES, "P2", "Bob"))

    def test_scoped_entry_never_leaks_to_omitted_scope(self):
        scoped = entries_for_scope(self.ENTRIES, "", "")
        self.assertNotIn("pers_doc", scoped)
        self.assertIn("ws_doc", scoped)

    def test_seeds_are_only_updated_entries(self):
        self.assertEqual(seeds_for_scope(entries_for_scope(self.ENTRIES, "P2", "Bob")),
                         {"ws_doc"})


class TestEntryOutcomeValidation(unittest.TestCase):
    def test_all_present_and_valid(self):
        scoped = {"a": ["updated", ""], "b": ["no_change", "why"],
                  "c": ["not_applicable", "wrong shape"]}
        self.assertEqual(validate_entry_outcomes(["a", "b", "c"], scoped), [])

    def test_missing_entry_flagged(self):
        problems = validate_entry_outcomes(["a", "b"], {"a": ["updated", ""]})
        self.assertTrue(any("'b'" in p for p in problems))

    def test_reason_required_for_no_change(self):
        problems = validate_entry_outcomes(["a"], {"a": ["no_change", ""]})
        self.assertTrue(any("requires a reason" in p for p in problems))

    def test_parse_outcome_args_roundtrip(self):
        out = parse_outcome_args("a, b", "c=busy week", "d=not this shape")
        self.assertEqual(out["a"], ["updated", ""])
        self.assertEqual(out["c"], ["no_change", "busy week"])
        self.assertEqual(out["d"], ["not_applicable", "not this shape"])

    def test_parse_outcome_args_requires_reason_syntax(self):
        with self.assertRaises(SystemExit):
            parse_outcome_args("", "c", "")


class TestSnapshotCheck(unittest.TestCase):
    LOG = [("sha_new", 2000.0, "pass one [run-1]"),
           ("sha_old", 1000.0, "other work")]

    def test_clean_recent_snapshot_accepted(self):
        sha, problem = check_snapshot(self.LOG, "run-1", 1500.0, dirty=False)
        self.assertEqual(sha, "sha_new")
        self.assertEqual(problem, "")

    def test_dirty_mirror_rejected(self):
        sha, problem = check_snapshot(self.LOG, "run-1", 1500.0, dirty=True)
        self.assertEqual(sha, "")
        self.assertIn("dirty", problem)

    def test_missing_run_commit_rejected(self):
        sha, problem = check_snapshot(self.LOG, "run-2", 1500.0, dirty=False)
        self.assertEqual(sha, "")
        self.assertIn("no mirror commit", problem)

    def test_stale_snapshot_rejected(self):
        # Snapshot at t=2000, but the run's last mutation is much later.
        sha, problem = check_snapshot(self.LOG, "run-1", 5000.0, dirty=False)
        self.assertEqual(sha, "")
        self.assertIn("predates", problem)

    def test_same_minute_tolerated(self):
        sha, problem = check_snapshot(self.LOG, "run-1", 2059.0, dirty=False)
        self.assertEqual(sha, "sha_new")
        self.assertEqual(problem, "")


if __name__ == "__main__":
    unittest.main()
