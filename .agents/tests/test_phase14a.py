"""Unit tests for Phase 14A (mirror export instrumentation and manifest
fingerprints):

- commit_workspace_state.drive_fingerprint(): non-volatile Drive metadata,
  blank (not a failure) when a field is unavailable
- export_sheet()/export_doc(): manifest entries carry fingerprint fields;
  two identical calls produce byte-identical entries (no volatile
  timestamp field that would dirty the manifest on an unchanged export)
- ExportStats: counts/timing collected without changing export output;
  with_retry() records retry attempts
- --stats-out equivalent (ExportStats.to_dict()) is valid, serializable JSON
- old-shape manifest entries (no fingerprint fields) survive the existing
  error-path carry-forward untouched
- prune_stale() behavior is unchanged (direct, no scope-awareness yet)
- document_graph.yaml lane validation (validate_repo.check_graph)

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

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import commit_workspace_state as cws  # noqa: E402
import validate_repo  # noqa: E402


# ---------------------------------------------------------------------------
# Fake Drive/Sheets doubles - just enough surface to exercise export_sheet
# and export_doc without any real API calls.
# ---------------------------------------------------------------------------

class _FakeExec:
    def __init__(self, value):
        self._value = value

    def execute(self):
        return self._value


class FakeDrive:
    def __init__(self, export_bytes_by_mime: dict):
        self._export_bytes_by_mime = export_bytes_by_mime

    def files(self):
        return self

    def export(self, fileId, mimeType):
        return _FakeExec(self._export_bytes_by_mime.get(mimeType, b""))


class FakeValuesResource:
    def __init__(self, values_by_tab: dict):
        self._values_by_tab = values_by_tab

    def get(self, spreadsheetId, range):
        tab = range.strip("'")
        return _FakeExec({"values": self._values_by_tab.get(tab, [])})


class FakeSpreadsheetsResource:
    def __init__(self, meta: dict, values_by_tab: dict):
        self._meta = meta
        self._values_by_tab = values_by_tab

    def get(self, spreadsheetId, fields):
        return _FakeExec(self._meta)

    def values(self):
        return FakeValuesResource(self._values_by_tab)


class FakeSheets:
    def __init__(self, meta: dict, values_by_tab: dict):
        self._meta = meta
        self._values_by_tab = values_by_tab

    def spreadsheets(self):
        return FakeSpreadsheetsResource(self._meta, self._values_by_tab)


def make_sheet_services():
    meta = {"sheets": [{"properties": {"title": "Sheet1"}}]}
    values_by_tab = {"Sheet1": [["a", "b"], ["1", "2"]]}
    services = {
        "drive": FakeDrive({cws.MIME_XLSX: b"fake-xlsx-bytes"}),
        "sheets": FakeSheets(meta, values_by_tab),
    }
    return services


def make_doc_services():
    services = {
        "drive": FakeDrive({"text/markdown": b"# hello\n", cws.MIME_DOCX: b"fake-docx-bytes"}),
    }
    return services


SHEET_ITEM = {
    "id": "fake-sheet-id-1",
    "name": "Placeholder Sheet",
    "mimeType": cws.MIME_GSHEET,
    "modifiedTime": "2026-01-01T00:00:00.000Z",
    "headRevisionId": "0001",
}

DOC_ITEM = {
    "id": "fake-doc-id-1",
    "name": "Placeholder Doc",
    "mimeType": cws.MIME_GDOC,
    "modifiedTime": "2026-01-02T00:00:00.000Z",
    "headRevisionId": "0002",
}


# ---------------------------------------------------------------------------
# drive_fingerprint()
# ---------------------------------------------------------------------------

class DriveFingerprintTests(unittest.TestCase):
    def test_fields_present_when_drive_metadata_available(self):
        fp = cws.drive_fingerprint(SHEET_ITEM, "some/mirror/path.xlsx")
        self.assertEqual(fp["drive_path"], "some/mirror/path.xlsx")
        self.assertEqual(fp["mimeType"], cws.MIME_GSHEET)
        self.assertEqual(fp["headRevisionId"], "0001")
        self.assertEqual(fp["modifiedTime"], "2026-01-01T00:00:00.000Z")

    def test_blank_not_failure_when_drive_metadata_missing(self):
        sparse_item = {"id": "x", "name": "y"}
        fp = cws.drive_fingerprint(sparse_item, "path.docx")
        self.assertEqual(fp["mimeType"], "")
        self.assertEqual(fp["headRevisionId"], "")
        self.assertEqual(fp["modifiedTime"], "")
        self.assertEqual(fp["drive_path"], "path.docx")


# ---------------------------------------------------------------------------
# export_sheet / export_doc manifest fingerprint + stability
# ---------------------------------------------------------------------------

class ExportManifestFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.out_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_export_sheet_manifest_entries_include_fingerprint_fields(self):
        services = make_sheet_services()
        manifest: dict = {}
        warnings: list[str] = []
        cws.export_sheet(services, SHEET_ITEM, self.out_dir, "", manifest, warnings)

        values_entry = manifest["Placeholder Sheet.values.json"]
        self.assertEqual(values_entry["headRevisionId"], "0001")
        self.assertEqual(values_entry["modifiedTime"], "2026-01-01T00:00:00.000Z")
        self.assertEqual(values_entry["drive_path"], "Placeholder Sheet.values.json")

        xlsx_entry = manifest["Placeholder Sheet.xlsx"]
        self.assertEqual(xlsx_entry["headRevisionId"], "0001")
        self.assertEqual(xlsx_entry["fileId"], "fake-sheet-id-1")

    def test_export_doc_manifest_entries_include_fingerprint_fields(self):
        services = make_doc_services()
        manifest: dict = {}
        warnings: list[str] = []
        cws.export_doc(services, DOC_ITEM, self.out_dir, "", manifest, warnings)

        docx_entry = manifest["Placeholder Doc.docx"]
        self.assertEqual(docx_entry["headRevisionId"], "0002")
        self.assertEqual(docx_entry["modifiedTime"], "2026-01-02T00:00:00.000Z")

    def test_repeat_export_produces_byte_identical_manifest_entries(self):
        """No volatile (wall-clock) field was added - the same unchanged
        Drive item must fingerprint identically across two separate export
        runs, or every export would dirty _manifest.json even with nothing
        else to commit."""
        manifest_1: dict = {}
        cws.export_sheet(make_sheet_services(), SHEET_ITEM, self.out_dir, "", manifest_1, [])

        out_dir_2 = Path(self.td.name) / "second"
        out_dir_2.mkdir()
        manifest_2: dict = {}
        cws.export_sheet(make_sheet_services(), SHEET_ITEM, out_dir_2, "", manifest_2, [])

        self.assertEqual(manifest_1, manifest_2)
        # json-serialize both the same way orchestrate_export does, and
        # confirm the bytes match - this is the actual thing write_if_changed
        # compares.
        b1 = json.dumps(manifest_1, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
        b2 = json.dumps(manifest_2, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
        self.assertEqual(b1, b2)


# ---------------------------------------------------------------------------
# ExportStats
# ---------------------------------------------------------------------------

class ExportStatsTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.out_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_stats_none_and_stats_instance_produce_identical_output(self):
        """Instrumentation must be purely observational - passing an
        ExportStats must never change written/manifest content."""
        manifest_no_stats: dict = {}
        written_no_stats = cws.export_sheet(make_sheet_services(), SHEET_ITEM, self.out_dir,
                                            "", manifest_no_stats, [])

        out_dir_2 = self.out_dir / "with_stats"
        out_dir_2.mkdir()
        manifest_with_stats: dict = {}
        stats = cws.ExportStats()
        written_with_stats = cws.export_sheet(make_sheet_services(), SHEET_ITEM, out_dir_2,
                                              "", manifest_with_stats, [], stats=stats)

        self.assertEqual(written_no_stats, written_with_stats)
        self.assertEqual(manifest_no_stats, manifest_with_stats)

    def test_stats_records_counts_for_a_changed_file(self):
        stats = cws.ExportStats()
        cws.export_sheet(make_sheet_services(), SHEET_ITEM, self.out_dir, "", {}, [], stats=stats)
        self.assertEqual(stats.files_exported_or_checked, 1)
        self.assertEqual(stats.files_written_changed, 1)
        self.assertEqual(stats.files_skipped_unchanged, 0)

    def test_stats_records_skipped_unchanged_on_second_identical_export(self):
        stats = cws.ExportStats()
        # First export writes the files to disk.
        cws.export_sheet(make_sheet_services(), SHEET_ITEM, self.out_dir, "", {}, [], stats=stats)
        # Second export of the same unchanged content over the same out_dir
        # should be a no-op at the write_if_changed layer.
        cws.export_sheet(make_sheet_services(), SHEET_ITEM, self.out_dir, "", {}, [], stats=stats)
        self.assertEqual(stats.files_exported_or_checked, 2)
        self.assertEqual(stats.files_written_changed, 1)
        self.assertEqual(stats.files_skipped_unchanged, 1)

    def test_with_retry_records_retry_count(self):
        stats = cws.ExportStats()
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("transient 500")
            return "ok"

        result = cws.with_retry(flaky, attempts=3, stats=stats)
        self.assertEqual(result, "ok")
        self.assertEqual(stats.retries_total, 1)

    def test_with_retry_without_stats_still_works(self):
        # stats is optional - existing callers that don't pass it must be unaffected.
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 2:
                raise RuntimeError("transient 500")
            return "ok"

        self.assertEqual(cws.with_retry(flaky, attempts=3), "ok")

    def test_slowest_files_sorted_descending_and_capped(self):
        stats = cws.ExportStats()
        for i in range(15):
            stats.record_file(f"file_{i}", float(i), "sheet")
        slowest = stats.slowest_files(limit=5)
        self.assertEqual(len(slowest), 5)
        self.assertEqual([f["path"] for f in slowest], ["file_14", "file_13", "file_12", "file_11", "file_10"])

    def test_to_dict_is_valid_json_serializable(self):
        stats = cws.ExportStats(mode="full")
        stats.folders_scanned = 3
        stats.files_considered = 14
        stats.files_exported_or_checked = 14
        stats.files_written_changed = 2
        stats.files_skipped_unchanged = 12
        stats.retries_total = 1
        stats.errors_count = 0
        stats.warnings_count = 0
        stats.elapsed_total_ms = 1234.5
        stats.record_file("some/placeholder/path.xlsx", 88.2, "sheet")

        as_json = json.dumps(stats.to_dict())
        round_tripped = json.loads(as_json)
        self.assertEqual(round_tripped["mode"], "full")
        self.assertEqual(round_tripped["folders_scanned"], 3)
        self.assertEqual(round_tripped["files_written_changed"], 2)
        self.assertEqual(len(round_tripped["slowest_files"]), 1)
        self.assertEqual(round_tripped["slowest_files"][0]["path"], "some/placeholder/path.xlsx")


# ---------------------------------------------------------------------------
# --stats-out CLI flag (subprocess smoke test, no real Drive access needed:
# argparse rejects before any service call if the flag itself is malformed)
# ---------------------------------------------------------------------------

class StatsOutCliTests(unittest.TestCase):
    def test_stats_out_flag_is_recognized_by_argparse(self):
        res = subprocess.run(
            [sys.executable, str(SCRIPTS / "commit_workspace_state.py"), "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("--stats-out", res.stdout)


# ---------------------------------------------------------------------------
# Old-shape manifest entries (no fingerprint fields) survive untouched
# ---------------------------------------------------------------------------

class ManifestBackwardCompatibilityTests(unittest.TestCase):
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

    def test_old_shape_entry_survives_error_path_carry_forward(self):
        # Pre-Phase-14A manifest entry: no drive_path/mimeType/headRevisionId/
        # modifiedTime keys at all.
        old_entry = {"fileId": "legacy-id", "name": "Legacy File", "kind": "document"}
        restore_manifest = self.mirror / "_manifest.json"
        restore_manifest.write_text(json.dumps({"legacy_file.docx": old_entry}), encoding="utf-8")
        (self.mirror / "legacy_file.docx").write_bytes(b"legacy content")

        def failing_read_queue(services, queue_id):
            raise Exception("orchestrated error")

        written, manifest, removed, warnings, errors, stats = cws.orchestrate_export(
            None, self.mirror, self.data_root,
            lambda *args: None,
            lambda rows, droot, mir: (set(), [], []),
            lambda services: "dummy",
            failing_read_queue,
        )

        self.assertTrue(any("orchestrated error" in e for e in errors))
        self.assertIn("legacy_file.docx", manifest)
        self.assertEqual(manifest["legacy_file.docx"], old_entry)
        self.assertTrue((self.mirror / "legacy_file.docx").exists())
        self.assertEqual(removed, 0)
        self.assertEqual(stats.errors_count, len(errors))


# ---------------------------------------------------------------------------
# prune_stale - unchanged behavior
# ---------------------------------------------------------------------------

class PruneStaleUnchangedTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.mirror = Path(self.td.name)
        (self.mirror / "_manifest.json").write_text("{}", encoding="utf-8")
        (self.mirror / "README.md").write_text("dummy", encoding="utf-8")
        (self.mirror / "keep.txt").write_text("keep", encoding="utf-8")
        (self.mirror / "stale.txt").write_text("stale", encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def test_prune_removes_only_files_outside_expected_set(self):
        removed = cws.prune_stale(self.mirror, {"keep.txt"})
        self.assertEqual(removed, 1)
        self.assertTrue((self.mirror / "keep.txt").exists())
        self.assertFalse((self.mirror / "stale.txt").exists())
        # protected regardless of the expected set
        self.assertTrue((self.mirror / "README.md").exists())
        self.assertTrue((self.mirror / "_manifest.json").exists())

    def test_prune_removes_nothing_when_everything_expected(self):
        removed = cws.prune_stale(self.mirror, {"keep.txt", "stale.txt"})
        self.assertEqual(removed, 0)
        self.assertTrue((self.mirror / "keep.txt").exists())
        self.assertTrue((self.mirror / "stale.txt").exists())


# ---------------------------------------------------------------------------
# document_graph.yaml lane validation
# ---------------------------------------------------------------------------

class LaneValidationTests(unittest.TestCase):
    def test_real_graph_lanes_pass_validator(self):
        validate_repo.failures.clear()
        validate_repo.warnings.clear()
        source_types = validate_repo.load_source_types()
        validate_repo.check_graph(source_types)
        self.assertEqual(validate_repo.failures, [])

    def test_validator_rejects_lane_with_empty_root_folder(self):
        import yaml
        graph = yaml.safe_load(validate_repo.GRAPH.read_text(encoding="utf-8"))
        graph["lanes"]["broken_lane"] = {"root_folder": ""}
        with TemporaryDirectory() as td:
            bad_graph_path = Path(td) / "document_graph.yaml"
            bad_graph_path.write_text(yaml.safe_dump(graph), encoding="utf-8")
            original_graph = validate_repo.GRAPH
            try:
                validate_repo.GRAPH = bad_graph_path
                validate_repo.failures.clear()
                validate_repo.warnings.clear()
                source_types = validate_repo.load_source_types()
                validate_repo.check_graph(source_types)
                self.assertTrue(any("broken_lane" in f for f in validate_repo.failures))
            finally:
                validate_repo.GRAPH = original_graph

    def test_validator_rejects_duplicate_lane_root_folder(self):
        import yaml
        graph = yaml.safe_load(validate_repo.GRAPH.read_text(encoding="utf-8"))
        graph["lanes"]["duplicate_lane"] = {"root_folder": "10_M1_People_Management"}
        with TemporaryDirectory() as td:
            bad_graph_path = Path(td) / "document_graph.yaml"
            bad_graph_path.write_text(yaml.safe_dump(graph), encoding="utf-8")
            original_graph = validate_repo.GRAPH
            try:
                validate_repo.GRAPH = bad_graph_path
                validate_repo.failures.clear()
                validate_repo.warnings.clear()
                source_types = validate_repo.load_source_types()
                validate_repo.check_graph(source_types)
                self.assertTrue(any("duplicate_lane" in f for f in validate_repo.failures))
            finally:
                validate_repo.GRAPH = original_graph


if __name__ == "__main__":
    unittest.main()
