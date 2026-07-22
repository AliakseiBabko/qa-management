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

from qa_manage import (STATES, TRANSITIONS, check_snapshot, dedup_scopes,
                       discovery_action, entries_for_scope,
                       enumerate_run_scopes, is_excluded, is_queue_only_dirt,
                       mint_run_id, missing_scope_fields, needed_scopes,
                       parse_outcome_args, resolve_route, resolve_scope_args,
                       queue_discovery_indexes,
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
        "ws_person_type": {"skills": [], "entry": ["ws_doc"],
                           "scope_required": ["person"]},
    },
}


class TestTransitions(unittest.TestCase):
    def test_happy_path(self):
        for a, b in [("discovered", "processing"), ("discovered", "needs_scope"),
                     ("needs_scope", "processing"), ("processing", "blocked"),
                     ("blocked", "processing"),
                     ("processing", "failed"), ("discovered", "historical"),
                     ("failed", "historical"), ("processing", "finalizing"),
                     ("finalizing", "completed"), ("finalizing", "failed")]:
            validate_transition(a, b)  # must not raise

    def test_completed_historical_ignored_are_terminal(self):
        for source in ("completed", "historical", "ignored"):
            for target in STATES:
                with self.assertRaises(SystemExit):
                    validate_transition(source, target)

    def test_ignored_only_from_pre_processing_states(self):
        for source in ("discovered", "needs_scope", "ready"):
            validate_transition(source, "ignored")
        for source in ("processing", "blocked", "finalizing", "failed"):
            with self.assertRaises(SystemExit):
                validate_transition(source, "ignored")

    def test_failed_only_corrects_to_historical(self):
        validate_transition("failed", "historical")
        for target in STATES - {"historical"}:
            with self.assertRaises(SystemExit):
                validate_transition("failed", target)

    def test_cannot_skip_to_completed(self):
        for source in ("discovered", "ready", "processing"):
            with self.assertRaises(SystemExit):
                validate_transition(source, "completed")

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

    def test_current_source_path_is_an_exact_known_pair(self):
        rows = [{
            "Run ID": "run-a",
            "Source": "00_Source_Docs/old.txt",
            "Current source": "00_Inbox/old.txt",
            "Source hash": "h1",
        }]
        by_pair, by_path, by_hash = queue_discovery_indexes(rows)
        self.assertEqual(
            discovery_action("00_Inbox/old.txt", "h1", by_pair, by_path, by_hash),
            ("skip", ""),
        )


class TestScanExclusion(unittest.TestCase):
    def test_storage_and_archive_roots_are_excluded(self):
        self.assertTrue(is_excluded(
            r"90_Storage\Reference\Source_Documents\placeholder\Task 1.docx"))
        self.assertTrue(is_excluded(
            "90_Storage/Processed_Sources/2026/07/run-id/source.txt"))
        self.assertTrue(is_excluded("90_Archive/legacy/source.txt"))
        self.assertTrue(is_excluded("80_Exports/package/source.txt"))

    def test_sibling_paths_not_excluded(self):
        self.assertFalse(is_excluded(
            r"00_Inbox\metrics.xlsx"))
        self.assertFalse(is_excluded(
            r"00_Inbox\M2_role_vision_notes.docx"))
        self.assertFalse(is_excluded(
            r"90_Storage_old\source.txt"))


class TestMintRunId(unittest.TestCase):
    def test_deterministic_and_slugged(self):
        rid = mint_run_id(r"00_Inbox\Person 1to1 2026-07-17.txt",
                          "abcdef0123456789", date="20260719")
        self.assertTrue(rid.startswith("20260719-person-1to1-2026-07-17-abcdef"))
        self.assertEqual(rid, mint_run_id(r"00_Inbox\Person 1to1 2026-07-17.txt",
                                          "abcdef0123456789", date="20260719"))

    def test_hash_suffix_disambiguates_same_name(self):
        a = mint_run_id("x/meeting.txt", "aaaa111122223333", date="20260719")
        b = mint_run_id("y/meeting.txt", "bbbb111122223333", date="20260719")
        self.assertNotEqual(a, b)

    def test_identical_content_same_filename_different_dirs_is_unique(self):
        a = mint_run_id("x/meeting.txt", "aaaa111122223333", date="20260719")
        b = mint_run_id("y/meeting.txt", "aaaa111122223333", date="20260719")
        self.assertNotEqual(a, b)

    def test_path_normalization_keeps_id_stable(self):
        self.assertEqual(mint_run_id(r"x\meeting.txt", "aaaa111122223333", date="20260719"),
                         mint_run_id("x/meeting.txt", "aaaa111122223333", date="20260719"))


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
        self.assertEqual(needed_scopes(GRAPH, {"entry": ["proj_doc", "pers_doc"]}),
                         {"project", "person"})

    def test_workspace_needs_nothing(self):
        self.assertEqual(needed_scopes(GRAPH, {"entry": ["ws_doc"]}), set())

    def test_scope_required_overrides_workspace_entries(self):
        self.assertEqual(needed_scopes(GRAPH, GRAPH["sources"]["ws_person_type"]),
                         {"person"})


class TestMissingScopeFields(unittest.TestCase):
    def test_partial_tuple_fails_route_requirements(self):
        # The add-scope bypass: a project-only tuple on a route that
        # requires both must be rejected the same way start rejects it.
        self.assertEqual(missing_scope_fields({"project", "person"}, "P1", ""),
                         ["person"])
        self.assertEqual(missing_scope_fields({"project", "person"}, "", "Alice"),
                         ["project"])

    def test_complete_tuple_passes(self):
        self.assertEqual(missing_scope_fields({"project", "person"}, "P1", "Alice"), [])

    def test_no_requirements_pass_anything(self):
        self.assertEqual(missing_scope_fields(set(), "", ""), [])


