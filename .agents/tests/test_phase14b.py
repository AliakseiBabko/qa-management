"""Unit tests for Phase 14B (opt-in scoped mirror snapshot mode):

- scope_resolver.resolve_scope(): pure scope-resolution logic (no Drive
  calls) - workspace-only/M2-project/M1-person/Project-Knowledge scopes,
  mixed (project+person) scopes, >4-scope warning, missing-lane refusal
- commit_workspace_state.py --scoped/--run-id CLI wiring
- orchestrate_export_scoped(): scoped export/prune/manifest-merge safety -
  out-of-scope entries and physical files survive byte-for-byte, scoped
  prune only removes stale files inside scope, export failure skips all
  pruning, malformed _manifest.json refuses before any write
- full-mode regression (orchestrate_export unaffected)
- qa_manage.py review/complete accept a scoped-shaped commit

No real names/projects in any fixture here - fake Drive folder/file names
are placeholders only.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import commit_workspace_state as cws  # noqa: E402
import scope_resolver  # noqa: E402
import qa_manage  # noqa: E402
import closure_outcomes  # noqa: E402


# ---------------------------------------------------------------------------
# scope_resolver.resolve_scope() - pure logic, no Drive calls.
# ---------------------------------------------------------------------------

FAKE_GRAPH = {
    "lanes": {
        "m2_project_management": {"root_folder": "20_M2_Project_Management"},
        "project_knowledge": {"root_folder": "30_Project_Knowledge"},
        "m1_people_management": {"root_folder": "10_M1_People_Management"},
    },
    "sources": {
        "qa_1to1": {},
        "project_knowledge_transcript": {"lane": "project_knowledge"},
        "admin_note": {},
    },
}


def make_row(source_type="admin_note", scopes="", entries="", variant=""):
    return {
        "Run ID": "fake-run-1",
        "Source type": source_type,
        "Scopes": scopes,
        "Entries": entries,
        "Route variant": variant,
    }


class ScopeResolverTests(unittest.TestCase):
    def _resolve(self, row, graph=FAKE_GRAPH, outcome_rows=None):
        with mock.patch.object(qa_manage, "find_queue", return_value="sheet"), \
             mock.patch.object(qa_manage, "read_queue", return_value=[row]), \
             mock.patch.object(qa_manage, "load_graph", return_value=graph), \
             mock.patch.object(closure_outcomes, "fetch_outcomes", return_value=outcome_rows or []):
            return scope_resolver.resolve_scope(services={}, run_id=row["Run ID"])

    def test_workspace_only_run_has_no_subtrees(self):
        res = self._resolve(make_row(source_type="admin_note"))
        self.assertTrue(res.ok, res.reason)
        self.assertEqual(res.lane_root_prefixes, set())
        self.assertEqual(res.subtree_prefixes, set())
        self.assertEqual(set(res.always_include_names),
                         {"_intake_queue", "_skill_invocations", "_closure_outcomes"})

    def test_m2_project_scope_resolves_lane_and_subtree(self):
        row = make_row(source_type="qa_1to1", scopes=json.dumps([["ProjectX", ""]]), variant="m2")
        res = self._resolve(row)
        self.assertTrue(res.ok, res.reason)
        self.assertEqual(res.lane_root_prefixes, {"20_M2_Project_Management"})
        self.assertEqual(res.subtree_prefixes, {"20_M2_Project_Management/ProjectX"})

    def test_m1_person_scope_resolves_lane_and_subtree(self):
        row = make_row(source_type="qa_1to1", scopes=json.dumps([["", "PersonY"]]), variant="m1")
        res = self._resolve(row)
        self.assertTrue(res.ok, res.reason)
        self.assertEqual(res.lane_root_prefixes, {"10_M1_People_Management"})
        self.assertEqual(res.subtree_prefixes, {"10_M1_People_Management/PersonY"})

    def test_project_knowledge_scope_resolves_pk_lane(self):
        row = make_row(source_type="project_knowledge_transcript",
                       scopes=json.dumps([["PKF", ""]]))
        res = self._resolve(row)
        self.assertTrue(res.ok, res.reason)
        self.assertEqual(res.lane_root_prefixes, {"30_Project_Knowledge"})
        self.assertEqual(res.subtree_prefixes, {"30_Project_Knowledge/PKF"})

    def test_mixed_scope_resolves_both_lanes(self):
        row = make_row(source_type="qa_1to1", scopes=json.dumps([["ProjectX", "PersonY"]]),
                       variant="mixed")
        res = self._resolve(row)
        self.assertTrue(res.ok, res.reason)
        self.assertEqual(res.lane_root_prefixes,
                         {"20_M2_Project_Management", "10_M1_People_Management"})
        self.assertEqual(res.subtree_prefixes,
                         {"20_M2_Project_Management/ProjectX", "10_M1_People_Management/PersonY"})

    def test_more_than_four_scopes_emits_warning_but_resolves(self):
        scopes = [[f"Project{i}", ""] for i in range(5)]
        row = make_row(source_type="qa_1to1", scopes=json.dumps(scopes), variant="m2")
        res = self._resolve(row)
        self.assertTrue(res.ok, res.reason)
        self.assertEqual(len(res.subtree_prefixes), 5)
        self.assertEqual(len(res.warnings), 1)
        self.assertIn("full export", res.warnings[0])

    def test_missing_lane_root_folder_refuses(self):
        broken_graph = json.loads(json.dumps(FAKE_GRAPH))
        del broken_graph["lanes"]["m1_people_management"]
        row = make_row(source_type="qa_1to1", scopes=json.dumps([["", "PersonY"]]), variant="m1")
        res = self._resolve(row, graph=broken_graph)
        self.assertFalse(res.ok)
        self.assertIn("m1_people_management", res.reason)

    def test_run_not_found_refuses(self):
        with mock.patch.object(qa_manage, "find_queue", return_value="sheet"), \
             mock.patch.object(qa_manage, "read_queue", return_value=[]), \
             mock.patch.object(qa_manage, "load_graph", return_value=FAKE_GRAPH):
            res = scope_resolver.resolve_scope(services={}, run_id="does-not-exist")
        self.assertFalse(res.ok)


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

class ScopedCliParserTests(unittest.TestCase):
    def test_scoped_without_run_id_is_a_parser_error(self):
        res = subprocess.run(
            [sys.executable, str(SCRIPTS / "commit_workspace_state.py"), "--scoped"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("--run-id", res.stderr)

    def test_help_lists_scoped_and_run_id(self):
        res = subprocess.run(
            [sys.executable, str(SCRIPTS / "commit_workspace_state.py"), "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("--scoped", res.stdout)
        self.assertIn("--run-id", res.stdout)


# ---------------------------------------------------------------------------
# Fake Drive/Sheets doubles for orchestrate_export_scoped()
# ---------------------------------------------------------------------------

class _FakeExec:
    def __init__(self, value):
        self._value = value

    def execute(self):
        return self._value


class FakeDriveTree:
    """Minimal double for both commit_workspace_state.list_children()'s
    query shape and m2_workspace_layout.find_child_folder()'s shape."""

    def __init__(self, children_by_folder: dict, export_bytes_by_mime: dict | None = None):
        self._children = children_by_folder
        self._export_bytes = export_bytes_by_mime or {}

    def files(self):
        return self

    def list(self, q, fields=None, pageSize=None, pageToken=None, **kwargs):
        start = q.index("'") + 1
        end = q.index("'", start)
        folder_id = q[start:end]
        items = list(self._children.get(folder_id, []))
        if "name = '" in q:
            n_start = q.index("name = '") + len("name = '")
            n_end = q.index("'", n_start)
            name = q[n_start:n_end]
            items = [i for i in items if i["name"] == name]
        if "mimeType = '" + cws.MIME_FOLDER + "'" in q:
            items = [i for i in items if i["mimeType"] == cws.MIME_FOLDER]
        return _FakeExec({"files": items, "nextPageToken": None})

    def export(self, fileId, mimeType):
        return _FakeExec(self._export_bytes.get(mimeType, b""))


