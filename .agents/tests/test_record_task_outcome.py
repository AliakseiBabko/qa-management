#!/usr/bin/env python3
"""Unit tests for record_task_outcome.py and task-outcomes.csv validation/diff-guard."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import operator_telemetry_common as common
import record_task_outcome as record_tool


def _base_task_outcome_row(**overrides) -> dict:
    row = {k: "" for k in common.TASK_OUTCOME_CSV_HEADER}
    row.update({
        "task_outcome_id": "outcome-intake-2026-07-23-a1b2c3d4",
        "date": "2026-07-23",
        "task_type": "intake_run",
        "runtime": "antigravity",
        "linked_session_run_id": "session-antigravity-2026-07-23-e4a53816",
        "queue_run_hash": "a1b2c3d4e5f67890",
        "lane": "project_knowledge",
        "source_type": "project_knowledge_document",
        "source_count": "1",
        "source_blob_present": "yes",
        "source_chars": "45200",
        "source_estimated_tokens": "11300",
        "record_apply_updated_count": "4",
        "record_apply_no_change_count": "0",
        "record_apply_not_applicable_count": "0",
        "closure_edges_count": "4",
        "closure_edges_updated_count": "4",
        "closure_edges_no_change_count": "0",
        "closure_edges_gated_count": "0",
        "mirror_export_mode": "scoped",
        "status": "ok",
        "notes": "clean pass",
    })
    row.update(overrides)
    return row


class TestTaskOutcomeValidation(unittest.TestCase):
    def test_task_outcome_id_generalizes_across_all_task_types(self):
        task_types = ["intake_run", "repo_maintenance", "retro_pass", "admin_pass", "quality_audit", "cleanup_pass"]
        for tt in task_types:
            prefix = tt.replace("_", "-")
            if prefix == "intake-run":
                prefix = "intake"
            tid = f"outcome-{prefix}-2026-07-23-12345678"
            row = _base_task_outcome_row(task_type=tt, task_outcome_id=tid)
            errors = common.validate_task_outcome_row(row)
            self.assertEqual(errors, [], f"Task type {tt} failed validation: {errors}")

    def test_non_zero_workload_guard_rejection(self):
        row = _base_task_outcome_row(
            source_count="0", source_chars="0", source_estimated_tokens="0",
            record_apply_updated_count="0", record_apply_no_change_count="0", record_apply_not_applicable_count="0",
            closure_edges_count="0", closure_edges_updated_count="0", closure_edges_no_change_count="0", closure_edges_gated_count="0"
        )
        errors = common.validate_task_outcome_row(row)
        self.assertTrue(any("non-zero workload guard" in e for e in errors))

    def test_enum_validation_invalid_task_type(self):
        row = _base_task_outcome_row(task_type="invalid_task_type")
        errors = common.validate_task_outcome_row(row)
        self.assertTrue(any("task_type" in e for e in errors))

    def test_enum_validation_invalid_runtime(self):
        row = _base_task_outcome_row(runtime="invalid_runtime")
        errors = common.validate_task_outcome_row(row)
        self.assertTrue(any("runtime" in e for e in errors))

    def test_enum_validation_invalid_status(self):
        row = _base_task_outcome_row(status="invalid_status")
        errors = common.validate_task_outcome_row(row)
        self.assertTrue(any("status" in e for e in errors))

    def test_dynamic_source_type_validation(self):
        row = _base_task_outcome_row(source_type="invalid_source_type_xyz")
        errors = common.validate_task_outcome_row(row)
        self.assertTrue(any("source_type" in e for e in errors))


class TestTaskOutcomeAppendAndDiffGuard(unittest.TestCase):
    def test_append_task_outcome_row_and_duplicate_rejection(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "task-outcomes.csv"
            with mock.patch.object(common, "TASK_OUTCOME_CSV_PATH", csv_path):
                common.append_task_outcome_row(_base_task_outcome_row(task_outcome_id="outcome-001"))
                header, rows = common.read_task_outcome_rows()
                self.assertEqual(header, common.TASK_OUTCOME_CSV_HEADER)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["task_outcome_id"], "outcome-001")

                with self.assertRaises(ValueError):
                    common.append_task_outcome_row(_base_task_outcome_row(task_outcome_id="outcome-001"))


def _real_shaped_review_result(entries: dict, **data_overrides) -> mock.MagicMock:
    """A cmd_review(...) return value shaped like the REAL CommandResult.data
    (qa_manage.py's cmd_review, read directly - see record_task_outcome.py's
    extract_from_run): no "lane"/"source_type" keys at all, and "entries" is
    {scope_key: {doc_name: [outcome, reason]}} - one level deeper than a flat
    {doc_name: [outcome, reason]} dict."""
    res = mock.MagicMock()
    res.ok = True
    res.data = {
        "run_id": "20260723-test-run-123",
        "source": "fake-source",
        "source_hash": "deadbeef",
        "status": "completed",
        "stage": "review",
        "scopes": [],
        "skills": [],
        "entries": entries,
        "outcomes": [],
        "unresolved_edges": [],
        "snapshot_sha": "abc123",
        "snapshot_problem": None,
        "invocation_present": True,
        "mirror_cleanliness": True,
        "ready_for_completion": True,
        "recommended_action": "complete",
    }
    res.data.update(data_overrides)
    return res


class TestExtractFromRunEntriesParsing(unittest.TestCase):
    """Regression tests for the nested-entries bug: real cmd_review output
    is {scope_key: {doc_name: [outcome, reason]}}, not a flat
    {doc_name: [outcome, reason]} dict - a flat-shaped fixture would have
    silently hidden this bug (the old test's mock used a flat shape and
    always passed while the real CLI produced all-zero counts)."""

    def test_nested_entries_are_counted_by_outcome(self):
        entries = {
            "ProjectA|": {
                "doc1": ["updated", "reason"],
                "doc2": ["updated", "reason"],
            },
            "ProjectB|PersonX": {
                "doc3": ["no_change", "reason"],
                "doc4": ["not_applicable", "reason"],
            },
        }
        with mock.patch("qa_manage.cmd_review", return_value=_real_shaped_review_result(entries)), \
             mock.patch("record_task_outcome._resolve_source_blob", return_value=("yes", "1000", "250")):
            extracted = record_tool.extract_from_run("20260723-test-run-123")
        self.assertEqual(extracted["record_apply_updated_count"], 2)
        self.assertEqual(extracted["record_apply_no_change_count"], 1)
        self.assertEqual(extracted["record_apply_not_applicable_count"], 1)

    def test_empty_entries_yields_zero_counts_not_an_error(self):
        with mock.patch("qa_manage.cmd_review", return_value=_real_shaped_review_result({})), \
             mock.patch("record_task_outcome._resolve_source_blob", return_value=("no", "", "")):
            extracted = record_tool.extract_from_run("20260723-test-run-123")
        self.assertEqual(extracted["record_apply_updated_count"], 0)
        self.assertEqual(extracted["record_apply_no_change_count"], 0)
        self.assertEqual(extracted["record_apply_not_applicable_count"], 0)

    def test_lane_and_source_type_are_always_blank(self):
        # cmd_review's real output has no "lane"/"source_type" key at all -
        # extract_from_run must not fabricate values for either, even if a
        # caller's mock happens to include those keys (a stale/incorrect
        # fixture should not silently pass).
        entries = {"ProjectA|": {"doc1": ["updated", "reason"]}}
        stale_result = _real_shaped_review_result(
            entries, lane="project_knowledge", source_type="project_knowledge_document",
        )
        with mock.patch("qa_manage.cmd_review", return_value=stale_result), \
             mock.patch("record_task_outcome._resolve_source_blob", return_value=("yes", "1000", "250")):
            extracted = record_tool.extract_from_run("20260723-test-run-123")
        self.assertEqual(extracted["lane"], "")
        self.assertEqual(extracted["source_type"], "")


class TestResolveSourceBlobManifestField(unittest.TestCase):
    """Regression test for the manifest field-name bug: the real
    _source_text_manifest.json entries key their blob location as
    "text_path" (see export_source_text.py), not "blob_path"."""

    def test_reads_text_path_field_from_manifest(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            mirror_root = Path(td) / "Documents" / "qa-drive-mirror"
            mirror_root.mkdir(parents=True)
            blob_rel = "_source_text/blobs/v1/fake.txt"
            (mirror_root / "_source_text").mkdir()
            (mirror_root / "_source_text" / "blobs").mkdir()
            (mirror_root / "_source_text" / "blobs" / "v1").mkdir()
            blob_text = "fake source text " * 10
            (mirror_root / blob_rel).write_text(blob_text, encoding="utf-8")
            manifest = {
                "20260723-test-run-123:v1": {
                    "text_path": blob_rel,
                    "source_path": "fake",
                    "queue_source_hash": "fake",
                    "source_sha256": "fake",
                    "text_sha256": "fake",
                    "extractor_profile": "fake",
                }
            }
            (mirror_root / "_source_text_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8",
            )

            with mock.patch.object(Path, "home", return_value=Path(td)):
                blob_present, chars, tokens = record_tool._resolve_source_blob("20260723-test-run-123")
        self.assertEqual(blob_present, "yes")
        self.assertEqual(chars, str(len(blob_text)))
        self.assertEqual(tokens, str(len(blob_text) // 4))


class TestRecordTaskOutcomeCLI(unittest.TestCase):
    def test_dry_run_output(self):
        entries = {"ProjectA|": {"doc1": ["updated", "reason"]}}
        with mock.patch("qa_manage.cmd_review", return_value=_real_shaped_review_result(entries)), \
             mock.patch("record_task_outcome._resolve_source_blob", return_value=("yes", "1000", "250")), \
             mock.patch("sys.argv", ["record_task_outcome.py", "--from-run", "20260723-test-run-123", "--dry-run"]):
            rc = record_tool.main()
            self.assertEqual(rc, 0)

    def test_missing_manifest_fallback_degrades_gracefully(self):
        blob_present, chars, tokens = record_tool._resolve_source_blob("nonexistent-run-id-999")
        self.assertEqual(blob_present, "no")
        self.assertEqual(chars, "")
        self.assertEqual(tokens, "")


if __name__ == "__main__":
    unittest.main()