class TestDedupScopes(unittest.TestCase):
    def test_differently_cased_copies_collapse_first_spelling_wins(self):
        self.assertEqual(dedup_scopes([("P1", "Alice"), ("p1", "ALICE"), ("P2", "Bob")]),
                         [("P1", "Alice"), ("P2", "Bob")])

    def test_distinct_tuples_kept_in_order(self):
        self.assertEqual(dedup_scopes([("P2", "Bob"), ("P1", "Alice")]),
                         [("P2", "Bob"), ("P1", "Alice")])


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

    def test_no_scope_anywhere_defaults_to_workspace_scope(self):
        # Never empty: complete must always have at least one scope to check.
        self.assertEqual(enumerate_run_scopes([], [], {}, ""), [("", "", "")])
        self.assertEqual(enumerate_run_scopes([], [], {}, "v"), [("", "", "v")])


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

    def test_specific_outcome_beats_wildcard_regardless_of_order(self):
        specific_first = {"P1|Alice": {"doc": ["updated", ""]},
                          "|": {"doc": ["no_change", "wildcard"]}}
        wildcard_first = {"|": {"doc": ["no_change", "wildcard"]},
                          "P1|Alice": {"doc": ["updated", ""]}}
        for entries in (specific_first, wildcard_first):
            scoped = entries_for_scope(entries, "P1", "Alice")
            self.assertEqual(scoped["doc"], ["updated", ""])


class TestResolveScopeArgs(unittest.TestCase):
    def row(self, scopes):
        import json
        return {"Run ID": "r1", "Scopes": json.dumps(scopes) if scopes else ""}

    def test_explicit_declared_scope_wins(self):
        self.assertEqual(resolve_scope_args(self.row([["P1", "A"], ["P2", "B"]]),
                                            "P2", "B", "x"), ("P2", "B"))

    def test_explicit_undeclared_scope_is_rejected(self):
        # A typo must not silently create a new scope; add-scope declares one.
        with self.assertRaises(SystemExit):
            resolve_scope_args(self.row([["P1", "A"]]), "P1", "Bob", "x")
        with self.assertRaises(SystemExit):
            resolve_scope_args(self.row([]), "P1", "A", "x")

    def test_explicit_scope_case_insensitive_membership(self):
        self.assertEqual(resolve_scope_args(self.row([["P1", "Alice"]]),
                                            "p1", "alice", "x"), ("p1", "alice"))

    def test_single_scope_defaults(self):
        self.assertEqual(resolve_scope_args(self.row([["P1", "A"]]), "", "", "x"),
                         ("P1", "A"))

    def test_no_scope_is_workspace(self):
        self.assertEqual(resolve_scope_args(self.row([]), "", "", "x"), ("", ""))

    def test_multi_scope_without_args_is_rejected(self):
        # Defaulting here would store a wildcard record satisfying every scope.
        with self.assertRaises(SystemExit):
            resolve_scope_args(self.row([["P1", "A"], ["P2", "B"]]), "", "", "x")


class TestQueueOnlyDirt(unittest.TestCase):
    def test_queue_files_and_manifest_are_recoverable_dirt(self):
        porcelain = (" M _intake_queue.values.json\n"
                     " M _intake_queue.Sheet1.csv\n"
                     " D _intake_queue.xlsx\n"
                     " M _manifest.json\n")
        self.assertTrue(is_queue_only_dirt(porcelain))

    def test_business_file_dirt_blocks(self):
        porcelain = (" M _intake_queue.values.json\n"
                     " M 20_M2_Project_Management/X/project_risk.Sheet1.csv\n")
        self.assertFalse(is_queue_only_dirt(porcelain))

    def test_clean_is_not_dirt(self):
        self.assertFalse(is_queue_only_dirt(""))

    def test_nested_queue_named_file_elsewhere_still_matches_by_basename(self):
        # Only basenames are checked; queue exports live at the root, and a
        # same-named file elsewhere would still be queue-export shaped.
        self.assertTrue(is_queue_only_dirt("?? _intake_queue.Sheet1.csv\n"))


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
        sha, problem = check_snapshot(self.LOG, {"Run ID": "run-1"}, 1500.0, dirty=False)
        self.assertEqual(sha, "sha_new")
        self.assertEqual(problem, "")

    def test_dirty_mirror_rejected(self):
        sha, problem = check_snapshot(self.LOG, {"Run ID": "run-1"}, 1500.0, dirty=True)
        self.assertEqual(sha, "")
        self.assertIn("dirty", problem)

    def test_missing_run_commit_rejected(self):
        sha, problem = check_snapshot(self.LOG, {"Run ID": "run-2"}, 1500.0, dirty=False)
        self.assertEqual(sha, "")
        self.assertIn("no mirror commit", problem)

    def test_stale_snapshot_rejected(self):
        # Snapshot at t=2000, but the run's last mutation is much later.
        sha, problem = check_snapshot(self.LOG, {"Run ID": "run-1"}, 5000.0, dirty=False)
        self.assertEqual(sha, "")
        self.assertIn("predates", problem)

    def test_same_minute_tolerated(self):
        sha, problem = check_snapshot(self.LOG, {"Run ID": "run-1"}, 2059.0, dirty=False)
        self.assertEqual(sha, "sha_new")
        self.assertEqual(problem, "")


if __name__ == "__main__":
    unittest.main()