class FakeValuesResourceMulti:
    def __init__(self, sheets_by_id):
        self._sheets_by_id = sheets_by_id

    def get(self, spreadsheetId, range):
        tab = range.strip("'")
        return _FakeExec({"values": self._sheets_by_id[spreadsheetId]["values_by_tab"].get(tab, [])})


class FakeSheetsMulti:
    def __init__(self, sheets_by_id):
        self._sheets_by_id = sheets_by_id

    def spreadsheets(self):
        return self

    def get(self, spreadsheetId, fields):
        return _FakeExec(self._sheets_by_id[spreadsheetId]["meta"])

    def values(self):
        return FakeValuesResourceMulti(self._sheets_by_id)


def sheet_item(item_id, name):
    return {"id": item_id, "name": name, "mimeType": cws.MIME_GSHEET,
            "modifiedTime": "2026-01-01T00:00:00.000Z", "headRevisionId": ""}


def folder_item(item_id, name):
    return {"id": item_id, "name": name, "mimeType": cws.MIME_FOLDER}


ROOT_ID = cws.ROOT_FOLDER_ID
M2_ROOT_ID = "m2root"
PROJECT_X_ID = "projx"
M1_ROOT_ID = "m1root"


def build_fixture_tree():
    """root (= the real ROOT_FOLDER_ID constant, so find_folder_path()'s
       lookups from ROOT_FOLDER_ID resolve against this fixture)
       |- _intake_queue (sheet)
       |- _skill_invocations (sheet)
       |- _closure_outcomes (sheet)
       |- 20_M2_Project_Management (folder)
       |    |- _project_registry (sheet)         <- lane-root direct file
       |    |- ProjectX (folder)
       |         |- evidence_log (sheet)
       |- 10_M1_People_Management (folder)        <- untouched sibling lane
       |    |- PersonY (sheet-ish placeholder, unused by these tests)
    """
    children = {
        ROOT_ID: [
            sheet_item("sid-intake-queue", "_intake_queue"),
            sheet_item("sid-skill-invocations", "_skill_invocations"),
            sheet_item("sid-closure-outcomes", "_closure_outcomes"),
            folder_item(M2_ROOT_ID, "20_M2_Project_Management"),
            folder_item(M1_ROOT_ID, "10_M1_People_Management"),
        ],
        M2_ROOT_ID: [
            sheet_item("sid-project-registry", "_project_registry"),
            folder_item(PROJECT_X_ID, "ProjectX"),
        ],
        PROJECT_X_ID: [
            sheet_item("sid-evidence-log", "evidence_log"),
        ],
        M1_ROOT_ID: [],
    }
    sheets_by_id = {}
    for folder_children in children.values():
        for item in folder_children:
            if item["mimeType"] == cws.MIME_GSHEET:
                sheets_by_id[item["id"]] = {
                    "meta": {"sheets": [{"properties": {"title": "Sheet1"}}]},
                    "values_by_tab": {"Sheet1": [["a", "b"]]},
                }
    drive = FakeDriveTree(children, {cws.MIME_XLSX: b"fake-xlsx"})
    sheets = FakeSheetsMulti(sheets_by_id)
    return {"drive": drive, "sheets": sheets}


