#!/usr/bin/env python3
"""Unit tests for closeout_telemetry.py - the one-command wrapper around the
completed_run_review / record_agent_session / record_task_outcome / six-
validator / commit sequence.

Every underlying script call goes through the single `run_subprocess`
chokepoint, so these tests mock that one function (never the real
subprocess/Drive/git calls) - fast, deterministic, and no network/API
dependency.
"""

from __future__ import annotations

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

import closeout_telemetry as closeout


RUN_ID = "20260723-example-run-abc123"
SESSION_ID = "11111111-2222-3333-4444-555555555555"


def _proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def _completed_review_envelope(status: str = "completed") -> str:
    return json.dumps({"schema_version": 1, "ok": True, "command": "review",
                       "data": {"run_id": RUN_ID, "status": status}, "warnings": [], "errors": []})


def _default_side_effect(validators_ok: bool = True):
    """A run_subprocess side_effect covering the happy path: run completed,
    all three telemetry rows created, all six validators pass."""

    def side_effect(argv: list[str]) -> subprocess.CompletedProcess:
        joined = " ".join(argv)
        if "qa_manage.py" in joined and "review" in joined:
            return _proc(0, stdout=_completed_review_envelope())
        if "measure_operator_outputs.py" in joined:
            row = {"run_id": "completed_run_review-2026-07-23-aaaa1111", "status": "ok"}
            return _proc(0, stdout=json.dumps(row) + "\nAppended row to .agents/telemetry/operator-runs.csv\n")
        if "record_agent_session.py" in joined:
            return _proc(0, stdout="Appended row for session_run_id=session-claude-task-2026-07-23-bbbb2222 "
                                   "to .agents/telemetry/agent-sessions.csv\n"
                                   "Diff guard OK: only the new row was added.\n")
        if "record_task_outcome.py" in joined:
            return _proc(0, stdout="Appended row for task_outcome_id=outcome-intake-2026-07-23-cccc3333 "
                                   "to [...]\nDiff guard OK: only the new task-outcome row was added.\n")
        if "git" in joined and "status" in joined and "--porcelain" in joined:
            return _proc(0, stdout=" M .agents/telemetry/operator-runs.csv\n"
                                   " M .agents/telemetry/agent-sessions.csv\n"
                                   " M .agents/telemetry/task-outcomes.csv\n")
        if "git" in joined and "add" in joined:
            return _proc(0)
        if "git" in joined and "commit" in joined:
            return _proc(0, stdout="[main abc1234] telemetry: closeout\n")
        if "git" in joined and "rev-parse" in joined:
            return _proc(0, stdout="abc1234567890abc1234567890abc1234567890\n")
        if "check_operator_csv.py" in joined or "check_sensitive_data.py" in joined \
                or "summarize_agent_telemetry.py" in joined:
            return _proc(0 if validators_ok else 1, stdout="ok\n" if validators_ok else "FAIL\n")
        if "git" in joined and "diff" in joined and "--check" in joined:
            return _proc(0 if validators_ok else 1)
        raise AssertionError(f"Unexpected run_subprocess call: {argv!r}")

    return side_effect


class TestParseJsonPrefix(unittest.TestCase):
    def test_parses_json_ignoring_trailing_text(self):
        text = json.dumps({"a": 1}) + "\nAppended row to somewhere\n"
        self.assertEqual(closeout.parse_json_prefix(text), {"a": 1})

    def test_returns_none_for_non_json_text(self):
        self.assertIsNone(closeout.parse_json_prefix("Appended row for session_run_id=x\n"))


class TestCheckRunCompleted(unittest.TestCase):
    def test_passes_for_completed_run(self):
        with mock.patch.object(closeout, "run_subprocess",
                               return_value=_proc(0, stdout=_completed_review_envelope())):
            closeout.check_run_completed(RUN_ID)  # should not raise

    def test_raises_for_non_completed_run(self):
        with mock.patch.object(closeout, "run_subprocess",
                               return_value=_proc(0, stdout=_completed_review_envelope(status="ready"))):
            with self.assertRaises(closeout.CloseoutError) as ctx:
                closeout.check_run_completed(RUN_ID)
        self.assertIn("not completed", str(ctx.exception))

    def test_raises_when_review_reports_error(self):
        envelope = json.dumps({"ok": False, "errors": ["No queue row with Run ID"]})
        with mock.patch.object(closeout, "run_subprocess", return_value=_proc(0, stdout=envelope)):
            with self.assertRaises(closeout.CloseoutError):
                closeout.check_run_completed(RUN_ID)


