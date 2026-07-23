"""Unit tests for the ported multi-runtime agent telemetry extractor
(extract_agent_telemetry.py) and its finalize_operator_run.py integration.

Ported from the erp-web-tests benchmark-playwright-debugging skill's
scripts/extract_telemetry.py (Claude/Codex/Cline/Antigravity adapters),
re-normalized to QA-management's own CSV field names
(operator_telemetry_common.CSV_HEADER's actual_* keys).

No real names/projects, no real session logs, no real API keys anywhere in
this file - every log/DB/CLI response is a fake fixture built in a temp
directory or mocked in-process.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import struct
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import extract_agent_telemetry as ext  # noqa: E402
import finalize_operator_run as finalize  # noqa: E402


# ---------------------------------------------------------------------------
# ClaudeAdapter - existing behavior must still work
# ---------------------------------------------------------------------------

class ClaudeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.home = Path(self.td.name)
        self.projects_dir = self.home / ".claude" / "projects" / "fake-project-hash"
        self.projects_dir.mkdir(parents=True)

    def tearDown(self):
        self.td.cleanup()

    def _write_session(self, session_id: str, entries: list[dict]) -> None:
        log = self.projects_dir / f"{session_id}.jsonl"
        log.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

    def test_sums_usage_across_assistant_turns(self):
        session_id = "fake-session-1"
        self._write_session(session_id, [
            {"type": "user", "message": {"content": "hi"}},
            {"type": "assistant", "message": {"model": "claude-sonnet-5", "usage": {
                "input_tokens": 100, "output_tokens": 20,
                "cache_creation_input_tokens": 5, "cache_read_input_tokens": 2}}},
            {"type": "assistant", "message": {"model": "claude-sonnet-5", "usage": {
                "input_tokens": 50, "output_tokens": 10,
                "cache_creation_input_tokens": 0, "cache_read_input_tokens": 8}}},
        ])
        totals = ext.ClaudeAdapter().extract(session_id, home=self.home)
        self.assertEqual(totals["actual_input_tokens"], 150)
        self.assertEqual(totals["actual_output_tokens"], 30)
        self.assertEqual(totals["actual_cache_creation_tokens"], 5)
        self.assertEqual(totals["actual_cache_read_tokens"], 10)
        self.assertEqual(totals["model_label"], "claude-sonnet-5")

    def test_missing_projects_dir_raises_file_not_found(self):
        empty_home = Path(self.td.name) / "no-claude-here"
        with self.assertRaises(FileNotFoundError):
            ext.ClaudeAdapter().extract("whatever", home=empty_home)

    def test_no_assistant_usage_entries_raises_value_error(self):
        session_id = "fake-session-empty"
        self._write_session(session_id, [{"type": "user", "message": {"content": "hi"}}])
        with self.assertRaises(ValueError):
            ext.ClaudeAdapter().extract(session_id, home=self.home)


# ---------------------------------------------------------------------------
# CodexAdapter
# ---------------------------------------------------------------------------

class CodexAdapterTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.home = Path(self.td.name)
        self.date_dir = self.home / ".codex" / "sessions" / "2026" / "07" / "22"
        self.date_dir.mkdir(parents=True)

    def tearDown(self):
        self.td.cleanup()

    def _token_count_event(self, input_tokens, output_tokens, cached, reasoning):
        return {
            "type": "event_msg",
            "payload": {"type": "token_count", "info": {"total_token_usage": {
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "cached_input_tokens": cached, "reasoning_output_tokens": reasoning,
            }}},
        }

    def test_single_file_uses_last_token_count_event(self):
        session_id = "aaaaaaaa-1111-2222-3333-444444444444"
        log = self.date_dir / f"rollout-2026-07-22T10-00-00-{session_id}.jsonl"
        events = [
            self._token_count_event(10, 5, 0, 0),
            self._token_count_event(100, 50, 20, 8),  # last one wins
        ]
        log.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

        totals = ext.CodexAdapter().extract(session_id, home=self.home)
        self.assertEqual(totals["actual_input_tokens"], 100)
        self.assertEqual(totals["actual_output_tokens"], 50)
        self.assertEqual(totals["actual_cache_read_tokens"], 20)
        self.assertEqual(totals["actual_reasoning_tokens"], 8)
        self.assertEqual(totals["actual_cache_creation_tokens"], 0)

    def test_continuation_file_via_session_meta_is_summed(self):
        main_session_id = "bbbbbbbb-1111-2222-3333-444444444444"
        continuation_id = "cccccccc-1111-2222-3333-444444444444"

        main_log = self.date_dir / f"rollout-2026-07-22T10-00-00-{main_session_id}.jsonl"
        main_log.write_text("\n".join(json.dumps(e) for e in [
            self._token_count_event(100, 50, 20, 8),
        ]) + "\n", encoding="utf-8")

        # Continuation file: different filename UUID, but its session_meta
        # payload links it back to the main session_id.
        continuation_log = self.date_dir / f"rollout-2026-07-22T10-05-00-{continuation_id}.jsonl"
        continuation_events = [
            {"type": "event_msg", "payload": {"session_id": main_session_id}},
            self._token_count_event(30, 15, 0, 2),
        ]
        continuation_log.write_text(
            "\n".join(json.dumps(e) for e in continuation_events) + "\n", encoding="utf-8")

        totals = ext.CodexAdapter().extract(main_session_id, home=self.home)
        self.assertEqual(totals["actual_input_tokens"], 130)
        self.assertEqual(totals["actual_output_tokens"], 65)
        self.assertEqual(totals["actual_reasoning_tokens"], 10)

    def test_no_matching_files_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            ext.CodexAdapter().extract("does-not-exist-uuid", home=self.home)

    def test_files_with_no_token_count_events_raises_value_error(self):
        session_id = "dddddddd-1111-2222-3333-444444444444"
        log = self.date_dir / f"rollout-2026-07-22T10-00-00-{session_id}.jsonl"
        log.write_text(json.dumps({"type": "event_msg", "payload": {"type": "other"}}) + "\n",
                       encoding="utf-8")
        with self.assertRaises(ValueError):
            ext.CodexAdapter().extract(session_id, home=self.home)


# ---------------------------------------------------------------------------
# ClineAdapter
# ---------------------------------------------------------------------------

class ClineAdapterTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.appdata = Path(self.td.name) / "AppData" / "Roaming"
        self.state_dir = (self.appdata / "Code" / "User" / "globalStorage"
                         / "saoudrizwan.claude-dev" / "state")
        self.state_dir.mkdir(parents=True)

    def tearDown(self):
        self.td.cleanup()

    def test_extracts_matching_task_by_id(self):
        history = [
            {"id": 111, "tokensIn": 10, "tokensOut": 5, "cacheWrites": 1, "cacheReads": 2,
             "totalCost": 0.0123, "modelId": "fake-model-x"},
            {"id": 222, "tokensIn": 100, "tokensOut": 50, "cacheWrites": 0, "cacheReads": 0,
             "totalCost": 0.5, "modelId": "fake-model-y"},
        ]
        (self.state_dir / "taskHistory.json").write_text(json.dumps(history), encoding="utf-8")

        totals = ext.ClineAdapter().extract("222", appdata=str(self.appdata))
        self.assertEqual(totals["actual_input_tokens"], 100)
        self.assertEqual(totals["actual_output_tokens"], 50)
        self.assertEqual(totals["model_label"], "fake-model-y")
        self.assertEqual(totals["estimated_cost_usd"], "0.500000")

    def test_missing_history_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            ext.ClineAdapter().extract("111", appdata=str(Path(self.td.name) / "nope"))

    def test_unknown_task_id_raises_value_error(self):
        (self.state_dir / "taskHistory.json").write_text(json.dumps([{"id": 1}]), encoding="utf-8")
        with self.assertRaises(ValueError):
            ext.ClineAdapter().extract("999", appdata=str(self.appdata))


# ---------------------------------------------------------------------------
# AntigravityAdapter
# ---------------------------------------------------------------------------

def _encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _encode_field(field_num: int, value: int) -> bytes:
    tag = (field_num << 3) | 0  # wire type 0 = varint
    return _encode_varint(tag) + _encode_varint(value)


def _fake_usage_blob(uncached=100, output=40, cached=10, thinking=5) -> bytes:
    # Fields 1 (arbitrary presence), 2 (uncached input), 3 (output),
    # 5 (cached input), 10 (thinking/reasoning) - matches
    # AntigravityAdapter._try_db's find_usage_submessage()/field mapping.
    return (
        _encode_field(1, 1)
        + _encode_field(2, uncached)
        + _encode_field(3, output)
        + _encode_field(5, cached)
        + _encode_field(10, thinking)
    )


class AntigravityAdapterTests(unittest.TestCase):
    def setUp(self):
        self.td = TemporaryDirectory()
        self.home = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_agy_cli_success(self):
        fake_result = mock.Mock(returncode=0, stdout=json.dumps({
            "usage_metadata": {
                "prompt_token_count": 200, "candidates_token_count": 80,
                "cached_content_token_count": 30, "thinking_token_count": 12,
            }
        }))
        with mock.patch.object(ext.subprocess, "run", return_value=fake_result) as run_mock:
            totals = ext.AntigravityAdapter().extract("session-x", home=self.home)
        run_mock.assert_called_once()
        self.assertEqual(totals["actual_input_tokens"], 200)
        self.assertEqual(totals["actual_output_tokens"], 80)
        self.assertEqual(totals["actual_cache_read_tokens"], 30)
        self.assertEqual(totals["actual_reasoning_tokens"], 12)
        self.assertEqual(totals["actual_cache_creation_tokens"], 0)

    def test_cli_unavailable_falls_back_to_db(self):
        conv_dir = self.home / ".gemini" / "antigravity" / "conversations"
        conv_dir.mkdir(parents=True)
        db_path = conv_dir / "session-y.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE steps (idx INTEGER, metadata BLOB, step_payload BLOB)")
        conn.execute("INSERT INTO steps VALUES (?, ?, ?)",
                    (0, _fake_usage_blob(uncached=100, output=40, cached=10, thinking=5), None))
        conn.commit()
        conn.close()

        with mock.patch.object(ext.subprocess, "run", side_effect=FileNotFoundError("no agy")):
            totals = ext.AntigravityAdapter().extract("session-y", home=self.home)

        self.assertEqual(totals["actual_input_tokens"], 100)  # uncached only
        self.assertEqual(totals["actual_output_tokens"], 40)
        self.assertEqual(totals["actual_cache_read_tokens"], 10)
        self.assertEqual(totals["actual_reasoning_tokens"], 5)

    def test_neither_source_available_raises_clear_runtime_error(self):
        with mock.patch.object(ext.subprocess, "run", side_effect=FileNotFoundError("no agy")):
            with self.assertRaises(RuntimeError) as ctx:
                ext.AntigravityAdapter().extract("session-z", home=self.home)
        message = str(ctx.exception)
        self.assertIn("session-z", message)
        self.assertIn("--telemetry-json", message)
        self.assertIn("manual", message.lower())


# ---------------------------------------------------------------------------
# Router / CLI-level behavior
# ---------------------------------------------------------------------------

class RouterTests(unittest.TestCase):
    def test_unknown_runtime_raises_value_error(self):
        with self.assertRaises(ValueError):
            ext.extract("some-unknown-runtime", "id")

    def test_runtime_aliases_resolve_to_claude_adapter(self):
        self.assertIs(ext.ADAPTERS["claude"].__class__, ext.ClaudeAdapter)
        self.assertIs(ext.ADAPTERS["claude-code"].__class__, ext.ClaudeAdapter)
        self.assertIs(ext.ADAPTERS["claudecode"].__class__, ext.ClaudeAdapter)

    def test_cli_help_lists_all_runtimes(self):
        import subprocess as sp
        res = sp.run([sys.executable, str(SCRIPTS / "extract_agent_telemetry.py"), "--help"],
                    capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        for runtime in ("claude", "codex", "cline", "antigravity"):
            self.assertIn(runtime, res.stdout)

    def test_out_path_only_ever_written_under_tmp_in_this_repos_own_usage(self):
        # Not a hard technical restriction (the script writes wherever --out
        # points), but the documented convention is tmp/telemetry/ only -
        # assert the module docstring says so, so the guidance can't drift
        # silently out of the help text.
        self.assertIn("tmp/telemetry", ext.__doc__)


# ---------------------------------------------------------------------------
# finalize_operator_run.py --telemetry-json merge
# ---------------------------------------------------------------------------

class FinalizeTelemetryMergeTests(unittest.TestCase):
    def _run_dry_run(self, row: dict, telemetry: dict) -> dict:
        with TemporaryDirectory() as td:
            row_path = Path(td) / "row.json"
            telemetry_path = Path(td) / "telemetry.json"
            row_path.write_text(json.dumps(row), encoding="utf-8")
            telemetry_path.write_text(json.dumps(telemetry), encoding="utf-8")

            argv_backup = sys.argv
            try:
                sys.argv = ["finalize_operator_run.py", "--from-json", str(row_path),
                           "--telemetry-json", str(telemetry_path), "--dry-run"]
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = finalize.main()
            finally:
                sys.argv = argv_backup
            self.assertEqual(rc, 0)
            printed = buf.getvalue().split("[dry-run]")[0]
            return json.loads(printed)

    def _base_row(self) -> dict:
        import operator_telemetry_common as common
        row = {k: "" for k in common.CSV_HEADER}
        row.update({
            "case_id": "dashboard_overview", "run_id": "run-merge-1", "date": "2026-01-01",
            "runtime": "codex", "command_name": "qa_manage.py dashboard",
            "command_args_redacted": "qa_manage.py dashboard --json", "json_mode": "yes",
            "status": "ok", "elapsed_ms": "100", "stdout_bytes": "500", "stderr_bytes": "0",
            "output_chars": "480", "truncated": "no",
        })
        return row

    def test_actual_token_fields_merged_from_telemetry_json(self):
        merged = self._run_dry_run(self._base_row(), {
            "actual_input_tokens": 111, "actual_output_tokens": 22,
            "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 3,
            "actual_reasoning_tokens": 7,
        })
        self.assertEqual(merged["actual_input_tokens"], 111)
        self.assertEqual(merged["actual_output_tokens"], 22)
        self.assertEqual(merged["actual_reasoning_tokens"], 7)
        self.assertEqual(merged["total_tokens"], "143")

    def test_model_label_merged_only_when_row_lacks_one(self):
        row = self._base_row()
        row["model_label"] = "already-set"
        merged = self._run_dry_run(row, {"model_label": "from-telemetry"})
        self.assertEqual(merged["model_label"], "already-set")

        merged2 = self._run_dry_run(self._base_row(), {"model_label": "from-telemetry"})
        self.assertEqual(merged2["model_label"], "from-telemetry")

    def test_directly_reported_cost_merged_without_recomputation(self):
        merged = self._run_dry_run(self._base_row(), {
            "actual_input_tokens": 100, "actual_output_tokens": 50,
            "estimated_cost_usd": "0.123456",
        })
        # A telemetry-reported cost (e.g. Cline's own totalCost) is trusted
        # as-is, not overwritten by the pricing-table estimate step.
        self.assertEqual(merged["estimated_cost_usd"], "0.123456")

    def test_unknown_model_label_yields_blank_cost_not_failure(self):
        merged = self._run_dry_run(self._base_row(), {
            "actual_input_tokens": 100, "actual_output_tokens": 50,
            "model_label": "some-totally-unknown-model",
        })
        self.assertEqual(merged.get("estimated_cost_usd", ""), "")


class NoRawLogLeakageTests(unittest.TestCase):
    """The extractor must only ever write small numeric-summary JSON to
    --out, never raw log lines/session content."""

    def test_out_file_contains_only_known_numeric_keys(self):
        totals = {"actual_input_tokens": 10, "actual_output_tokens": 5,
                  "actual_cache_creation_tokens": 0, "actual_cache_read_tokens": 0,
                  "actual_reasoning_tokens": 0}
        with TemporaryDirectory() as td:
            out_path = Path(td) / "telemetry.json"
            argv_backup = sys.argv
            try:
                with mock.patch.object(ext, "extract", return_value=totals):
                    sys.argv = ["extract_agent_telemetry.py", "--runtime", "claude",
                               "--session-id", "fake-session", "--out", str(out_path)]
                    rc = ext.main()
            finally:
                sys.argv = argv_backup
            self.assertEqual(rc, 0)
            written = json.loads(out_path.read_text(encoding="utf-8"))
            allowed_keys = {"actual_input_tokens", "actual_output_tokens",
                           "actual_cache_creation_tokens", "actual_cache_read_tokens",
                           "actual_reasoning_tokens", "model_label", "estimated_cost_usd",
                           "extraction_method", "session_started_at", "session_ended_at"}
            self.assertTrue(set(written) <= allowed_keys)

    def test_real_claude_adapter_output_contains_only_known_keys(self):
        # Same check, but against a REAL adapter (fake log fixture), not a
        # hand-built totals dict - proves the actual production code path
        # never emits an unexpected key either.
        with TemporaryDirectory() as td:
            home = Path(td)
            projects_dir = home / ".claude" / "projects" / "fake-hash"
            projects_dir.mkdir(parents=True)
            session_id = "real-adapter-check"
            (projects_dir / f"{session_id}.jsonl").write_text(
                json.dumps({"type": "assistant", "timestamp": "2026-01-01T00:00:00.000Z",
                           "message": {"model": "claude-sonnet-5",
                                       "usage": {"input_tokens": 1, "output_tokens": 1}}}) + "\n",
                encoding="utf-8")
            totals = ext.ClaudeAdapter().extract(session_id, home=home)
            allowed_keys = {"actual_input_tokens", "actual_output_tokens",
                           "actual_cache_creation_tokens", "actual_cache_read_tokens",
                           "actual_reasoning_tokens", "model_label", "estimated_cost_usd",
                           "extraction_method", "session_started_at", "session_ended_at"}
            self.assertTrue(set(totals) <= allowed_keys)


if __name__ == "__main__":
    unittest.main()