def make_resolution(lane_root_prefixes, subtree_prefixes, warnings=None):
    return scope_resolver.ScopeResolution(
        ok=True, warnings=warnings or [],
        lane_root_prefixes=set(lane_root_prefixes), subtree_prefixes=set(subtree_prefixes),
    )


def refusing_resolution(reason):
    return scope_resolver.ScopeResolution(ok=False, reason=reason)


# ---------------------------------------------------------------------------
# orchestrate_export_scoped() - safety properties
# ---------------------------------------------------------------------------

class OrchestrateScopedTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.root = Path(self.td.name).resolve()
        self.data_root = self.root / "data"
        self.mirror = self.root / "mirror"
        self.data_root.mkdir()
        self.mirror.mkdir()
        for r in ("00_Inbox", "90_Storage/Processed_Sources"):
            (self.data_root / r).mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=self.mirror, capture_output=True, check=True)
        (self.mirror / "README.md").write_text("dummy", encoding="utf-8")
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.mirror, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"], cwd=self.mirror, check=True)

    def tearDown(self):
        self.td.cleanup()

    def _no_op_source_text(self, rows, data_root, mirror):
        return set(), [], []

    def test_missing_manifest_refuses_before_any_write(self):
        services = build_fixture_tree()
        with self.assertRaises(cws.ScopedExportRefused):
            cws.orchestrate_export_scoped(
                services, self.mirror, self.data_root, "run-1",
                export_source_texts_fn=self._no_op_source_text,
                find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
                resolve_scope_fn=lambda s, r: make_resolution(
                    {"20_M2_Project_Management"}, {"20_M2_Project_Management/ProjectX"}),
            )
        self.assertFalse((self.mirror / "_manifest.json").exists())

    def test_malformed_manifest_refuses_before_write_or_prune(self):
        (self.mirror / "_manifest.json").write_text("{not valid json", encoding="utf-8")
        (self.mirror / "unrelated.txt").write_text("keep me", encoding="utf-8")
        services = build_fixture_tree()
        with self.assertRaises(cws.ScopedExportRefused):
            cws.orchestrate_export_scoped(
                services, self.mirror, self.data_root, "run-1",
                export_source_texts_fn=self._no_op_source_text,
                find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
                resolve_scope_fn=lambda s, r: make_resolution(
                    {"20_M2_Project_Management"}, {"20_M2_Project_Management/ProjectX"}),
            )
        # untouched - still malformed, nothing pruned
        self.assertEqual((self.mirror / "_manifest.json").read_text(encoding="utf-8"), "{not valid json")
        self.assertTrue((self.mirror / "unrelated.txt").exists())

    def test_resolution_refusal_propagates_without_touching_mirror(self):
        (self.mirror / "_manifest.json").write_text("{}", encoding="utf-8")
        services = build_fixture_tree()
        with self.assertRaises(cws.ScopedExportRefused) as ctx:
            cws.orchestrate_export_scoped(
                services, self.mirror, self.data_root, "run-1",
                export_source_texts_fn=self._no_op_source_text,
                find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
                resolve_scope_fn=lambda s, r: refusing_resolution("lane not found"),
            )
        self.assertIn("lane not found", str(ctx.exception))

    def test_missing_drive_folder_refuses(self):
        (self.mirror / "_manifest.json").write_text("{}", encoding="utf-8")
        services = build_fixture_tree()
        with self.assertRaises(cws.ScopedExportRefused):
            cws.orchestrate_export_scoped(
                services, self.mirror, self.data_root, "run-1",
                export_source_texts_fn=self._no_op_source_text,
                find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
                resolve_scope_fn=lambda s, r: make_resolution(
                    {"20_M2_Project_Management"}, {"20_M2_Project_Management/NoSuchProject"}),
            )

    def test_out_of_scope_manifest_entries_and_files_survive_byte_for_byte(self):
        old_entry = {"fileId": "out-of-scope-id", "name": "Out Of Scope", "kind": "document"}
        (self.mirror / "_manifest.json").write_text(
            json.dumps({"10_M1_People_Management/PersonZ/PersonZ.docx": old_entry}), encoding="utf-8")
        (self.mirror / "10_M1_People_Management" / "PersonZ").mkdir(parents=True)
        (self.mirror / "10_M1_People_Management/PersonZ/PersonZ.docx").write_bytes(b"out of scope content")

        services = build_fixture_tree()
        written, manifest, removed, warnings, errors, stats = cws.orchestrate_export_scoped(
            services, self.mirror, self.data_root, "run-1",
            export_source_texts_fn=self._no_op_source_text,
            find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
            resolve_scope_fn=lambda s, r: make_resolution(
                {"20_M2_Project_Management"}, {"20_M2_Project_Management/ProjectX"}),
        )

        self.assertEqual(errors, [])
        self.assertEqual(manifest["10_M1_People_Management/PersonZ/PersonZ.docx"], old_entry)
        self.assertEqual(
            (self.mirror / "10_M1_People_Management/PersonZ/PersonZ.docx").read_bytes(),
            b"out of scope content")
        self.assertEqual(removed, 0)
        self.assertEqual(stats.mode, "scoped")
        self.assertEqual(stats.scoped_prefix_count, 1)

    def test_scoped_exports_lane_root_and_subtree_and_workspace_root(self):
        (self.mirror / "_manifest.json").write_text("{}", encoding="utf-8")
        services = build_fixture_tree()
        written, manifest, removed, warnings, errors, stats = cws.orchestrate_export_scoped(
            services, self.mirror, self.data_root, "run-1",
            export_source_texts_fn=self._no_op_source_text,
            find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
            resolve_scope_fn=lambda s, r: make_resolution(
                {"20_M2_Project_Management"}, {"20_M2_Project_Management/ProjectX"}),
        )
        self.assertEqual(errors, [])
        self.assertIn("_intake_queue.xlsx", manifest)
        self.assertIn("20_M2_Project_Management/_project_registry.xlsx", manifest)
        self.assertIn("20_M2_Project_Management/ProjectX/evidence_log.xlsx", manifest)
        # sibling lane never touched
        self.assertFalse(any(k.startswith("10_M1_People_Management") for k in manifest))

    def test_scoped_prune_removes_only_stale_files_inside_scope(self):
        (self.mirror / "_manifest.json").write_text("{}", encoding="utf-8")
        stale_in_scope_dir = self.mirror / "20_M2_Project_Management" / "ProjectX"
        stale_in_scope_dir.mkdir(parents=True)
        (stale_in_scope_dir / "stale_old_doc.docx").write_bytes(b"stale in-scope file")

        stale_out_of_scope_dir = self.mirror / "10_M1_People_Management" / "PersonZ"
        stale_out_of_scope_dir.mkdir(parents=True)
        (stale_out_of_scope_dir / "keep_me.docx").write_bytes(b"never touched")

        services = build_fixture_tree()
        written, manifest, removed, warnings, errors, stats = cws.orchestrate_export_scoped(
            services, self.mirror, self.data_root, "run-1",
            export_source_texts_fn=self._no_op_source_text,
            find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
            resolve_scope_fn=lambda s, r: make_resolution(
                {"20_M2_Project_Management"}, {"20_M2_Project_Management/ProjectX"}),
        )
        self.assertEqual(errors, [])
        self.assertFalse((stale_in_scope_dir / "stale_old_doc.docx").exists(), "stale in-scope file must be pruned")
        self.assertTrue((stale_out_of_scope_dir / "keep_me.docx").exists(), "out-of-scope file must survive")
        self.assertGreaterEqual(removed, 1)

    def test_export_failure_skips_all_pruning_and_marks_partial(self):
        (self.mirror / "_manifest.json").write_text("{}", encoding="utf-8")
        stale_in_scope_dir = self.mirror / "20_M2_Project_Management" / "ProjectX"
        stale_in_scope_dir.mkdir(parents=True)
        (stale_in_scope_dir / "would_be_pruned.docx").write_bytes(b"stale")

        services = build_fixture_tree()

        def failing_source_text(rows, data_root, mirror):
            raise RuntimeError("boom")

        written, manifest, removed, warnings, errors, stats = cws.orchestrate_export_scoped(
            services, self.mirror, self.data_root, "run-1",
            export_source_texts_fn=failing_source_text,
            find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
            resolve_scope_fn=lambda s, r: make_resolution(
                {"20_M2_Project_Management"}, {"20_M2_Project_Management/ProjectX"}),
        )
        self.assertTrue(any("boom" in e for e in errors))
        self.assertEqual(removed, 0)
        self.assertTrue((stale_in_scope_dir / "would_be_pruned.docx").exists(),
                        "prune must be skipped entirely when export errors occur")

    def test_scope_warning_threaded_into_stats(self):
        (self.mirror / "_manifest.json").write_text("{}", encoding="utf-8")
        services = build_fixture_tree()
        _, _, _, warnings, _, stats = cws.orchestrate_export_scoped(
            services, self.mirror, self.data_root, "run-1",
            export_source_texts_fn=self._no_op_source_text,
            find_queue_fn=lambda s: "q", read_queue_fn=lambda s, q: [],
            resolve_scope_fn=lambda s, r: make_resolution(
                {"20_M2_Project_Management"}, {"20_M2_Project_Management/ProjectX"},
                warnings=["touches too many scopes"]),
        )
        self.assertIn("touches too many scopes", warnings)
        self.assertEqual(stats.scope_warnings, ["touches too many scopes"])