class TestStepAgentSessionWindowing(unittest.TestCase):
    def test_claude_runtime_passes_from_run(self):
        captured = {}

        def side_effect(argv):
            captured["argv"] = argv
            return _proc(0, stdout="Appended row for session_run_id=session-claude-task-2026-07-23-x "
                                   "to file\n")

        with mock.patch.object(closeout, "run_subprocess", side_effect=side_effect):
            session_run_id, warnings = closeout.step_agent_session(RUN_ID, "claude", SESSION_ID, "")
        self.assertIn("--from-run", captured["argv"])
        self.assertEqual(session_run_id, "session-claude-task-2026-07-23-x")
        self.assertEqual(warnings, [])

    def test_non_claude_runtime_falls_back_to_whole_session_with_warning(self):
        captured = {}

        def side_effect(argv):
            captured["argv"] = argv
            return _proc(0, stdout="Appended row for session_run_id=session-antigravity-2026-07-23-y "
                                   "to file\n")

        with mock.patch.object(closeout, "run_subprocess", side_effect=side_effect):
            session_run_id, warnings = closeout.step_agent_session(RUN_ID, "antigravity", SESSION_ID, "")
        self.assertNotIn("--from-run", captured["argv"])
        self.assertEqual(session_run_id, "session-antigravity-2026-07-23-y")
        self.assertEqual(len(warnings), 1)
        self.assertIn("whole-session", warnings[0].lower())
        self.assertIn("not scoped", warnings[0].lower())


class TestFullCloseoutHappyPath(unittest.TestCase):
    def test_creates_all_three_rows_and_reports_validators(self):
        with mock.patch.object(closeout, "run_subprocess", side_effect=_default_side_effect()), \
             mock.patch("sys.argv", ["closeout_telemetry.py", "--run-id", RUN_ID, "--runtime", "claude",
                                      "--session-id", SESSION_ID, "--json"]), \
             mock.patch("builtins.print") as mock_print:
            rc = closeout.main()
        self.assertEqual(rc, 0)
        printed = json.loads(mock_print.call_args[0][0])
        self.assertEqual(printed["operator_run_id"], "completed_run_review-2026-07-23-aaaa1111")
        self.assertEqual(printed["session_run_id"], "session-claude-task-2026-07-23-bbbb2222")
        self.assertEqual(printed["task_outcome_id"], "outcome-intake-2026-07-23-cccc3333")
        self.assertTrue(printed["validators_ok"])
        self.assertEqual(len(printed["validators"]), 6)
        self.assertFalse(printed["committed"])
        self.assertIsNone(printed["commit_sha"])
        self.assertTrue(printed["next_command"])
        self.assertEqual(printed["changed_telemetry_files"],
                         [".agents/telemetry/operator-runs.csv",
                          ".agents/telemetry/agent-sessions.csv",
                          ".agents/telemetry/task-outcomes.csv"])


class TestRefusesNonCompletedRun(unittest.TestCase):
    def test_no_writes_attempted_for_incomplete_run(self):
        calls = []

        def side_effect(argv):
            calls.append(argv)
            joined = " ".join(argv)
            if "qa_manage.py" in joined and "review" in joined:
                return _proc(0, stdout=_completed_review_envelope(status="processing"))
            raise AssertionError(f"Should not have called: {argv!r}")

        with mock.patch.object(closeout, "run_subprocess", side_effect=side_effect), \
             mock.patch("sys.argv", ["closeout_telemetry.py", "--run-id", RUN_ID, "--runtime", "claude",
                                      "--session-id", SESSION_ID, "--json"]), \
             mock.patch("builtins.print") as mock_print:
            rc = closeout.main()
        self.assertEqual(rc, 1)
        printed = json.loads(mock_print.call_args[0][0])
        self.assertFalse(printed["ok"])
        self.assertTrue(printed["errors"])
        self.assertIsNone(printed["operator_run_id"])
        # Only the one review call - no measure/record/validator calls at all.
        self.assertEqual(len(calls), 1)


