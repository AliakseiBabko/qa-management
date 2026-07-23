"""Unit tests for the session-level telemetry path added alongside
operator-runs.csv:

- operator_telemetry_common.py's agent-sessions.csv schema/helpers
  (read/validate/append/diff-guard, generalized from the operator-runs.csv
  originals without changing their behavior)
- record_agent_session.py's row-building/CLI behavior: automatic
  extraction (mocked adapters), manual entry, confidence defaulting,
  cost/total computation, unknown-linked-run-id warnings, and the hard
  guarantee that operator-runs.csv is never touched by this path.

No real names/projects, no real session logs in any fixture here.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import operator_telemetry_common as common  # noqa: E402
import record_agent_session as record  # noqa: E402
import extract_agent_telemetry as ext  # noqa: E402


def _base_session_row(**overrides) -> dict:
    row = {k: "" for k in common.AGENT_SESSION_CSV_HEADER}
    row.update({
        "session_run_id": "session-claude-2026-01-01-aaaa1111",
        "date": "2026-01-01",
        "runtime": "claude",
        "session_id": "fake-session-id",
        "objective": "fake objective for tests",
        "extraction_method": "claude_log",
        "confidence": "high",
    })
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# operator_telemetry_common.py - agent-sessions.csv schema/helpers
# ---------------------------------------------------------------------------

class AgentSessionCsvHeaderTests(unittest.TestCase):
    def test_header_has_expected_columns_in_order(self):
        self.assertEqual(common.AGENT_SESSION_CSV_HEADER, [
            "session_run_id", "date", "runtime", "model_label", "session_id",
            "linked_operator_run_ids", "objective", "started_at", "ended_at",
            "elapsed_min", "actual_input_tokens", "actual_cache_creation_tokens",
            "actual_cache_read_tokens", "actual_output_tokens", "actual_reasoning_tokens",
            "total_tokens", "estimated_cost_usd", "extraction_method", "confidence", "notes",
        ])

    def test_validate_rejects_missing_required_field(self):
        row = _base_session_row(objective="")
        errors = common.validate_agent_session_row(row)
        self.assertTrue(any("objective" in e for e in errors))

    def test_validate_rejects_invalid_extraction_method(self):
        row = _base_session_row(extraction_method="not_a_real_method")
        errors = common.validate_agent_session_row(row)
        self.assertTrue(any("extraction_method" in e for e in errors))

    def test_validate_rejects_invalid_confidence(self):
        row = _base_session_row(confidence="super-sure")
        errors = common.validate_agent_session_row(row)
        self.assertTrue(any("confidence" in e for e in errors))

    def test_validate_accepts_manual_confidence(self):
        row = _base_session_row(extraction_method="manual", confidence="manual")
        self.assertEqual(common.validate_agent_session_row(row), [])

    def test_validate_accepts_legacy_claude_code_runtime(self):
        row = _base_session_row(runtime="claude-code")
        self.assertEqual(common.validate_agent_session_row(row), [])

    def test_validate_rejects_unknown_runtime(self):
        row = _base_session_row(runtime="some-agent")
        errors = common.validate_agent_session_row(row)
        self.assertTrue(any("runtime" in e for e in errors))

    def test_validate_rejects_non_ascii_objective(self):
        row = _base_session_row(objective="проект PKF")
        errors = common.validate_agent_session_row(row)
        self.assertTrue(any("objective" in e for e in errors))


class AgentSessionAppendTests(unittest.TestCase):
    def test_append_creates_file_with_header(self):
        with TemporaryDirectory() as td:
            csv_path = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", csv_path):
                common.append_agent_session_row(_base_session_row())
                header, rows = common.read_agent_session_rows()
            self.assertEqual(header, common.AGENT_SESSION_CSV_HEADER)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["session_run_id"], "session-claude-2026-01-01-aaaa1111")

    def test_append_rejects_duplicate_session_run_id(self):
        with TemporaryDirectory() as td:
            csv_path = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", csv_path):
                common.append_agent_session_row(_base_session_row())
                with self.assertRaises(ValueError):
                    common.append_agent_session_row(_base_session_row())

    def test_append_preserves_unrelated_rows(self):
        with TemporaryDirectory() as td:
            csv_path = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", csv_path):
                common.append_agent_session_row(_base_session_row(session_run_id="s1"))
                common.append_agent_session_row(_base_session_row(session_run_id="s2"))
                header, rows = common.read_agent_session_rows()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["session_run_id"], "s1")
            self.assertEqual(rows[1]["session_run_id"], "s2")

    def test_diff_guard_flags_unrelated_row_rewrite(self):
        with TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

            csv_path = repo / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", csv_path):
                common.append_agent_session_row(_base_session_row(session_run_id="s1"))
                subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
                subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repo, check=True)

                common.append_agent_session_row(_base_session_row(session_run_id="s2"))
                ok, violations = common.diff_guard_agent_session_new_row_only("s2", repo_root=repo)
                self.assertTrue(ok, violations)

                header, rows = common.read_agent_session_rows()
                for r in rows:
                    if r["session_run_id"] == "s1":
                        r["objective"] = "tampered"
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writeheader()
                    writer.writerows(rows)

                ok2, violations2 = common.diff_guard_agent_session_new_row_only("s2", repo_root=repo)
                self.assertFalse(ok2)
                self.assertTrue(any("s1" in v for v in violations2))


class OperatorRunsUntouchedTests(unittest.TestCase):
    """The hard guarantee: nothing in the agent-sessions.csv path ever
    reads-and-rewrites operator-runs.csv."""

    def test_appending_a_session_row_does_not_touch_operator_runs_csv(self):
        with TemporaryDirectory() as td:
            operator_csv = Path(td) / "operator-runs.csv"
            session_csv = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "CSV_PATH", operator_csv), \
                 mock.patch.object(common, "AGENT_SESSION_CSV_PATH", session_csv):
                # Seed an operator-runs.csv row first.
                op_row = {k: "" for k in common.CSV_HEADER}
                op_row.update({
                    "case_id": "dashboard_overview", "run_id": "op-run-1", "date": "2026-01-01",
                    "runtime": "manual_script", "command_name": "qa_manage.py dashboard",
                    "command_args_redacted": "qa_manage.py dashboard --json", "json_mode": "yes",
                    "status": "ok", "elapsed_ms": "10", "stdout_bytes": "1", "stderr_bytes": "0",
                    "output_chars": "1", "truncated": "no",
                })
                common.append_row(op_row)
                before = operator_csv.read_bytes()

                common.append_agent_session_row(_base_session_row())

                after = operator_csv.read_bytes()
                self.assertEqual(before, after, "operator-runs.csv bytes must be unchanged")


# ---------------------------------------------------------------------------
# record_agent_session.py - row building
# ---------------------------------------------------------------------------

class Args:
    """Minimal stand-in for argparse.Namespace, defaults matching parser."""
    def __init__(self, **overrides):
        defaults = dict(
            runtime="claude", session_id="fake-session", session_run_id=None, date=None,
            model_label=None, objective="fake objective", linked_operator_run_ids=[],
            started_at=None, ended_at=None, elapsed_min=None, manual=False,
            actual_input_tokens=None, actual_cache_creation_tokens=None,
            actual_cache_read_tokens=None, actual_output_tokens=None, actual_reasoning_tokens=None,
            estimated_cost_usd=None, extraction_method=None, confidence=None, notes=None,
        )
        defaults.update(overrides)
        for k, v in defaults.items():
            setattr(self, k, v)


class BuildRowExtractionTests(unittest.TestCase):
    def test_claude_extraction_maps_into_session_row(self):
        fake_totals = {
            "actual_input_tokens": 100, "actual_output_tokens": 20,
            "actual_cache_creation_tokens": 5, "actual_cache_read_tokens": 2,
            "actual_reasoning_tokens": 0, "model_label": "claude-sonnet-5",
            "extraction_method": "claude_log",
            "session_started_at": "2026-01-01T00:00:00.000Z",
            "session_ended_at": "2026-01-01T00:10:00.000Z",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, warnings = record.build_row(Args(runtime="claude"))
        self.assertEqual(row["actual_input_tokens"], 100)
        self.assertEqual(row["actual_output_tokens"], 20)
        self.assertEqual(row["model_label"], "claude-sonnet-5")
        self.assertEqual(row["extraction_method"], "claude_log")
        self.assertEqual(row["confidence"], "high")
        self.assertEqual(row["total_tokens"], "127")
        self.assertEqual(row["elapsed_min"], "10.00")
        self.assertEqual(warnings, [])

    def test_codex_extraction_maps_into_session_row(self):
        fake_totals = {
            "actual_input_tokens": 1000, "actual_output_tokens": 200,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 300,
            "actual_reasoning_tokens": 50, "extraction_method": "codex_log",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, _ = record.build_row(Args(runtime="codex"))
        self.assertEqual(row["extraction_method"], "codex_log")
        self.assertEqual(row["confidence"], "high")
        self.assertEqual(row["total_tokens"], "1550")

    def test_antigravity_db_fallback_gets_medium_confidence(self):
        fake_totals = {
            "actual_input_tokens": 500, "actual_output_tokens": 100,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 50,
            "actual_reasoning_tokens": 10, "extraction_method": "antigravity_db",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, _ = record.build_row(Args(runtime="antigravity"))
        self.assertEqual(row["confidence"], "medium")

    def test_antigravity_cli_gets_high_confidence(self):
        fake_totals = {
            "actual_input_tokens": 500, "actual_output_tokens": 100,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 50,
            "actual_reasoning_tokens": 10, "extraction_method": "antigravity_cli",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, _ = record.build_row(Args(runtime="antigravity"))
        self.assertEqual(row["confidence"], "high")

    def test_extraction_failure_without_manual_raises_with_guidance(self):
        with mock.patch.object(ext, "extract", side_effect=RuntimeError("no agy CLI, no db")):
            with self.assertRaises(RuntimeError) as ctx:
                record.build_row(Args(runtime="antigravity"))
        self.assertIn("--manual", str(ctx.exception))

    def test_manual_path_skips_extraction_entirely(self):
        with mock.patch.object(ext, "extract", side_effect=AssertionError("must not be called")):
            row, _ = record.build_row(Args(
                manual=True, actual_input_tokens=10, actual_output_tokens=5,
                confidence="manual",
            ))
        self.assertEqual(row["actual_input_tokens"], 10)
        self.assertEqual(row["extraction_method"], "manual")
        self.assertEqual(row["confidence"], "manual")
        self.assertEqual(row["total_tokens"], "15")

    def test_manual_path_requires_at_least_one_actual_token_value(self):
        with self.assertRaises(ValueError) as ctx:
            record.build_row(Args(manual=True, confidence="manual"))
        self.assertIn("--manual requires at least one --actual-*-tokens", str(ctx.exception))

    def test_claude_code_alias_is_persisted_as_claude(self):
        fake_totals = {
            "actual_input_tokens": 100, "actual_output_tokens": 20,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 0,
            "actual_reasoning_tokens": 0, "extraction_method": "claude_log",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, _ = record.build_row(Args(runtime="claude-code"))
        self.assertEqual(row["runtime"], "claude")
        self.assertTrue(row["session_run_id"].startswith("session-claude-"))

    def test_claudecode_no_hyphen_alias_is_also_persisted_as_claude(self):
        # Regression: extract_agent_telemetry.ADAPTERS and this script's own
        # --runtime argparse choices both accept the no-hyphen "claudecode"
        # spelling, but canonical_runtime()'s alias map only listed
        # "claude-code" - a row built with --runtime claudecode would persist
        # runtime="claudecode" unnormalized and then fail
        # validate_agent_session_row's runtime check on write.
        fake_totals = {
            "actual_input_tokens": 100, "actual_output_tokens": 20,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 0,
            "actual_reasoning_tokens": 0, "extraction_method": "claude_log",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, _ = record.build_row(Args(runtime="claudecode"))
        self.assertEqual(row["runtime"], "claude")
        self.assertEqual(common.validate_agent_session_row(row), [])

    def test_cost_computed_from_pricing_table_when_model_known(self):
        fake_totals = {
            "actual_input_tokens": 1_000_000, "actual_output_tokens": 1_000_000,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 0,
            "actual_reasoning_tokens": 0, "model_label": "claude-sonnet-5",
            "extraction_method": "claude_log",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, _ = record.build_row(Args(runtime="claude"))
        # 1M input @ $3/1M + 1M output @ $15/1M = $18.00
        self.assertEqual(row["estimated_cost_usd"], "18.000000")

    def test_reported_cost_used_verbatim_not_recomputed(self):
        fake_totals = {
            "actual_input_tokens": 1_000_000, "actual_output_tokens": 1_000_000,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 0,
            "actual_reasoning_tokens": 0, "model_label": "claude-sonnet-5",
            "extraction_method": "cline_history", "estimated_cost_usd": "0.010000",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, _ = record.build_row(Args(runtime="cline"))
        self.assertEqual(row["estimated_cost_usd"], "0.010000")

    def test_unknown_model_label_yields_blank_cost(self):
        fake_totals = {
            "actual_input_tokens": 100, "actual_output_tokens": 10,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 0,
            "actual_reasoning_tokens": 0, "model_label": "some-unknown-model",
            "extraction_method": "claude_log",
        }
        with mock.patch.object(ext, "extract", return_value=fake_totals):
            row, _ = record.build_row(Args(runtime="claude"))
        self.assertEqual(row.get("estimated_cost_usd", ""), "")


class LoadRegistryWatchlistTests(unittest.TestCase):
    """load_registry_watchlist() is best-effort: any failure (missing
    credentials, no Drive access, import error) degrades to an empty
    watch-list plus a warning, never an exception - the whole point is
    that this script must not hard-depend on Drive being reachable."""

    def test_success_path_returns_loaded_watch_and_no_warnings(self):
        fake_module = mock.MagicMock()
        fake_module.load_watch_strings.return_value = {"Example Placeholder Person"}
        with mock.patch.dict(sys.modules, {"check_sensitive_data": fake_module}), \
             mock.patch("pipeline_common.get_services", return_value={"drive": mock.MagicMock()}, create=True):
            watch, warnings = record.load_registry_watchlist()
        self.assertEqual(watch, {"Example Placeholder Person"})
        self.assertEqual(warnings, [])

    def test_failure_degrades_to_empty_watch_with_warning(self):
        with mock.patch.dict(sys.modules, {"check_sensitive_data": None}):
            watch, warnings = record.load_registry_watchlist()
        self.assertEqual(watch, set())
        self.assertEqual(len(warnings), 1)
        self.assertIn("Could not load", warnings[0])


class LinkedRunIdWarningTests(unittest.TestCase):
    def test_unknown_linked_run_id_warns_but_does_not_raise(self):
        with TemporaryDirectory() as td:
            operator_csv = Path(td) / "operator-runs.csv"
            with mock.patch.object(common, "CSV_PATH", operator_csv):
                op_row = {k: "" for k in common.CSV_HEADER}
                op_row.update({
                    "case_id": "dashboard_overview", "run_id": "real-run-1", "date": "2026-01-01",
                    "runtime": "manual_script", "command_name": "qa_manage.py dashboard",
                    "command_args_redacted": "qa_manage.py dashboard --json", "json_mode": "yes",
                    "status": "ok", "elapsed_ms": "10", "stdout_bytes": "1", "stderr_bytes": "0",
                    "output_chars": "1", "truncated": "no",
                })
                common.append_row(op_row)

                fake_totals = {
                    "actual_input_tokens": 10, "actual_output_tokens": 5,
                    "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 0,
                    "actual_reasoning_tokens": 0, "extraction_method": "claude_log",
                }
                with mock.patch.object(ext, "extract", return_value=fake_totals):
                    row, warnings = record.build_row(Args(
                        runtime="claude",
                        linked_operator_run_ids=["real-run-1", "totally-made-up-id"],
                    ))
        self.assertEqual(row["linked_operator_run_ids"], "real-run-1,totally-made-up-id")
        self.assertTrue(any("totally-made-up-id" in w for w in warnings))
        self.assertFalse(any("real-run-1" in w for w in warnings))


# ---------------------------------------------------------------------------
# CLI-level: dry-run, --append-csv, no raw log leakage
# ---------------------------------------------------------------------------

class CliTests(unittest.TestCase):
    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        argv_backup = sys.argv
        try:
            sys.argv = ["record_agent_session.py"] + argv
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = record.main()
        finally:
            sys.argv = argv_backup
        return rc, buf.getvalue()

    def test_dry_run_manual_prints_row_and_writes_nothing(self):
        with TemporaryDirectory() as td:
            session_csv = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", session_csv):
                rc, out = self._run_cli([
                    "--runtime", "manual", "--session-id", "fake", "--manual",
                    "--actual-input-tokens", "10", "--actual-output-tokens", "5",
                    "--confidence", "manual", "--objective", "smoke test", "--dry-run",
                ])
            self.assertEqual(rc, 0)
            self.assertIn("[dry-run] nothing written.", out)
            self.assertFalse(session_csv.exists())

    def test_append_csv_writes_one_row(self):
        with TemporaryDirectory() as td:
            session_csv = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", session_csv):
                rc, out = self._run_cli([
                    "--runtime", "manual", "--session-id", "fake", "--manual",
                    "--actual-input-tokens", "10", "--actual-output-tokens", "5",
                    "--confidence", "manual", "--objective", "smoke test", "--append-csv",
                ])
                self.assertEqual(rc, 0)
                _, rows = common.read_agent_session_rows()
            self.assertEqual(len(rows), 1)

    def test_neither_append_nor_dry_run_is_a_parser_error(self):
        res = subprocess.run(
            [sys.executable, str(SCRIPTS / "record_agent_session.py"),
             "--runtime", "manual", "--session-id", "fake", "--manual",
             "--objective", "x"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("--append-csv", res.stderr + res.stdout)

    def test_out_only_contains_known_schema_keys_no_raw_content(self):
        with TemporaryDirectory() as td:
            session_csv = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", session_csv):
                rc, _ = self._run_cli([
                    "--runtime", "manual", "--session-id", "fake", "--manual",
                    "--actual-input-tokens", "10", "--actual-output-tokens", "5",
                    "--confidence", "manual", "--objective", "smoke test", "--append-csv",
                ])
                self.assertEqual(rc, 0)
                header, rows = common.read_agent_session_rows()
            self.assertEqual(set(header), set(common.AGENT_SESSION_CSV_HEADER))


class CheckRegistryCliTests(unittest.TestCase):
    """--check-registry end to end: load_registry_watchlist() is mocked so
    no real Drive access happens, but main()'s actual wiring (call the
    loader, pass its result into validate_agent_session_row, refuse on a
    hit) is exercised for real. Only placeholder names appear here."""

    def _run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        argv_backup = sys.argv
        try:
            sys.argv = ["record_agent_session.py"] + argv
            out_buf, err_buf = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
                rc = record.main()
        finally:
            sys.argv = argv_backup
        return rc, out_buf.getvalue(), err_buf.getvalue()

    def test_check_registry_blocks_a_known_watchlist_match(self):
        with TemporaryDirectory() as td:
            session_csv = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", session_csv), \
                 mock.patch.object(record, "load_registry_watchlist",
                                    return_value=({"Example Placeholder Person"}, [])):
                rc, _out, err = self._run_cli([
                    "--runtime", "manual", "--session-id", "fake", "--manual",
                    "--actual-input-tokens", "10", "--actual-output-tokens", "5",
                    "--confidence", "manual",
                    "--objective", "processed a source about Example Placeholder Person",
                    "--check-registry", "--append-csv",
                ])
            self.assertNotEqual(rc, 0)
            self.assertIn("Example Placeholder Person", err)
            self.assertFalse(session_csv.exists())

    def test_without_flag_registry_loader_is_never_called(self):
        with TemporaryDirectory() as td:
            session_csv = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", session_csv), \
                 mock.patch.object(record, "load_registry_watchlist",
                                    side_effect=AssertionError("must not be called without --check-registry")):
                rc, _out, _err = self._run_cli([
                    "--runtime", "manual", "--session-id", "fake", "--manual",
                    "--actual-input-tokens", "10", "--actual-output-tokens", "5",
                    "--confidence", "manual",
                    "--objective", "processed a source about Example Placeholder Person",
                    "--append-csv",
                ])
            self.assertEqual(rc, 0)
            self.assertTrue(session_csv.exists())

    def test_check_registry_degrades_to_warning_when_load_fails(self):
        with TemporaryDirectory() as td:
            session_csv = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", session_csv), \
                 mock.patch.object(record, "load_registry_watchlist",
                                    return_value=(set(), ["Could not load the real-name/project "
                                                          "registry watch-list (fake failure)"])):
                rc, _out, err = self._run_cli([
                    "--runtime", "manual", "--session-id", "fake", "--manual",
                    "--actual-input-tokens", "10", "--actual-output-tokens", "5",
                    "--confidence", "manual",
                    "--objective", "fake objective, nothing sensitive here",
                    "--check-registry", "--append-csv",
                ])
            self.assertEqual(rc, 0)
            self.assertIn("Could not load", err)
            self.assertTrue(session_csv.exists())

    def test_email_in_objective_is_always_blocked_even_without_flag(self):
        with TemporaryDirectory() as td:
            session_csv = Path(td) / "agent-sessions.csv"
            with mock.patch.object(common, "AGENT_SESSION_CSV_PATH", session_csv):
                rc, _out, err = self._run_cli([
                    "--runtime", "manual", "--session-id", "fake", "--manual",
                    "--actual-input-tokens", "10", "--actual-output-tokens", "5",
                    "--confidence", "manual",
                    "--objective", "contact fake.person@example.com about this",
                    "--append-csv",
                ])
            self.assertNotEqual(rc, 0)
            self.assertIn("email address", err)
            self.assertFalse(session_csv.exists())


# ---------------------------------------------------------------------------
# Docs: no-queue passes must point at agent-sessions.csv, not
# completed_run_review (which requires a run_id they don't have).
# ---------------------------------------------------------------------------

class NoQueuePassDocsTests(unittest.TestCase):
    REPO_ROOT = Path(__file__).resolve().parents[2]

    def test_agents_md_distinguishes_queue_vs_no_queue_closing_step(self):
        text = (self.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("No-queue direct-note/conversational rollup passes are different", text)
        self.assertIn("record_agent_session.py", text)
        self.assertIn("completed_run_review", text)

    def test_telemetry_readme_distinguishes_queue_vs_no_queue_closing_step(self):
        text = (self.REPO_ROOT / ".agents" / "telemetry" / "README.md").read_text(encoding="utf-8")
        self.assertIn("No-queue direct-note or conversational rollup pass", text)
        self.assertIn("record_agent_session.py", text)
        self.assertIn("completed_run_review", text)
        self.assertIn("optional and only measures", text)


if __name__ == "__main__":
    unittest.main()
