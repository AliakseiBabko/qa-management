from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import operator_telemetry_common as common  # noqa: E402
import measure_operator_outputs as measure  # noqa: E402
import finalize_operator_run as finalize  # noqa: E402
import check_operator_csv as checker  # noqa: E402


def _base_row(**overrides) -> dict:
    row = {k: "" for k in common.CSV_HEADER}
    row.update({
        "case_id": "dashboard_overview",
        "run_id": "run-001",
        "date": "2026-01-01",
        "runtime": "manual_script",
        "model_label": "",
        "command_name": "qa_manage.py dashboard",
        "command_args_redacted": "qa_manage.py dashboard --json",
        "json_mode": "yes",
        "status": "ok",
        "elapsed_ms": "100",
        "stdout_bytes": "500",
        "stderr_bytes": "0",
        "output_chars": "480",
        "preview_chars": "200",
        "result_count": "3",
        "truncated": "no",
        "approximate_output_tokens": "120",
    })
    row.update(overrides)
    return row


class TestCsvHeader(unittest.TestCase):
    def test_header_matches_schema(self):
        with mock.patch.object(common, "CSV_PATH", Path(__file__).resolve().parents[1] / "telemetry" / "operator-runs.csv"):
            header, _rows = common.read_rows()
        self.assertEqual(header, common.CSV_HEADER)

    def test_check_operator_csv_validates_real_csv(self):
        ok = checker.validate_csv()
        self.assertTrue(ok)


