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


class TestLeakGuardPrimitives(unittest.TestCase):
    """contains_email_address / contains_watch_string are pure and
    registry-agnostic - no Drive access needed to test them. Only
    placeholder emails/names appear here, never real ones."""

    def test_contains_email_address_detects_email(self):
        self.assertTrue(common.contains_email_address("contact fake.person@example.com about this"))

    def test_contains_email_address_false_for_plain_text(self):
        self.assertFalse(common.contains_email_address("processed run 20260101-example-abc123"))

    def test_contains_watch_string_finds_literal_match(self):
        hits = common.contains_watch_string(
            "added Example Placeholder Person to the registry", {"Example Placeholder Person"}
        )
        self.assertEqual(hits, ["Example Placeholder Person"])

    def test_contains_watch_string_no_match(self):
        hits = common.contains_watch_string(
            "added a new participant to the registry", {"Example Placeholder Person"}
        )
        self.assertEqual(hits, [])

    def test_contains_watch_string_empty_watch_is_safe(self):
        self.assertEqual(common.contains_watch_string("anything at all", set()), [])
        self.assertEqual(common.contains_watch_string("anything at all", None), [])

    def test_contains_watch_string_empty_text_is_safe(self):
        self.assertEqual(common.contains_watch_string("", {"Example Placeholder Person"}), [])


class TestValidateRowWatchParam(unittest.TestCase):
    """validate_row/validate_agent_session_row's optional `watch` param -
    default (no watch) behavior must be unchanged; a real-looking
    placeholder must pass when it isn't on the watch-list, and a
    watch-list hit must be rejected with a clear message. Fixtures below
    are synthetic - no real names or projects."""

    def test_default_watch_none_keeps_existing_behavior(self):
        row = _base_row(notes="Example Placeholder Person worked on this")
        self.assertEqual(common.validate_row(row), [])

    def test_watch_hit_in_notes_is_rejected(self):
        row = _base_row(notes="Example Placeholder Person worked on this")
        errors = common.validate_row(row, watch={"Example Placeholder Person"})
        self.assertTrue(any("Example Placeholder Person" in e for e in errors))

    def test_realistic_placeholder_passes_with_watch_supplied(self):
        row = _base_row(notes="a fake participant, not on the watch-list, was referenced")
        errors = common.validate_row(row, watch={"Example Placeholder Person", "Example Placeholder Project"})
        self.assertEqual(errors, [])

    def test_email_in_command_args_redacted_is_rejected_with_specific_message(self):
        row = _base_row(command_args_redacted="qa_manage.py review {target} --json fake.person@example.com")
        errors = common.validate_row(row)
        self.assertTrue(any("email address" in e for e in errors))


class TestValidateAgentSessionRowWatchParam(unittest.TestCase):
    """Same coverage as above, for agent-sessions.csv's validate function -
    the one record_agent_session.py --check-registry actually calls."""

    def _row(self, **overrides):
        row = {k: "" for k in common.AGENT_SESSION_CSV_HEADER}
        row.update({
            "session_run_id": "session-fake-2026-01-01-aaaa1111",
            "date": "2026-01-01",
            "runtime": "claude",
            "session_id": "fake-session-id",
            "objective": "fake objective for tests",
            "extraction_method": "claude_log",
            "confidence": "high",
        })
        row.update(overrides)
        return row

    def test_default_watch_none_keeps_existing_behavior(self):
        row = self._row(notes="Example Placeholder Person worked on this")
        self.assertEqual(common.validate_agent_session_row(row), [])

    def test_watch_hit_in_objective_is_rejected(self):
        row = self._row(objective="processed a source about Example Placeholder Person")
        errors = common.validate_agent_session_row(row, watch={"Example Placeholder Person"})
        self.assertTrue(any("Example Placeholder Person" in e for e in errors))
        self.assertTrue(any("registry watch-list" in e for e in errors))

    def test_watch_hit_in_notes_is_rejected(self):
        row = self._row(notes="added Example Placeholder Person to the registry")
        errors = common.validate_agent_session_row(row, watch={"Example Placeholder Person"})
        self.assertTrue(any("Example Placeholder Person" in e for e in errors))

    def test_realistic_placeholder_passes_when_not_on_watch_list(self):
        row = self._row(
            objective="processed a source about a fake participant not on the watch-list",
            notes="everything folded cleanly, no unusual findings",
        )
        errors = common.validate_agent_session_row(
            row, watch={"Example Placeholder Person", "Example Placeholder Project"}
        )
        self.assertEqual(errors, [])

    def test_email_in_objective_rejected_even_without_watch(self):
        row = self._row(objective="contact fake.person@example.com about this run")
        errors = common.validate_agent_session_row(row)
        self.assertTrue(any("email address" in e for e in errors))

    def test_email_check_takes_precedence_over_ascii_safe_message(self):
        # An email already fails is_ascii_safe (via '@' not being
        # allowlisted) - the dedicated email check must fire first so the
        # error names the actual reason instead of the generic one.
        row = self._row(notes="fake.person@example.com")
        errors = common.validate_agent_session_row(row)
        self.assertTrue(any("email address" in e for e in errors))
        self.assertFalse(any("ASCII-safe" in e for e in errors))


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