class TestCommitBehavior(unittest.TestCase):
    def test_commit_stages_only_telemetry_files(self):
        add_calls = []

        def side_effect(argv):
            joined = " ".join(argv)
            if "git" in joined and argv[1:2] == ["add"]:
                add_calls.append(argv)
                return _proc(0)
            return _default_side_effect()(argv)

        with mock.patch.object(closeout, "run_subprocess", side_effect=side_effect), \
             mock.patch("sys.argv", ["closeout_telemetry.py", "--run-id", RUN_ID, "--runtime", "claude",
                                      "--session-id", SESSION_ID, "--commit", "--json"]), \
             mock.patch("builtins.print") as mock_print:
            rc = closeout.main()
        self.assertEqual(rc, 0)
        printed = json.loads(mock_print.call_args[0][0])
        self.assertTrue(printed["committed"])
        self.assertEqual(printed["commit_sha"], "abc1234567890abc1234567890abc1234567890")
        self.assertEqual(len(add_calls), 1)
        staged = add_calls[0][2:]
        self.assertEqual(set(staged), {
            ".agents/telemetry/operator-runs.csv",
            ".agents/telemetry/agent-sessions.csv",
            ".agents/telemetry/task-outcomes.csv",
        })

    def test_refuses_commit_when_a_validator_fails(self):
        commit_calls = []

        def side_effect(argv):
            joined = " ".join(argv)
            if "git" in joined and argv[1:2] == ["commit"]:
                commit_calls.append(argv)
                return _proc(0)
            return _default_side_effect(validators_ok=False)(argv)

        with mock.patch.object(closeout, "run_subprocess", side_effect=side_effect), \
             mock.patch("sys.argv", ["closeout_telemetry.py", "--run-id", RUN_ID, "--runtime", "claude",
                                      "--session-id", SESSION_ID, "--commit", "--json"]), \
             mock.patch("builtins.print") as mock_print:
            rc = closeout.main()
        self.assertEqual(rc, 1)
        printed = json.loads(mock_print.call_args[0][0])
        self.assertFalse(printed["committed"])
        self.assertIsNone(printed["commit_sha"])
        self.assertTrue(any("validator" in e.lower() for e in printed["errors"]))
        self.assertEqual(commit_calls, [])

    def test_no_commit_reports_next_command_when_flag_omitted(self):
        with mock.patch.object(closeout, "run_subprocess", side_effect=_default_side_effect()), \
             mock.patch("sys.argv", ["closeout_telemetry.py", "--run-id", RUN_ID, "--runtime", "claude",
                                      "--session-id", SESSION_ID, "--json"]), \
             mock.patch("builtins.print") as mock_print:
            rc = closeout.main()
        self.assertEqual(rc, 0)
        printed = json.loads(mock_print.call_args[0][0])
        self.assertFalse(printed["committed"])
        self.assertIn("git add", printed["next_command"])
        self.assertIn("git commit", printed["next_command"])


class TestPartialFailureReporting(unittest.TestCase):
    def test_step_failure_reports_earlier_created_rows(self):
        def side_effect(argv):
            joined = " ".join(argv)
            if "qa_manage.py" in joined and "review" in joined:
                return _proc(0, stdout=_completed_review_envelope())
            if "measure_operator_outputs.py" in joined:
                row = {"run_id": "completed_run_review-2026-07-23-aaaa1111", "status": "ok"}
                return _proc(0, stdout=json.dumps(row) + "\n")
            if "record_agent_session.py" in joined:
                return _proc(1, stdout="", stderr="boom: something went wrong")
            raise AssertionError(f"Should not reach: {argv!r}")

        with mock.patch.object(closeout, "run_subprocess", side_effect=side_effect), \
             mock.patch("sys.argv", ["closeout_telemetry.py", "--run-id", RUN_ID, "--runtime", "claude",
                                      "--session-id", SESSION_ID, "--json"]), \
             mock.patch("builtins.print") as mock_print:
            rc = closeout.main()
        self.assertEqual(rc, 1)
        printed = json.loads(mock_print.call_args[0][0])
        self.assertEqual(printed["operator_run_id"], "completed_run_review-2026-07-23-aaaa1111")
        self.assertIsNone(printed["session_run_id"])
        self.assertIsNone(printed["task_outcome_id"])
        self.assertTrue(printed["errors"])


class TestJsonEnvelopeIsStrict(unittest.TestCase):
    """Every path through main() must produce the same top-level key set -
    a caller parsing --json output should never need to branch on which
    keys exist."""

    EXPECTED_KEYS = {
        "ok", "run_id", "runtime", "operator_run_id", "session_run_id", "task_outcome_id",
        "warnings", "errors", "validators", "validators_ok", "changed_telemetry_files",
        "committed", "commit_sha", "next_command",
    }

    def _run_and_get_envelope(self, side_effect, argv_extra=()) -> dict:
        with mock.patch.object(closeout, "run_subprocess", side_effect=side_effect), \
             mock.patch("sys.argv", ["closeout_telemetry.py", "--run-id", RUN_ID, "--runtime", "claude",
                                      "--session-id", SESSION_ID, "--json"] + list(argv_extra)), \
             mock.patch("builtins.print") as mock_print:
            closeout.main()
        return json.loads(mock_print.call_args[0][0])

    def test_happy_path_envelope_keys(self):
        envelope = self._run_and_get_envelope(_default_side_effect())
        self.assertEqual(set(envelope.keys()), self.EXPECTED_KEYS)

    def test_refused_early_envelope_keys(self):
        def side_effect(argv):
            return _proc(0, stdout=_completed_review_envelope(status="discovered"))
        envelope = self._run_and_get_envelope(side_effect)
        self.assertEqual(set(envelope.keys()), self.EXPECTED_KEYS)

    def test_step_failure_envelope_keys(self):
        def side_effect(argv):
            joined = " ".join(argv)
            if "qa_manage.py" in joined and "review" in joined:
                return _proc(0, stdout=_completed_review_envelope())
            return _proc(1, stdout="", stderr="boom")
        envelope = self._run_and_get_envelope(side_effect)
        self.assertEqual(set(envelope.keys()), self.EXPECTED_KEYS)


if __name__ == "__main__":
    unittest.main()