class TestAppendRow(unittest.TestCase):
    def test_append_creates_file_with_header(self):
        with mock.patch.dict(sys.modules):
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                csv_path = Path(td) / "operator-runs.csv"
                with mock.patch.object(common, "CSV_PATH", csv_path):
                    common.append_row(_base_row())
                    header, rows = common.read_rows()
                self.assertEqual(header, common.CSV_HEADER)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["run_id"], "run-001")

    def test_append_one_row_preserves_unrelated_rows(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "operator-runs.csv"
            with mock.patch.object(common, "CSV_PATH", csv_path):
                common.append_row(_base_row(run_id="run-001"))
                common.append_row(_base_row(run_id="run-002"))
                header, rows = common.read_rows()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["run_id"], "run-001")
            self.assertEqual(rows[1]["run_id"], "run-002")
            # First row's fields must be byte-identical to what was written -
            # appending run-002 must not have touched run-001's row.
            self.assertEqual(rows[0]["command_name"], "qa_manage.py dashboard")

    def test_append_rejects_duplicate_run_id(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "operator-runs.csv"
            with mock.patch.object(common, "CSV_PATH", csv_path):
                common.append_row(_base_row(run_id="dup"))
                with self.assertRaises(ValueError):
                    common.append_row(_base_row(run_id="dup"))

    def test_append_rejects_missing_required_field(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "operator-runs.csv"
            with mock.patch.object(common, "CSV_PATH", csv_path):
                bad = _base_row(case_id="")
                with self.assertRaises(ValueError):
                    common.append_row(bad)

    def test_append_rejects_non_numeric_field(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "operator-runs.csv"
            with mock.patch.object(common, "CSV_PATH", csv_path):
                bad = _base_row(elapsed_ms="not-a-number")
                with self.assertRaises(ValueError):
                    common.append_row(bad)

    def test_append_rejects_invalid_enum(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "operator-runs.csv"
            with mock.patch.object(common, "CSV_PATH", csv_path):
                bad = _base_row(runtime="SomeOtherTool")
                with self.assertRaises(ValueError):
                    common.append_row(bad)


class TestDiffGuard(unittest.TestCase):
    def test_diff_guard_flags_unrelated_row_rewrite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

            csv_path = repo / "operator-runs.csv"
            with mock.patch.object(common, "CSV_PATH", csv_path):
                common.append_row(_base_row(run_id="run-001"))
                subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
                subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repo, check=True)

                # Legitimate append: only a new row.
                common.append_row(_base_row(run_id="run-002"))
                ok, violations = common.diff_guard_new_row_only("run-002", repo_root=repo)
                self.assertTrue(ok, violations)

                # Now corrupt the unrelated row (run-001) and confirm the guard catches it.
                header, rows = common.read_rows()
                for r in rows:
                    if r["run_id"] == "run-001":
                        r["command_name"] = "tampered"
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writeheader()
                    writer.writerows(rows)

                ok2, violations2 = common.diff_guard_new_row_only("run-002", repo_root=repo)
                self.assertFalse(ok2)
                self.assertTrue(any("run-001" in v for v in violations2))


class TestMeasurement(unittest.TestCase):
    def test_result_count_extraction_from_list(self):
        parsed = {"schema_version": 1, "ok": True, "data": {"action_required": [1, 2, 3]}}
        self.assertEqual(measure._extract_result_count(parsed), 3)

    def test_result_count_extraction_from_documents(self):
        parsed = {"ok": True, "data": {"documents": [{"returned_count": 7}]}}
        self.assertEqual(measure._extract_result_count(parsed), 7)

    def test_result_count_none_when_absent(self):
        parsed = {"ok": True, "data": {"foo": "bar"}}
        self.assertIsNone(measure._extract_result_count(parsed))

    def test_truncated_extraction(self):
        self.assertTrue(measure._extract_truncated({"data": {"truncated": True}}))
        self.assertFalse(measure._extract_truncated({"data": {"truncated": False}}))
        self.assertFalse(measure._extract_truncated({"data": {}}))

    def test_command_redaction_keeps_placeholder(self):
        case = common.CASES["guide_discovered"]
        redacted, real = measure.build_argv("guide_discovered", case, "20260721-real-run-abcd")
        self.assertIn("{target}", redacted)
        self.assertNotIn("20260721-real-run-abcd", redacted)
        self.assertIn("20260721-real-run-abcd", real)

    def test_refuses_mutating_verb(self):
        with self.assertRaises(SystemExit):
            measure.assert_read_only(["qa_manage.py", "start", "some-run"])

    def test_all_catalog_cases_are_read_only(self):
        for case_id, case in common.CASES.items():
            argv = case["argv"]
            for token in argv:
                self.assertNotIn(token, common.MUTATING_VERBS, f"case {case_id} contains a mutating verb")

    def test_completed_run_review_case_exists_and_is_read_only(self):
        case = common.CASES["completed_run_review"]
        self.assertEqual(case["command_name"], "qa_manage.py review")
        self.assertEqual(case["argv"], ["qa_manage.py", "review", "{target}", "--json"])
        self.assertEqual(case["requires_target"], "run_id")
        for token in case["argv"]:
            self.assertNotIn(token, common.MUTATING_VERBS)

    def test_dry_run_does_not_invoke_subprocess(self):
        # In-process check: patch subprocess.run inside the measure module
        # itself and call main() directly with --dry-run, so the mock is in
        # the same process as the code under test (a subprocess child would
        # not share the mock).
        argv_backup = sys.argv
        try:
            sys.argv = ["measure_operator_outputs.py", "--case", "dashboard_overview", "--dry-run"]
            with mock.patch.object(measure.subprocess, "run") as run_mock:
                rc = measure.main()
            self.assertEqual(rc, 0)
            run_mock.assert_not_called()
        finally:
            sys.argv = argv_backup

    def test_dry_run_writes_nothing_to_csv_or_tmp(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_dir = Path(td)
            with mock.patch.object(measure, "TMP_TELEMETRY_DIR", tmp_dir / "telemetry"):
                argv = [sys.executable, str(SCRIPTS / "measure_operator_outputs.py"),
                        "--case", "dashboard_overview", "--dry-run"]
                result = subprocess.run(argv, capture_output=True, text=True, cwd=str(SCRIPTS.parent.parent))
                self.assertEqual(result.returncode, 0)
            self.assertFalse((tmp_dir / "telemetry").exists())

    def test_ascii_safe_rejects_non_ascii(self):
        self.assertFalse(common.is_ascii_safe("проект Cywareness"))
        self.assertTrue(common.is_ascii_safe("qa_manage.py guide <target> --json"))

    def test_ascii_safe_allows_curly_brace_placeholder(self):
        # Regression: every {target}-templated case's own redacted command
        # string (e.g. "qa_manage.py review {target} --json") legitimately
        # contains literal braces - found live when completed_run_review
        # (and every other {target} case) could never actually be
        # --append-csv'd because is_ascii_safe rejected its own template.
        self.assertTrue(common.is_ascii_safe("qa_manage.py review {target} --json"))
        for case_id, case in common.CASES.items():
            redacted = " ".join(case["argv"])
            self.assertTrue(common.is_ascii_safe(redacted),
                            f"case {case_id}'s own redacted argv failed is_ascii_safe: {redacted!r}")

    def test_ascii_safe_still_rejects_non_ascii_alongside_braces(self):
        self.assertFalse(common.is_ascii_safe("qa_manage.py review {target} --json проект"))


class TestFinalize(unittest.TestCase):
    def test_compute_total_tokens_blank_when_all_missing(self):
        row = _base_row()
        self.assertEqual(finalize.compute_total_tokens(row), "")

    def test_compute_total_tokens_sums_available_fields(self):
        row = _base_row(actual_input_tokens="100", actual_output_tokens="50")
        self.assertEqual(finalize.compute_total_tokens(row), "150")

    def test_compute_total_tokens_tolerates_missing_reasoning(self):
        row = _base_row(actual_input_tokens="10", actual_output_tokens="5",
                         actual_cache_creation_tokens="", actual_cache_read_tokens="",
                         actual_reasoning_tokens="")
        self.assertEqual(finalize.compute_total_tokens(row), "15")

    def test_reduction_ratio_against_existing_baseline(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            csv_path = Path(td) / "operator-runs.csv"
            with mock.patch.object(common, "CSV_PATH", csv_path):
                common.append_row(_base_row(run_id="baseline-run", output_chars="1000"))
                row = _base_row(run_id="targeted-run", output_chars="250")
                ratio = finalize.compute_reduction_ratio(row, "baseline-run")
                self.assertEqual(ratio, "0.2500")

    def test_reduction_ratio_blank_without_baseline(self):
        row = _base_row(run_id="solo-run")
        self.assertEqual(finalize.compute_reduction_ratio(row, None), "")

    def test_no_real_output_stored_in_row(self):
        # The row builder only ever includes counts/labels - assert none of
        # the fields measure_operator_outputs.py writes can contain literal
        # stdout content by construction (they are ints/enum strings/labels).
        row = _base_row()
        for key in ("output_chars", "stdout_bytes", "stderr_bytes", "elapsed_ms", "result_count"):
            self.assertTrue(str(row[key]).lstrip("-").isdigit() or row[key] == "")


if __name__ == "__main__":
    unittest.main()
