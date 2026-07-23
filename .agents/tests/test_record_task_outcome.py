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


class TestRecordTaskOutcomeCLI(unittest.TestCase):
    def test_dry_run_output(self):
        mock_review_res = mock.MagicMock()
        mock_review_res.ok = True
        mock_review_res.data = {
            "lane": "project_knowledge",
            "source_type": "project_knowledge_document",
            "status": "completed",
            "unresolved_edges": [],
            "entries": {"doc1": ["updated", "reason"]},
        }
        with mock.patch("qa_manage.cmd_review", return_value=mock_review_res), \
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