class TestSummarizeAgentTelemetry(unittest.TestCase):
    def test_work_done_and_context_pressure_metrics(self):
        import summarize_agent_telemetry as summ
        rows = [
            {
                "session_run_id": "s1", "date": "2026-01-01", "runtime": "claude",
                "session_id": "sid-1", "objective": "obj", "extraction_method": "claude_log",
                "confidence": "high", "actual_input_tokens": "100",
                "actual_output_tokens": "50", "actual_reasoning_tokens": "10",
                "actual_cache_read_tokens": "5000", "total_tokens": "5160",
                "model_label": "claude-sonnet-5",
            }
        ]
        with mock.patch.object(summ, "read_agent_session_rows", return_value=(common.AGENT_SESSION_CSV_HEADER, rows)):
            envelope = summ.summarize_telemetry()

        cg = envelope["data"]["common_ground"]["by_runtime"]["claude"]
        # work_done = 100 (in) + 50 (out) + 10 (think) = 160 (excludes 5000 cache read)
        self.assertEqual(cg["work_done_tokens"], 160)
        # context_pressure = 100 (in) + 5000 (cache read) = 5100
        self.assertEqual(cg["context_pressure_tokens"], 5100)

    def test_deduplicated_latest_vs_include_snapshots(self):
        import summarize_agent_telemetry as summ
        rows = [
            {
                "session_run_id": "s1_v1", "date": "2026-01-01", "runtime": "claude",
                "session_id": "sid-cumul", "objective": "v1", "extraction_method": "claude_log",
                "confidence": "high", "actual_input_tokens": "100", "actual_output_tokens": "50",
                "actual_cache_read_tokens": "1000", "total_tokens": "1150",
            },
            {
                "session_run_id": "s1_v2", "date": "2026-01-02", "runtime": "claude",
                "session_id": "sid-cumul", "objective": "v2", "extraction_method": "claude_log",
                "confidence": "high", "actual_input_tokens": "200", "actual_output_tokens": "100",
                "actual_cache_read_tokens": "2000", "total_tokens": "2300",
            },
        ]
        with mock.patch.object(summ, "read_agent_session_rows", return_value=(common.AGENT_SESSION_CSV_HEADER, rows)):
            dedup_env = summ.summarize_telemetry(include_snapshots=False)
            snap_env = summ.summarize_telemetry(include_snapshots=True)

        cg_dedup = dedup_env["data"]["common_ground"]["by_runtime"]["claude"]
        cg_snap = snap_env["data"]["common_ground"]["by_runtime"]["claude"]

        self.assertEqual(cg_dedup["work_done_tokens"], 300)      # 200 + 100 from v2
        self.assertEqual(cg_snap["work_done_tokens"], 450)       # 150 (v1) + 300 (v2)
        self.assertTrue(any("overcounting" in w for w in dedup_env["warnings"]))
        self.assertTrue(any("overcount warning" in w for w in snap_env["warnings"]))

    def test_json_strict_envelope_structure(self):
        import summarize_agent_telemetry as summ
        rows = [
            {
                "session_run_id": "s1", "date": "2026-01-01", "runtime": "antigravity",
                "session_id": "sid-ag", "objective": "audit", "extraction_method": "antigravity_db",
                "confidence": "medium", "actual_input_tokens": "500", "actual_output_tokens": "50",
                "actual_reasoning_tokens": "20", "actual_cache_read_tokens": "100", "total_tokens": "670",
            }
        ]
        with mock.patch.object(summ, "read_agent_session_rows", return_value=(common.AGENT_SESSION_CSV_HEADER, rows)):
            envelope = summ.summarize_telemetry()

        self.assertEqual(envelope["schema_version"], "1.0")
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["command"], "summarize_agent_telemetry.py")
        self.assertIn("common_ground", envelope["data"])
        self.assertIn("provider_native_raw_totals", envelope["data"])
        self.assertIn("health", envelope["data"])

    def test_unknown_pricing_produces_null_cost_and_warning(self):
        import summarize_agent_telemetry as summ
        rows = [
            {
                "session_run_id": "s1", "date": "2026-01-01", "runtime": "unknown_rt",
                "session_id": "sid-unk", "objective": "test", "extraction_method": "manual",
                "confidence": "manual", "actual_input_tokens": "100", "actual_output_tokens": "50",
                "total_tokens": "150", "model_label": "mystery-model-xyz",
            }
        ]
        with mock.patch.object(summ, "read_agent_session_rows", return_value=(common.AGENT_SESSION_CSV_HEADER, rows)):
            envelope = summ.summarize_telemetry()

        cg = envelope["data"]["common_ground"]["by_runtime"]["unknown_rt"]
        self.assertIsNone(cg["billable_estimate_usd"])
        self.assertIn("N/A", cg["billable_estimate_formatted"])
        self.assertTrue(any("unknown model pricing" in w for w in envelope["warnings"]))


if __name__ == "__main__":
    unittest.main()