# ---------------------------------------------------------------------------
# scoped membership / prune helpers - direct unit tests
# ---------------------------------------------------------------------------

class PathInScopeTests(unittest.TestCase):
    def test_recursive_prefix_matches_nested_paths(self):
        self.assertTrue(cws.path_in_scope(
            "20_M2_Project_Management/ProjectX/private/evidence_log.xlsx",
            {"20_M2_Project_Management/ProjectX"}, set()))

    def test_recursive_prefix_does_not_match_sibling_project(self):
        self.assertFalse(cws.path_in_scope(
            "20_M2_Project_Management/ProjectOther/evidence_log.xlsx",
            {"20_M2_Project_Management/ProjectX"}, set()))

    def test_shallow_prefix_matches_direct_child_only(self):
        self.assertTrue(cws.path_in_scope(
            "20_M2_Project_Management/_project_registry.xlsx", set(), {"20_M2_Project_Management"}))

    def test_shallow_prefix_does_not_match_grandchild(self):
        self.assertFalse(cws.path_in_scope(
            "20_M2_Project_Management/ProjectX/evidence_log.xlsx", set(), {"20_M2_Project_Management"}))

    def test_workspace_root_shallow_prefix_is_empty_string(self):
        self.assertTrue(cws.path_in_scope("_intake_queue.xlsx", set(), {""}))


class MergeScopedManifestTests(unittest.TestCase):
    def test_out_of_scope_entries_carried_forward_unchanged(self):
        old = {"10_M1_People_Management/PersonZ/PersonZ.docx": {"fileId": "z"}}
        merged = cws.merge_scoped_manifest(old, {}, {"20_M2_Project_Management/ProjectX"}, {""})
        self.assertEqual(merged, old)

    def test_stale_in_scope_entry_dropped(self):
        old = {
            "20_M2_Project_Management/ProjectX/old_doc.docx": {"fileId": "stale"},
            "10_M1_People_Management/PersonZ/PersonZ.docx": {"fileId": "z"},
        }
        merged = cws.merge_scoped_manifest(old, {}, {"20_M2_Project_Management/ProjectX"}, {""})
        self.assertNotIn("20_M2_Project_Management/ProjectX/old_doc.docx", merged)
        self.assertIn("10_M1_People_Management/PersonZ/PersonZ.docx", merged)

    def test_fresh_entries_overlay_old(self):
        old = {"20_M2_Project_Management/ProjectX/evidence_log.xlsx": {"fileId": "old-id"}}
        fresh = {"20_M2_Project_Management/ProjectX/evidence_log.xlsx": {"fileId": "new-id"}}
        merged = cws.merge_scoped_manifest(old, fresh, {"20_M2_Project_Management/ProjectX"}, {""})
        self.assertEqual(merged["20_M2_Project_Management/ProjectX/evidence_log.xlsx"]["fileId"], "new-id")


class PruneStaleScopedTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.mirror = Path(self.td.name)
        (self.mirror / "_manifest.json").write_text("{}", encoding="utf-8")
        (self.mirror / "_source_text_manifest.json").write_text("{}", encoding="utf-8")
        (self.mirror / "README.md").write_text("dummy", encoding="utf-8")
        (self.mirror / "_source_text" / "blobs" / "v1").mkdir(parents=True)
        (self.mirror / "_source_text/blobs/v1/somehash.txt").write_text("blob", encoding="utf-8")
        (self.mirror / "20_M2_Project_Management" / "ProjectX").mkdir(parents=True)
        (self.mirror / "20_M2_Project_Management/ProjectX/stale.docx").write_text("stale", encoding="utf-8")
        (self.mirror / "10_M1_People_Management" / "PersonZ").mkdir(parents=True)
        (self.mirror / "10_M1_People_Management/PersonZ/keep.docx").write_text("keep", encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def test_prunes_only_stale_in_scope_file(self):
        removed = cws.prune_stale_scoped(
            self.mirror, expected=set(),
            scoped_prefixes={"20_M2_Project_Management/ProjectX"}, scoped_shallow_prefixes={""})
        self.assertEqual(removed, 1)
        self.assertFalse((self.mirror / "20_M2_Project_Management/ProjectX/stale.docx").exists())
        self.assertTrue((self.mirror / "10_M1_People_Management/PersonZ/keep.docx").exists())

    def test_never_prunes_manifest_or_source_text_tree(self):
        cws.prune_stale_scoped(
            self.mirror, expected=set(),
            scoped_prefixes={"20_M2_Project_Management/ProjectX"}, scoped_shallow_prefixes={""})
        self.assertTrue((self.mirror / "_manifest.json").exists())
        self.assertTrue((self.mirror / "_source_text_manifest.json").exists())
        self.assertTrue((self.mirror / "_source_text/blobs/v1/somehash.txt").exists())
        self.assertTrue((self.mirror / "README.md").exists())


# ---------------------------------------------------------------------------
# Full mode regression - orchestrate_export() unaffected by Phase 14B
# ---------------------------------------------------------------------------

class FullModeUnaffectedTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.root = Path(self.td.name).resolve()
        self.data_root = self.root / "data"
        self.mirror = self.root / "mirror"
        self.data_root.mkdir()
        self.mirror.mkdir()
        subprocess.run(["git", "init"], cwd=self.mirror, capture_output=True, check=True)
        (self.mirror / "README.md").write_text("dummy", encoding="utf-8")
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.mirror, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"], cwd=self.mirror, check=True)

    def tearDown(self):
        self.td.cleanup()

    def test_full_mode_still_prunes_globally(self):
        (self.mirror / "stale.txt").write_text("stale", encoding="utf-8")

        def fake_walk(services, folder_id, out_dir, rel, manifest, written, errors, warnings, stats=None):
            written.append("dummy.txt")
            (out_dir / "dummy.txt").write_text("hello", encoding="utf-8")

        written, manifest, removed, warnings, errors, stats = cws.orchestrate_export(
            None, self.mirror, self.data_root, fake_walk,
            lambda rows, droot, mir: (set(), [], []),
            lambda services: None, lambda services, q: [],
        )
        self.assertEqual(stats.mode, "full")
        self.assertFalse((self.mirror / "stale.txt").exists())


# ---------------------------------------------------------------------------
# qa_manage.py review/complete accept a scoped-shaped commit
# ---------------------------------------------------------------------------

class ScopedShapedCommitReviewTests(unittest.TestCase):
    """A scoped commit's tree only has a subset of paths at that SHA - as
    established in the Phase 14 design, review/complete verify via `git show
    <sha>:<path>` against one specific commit and never care how that
    commit's tree was assembled. This proves that directly: a fixture
    mirror commit containing only _skill_invocations (no other canonical
    docs at all) still satisfies the invocation-token check the same way a
    full commit would."""

    def setUp(self):
        self.td = TemporaryDirectory()
        self.mirror = Path(self.td.name)
        subprocess.run(["git", "init"], cwd=self.mirror, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.mirror, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"], cwd=self.mirror, check=True)

    def tearDown(self):
        self.td.cleanup()

    def test_scoped_shaped_commit_satisfies_invocation_token_check(self):
        run_id = "fake-run-scoped-1"
        (self.mirror / "_skill_invocations.values.json").write_text(
            json.dumps({"Sheet1": [["header"], [f"note with run:{run_id} token"]]}), encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.mirror, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", f"scoped snapshot [{run_id}]"],
                       cwd=self.mirror, capture_output=True, check=True)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.mirror,
                             capture_output=True, text=True, check=True).stdout.strip()

        with mock.patch.object(qa_manage, "MIRROR", self.mirror):
            res_git = qa_manage.mirror_git(self.mirror, "show", f"{sha}:_skill_invocations.values.json")
            token = f"run:{run_id}"
            self.assertEqual(res_git.returncode, 0)
            self.assertIn(token, res_git.stdout)


if __name__ == "__main__":
    unittest.main()
